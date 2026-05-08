
---

## 十二、v0.9.0 追加任务（来自社区建议）

### 任务 A: 插件声明式命令注册（P0）

**问题：** 当前插件在 `on_command` 里手动 if/elif 匹配命令，效率低且容易遗漏。

**方案：** 插件类属性声明命令列表，loader 自动扫描注册。

```python
class WeatherPlugin(Plugin):
    key = "weather"
    commands = {
        "weather": "查询天气",
        "w": "weather 的别名",
    }
```

loader 在加载插件时检查 `commands` 属性 → 自动注册到命令路由表 → 帮助系统自动列出。不需要命令的纯服务插件不声明 `commands`，不在帮助列表出现。

**改动文件：**
- `backend/app/worker/plugins/base.py` — Plugin 基类加 `commands: dict[str, str]` 属性
- `backend/app/worker/plugins/loader.py` — 扫描 `commands` 自动注册
- `backend/app/worker/command.py` — 命令派发改为查注册表
- 现有 builtin 插件适配新方式

---

### 任务 B: 插件内部设置（P1）

**问题：** 远程插件安装后缺少配置界面。

**方案：** manifest.json 中声明 `config_schema`（JSON Schema），前端根据 schema 自动生成设置表单。

```json
{
  "name": "weather",
  "config_schema": {
    "type": "object",
    "properties": {
      "api_key": { "type": "string", "title": "API Key", "description": "可选" },
      "default_city": { "type": "string", "title": "默认城市", "default": "Beijing" }
    }
  }
}
```

安装完成后 → 前端显示配置表单 → 保存到 rule.config → 插件通过 `ctx.config` 读取。

**改动文件：**
- `frontend/src/pages/RemotePlugins/index.tsx` — 安装后弹出配置表单
- 后端 API 增加 `POST /api/remote-plugins/{name}/config`

---

### 任务 C: Userbot 命令仅允许自己触发（P0）

**问题：** Userbot 模式下，群里其他人发命令会被处理，导致风控、刷屏、炸号。

**方案：** 在 Plugin 基类增加 `owner_only` 属性，默认 True。

```python
class Plugin:
    owner_only: bool = True   # 默认仅 owner 可触发
```

命令派发入口根据插件属性判断：
- `owner_only=True`：仅 owner + sudo 用户可触发
- `owner_only=False`：所有人可触发（如关键词自动回复、群组监控类插件）

```python
# backend/app/worker/command.py 命令派发入口
if is_userbot_mode and event.sender_id not in allowed_senders:
    # 检查该插件是否允许非 owner 触发
    if getattr(plugin_cls, "owner_only", True):
        return  # 跳过
```

**例外：** Sudo 用户（经过授权的管理员）始终不受限制。

**改动文件：**
- `backend/app/worker/plugins/base.py` — Plugin 基类加 `owner_only: bool = True`
- `backend/app/worker/command.py` — 命令派发时按插件属性判断

**优先级：** P0，安全红线，与远程插件系统并行开发。

---

### 任务 D: 插件中心重构 — 去矩阵，按账号管理（P0）

**问题：** 当前"插件中心"用"功能矩阵"（账号 × 功能的 N×M 表格）管理启停。插件少时能用，插件多了（几十上百个）矩阵爆炸，不可扩展。且"已加载插件"Tab 与即将上线的远程插件功能重叠。

**方案：** 去掉功能矩阵，改为"按账号管理插件"的模式（账号少、插件多，账号侧更线性可读）。

**当前结构（Extensions.tsx 3 Tab）：**
- Tab 1: 功能矩阵 — 账号 × 功能开关总览
- Tab 2: 已加载插件 — 本地插件 enable/disable/uninstall
- Tab 3: 开发指南 — PLUGIN-DEV-GUIDE.md 渲染

**重构后结构（2 Tab）：**

**Tab 1: 插件管理**（合并原 Tab 2 + 远程插件页面）
```
┌─────────────────────────────────────┐
│ 🔍 搜索插件...                       │
├─────────────────────────────────────┤
│ 📦 已安装（本地 + 远程统一展示）      │
│ ┌───────────────────────────────┐   │
│ │ weather  v1.0  ✅ 已启用 [⚙] │   │
│ │ translate v2.1  ✅ 已启用 [⚙] │   │
│ │ game24   v0.5  ✅ 已启用 [⚙] │   │
│ └───────────────────────────────┘   │
│                                     │
│ 🌐 远程插件市场                      │
│ ┌───────────────────────────────┐   │
│ │ [输入 GitHub URL] [安装]       │   │
│ └───────────────────────────────┘   │
│                                     │
│ 每个插件卡片点击 [⚙] → 展开配置表单  │
│ (config_schema 驱动的 JSON 表单)    │
└─────────────────────────────────────┘
```

**Tab 2: 账号配置**（替代原功能矩阵）
```
┌─────────────────────────────────────┐
│ 选择账号: [账号A ▼]                  │
├─────────────────────────────────────┤
│ 该账号启用的插件：                    │
│ ✅ weather        (全局已安装)       │
│ ✅ translate      (全局已安装)       │
│ ❌ game24         (全局已安装)       │
│ ❌ new_plugin     (全局已安装)       │
│                                     │
│ [保存]                               │
│                                     │
│ ℹ️ 新账号自动继承"默认插件集"          │
└─────────────────────────────────────┘
```

**关键设计决策：**

| 维度 | 旧方案（功能矩阵） | 新方案（账号配置） |
|------|-------------------|-------------------|
| 复杂度 | N×M（账号×功能） | N×M 但按账号分页 |
| 插件多了怎么办 | 矩阵爆炸 | 列表线性可读 |
| 新账号配置 | 每个都从头配 | 继承默认插件集 |
| 安全性 | 无默认关闭 | 插件默认关闭，手动启用 |

**默认插件集概念：**
- 新安装的插件默认对所有账号 **关闭**
- 管理员可以设置"默认插件集"，新账号自动继承
- 避免插件一装就全账号生效的风险

**改动文件：**
- `frontend/src/pages/Extensions.tsx` — 重构 Tab 结构
- 删除 `frontend/src/pages/RemotePlugins/index.tsx`（合并到 Extensions）
- `frontend/src/api/remotePlugin.ts` — 远程插件 API
- 后端增加 `POST /api/accounts/{id}/plugins` — 账号级插件启停

**优先级：** P0，与远程插件系统一起交付。
