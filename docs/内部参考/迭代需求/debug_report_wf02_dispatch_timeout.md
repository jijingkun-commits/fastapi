# debug_report_wf02_dispatch_timeout

## 1. 问题现象与影响范围
- 现象：`jjk-cardrun` 在 `dispatch` 阶段可能长时间挂起，现场只能通过手工终止进程并改走 `verify -> merge` 收口。
- 影响范围：`/Users/jijingkun/bojxAI/fastapi/scripts/coder4/coder4_bootstrap_kernel.py`、`/Users/jijingkun/bojxAI/fastapi/scripts/coder4/wtimp_dispatch_bridge.py`、相关 dispatch 回归测试。
- 直接影响：`cardrun` 无法在合理时间内识别“wtimp 没有及时返回 JSON 回执”，执行链被阻塞。

## 2. 根因证据链
- 已排除假设 A：bridge 完全没有超时处理。证据：`run_dispatch()` 已捕获 `subprocess.TimeoutExpired` 并映射为 `CARDRUN_SUBAGENT_FAILED`。
- 已排除假设 B：kernel 完全不校验 commit 证据。证据：`apply_action(action=dispatch)` 已对 `commit_sha` 为空做 `CARDRUN_NO_COMMIT_EVIDENCE` 阻断。
- 最终根因：dispatch 超时策略没有成为 cardrun 契约的一部分。
  - bridge 默认 `timeout_seconds=1800`；
  - kernel `KernelContext` 没有 `dispatch_timeout_seconds`；
  - `build_wtimp_dispatch_request()` 无法把更短超时下传给 bridge；
  - 结果是挂起时虽然理论上会超时，但实际会把 `cardrun` 卡住很久，等价于“未及时返回 JSON 回执”。

## 2.1 本窗口追加根因（2026-03-08）
- 已确认“超时契约补齐”并不等于问题闭环。证据：修复前的 `scripts/coder4/wtimp_dispatch_bridge.py` 使用 `subprocess.run(...)` 直接执行 `codex exec`，timeout 时只能保证最外层命令被终止，不能显式回收整条 `codex -> shell -> wtimp` 进程链。
- 已确认 JSON 提取存在误判窗口。证据：修复前的 `_extract_last_json_object()` 允许 fallback 到“任意 dict”，只要 stdout 中存在普通 JSON 日志，就可能被错误当作 dispatch 结果对象。
- 因此 `WF-02` 的剩余根因不是“timeout 值不够短”，而是：
  1. 子执行器生命周期没有落在 bridge 的责任边界内；
  2. dispatch 回执没有做“单结果、强 schema、不可歧义”的契约收口。

## 3. 修复内容
- 在 `/Users/jijingkun/bojxAI/fastapi/scripts/coder4/coder4_bootstrap_kernel.py` 中新增：
  - `DEFAULT_DISPATCH_TIMEOUT_SECONDS = 600`
  - `DISPATCH_TIMEOUT_ENV = "CODER4_DISPATCH_TIMEOUT_SECONDS"`
  - `KernelContext.dispatch_timeout_seconds`
  - `resolve_dispatch_timeout_seconds()`
  - `--dispatch-timeout-seconds` CLI 参数
- 修改 `build_wtimp_dispatch_request()`，将 `dispatch_timeout_seconds` 下传到 `WtimpDispatchRequest.timeout_seconds`。
- 保持 bridge 的超时异常映射不变，仅让 cardrun 可以显式控制超时策略。

## 3.1 本窗口完成修复（2026-03-08）
- 将 bridge 启动方式改为受控 `Popen(..., start_new_session=True)`；timeout、非零退出、非法回执三类失败路径统一补 `session_cleanup` 证据，并尝试回收当前 process-group。
- 将 JSON 提取从“最后一个/任意 dict”改为“唯一一个满足 dispatch contract 的对象”；若没有 contract payload 或出现多个候选 payload，一律 `fail-fast` 为 `CARDRUN_EXECUTION_RESULT_INVALID`。
- 将 payload 校验收紧为强类型语义：`ok` 必须为 `bool`，`changed_files` 必须为 `list[str]`，`acceptance_results` 必须为 `list[dict]`；不再允许宽松 coercion 悄悄吞掉 schema 漂移。
- 保持 kernel 只做错误透传，不把 session 回收细节上抬到编排层。

## 4. 验证命令与结果
- RED：
  - `venv/bin/python -m pytest tests/unit/test_coder4_wtimp_dispatch_bridge.py -k 'timeout_terminates_process_group or rejects_non_contract_json_log_object or rejects_multiple_contract_payloads' --no-cov -q`
  - 结果：`3 failed`；失败点显示 `run_dispatch()` 仍走 `subprocess.run(...)`，尚未进入受控 `Popen` / process-group 清理路径。
- GREEN：
  - `venv/bin/python -m pytest tests/unit/test_coder4_wtimp_dispatch_bridge.py --no-cov -q`
  - 结果：`8 passed`
  - `venv/bin/python -m pytest tests/unit/test_coder4_dispatch_executor.py tests/unit/test_coder4_wtimp_dispatch_bridge.py --no-cov -q`
  - 结果：`13 passed`

## 5. 风险、回滚点与后续建议
- 当前修复已覆盖“同一 process-group 内的挂起会话清理 + 唯一 JSON contract 校验”；若未来 `wtimp` 主动脱离当前 session（例如双重 fork），仍需补跨 session 清理策略。
- 若 `600s` 对某些大卡仍偏短，可通过：
  - `--dispatch-timeout-seconds`
  - `CODER4_DISPATCH_TIMEOUT_SECONDS`
  - `active_task.dispatch_timeout_seconds`
  做临时调整。
- 若要回滚，可恢复 `bridge=subprocess.run + 宽松 JSON 提取` 的旧实现，但会重新暴露“timeout 后残留会话”和“日志 JSON 被误当回执”的结构性问题，不建议回退。
