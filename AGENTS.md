# TelePilot Agent Rules

## 版本与发布

- 不要为每个微小提交单独迭代版本号。版本号只在准备发布、推送稳定检查点、创建 release/PR，或用户明确要求“推一版/发一版”时统一迭代。
- 一批相关改动只对应一个版本号；开发过程中先积累到 `CHANGELOG.md` 的 `Unreleased`，发布前再决定版本号并移动到正式版本段落。
- 版本 bump 必须按 SemVer 判断：
  - `MAJOR`：破坏兼容的数据库迁移、配置格式变更、API 路径或语义不兼容、老版本无法平滑升级。
  - `MINOR`：用户可感知的新能力、主要入口/信息架构重组、后端能力完整前端化、新模块或重要工作流变化。
  - `PATCH`：bug 修复、文案、小 UI、错误提示、测试补充、兼容性补丁和不改变主要用户路径的小调整。
- 发布时版本号必须同步更新：`backend/app/__init__.py`、`backend/pyproject.toml`、`frontend/package.json`、`frontend/src/lib/version.ts`，并用中文写入 `CHANGELOG.md`。
- commit / PR / release 文案使用中文。

## 工作区安全

- 可能存在用户或其他 agent 的未提交改动。不要 revert、checkout 或 reset 你没有明确负责的改动。
- 手工编辑文件使用 `apply_patch`。
