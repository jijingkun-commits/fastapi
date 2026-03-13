# debug_report_wf04_porcelain_z_dirty_parser

## 1. 问题现象与影响范围
- 现象：`wt-flow.sh` 与 `coder4_bootstrap_kernel.py` 的 dirty path 解析仍基于 `git status --porcelain` 行文本，虽然已补 quoted-path decode，但对 rename/copy 场景仍依赖文本箭头切割。
- 影响范围：`/Users/jijingkun/bojxAI/fastapi/scripts/coder4/wt-flow.sh`、`/Users/jijingkun/bojxAI/fastapi/scripts/coder4/coder4_bootstrap_kernel.py`、`tests/unit/test_coder4_wt_flow_verified_state.py`、`tests/unit/test_coder4_bootstrap_kernel_local_mode.py`。
- 直接影响：当文件名自身包含 ` -> ` 时，旧解析会把 rename 目标路径截断，导致 whitelist 误判、dirty policy 错阻断。

## 2. 根因证据链
- 已排除假设 A：问题只来自 `core.quotePath=true`。证据：quoted-path 解码后，普通中文路径已能恢复，但 rename 仍依赖文本箭头切割。
- 已排除假设 B：问题只存在于 shell。证据：`wt-flow.sh` 与 `coder4_bootstrap_kernel.py` 都使用“取第 3 位后文本 + 处理 ` -> `”的同类逻辑。
- 最终根因：dirty path 的真理源选错了层级。
  - 旧实现依赖 `git status --porcelain` 文本行；
  - rename/copy 目标路径靠字符串切割推断；
  - 文件名自身包含 ` -> ` 时，解析层无法区分“Git 语法箭头”和“真实文件名内容”；
  - 结果是 whitelist 命中依赖运气，不是协议保障。

## 3. 修复内容
- `scripts/coder4/wt-flow.sh`
  - 删除 quoted-path 文本补丁主路径；
  - `_collect_disallowed_dirty_lines()` 改为消费 `git status --porcelain -z --untracked-files=no`；
  - rename/copy 通过读取额外 NUL token 跳过 source path，仅用目标路径参与 whitelist 匹配。
- `scripts/coder4/coder4_bootstrap_kernel.py`
  - 删除 `_decode_git_status_path()` / `_extract_dirty_path()` 文本补码逻辑；
  - 新增 `_parse_porcelain_z_output()`，统一解析 NUL 分隔记录；
  - `inspect_repo_clean()` 改为 `text=False` 读取原始 bytes，并将 preview/ignored 行重建为 `status + path`。
- 测试
  - 新增“中文目录 + 空格 + rename + 文件名包含 ` -> `”回归，分别覆盖 shell 与 Python 两条 dirty parser 主路径。

## 4. 验证命令与结果
- RED：
  - `venv/bin/python -m pytest tests/unit/test_coder4_bootstrap_kernel_local_mode.py::test_inspect_repo_clean_allows_whitelisted_utf8_rename_with_arrow_in_name tests/unit/test_coder4_wt_flow_verified_state.py::test_wt_flow_merge_allows_whitelisted_utf8_rename_with_arrow_in_name --no-cov -q`
  - 结果：`2 failed`；一个显示 kernel `allowed_dirty` 未保留正确目标路径，一个显示 `wt-flow` 把 rename 误判为非白名单脏改。
- GREEN：
  - `venv/bin/python -m pytest tests/unit/test_coder4_bootstrap_kernel_local_mode.py::test_inspect_repo_clean_allows_whitelisted_utf8_rename_with_arrow_in_name tests/unit/test_coder4_wt_flow_verified_state.py::test_wt_flow_create_allows_whitelisted_utf8_rename_with_arrow_in_name --no-cov -q`
  - 结果：`2 passed`
  - `venv/bin/python -m pytest tests/unit/test_coder4_bootstrap_kernel_local_mode.py tests/unit/test_coder4_wt_flow_verified_state.py --no-cov -q`
  - 结果：`18 passed`

## 5. 风险、回滚点与后续建议
- 当前修复已覆盖中文、空格、rename/copy 目标路径以及文件名含 ` -> ` 的场景；这类问题不应再依赖 `core.quotePath=false`。
- 若未来需要复用 dirty parser，建议把 shell/python 两侧的“记录级契约”继续显式化，避免再次各自实现一套文本补码。
- 若要回滚，可恢复 `--porcelain` 文本解析，但会重新暴露 rename 文本歧义与 quoted-path patch-only 的脆弱性，不建议回退。
