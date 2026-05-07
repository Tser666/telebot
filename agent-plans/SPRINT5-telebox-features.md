# Sprint 5 Plan — TeleBox 借鉴特性引入

## Context

用户分析了 TeleBox (TypeScript userbot) 的架构后，希望将以下 5 个设计引入本项目：

1. **Conversation 封装**（优先）— 与其他 Bot 交互的工具类
2. **命令别名系统**（优先）— 多词别名 + 贪心匹配 + 参数透传
3. **Generation Guard** — 热重载时防止旧 handler 执行的竞态保护
4. **Sudo 消息代发** — 让授权用户也能触发命令（严格控权）
5. **多词别名贪心匹配** — 已合并到第 2 点

实际交付 4 个功能模块，按优先级排序：
- P0: Conversation 封装（插件与其他 Bot 交互）
- P0: 命令别名（多词贪心匹配 + 参数透传）
- P1: Generation Guard（插件热重载竞态保护）
- P1: Sudo 消息代发（授权用户触发命令）

---

## 模块 1: Conversation 封装（P0）

### 目标
提供一个 `Conversation` 工具类，让插件能方便地与其他 Bot 进行"发消息 → 等回复 → 点按钮"的交互流程。

### 文件白名单
- `backend/app/worker/conversation.py`（新建）
- `backend/app/worker/__init__.py`（追加 export）
- `backend/app/worker/plugins/base.py`（PluginContext 追加 conversation 工厂方法）
- `backend/app/tests/test_conversation.py`（新建）

### 实现要点
```python
# conversation.py 核心 API
class Conversation:
    def __init__(self, client: TelegramClient, peer: EntityLike, timeout: float = 30.0): ...
    async def send(self, message: str, **kwargs) -> Message: ...
    async def get_response(self, timeout: float | None = None) -> Message: ...
    async def click_button(self, message: Message, row: int, col: int) -> None: ...
    async def mark_read(self) -> None: ...
    async def close(self) -> None: ...

# 上下文管理器用法
async with conversation(ctx.client, "@BotFather") as conv:
    await conv.send("/newbot")
    resp = await conv.get_response()
    ...
```

- 用一次性 `NewMessage` event handler + asyncio.Event 实现等待
- handler 注册后在收到匹配消息或超时后自动移除（避免泄漏）
- `PluginContext` 新增 `conversation(peer, timeout=30)` 工厂方法，返回 async context manager
- 超时抛 `ConversationTimeout`；插件可 catch 做降级

---

## 模块 2: 命令别名系统（P0）

### 目标
用户可通过 Web UI 或 TG 内命令创建别名，支持多词别名和参数透传。

### 文件白名单
- `backend/alembic/versions/0016_command_alias.py`（新建迁移）
- `backend/app/db/models/command.py`（追加 `CommandAlias` 模型）
- `backend/app/schemas/command.py`（追加 alias schema）
- `backend/app/services/command_service.py`（追加 alias CRUD）
- `backend/app/api/commands.py`（追加 alias 路由）
- `backend/app/worker/command.py`（修改派发逻辑：别名解析）
- `backend/app/worker/runtime.py`（CommandContext 追加 aliases 字段）
- `frontend/src/api/types.ts`（追加 alias 类型块）
- `backend/app/tests/test_alias.py`（新建）

### 数据模型
```python
class CommandAlias(Base):
    __tablename__ = "command_alias"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias: Mapped[str] = mapped_column(String(64), unique=True)  # 别名（可含空格）
    target: Mapped[str] = mapped_column(String(128))  # 目标命令（可含空格前缀参数）
    account_id: Mapped[int | None]  # None = 全局；有值 = 仅该账号
    created_at: Mapped[datetime]
```

### 派发逻辑（贪心匹配）
```python
# 在 _h handler 中，builtin 匹配失败后、模板匹配前插入：
# 1. 从 ctx.aliases 中按"最长前缀"贪心匹配
# 2. 匹配到后：把 alias 部分替换为 target，剩余 args 拼接
# 3. 用替换后的文本重新走一遍 builtin → template 派发
```

### TG 内命令
新增 builtin 命令 `,alias`：
- `,alias set <别名> <目标命令>` — 创建/更新
- `,alias del <别名>` — 删除
- `,alias ls` — 列出所有

---

## 模块 3: Generation Guard（P1）

### 目标
在插件热重载（`reload_account_config` / `reload_plugin`）时，防止旧插件实例的 handler 继续执行。

### 文件白名单
- `backend/app/worker/plugins/loader.py`（修改）
- `backend/app/worker/plugins/base.py`（PluginContext 追加 generation 字段）

### 实现要点
- `_AccountState` 新增 `generation: int` 字段，初始 1
- 每次 `reload_account_config` / `reload_plugin` 时 `state.generation += 1`
- `PluginContext` 新增 `generation: int` 字段，在 `_activate` 时从 state 拷贝
- 全局消息派发器 `_dispatch` 在调 `inst.on_message` 前检查：
  ```python
  if ctx.generation != state.generation:
      continue  # 旧实例，跳过
  ```
- 这样旧实例的 handler 即使还在 event loop 队列里，也不会执行业务逻辑

---

## 模块 4: Sudo 消息代发（P1）

### 目标
允许账号主人授权特定 TG 用户（sudo users）在指定对话中触发命令。

### 文件白名单
- `backend/alembic/versions/0017_sudo_user.py`（新建迁移）
- `backend/app/db/models/account.py`（追加 `SudoUser` 模型）
- `backend/app/schemas/account.py`（追加 sudo schema）
- `backend/app/api/accounts.py`（追加 sudo 路由）
- `backend/app/worker/command.py`（修改：监听 incoming + sudo 判定 + 代发）
- `backend/app/worker/runtime.py`（CommandContext 追加 sudo_users / sudo_chats）
- `backend/app/worker/ipc.py`（追加 CMD_RELOAD_SUDO）
- `frontend/src/api/types.ts`（追加 sudo 类型块）
- `backend/app/tests/test_sudo.py`（新建）

### 数据模型
```python
class SudoUser(Base):
    __tablename__ = "sudo_user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    tg_user_id: Mapped[int] = mapped_column(BigInteger)
    display_name: Mapped[str | None]
    # 白名单对话（空 = 所有对话均可）
    allowed_chat_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    # 白名单命令（空 = 所有命令均可）
    allowed_commands: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime]
```

### 执行逻辑（借鉴 TeleBox 的代发模式）

sudo 用户使用**可自定义的独立前缀**（默认 `.`，通过 DB 配置，与主人的 `,` 区分）触发命令。

```python
# 在 runtime.py 的 incoming 派发器中（_make_dispatcher("incoming")）：
# 1. 检查 msg.sender_id 是否在 ctx.sudo_users 中
# 2. 检查 msg.chat_id 是否在该 sudo user 的 allowed_chat_ids 中（空=全部允许）
# 3. 用 sudo_prefix 解析命令前缀 + 命令名
# 4. 检查命令是否在 allowed_commands 中（空=全部允许）
# 5. 以 bot 自己的身份发一条相同内容的消息（保留 reply_to）
# 6. 对新消息执行命令派发（msg.edit 编辑的是 bot 自己的消息）
```

sudo_prefix 存储在 `SystemSetting` 表中（key=`sudo_prefix`），默认 `.`；
通过 IPC `reload_global` 热更新到 worker 的 `CommandContext.sudo_prefix`。

### TG 内命令
新增 builtin 命令 `,sudo`：
- `,sudo add <@username|uid>` — 添加（回复消息也可）
- `,sudo del <@username|uid>` — 删除
- `,sudo ls` — 列出
- `,sudo chat add/del/ls` — 管理对话白名单

### 安全约束
- sudo 用户**不能**执行 `,reboot` / `,restart` / `,sudo` 本身（防提权）
- 所有 sudo 触发的命令在 runtime_log 中标记 `triggered_by: sudo_user_id`
- Web UI 提供 sudo 用户管理界面（CRUD + 权限配置）

---

## Alembic 迁移编号分配

| 编号 | 内容 |
|------|------|
| 0016 | command_alias 表 |
| 0017 | sudo_user 表 |

---

## 验收清单

- [ ] `pytest -q` 全绿
- [ ] `pnpm run build` 全绿
- [ ] `ruff check backend/` 全绿
- [ ] `alembic upgrade head` 不报错
- [ ] `alembic heads` 只一个 head
- [ ] Conversation: 插件能 `async with ctx.conversation("@BotFather")` 完成一轮对话
- [ ] Alias: `,alias set fy fy_handler` 后 `,fy zh` 能正确派发
- [ ] Generation Guard: `reload_plugin` 后旧 handler 不再触发
- [ ] Sudo: 授权用户发 `,ping` 后 bot 代发并编辑为 "pong"
- [ ] 浏览器手测：别名管理页 + sudo 管理页能正常 CRUD

---

## 完成报告

（待实现完成后填写）
