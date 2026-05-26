# TelePilot 远程模块

本文保留旧版开发指南中远程模块相关章节的原文内容。

## 10. 远程模块

远程模块与内置模块共用同一套 Plugin API、`Manifest`、`PluginContext`、权限沙箱、配置 schema、模块分类和交互 Bot 声明。区别只在安装来源：远程模块从 Git 仓库安装到 `plugins/installed/{name}/`，安装阶段先静态读取 `plugin.json`，不会执行 Python；运行阶段再由 worker loader 加载 `manifest.py` / `plugin.py`。

旧文档 `docs/REMOTE-PLUGIN-GUIDE.md` 只保留跳转说明，远程模块开发与安装规范以本章节为准。

### 适用场景

远程模块适合这些场景：

- 希望把模块独立成仓库，由 Web UI 一键安装、更新、卸载。
- 模块需要给多个 TelePilot 部署复用。
- 模块作者不想改 TelePilot 主仓库，但愿意遵循统一的 Manifest、权限和配置规范。

当前实现采用：

- Git clone / pull 安装更新。
- `plugin.json` 作为安装阶段静态元数据。
- `manifest.py` 作为运行阶段真实 Manifest。
- `Plugin` / `PluginContext` 作为运行时 API。
- 第三方模块使用 `SandboxClient`，按 `permissions` 最小授权。

### 远程模块结构

一个可安装的远程模块仓库至少包含：

```text
guess_number/
├── plugin.json      # 安装阶段静态元数据，不能执行 Python
├── manifest.py      # 运行阶段 Manifest
├── plugin.py        # 模块主类
└── __init__.py      # 导出 PLUGIN_CLASS 和 MANIFEST
```

不再兼容旧的“只有 `plugin.json` + `plugin.py`”单文件结构；缺少 `manifest.py` 或 `__init__.py` 会在安装/更新阶段被拒绝。

### plugin.json

`plugin.json` 用于安装、列表展示和安全校验。安装阶段只读取这个文件，但会同时检查运行期必须存在 `manifest.py`、`plugin.py`、`__init__.py`。

```json
{
  "name": "guess_number",
  "display_name": "猜数字",
  "description": "一个抢答小游戏模块",
  "author": "example",
  "version": "0.1.0",
  "entry": "plugin.py",
  "min_telepilot_version": "0.19.0",
  "commands": ["guess"],
  "cleanup_mode": "resource",
  "tags": ["game", "quiz"],
  "category": "interactive",
  "interaction_entries": [
    {
      "key": "start_game",
      "title": "开始游戏",
      "description": "由交互 Bot 在群内开启一局游戏。",
      "session_scope": "chat",
      "input_schema": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "prize": {
            "type": "integer",
            "title": "奖金",
            "default": 123,
            "minimum": 1
          }
        }
      }
    }
  ],
  "permissions": ["send_message", "edit_message", "read_chat"],
  "config_schema": {
    "type": "object",
    "x-ui-mode": "single",
    "properties": {
      "command": {
        "type": "string",
        "title": "触发指令名",
        "default": "guess",
        "minLength": 1,
        "maxLength": 32,
        "pattern": "^\\S+$"
      }
    }
  }
}
```

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `name` / `key` | 二选一 | string | 模块唯一标识，优先使用 `name` |
| `display_name` | 推荐 | string | UI 显示名 |
| `description` | 推荐 | string | 模块用途说明 |
| `author` | 推荐 | string | 作者 |
| `version` | 是 | string | 语义化版本，如 `0.1.0` |
| `entry` | 否 | string | 入口文件，默认 `plugin.py`；当前仍要求同时提供标准 `manifest.py` / `__init__.py` |
| `min_telepilot_version` | 推荐 | string | 最低 TelePilot 版本 |
| `min_telebot_version` | 兼容 | string | 旧字段名，0.15 起仅作为 legacy alias 解析 |
| `commands` | 否 | array | 模块声明的触发指令名，用于帮助文档 |
| `cleanup_mode` | 否 | string | 开发约定字段，建议取 `resource` / `reset` / `no-op`；当前平台不会自动执行该字段对应的清理策略，模块仍需在 `on_shutdown` / 取消 / 超时路径里自行实现幂等清理 |
| `tags` | 否 | array | 分类搜索标签 |
| `category` | 推荐 | string | `interactive` / `automation` / `utility`，与 `manifest.py` 保持一致 |
| `interaction_entries` | 按需 | array | 只有互动娱乐模块才声明；工具/自动化模块保持空或不填 |
| `permissions` | 推荐 | array | 运行时沙箱权限声明 |
| `config_schema` | 推荐 | object | 配置表单和 API 校验依据 |

`plugin.json` 与 `manifest.py` 中的 `version`、`category`、`interaction_entries` 应保持一致；如果模块进入 Registry，Registry 里的 `version` 也要同步。

远程模块推荐把 `config_schema["x-ui-mode"]` 写成 `single`。需要多条规则 CRUD 时使用 `rules`，系统常驻能力才使用 `platform`。旧 `schema` 仅作为兼容别名，含义是“字段由 schema 提供，入口使用通用单配置独立页”。

### manifest.py

`manifest.py` 是运行阶段的 Manifest，必须导出 `MANIFEST`。运行时真正生效的是这里的 `Manifest`，因此远程模块要在 `plugin.json` 和 `manifest.py` 两处同步声明模块身份。

```python
from app.worker.plugins.manifest import Manifest

MANIFEST = Manifest(
    key="guess_number",
    display_name="猜数字",
    version="0.1.0",
    author="example",
    description="一个抢答小游戏模块",
    category="interactive",
    interaction_entries=[
        {
            "key": "start_game",
            "title": "开始游戏",
            "description": "由交互 Bot 在群内开启一局游戏。",
            "session_scope": "chat",
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "prize": {
                        "type": "integer",
                        "title": "奖金",
                        "default": 123,
                        "minimum": 1,
                    },
                },
            },
        }
    ],
    permissions=["send_message", "edit_message", "read_chat"],
    config_schema={
        "type": "object",
        "x-ui-mode": "single",
        "properties": {
            "command": {
                "type": "string",
                "title": "触发指令名",
                "default": "guess",
                "minLength": 1,
                "maxLength": 32,
                "pattern": r"^\S+$",
            },
            "timeout": {
                "type": "integer",
                "title": "超时时间（秒）",
                "default": 60,
                "minimum": 10,
                "maximum": 86400,
            },
        },
    },
)
```

不是互动娱乐型的模块不要声明 `interaction_entries`：

```python
MANIFEST = Manifest(
    key="image_tool",
    display_name="图片工具",
    version="1.0.0",
    category="utility",
    interaction_entries=[],
)
```

`plugin.py` 仍然继承 `Plugin`，不要使用旧的 `group/private` 频道写法。当前只支持 `incoming` / `outgoing` 两类消息方向。`__init__.py` 必须导出 `PLUGIN_CLASS` 和 `MANIFEST`：

```python
from .manifest import MANIFEST
from .plugin import GuessNumberPlugin

PLUGIN_CLASS = GuessNumberPlugin

__all__ = ["PLUGIN_CLASS", "MANIFEST"]
```

### 安装与启用流程

通过 Web UI：

1. 进入模块中心的远程模块页面。
2. 输入 Git 仓库地址或子目录 URL。
3. 点击安装。
4. 安装完成后，回到模块中心选择账号启用和配置。

通过 REST API：

```text
POST /api/remote-plugins/install
POST /api/remote-plugins/{name}/enable
POST /api/remote-plugins/{name}/enable-accounts   # body: {"account_ids": [1, 2]}
POST /api/remote-plugins/{name}/disable-accounts  # body: {"account_ids": [1, 2]}
POST /api/remote-plugins/{name}/update
DELETE /api/remote-plugins/{name}
```

安装流程：

```text
1. git clone 到 plugins/installed/{name}/
2. 读取 plugin.json → Pydantic 校验（安装阶段不执行 Python）
3. 静态检查 manifest.py / plugin.py / __init__.py 是否齐全
4. 验证通过 → 注册到数据库
5. 广播 CMD_RELOAD_CONFIG，worker 重新扫描 installed 模块
6. 验证失败 → 删除目录，返回错误
```

启用远程模块有两层开关：

- “远程模块管理”里的启用/禁用是远程模块全局开关。
- “模块中心”里的账号启用/禁用是账号级开关。

远程模块实际加载需要 `InstalledPlugin.enabled` 和 `AccountFeature.enabled` 同时为真；旧 `RemotePlugin` 表仅作为升级兼容的只读快照保留。

Docker 部署时，`plugins/installed/{name}/` 和 `data/plugin_repos/` 必须挂载到持久化卷。否则 `docker compose up -d --build` 重建 web 容器后，数据库可能还保留模块开关，但模块文件或仓库缓存已经从容器临时文件系统消失，最终表现为远程模块指令没有响应。

### API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/remote-plugins` | 列出已安装远程模块 |
| `POST` | `/api/remote-plugins/install` | 从 Git URL 安装 |
| `POST` | `/api/remote-plugins/{name}/enable` | 全局启用远程模块 |
| `POST` | `/api/remote-plugins/{name}/disable` | 全局禁用远程模块 |
| `POST` | `/api/remote-plugins/{name}/enable-accounts` | 按请求体 `account_ids` 批量启用账号 |
| `POST` | `/api/remote-plugins/{name}/disable-accounts` | 按请求体 `account_ids` 批量禁用账号 |
| `POST` | `/api/remote-plugins/{name}/update` | 拉取更新并热重载 |
| `DELETE` | `/api/remote-plugins/{name}` | 卸载并清理 DB |

### 沙箱与权限

第三方远程模块运行时拿到的 `ctx.client` 是 `SandboxClient`，只允许调用 `manifest.py` 中声明的权限。

| 权限 | 允许方法 | 说明 |
|------|----------|------|
| `send_message` | `send_message` / `respond` / `reply` | 发送文本消息 |
| `edit_message` | `edit` / `edit_message` | 编辑消息 |
| `read_chat` | `get_messages` / `get_chat` / `iter_messages` | 读取聊天 |
| `send_file` | `send_file` | 发送图片、文件 |
| `join_chat` | `join_chat` | 加入聊天 |
| `delete_message` | `delete_messages` | 删除消息 |
| `moderate_chat` | `ban_user` / `kick_user` / `mute_user` / `unban_user` | 受控成员管理；高危权限，仅在确实需要封禁、踢出、禁言或解封成员时声明 |

第三方模块不会拿到：

- 真实 `client.session`
- Redis 客户端
- DB engine/session
- worker 内部 `engine`
- raw MTProto `client(functions.xxx(...))`

注意：

- 缺权限时会抛 `PermissionError`，请在日志里提示“缺少哪个权限”，不要吞掉异常。
- `event.reply/respond/edit` 也必须按同等能力声明权限，不要把 event helper 当成越权发送路径。
- 不要把 API Key、session、Bot Token、完整本地路径写进日志。
- 外部 HTTP 请求必须设置 timeout。
- 需要长期后台任务时，优先使用 `ctx.scheduler`，不要自己写永久循环。

### 通用配置页的数据来源

远程模块通用配置页由 `config_schema` 驱动。前端点击“配置”时，不会直接读取磁盘上的 `plugin.json` 或 `manifest.py`，而是读取：

```text
GET /api/accounts/{aid}/features
```

也就是接口返回的 `features[].config_schema`。这个字段来自数据库里的 `Feature.manifest.config_schema`。

远程模块配置链路：

```text
plugin.json.config_schema
  -> 安装/更新服务解析 plugin.json
  -> 后端写入 Feature.manifest.config_schema
  -> /api/accounts/{aid}/features 返回 config_schema
  -> 前端通用独立配置页自动渲染配置表单
```

开发与排查时请记住：

- `plugin.json.config_schema` 是远程模块安装阶段的静态来源。
- 安装/更新后，后端必须把它持久化到 `Feature.manifest.config_schema`。
- 前端通用配置页实际读取 `/api/accounts/{aid}/features` 返回的 `config_schema`。
- 如果 UI 显示“该模块没有可配置的选项”，先检查该 API 返回里的 `config_schema` 是否为空。
- 修改远程模块的 `config_schema` 后，需要在模块中心执行“更新模块”，并确认后端完成元数据回写。

### 远程模块发布前检查

- [ ] `plugin.json` 能被静态解析，不依赖 Python 执行。
- [ ] `manifest.py` 导出 `MANIFEST`，`__init__.py` 导出 `PLUGIN_CLASS` 和 `MANIFEST`。
- [ ] 不是旧的单文件结构；`manifest.py`、`plugin.py`、`__init__.py` 三个运行期文件都存在。
- [ ] 模块名、Manifest key、目录名一致。
- [ ] `plugin.json.version`、`MANIFEST.version`、Registry `version` 一致。
- [ ] `category` 在 `plugin.json` 与 `manifest.py` 中一致。
- [ ] 只有互动娱乐型模块声明 `interaction_entries`；工具类和自动化类模块保持空或不填。
- [ ] 启动日志或主要交互消息包含当前模块版本，方便确认远程热更新是否生效。
- [ ] `permissions` 覆盖实际调用的 `ctx.client` 方法。
- [ ] 指令可触发，指令改名后热重载生效。
- [ ] 群聊、私聊、频道/匿名频道下不会因为事件属性缺失崩溃。
- [ ] 进行中重复触发会提示当前状态和下一步操作，不会覆盖已有局。
- [ ] 抢答并发只奖励一次。
- [ ] 超时和答题同时发生时只结束一次。
- [ ] 高频交互有冷却/限流/超时策略，且用户可见文案说明关键规则。
- [ ] 模板类配置有占位符说明和示例预览。
- [ ] 模块禁用、热重载、worker 退出后没有幽灵任务。
- [ ] 取消、完成、超时、禁用、热重载都会清理临时消息、文件和后台任务。
- [ ] 外部 HTTP 请求有 timeout，错误提示已脱敏。
- [ ] 模块日志足够排查“为什么没触发/为什么没发出去”。

### 示例与 CI 建议

当前 CI 已校验 `examples/plugins/with_http` 和 `examples/plugins/with_ai`，分别用于演示 `ctx.http` / `external_http` / `allowed_hosts` 的最小组合，以及 `ctx.ai` / `ai_text` / 平台统一 LLM 池的推荐接入方式。`examples/plugins/translate` 是历史示例，尚未迁移到受限 `PluginContext` + sandbox 权限模型，因此在示例校验脚本中明确跳过。

新增示例时请同步更新 `scripts/validate-plugin-examples.py`：

1. 已迁移到公开 API 的示例加入 `INCLUDED_EXAMPLES`，CI 会检查必要文件、`plugin.json`、`MANIFEST`、`PLUGIN_CLASS`、key/version/category/permissions/allowed_hosts 一致性，并实例化插件类。
2. 暂时保留的历史示例加入 `SKIPPED_EXAMPLES` 并写清原因；不要让示例通过 import worker 私有实现绕过 `ctx.http` / `ctx.ai` facade。
3. 示例不得访问网络、真实 LLM Provider、数据库或账号会话；CI 只做静态和 import 级校验。

### Registry 机制

支持从远程 registry 同步可用模块列表：

```json
{
  "plugins": [
    {
      "name": "guess_number",
      "display_name": "猜数字",
      "source_url": "https://github.com/user/repo",
      "version": "0.1.0",
      "description": "一个抢答小游戏模块",
      "author": "example",
      "tags": ["game", "quiz"]
    }
  ]
}
```

---
