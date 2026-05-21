# TelePilot 远程模块开发与安装指南

> 本文档已合并到 [模块开发指南（Plugin API）](./PLUGIN-DEV-GUIDE.md#10-远程模块)。

远程模块和内置模块共用同一套 `Plugin` / `Manifest` / `PluginContext` 规范；区别只在远程模块额外需要 `plugin.json` 作为安装阶段静态元数据，并由 Git 仓库安装到 `plugins/installed/{name}/`。

请直接阅读：

- [模块开发指南：远程模块](./PLUGIN-DEV-GUIDE.md#10-远程模块)
- [Manifest 元数据](./PLUGIN-DEV-GUIDE.md#5-manifest-元数据)
- [交互 Bot 兼容声明](./PLUGIN-DEV-GUIDE.md#交互-bot-兼容声明interaction-entries)
- [交互 Bot 端到端示例](./PLUGIN-DEV-GUIDE.md#端到端示例24-点交互入口)
- [安全边界](./PLUGIN-DEV-GUIDE.md#12-安全边界)
- [模块最小测试清单](./PLUGIN-DEV-GUIDE.md#模块最小测试清单)

保留这个文件只是为了兼容旧链接；后续内容维护只更新 `docs/PLUGIN-DEV-GUIDE.md`。
