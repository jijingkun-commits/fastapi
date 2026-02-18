# 工作包说明

> WS 编号: WS-G1
> 名称: 集成回归门禁
> 类型: gate

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260216-TOOL-GOVERNANCE`
- 来源主计划：`docs/内部参考/迭代需求/ai_tools_governance_implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/parallel_plan.md`

---

## 1. 目标

- 本包目标：执行并记录治理改造后的统一门禁，形成责任 WS 归因。
- 完成定义（DoD）：
  1. 单元/集成/API/文档门禁全部执行并产出结果。
  2. 未通过项完成责任归因（WS-01/WS-02/WS-03）。
  3. `parallel_plan.md` 第 10、11 节完成回填。

---

## 2. 文件边界

### 可修改（白名单）

- `docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/parallel_plan.md`
- `docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/workstreams/WS-G1_集成回归门禁.md`

### 禁止修改（黑名单）

- `app/**`
- `web/**`

---

## 3. 状态与契约

- 可写字段：`gate.g1.status`、`gate.g1.tc_matrix`、`gate.g1.owner_mapping`。
- 只读字段：业务代码实现与协议冻结定义。

---

## 4. 实施步骤

1. 执行 WS-01/02/03 约定测试命令。
2. 记录失败项与责任 WS。
3. 执行文档门禁并记录结果。
4. 回填 `parallel_plan.md` 的 Gate 结果。

---

## 5. 测试与验收

- 最小测试集：
  - `venv/bin/python -m pytest -q tests/unit/test_tool_registry.py tests/unit/test_tool_policy.py tests/unit/test_tool_hooks.py`
  - `venv/bin/python -m pytest -q tests/integration/test_tool_policy_in_graph.py tests/integration/test_tool_lifecycle_events.py`
  - `venv/bin/python -m pytest -q tests/api/test_chat_api.py`
  - `python3 scripts/docs_guard.py --strict`
- 验收标准：
  1. 门禁结果可追溯到具体 WS。
  2. 未通过项有明确回滚或修复路径。

### 5.1 TC-ID 映射表（Gate WS 必填）

| TC-ID | 门禁命令/检查项 | 自动化脚本或 pytest nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|---|---|---|---|---|---|
| TG-G1-001 | Registry/Policy 单元门禁 | `tests/unit/test_tool_registry.py` + `tests/unit/test_tool_policy.py` | 待执行 | WS-01 | - |
| TG-G1-002 | Hook/Audit 单元门禁 | `tests/unit/test_tool_hooks.py` + `tests/unit/test_tool_audit_service.py` | 待执行 | WS-02 | - |
| TG-G1-003 | 编排接线集成门禁 | `tests/integration/test_tool_policy_in_graph.py` + `tests/integration/test_tool_lifecycle_events.py` | 待执行 | WS-03 | - |
| TG-G1-004 | API + 文档门禁 | `tests/api/test_chat_api.py` + `python3 scripts/docs_guard.py --strict` | 待执行 | WS-G1 | - |

### 5.2 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：否
- 触发依据（命中项）：当前 Gate 仅后端与文档门禁。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因：无前端交互改造。

---

## 6. 风险与回滚

- 主要风险：跨 WS 失败归因不清导致修复循环。
- 回滚点：保持 Gate 文档回填，按责任 WS 回滚代码分支。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
- 是否修改了白名单外文件（是/否）：
- 测试命令与结果：
- 已知风险点：
- 回滚建议：

---

## 8. card_export（机读，必填）

```yaml
card_export:
  id: WS-G1
  card_key: PP-20260216-TOOL-GOVERNANCE::WS-G1
  title: 集成回归门禁
  type: gate
  lane: lane-gate
  hard_depends_on:
    - WS-01
    - WS-02
    - WS-03
  soft_depends_on: []
  depends_on:
    - WS-01
    - WS-02
    - WS-03
  file_whitelist:
    - docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/parallel_plan.md
    - docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/workstreams/WS-G1_集成回归门禁.md
  readonly_scope:
    - app/
    - web/
  owner_fields:
    - gate.g1.status
    - gate.g1.tc_matrix
    - gate.g1.owner_mapping
  check_cmd:
    - venv/bin/python -m pytest -q tests/unit/test_tool_registry.py tests/unit/test_tool_policy.py tests/unit/test_tool_hooks.py
    - venv/bin/python -m pytest -q tests/integration/test_tool_policy_in_graph.py tests/integration/test_tool_lifecycle_events.py
    - venv/bin/python -m pytest -q tests/api/test_chat_api.py
    - python3 scripts/docs_guard.py --strict
  handoff_artifacts:
    - docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/parallel_plan.md
  dod:
    - G1 门禁执行并完成责任 WS 归因
```
