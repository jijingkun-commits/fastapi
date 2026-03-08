# debug_report_wf03_state_dirty_whitelist

## 1. 问题现象与影响范围
- 现象：运行 `bootstrap` 或 `wt-flow merge` 后，active task 对应 `.state/<task_key>/` 下的 `task-runner-state.json` / `task-ledger.jsonl` / `coder4-idempotency.json` 等运行态文件会持续变脏；未显式传入 `WT_FLOW_DIRTY_WHITELIST` 时，主流程容易被误阻断。
- 影响范围：`/Users/jijingkun/bojxAI/fastapi/scripts/coder4/wt-flow.sh`、`/Users/jijingkun/bojxAI/fastapi/scripts/coder4/coder4_bootstrap_kernel.py`、相关 dirty policy 回归测试。

## 2. 根因证据链
- 已确认根因 A：dirty whitelist 默认只覆盖 `docs/plans/` 与 `docs/内部参考/迭代需求/`，没有覆盖 active task 的 `.state/<task_key>/`。
- 已确认根因 B：即便补上了 `.state/<task_key>/` 前缀，中文路径在 git status 中会以 quoted path 形式出现，原有 path 提取逻辑无法正确匹配 whitelist。
- 被排除假设：不是 `merge` 本身的 Git 流程问题；在补齐 whitelist 与 quoted path 解码后，同一 `merge` 测试可以直接通过。

## 3. 修复内容
- `wt-flow.sh`
  - 新增 `_active_task_state_dirty_prefix()`；
  - `_dirty_whitelist_csv()` 会自动追加 active task `.state/<task_key>/` 前缀；
  - 新增 `_decode_git_quoted_path()`，使中文路径的 dirty line 能正确还原。
- `coder4_bootstrap_kernel.py`
  - 新增 `build_active_task_state_dirty_whitelist()` 与 `merge_dirty_whitelist()`；
  - `build_kernel_context()` 会自动并入 active task `.state/<task_key>/`；
  - 新增 `_decode_git_status_path()`，消除对 `core.quotePath=false` 的直接依赖。

## 4. 验证命令与结果
- RED：
  - `venv/bin/python -m pytest tests/unit/test_coder4_wt_flow_verified_state.py tests/unit/test_coder4_bootstrap_kernel_local_mode.py -k "state_dirty or auto_whitelists_active_task_state_dir" --no-cov -q`
  - 结果：
    - `wt-flow merge` 被 `.state/<task_key>/task-runner-state.json` 误阻断；
    - `build_kernel_context()` 仍把 active task state 文件计入 `main_repo_dirty_preview`。
- GREEN：
  - `venv/bin/python -m pytest tests/unit/test_coder4_wt_flow_verified_state.py tests/unit/test_coder4_bootstrap_kernel_local_mode.py --no-cov -q`
  - 结果：`16 passed`

## 5. 风险、回滚点与后续建议
- 本轮先解决 active task state 文件的自动白名单与 quoted path 解析问题；还没有把 lock/session 文件再细分成更细粒度的运行态类型。
- 后续建议继续推进 `WF-04`：将 dirty path 解析统一升级到 `git status --porcelain -z`，并补中文/空格/rename 路径的专项回归。
- 若要回滚，可去掉 active-task state 前缀自动追加逻辑，但会重新暴露“每次都要手传 whitelist”的阻断。
