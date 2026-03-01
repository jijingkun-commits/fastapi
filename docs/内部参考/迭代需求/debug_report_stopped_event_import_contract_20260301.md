# debug_report_stopped_event_import_contract_20260301

## 1. 问题摘要
- 现象: 在一次 `$jjk-verify` 执行中，`pytest` 阶段出现 `ImportError: cannot import name 'stopped_event' from app.ai.events`，导致验收阻断。
- 影响范围: 影响 `app.services.chat_service` 导入链，进而阻断 planner 相关回归测试与验收流程。
- 严重等级: 中（阻断验收，但当前分支可恢复）。
- 复现稳定性: `REPRO_NOT_STABLE`（后续复测无法稳定复现同一 ImportError）。

## 2. 根因证据链

```yaml
root_cause_chain:
  symptom: "pytest 导入 app.services.chat_service 时偶发 stopped_event ImportError"
  hypotheses:
    - id: H1
      statement: "PYTHONPATH 指向错误模块，导致导入了非仓库内 app.ai.events"
      evidence:
        - "venv/bin/python 导入 app.ai.events 后 __file__ 指向 /Users/jijingkun/bojxAI/fastapi/app/ai/events.py"
        - "同一环境下 import app.services.chat_service 可成功"
      verdict: rejected
    - id: H2
      statement: "events.py 发生循环导入或运行期异常，导致 stopped_event 未完成定义"
      evidence:
        - "直接导入 app.ai.events 不报错，hasattr(stopped_event) == True"
        - "重复执行目标 planner 测试集通过"
      verdict: rejected
    - id: H3
      statement: "事件模块导出契约缺少测试守护，近期改动导致 stopped 区域 API 发生漂移，触发偶发导入失败窗口"
      evidence:
        - "git diff 显示 app/ai/events.py 中 stopped 区域存在导出函数删改（emit_confirmation/emit_stopped/emit_done 被移除）"
        - "新增契约测试首轮失败（缺少 emit_confirmation），说明该区域 API 已发生漂移且无测试拦截"
      verdict: confirmed
  final_root_cause: "根因为 events 公共导出契约缺失回归保护，导致 stopped 相关导出在改动中发生漂移并引入导入链不稳定风险。"
```

## 3. 修复内容
- 修改文件:
  - `app/ai/events.py`
  - `tests/unit/test_events_contract.py`
- 关键符号:
  - `emit_confirmation`
  - `emit_stopped`
  - `emit_done`
  - `stopped_event`
  - `_build_stopped_payload`
- 修复说明:
  - 先以 TDD 补充导出契约测试，锁定 stopped 相关公共 API；
  - 恢复 `events.py` 中兼容导出 `emit_confirmation/emit_stopped/emit_done`，消除契约漂移；
  - 新增 chat_service 契约测试，确保 `_build_stopped_payload` 通过 `stopped_event` 返回标准载荷。

## 4. 验证证据
- 复现（RED）命令:
  - `cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest -q tests/unit/test_events_contract.py`
  - 结果: `FAILED`（`缺少导出: emit_confirmation`）
- 修复后（GREEN）命令:
  - `cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest -q tests/unit/test_events_contract.py`
  - 结果: `2 passed`
- 回归命令:
  - `cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest -q tests/unit/test_events_contract.py tests/unit/test_planner_strategy_router.py tests/unit/test_planner_tool_call_primary.py tests/unit/test_planner_json_object_fallback.py tests/unit/test_planner_text_parse_fallback.py tests/unit/test_multi_intent_queue_flow.py`
  - 结果: `29 passed`
- 导入链验证:
  - `cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python - <<'PY' ... import app.services.chat_service ... PY`
  - 结果: `chat_service_import: ok`

## 5. 风险与回滚
- 风险:
  - 恢复兼容导出会增加少量公开 API 面积，但均为历史语义一致函数，行为风险低。
  - 当前 ImportError 仍属一次性现象；本次修复重点是“防回归”与“导出契约稳定”。
- 回滚点:
  - 回滚 `app/ai/events.py` 的三处兼容函数恢复与 `tests/unit/test_events_contract.py` 新增文件，即可恢复到修复前状态。

## 6. 下一步建议
- 继续执行 `$jjk-verify`，以本报告作为证据输入，重新给出 `PASS|WARN|FAIL` 结论。
- 若后续再次出现同类导入抖动，优先记录触发时刻的 `git status` 与命令上下文，排查“并发改码窗口”与执行环境漂移。
