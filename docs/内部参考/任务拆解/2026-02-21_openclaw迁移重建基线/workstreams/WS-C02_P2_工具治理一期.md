# 工作包说明

> WS 编号: WS-C02
> 名称: P2 工具治理一期
> 类型: parallel
> 对应 feature_id: P2-01

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: C02
- 来源主计划: `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md`

## 1. 目标

- 本包目标: P2 工具治理一期 的可执行落地。
- 完成定义（DoD）:
  - Tool Registry/Policy/Broker 接线通过
  - ENABLE_TOOL_GOVERNANCE 与 TOOL_POLICY_FAIL_MODE 回滚验证通过

### 1.1 功能机制

  - 引入 Tool Registry/Policy/Broker 首期治理链路
  - 按 task_mode/requires_evidence 分层启用证据门禁
  - settings 与 DB 策略覆盖一致生效

### 1.2 代码锚点

  - app/ai/workflow/multi_agent_graph.py::_get_common_tools
  - app/ai/workflow/multi_agent_graph.py::_get_supervisor_tools
  - app/services/config_resolver.py::ConfigResolver
  - app/core/config_contract.py::ToolPolicyContract

- 来源证据:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.7

## 2. 文件边界

### 可修改（白名单）
  - app/ai/workflow/multi_agent_graph.py
  - app/services/config_resolver.py
  - app/core/config_contract.py
  - app/ai/tools
  - tests/unit/test_multi_agent_streaming_helpers.py

### 禁止修改（黑名单）
- 其他 card_id 对应白名单外文件

## 3. 串行门禁

- 前置卡: C01
- 解锁条件: 前置卡 `done_gate` 全部通过
- 本 WS 不得推进条件: 前置卡存在 `TODO/IN_PROGRESS/BLOCKED`

## 4. 测试与验收

- 验收命令:
  - PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py

## 5. 风险与回滚

- 回滚锚点:
  - ENABLE_TOOL_GOVERNANCE
  - TOOL_POLICY_FAIL_MODE

## 6. card_export

```yaml
card_export:
  id: WS-C02
  card_id: C02
  feature_ids: [P2-01]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-C02
  title: P2 工具治理一期
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: [C01]
  depends_on: [C01]
  file_whitelist:
  - app/ai/workflow/multi_agent_graph.py
  - app/services/config_resolver.py
  - app/core/config_contract.py
  - app/ai/tools
  - tests/unit/test_multi_agent_streaming_helpers.py
  mechanism_summary:
  - 引入 Tool Registry/Policy/Broker 首期治理链路
  - 按 task_mode/requires_evidence 分层启用证据门禁
  - settings 与 DB 策略覆盖一致生效
  code_anchor_refs:
  - app/ai/workflow/multi_agent_graph.py::_get_common_tools
  - app/ai/workflow/multi_agent_graph.py::_get_supervisor_tools
  - app/services/config_resolver.py::ConfigResolver
  - app/core/config_contract.py::ToolPolicyContract
  acceptance_checks:
  - PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py
  rollback_anchors:
  - ENABLE_TOOL_GOVERNANCE
  - TOOL_POLICY_FAIL_MODE
  evidence_entry: docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.7
  done_gate:
  - Tool Registry/Policy/Broker 接线通过
  - ENABLE_TOOL_GOVERNANCE 与 TOOL_POLICY_FAIL_MODE 回滚验证通过
```
