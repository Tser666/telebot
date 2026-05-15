# builtin 插件目录说明

## codex_image 下沉兼容（0.14 PLAN F9/B2）

- 当前版本优先保证运行时兼容：若旧账号仍启用 `codex_image`，但本地不存在该插件实现，worker 会写入 runtime log 并将该账号该功能标记为 failed，不会导致 worker 进程崩溃。
- `codex_image` 的物理迁移（从 builtin 目录移动到 installed 分发）在本次改动中**未执行**，避免半迁移造成 import 崩溃。
- 后续若执行真实迁移，请确保以下条件同时满足：
  - installed 插件目录与 manifest 可被 loader 发现；
  - 旧 `account_feature(feature_key='codex_image')` 有明确迁移策略；
  - 前端存在降级提示，避免用户误认为功能仍可直接启用。
