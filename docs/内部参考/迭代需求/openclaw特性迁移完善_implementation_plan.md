# OpenClaw 特性迁移完善实施方案

> 文档日期：2026-02-27  
> 文档定位：基于现有代码与数据库现状，完成“骨架 -> 可感知上线”的落地计划  
> 执行模式：`serial`（先收敛正确性，再做并行优化）

---

## 0. 输入来源清单

1. `docs/内部参考/迭代需求/openclaw特性迁移完善_requirements.md`
2. `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`
3. 当前代码现状（`app/services/*`、`app/ai/workflow/*`、`tests/*`）
4. 当前数据库现状（`t_agent_skills` 有历史数据；三层 Skill 表与 `t_chat_run` 已建但仍需切流与数据填充）

---

## 1. 架构影响与约束

### 1.1 模块边界

1. 运行态控制层：`app/services/run_control_service.py` + `app/api/v1/endpoints/chat_api.py`
2. 编排与工具层：`app/ai/workflow/multi_agent_graph.py`
3. Skill 治理层：`app/services/skill_service.py` + `app/models/agent_skill.py`
4. 记忆治理层：`app/services/user_preference_memory_service.py` + `app/services/chat_service.py`
5. 配置治理层：`app/services/config_resolver.py` + `app/core/config_contract.py`

### 1.2 状态契约

1. run 契约：`run_id/thread_id/user_id/status/cancel_reason`
2. Skill 契约：`skill_id/version/user_id/binding_status`
3. memory 契约：`user_id/memory_key/memory_value/scope`
4. queue 契约：`pending_handoff/handoff_queue/handoff_execution_trace/multi_intent_mode`

### 1.3 路由闭环

1. preprocess 注入 skill/memory -> supervisor 决策 -> handoff queue -> evaluate -> summarize/postprocess
2. cancel 信号优先于后续 token 输出，`stopped` 与 `done` 语义兼容

### 1.4 端到端链路

1. 前端请求携带 `thread_id/run_id/current_todo_id`
2. 后端 stream/resume/cancel API 同步 run 生命周期
3. 编排层基于用户上下文执行 Skill 与 memory 注入

### 1.5 可测试性缺口

1. 缺“跨请求积压合并”端到端测试（本轮不强制实现，明确为后续项）
2. 文档门禁存在历史断链，需与功能门禁解耦处理

---

## 2. SSE 契约冻结（涉及跨端协议）

本轮冻结字段（兼容优先）：

1. `done`：必须包含 `thread_id/run_id`；可选 `meta.status`
2. `result`：保持既有结构，禁止破坏既有消费字段
3. `interrupt`：保持既有语义，不与 `stopped` 混淆
4. `stopped`：仅在 `ENABLE_SSE_STOPPED_EVENT=true` 发出；与 `done(meta.status=stopped)` 保持一致

---

## 3. 功能机制包总表（Feature Packet）

| feature_id | card_id | 目标摘要 | 主要代码锚点 | 验证命令 |
|---|---|---|---|---|
| P0-01 | C00 | 基线冻结与观测快照 | `scripts/*` + SQL 快照 | `venv/bin/alembic current` |
| P1-01 | C01 | run 生命周期 + 取消语义上线 | `run_control_service.py` / `chat_api.py` | `pytest -k cancel` |
| P2-01 | C02 | Skill 数据迁移（老表 -> 三层） | `skill_service.py` | `pytest test_skill_service.py` |
| P2-02 | C02 | Skill 主读路径切流与回退 | `skill_service.py` / `multi_agent_graph.py` | `pytest test_multi_agent_skill_workflow.py` |
| P3-01 | C03 | 工具治理配置落库与生效 | `multi_agent_graph.py` / `config_resolver.py` | `pytest test_multi_agent_tool_governance_runtime.py` |
| P4-01 | C04 | memory recall/flush 灰度上线 | `chat_service.py` / `user_preference_memory_service.py` | `pytest test_user_preference_memory_service.py` |
| P5-01 | C05 | 复合任务队列与汇总稳定化 | `multi_agent_graph.py` | `pytest test_multi_intent_queue_flow.py` |
| P6-01 | C06 | 发布门禁与回滚演练 | 全链路 | `/jjk-verify` 自动模式 |
| G-1 | G01 | 数据与配置一致性门禁 | SQL + config 快照 | SQL 脚本 |
| G-2 | G02 | E2E 与灰度门禁 | API + unit + docs | `pytest + docs_guard` |

---

## 4. Feature Packet 详情

### 4.1 P0-01 基线冻结与观测快照

1. 目标与边界：
   - 做：冻结当前表数据量、开关状态、关键测试基线。
   - 不做：任何业务行为变更。
2. 触发条件与状态流转：启动实施前必须完成。
3. 代码锚点：`docs/`、`scripts/`（观测脚本）、DB 查询。
4. 关键字段：`table_count`、`config_snapshot`、`test_snapshot`。
5. 回滚锚点：无（纯观测）。
6. 验证命令：
   - `venv/bin/alembic current`
7. 最小代码样例：

```python
snapshot = {"ts": now_iso(), "tables": counts, "flags": config_values}
```

---

### 4.2 P1-01 run 生命周期 + 取消语义上线

1. 目标与边界：
   - 做：启用 run 控制，保证 cancel 幂等与多用户隔离。
   - 不做：前端大改。
2. 触发条件与状态流转：`running -> stopping -> stopped/completed/failed`
3. 代码锚点：
   - `app/services/run_control_service.py`
   - `app/api/v1/endpoints/chat_api.py`
   - `app/services/chat_service.py`
4. 关键字段：`accepted/status/idempotent/cancel_reason`
5. 回滚锚点：
   - `ENABLE_RUN_CONTROL=false`
   - `ENABLE_SSE_STOPPED_EVENT=false`
6. 验证命令：
   - `venv/bin/python -m pytest -q tests/api/test_chat_api.py -k cancel`
   - `venv/bin/python -m pytest -q tests/unit/test_run_control_service.py tests/unit/test_chat_service_cancel_stream.py tests/unit/test_chat_service_resume_after_cancel.py`
7. 最小代码样例：

```python
result = run_control_service.cancel_run(run_id=run_id, requester_user_id=user_id, db=db)
return {"accepted": result.accepted, "status": result.status}
```

---

### 4.3 P2-01 Skill 数据迁移（老表 -> 三层）

1. 目标与边界：
   - 做：将 `t_agent_skills` 的有效记录迁移到 `definition/version`。
   - 不做：一次性删除老表。
2. 触发条件与状态流转：迁移脚本执行成功后才允许切流。
3. 代码锚点：
   - `app/models/agent_skill.py`
   - `app/services/skill_service.py`
4. 关键字段：`skill_id/version/status/published_at`
5. 回滚锚点：
   - `ENABLE_SKILL_VERSIONING=false`
   - 保留 `t_agent_skills` 兼容路径
6. 验证命令：
   - `venv/bin/python -m pytest -q tests/unit/test_skill_service.py -k "version or binding"`
7. 最小代码样例：

```python
if not definition_exists(skill_id):
    create_definition(skill_id, name)
publish_version(skill_id, version="v1", status="published")
```

---

### 4.4 P2-02 Skill 主读路径切流与回退

1. 目标与边界：
   - 做：在版本化开关开启时优先读三层路径；传递 `user_id` 绑定版本。
   - 不做：移除兼容代码。
2. 触发条件与状态流转：开关开启 + 新表数据就绪。
3. 代码锚点：
   - `app/services/skill_service.py`
   - `app/ai/workflow/multi_agent_graph.py`
4. 关键字段：`user_id/selected_skill_ids/effective_version`
5. 回滚锚点：
   - 关闭 `ENABLE_SKILL_VERSIONING` 回退旧路径。
6. 验证命令：
   - `venv/bin/python -m pytest -q tests/unit/test_multi_agent_skill_workflow.py tests/api/test_skill_admin_api.py`
7. 最小代码样例：

```python
debug_payload = SkillService.search_skills_debug(query, user_id=state.get("user_id"))
```

---

### 4.5 P3-01 工具治理配置落库与生效

1. 目标与边界：
   - 做：将策略配置从代码常量推进为 DB/ENV 可运营配置。
   - 不做：重写工具执行框架。
2. 触发条件与状态流转：策略加载 -> 过滤 -> 工具绑定。
3. 代码锚点：
   - `app/ai/workflow/multi_agent_graph.py`
   - `app/services/config_resolver.py`
4. 关键字段：`tool_governance.enabled/fail_mode/policy.*`
5. 回滚锚点：
   - `ENABLE_TOOL_GOVERNANCE=false`
   - `TOOL_POLICY_FAIL_MODE=compat`
6. 验证命令：
   - `venv/bin/python -m pytest -q tests/unit/test_multi_agent_tool_governance_runtime.py`
7. 最小代码样例：

```python
entries = _get_common_tool_entries()
tools = _apply_tool_governance_policy(entries, agent_name="supervisor")
```

---

### 4.6 P4-01 memory recall/flush 灰度上线

1. 目标与边界：
   - 做：优先 recall，稳定后再启 flush。
   - 不做：向量化记忆引擎重构。
2. 触发条件与状态流转：`memory_enabled -> recall_on -> flush_on`
3. 代码锚点：
   - `app/services/chat_service.py`
   - `app/services/user_preference_memory_service.py`
   - `app/core/config_contract.py`
4. 关键字段：`feature.enable_memory_recall`、`feature.enable_pre_compaction_flush`
5. 回滚锚点：
   - `ENABLE_MEMORY_RECALL=false`
   - `ENABLE_PRE_COMPACTION_FLUSH=false`
6. 验证命令：
   - `venv/bin/python -m pytest -q tests/unit/test_user_preference_memory_service.py tests/unit/test_chat_service_memory_flags.py`
7. 最小代码样例：

```python
if _is_memory_feature_enabled("ENABLE_MEMORY_RECALL", False):
    context = memory_service.recall(db, user_id=user_id, max_items=8)
```

---

### 4.7 P5-01 复合任务队列与汇总稳定化

1. 目标与边界：
   - 做：确保单次请求内 multi-intent 队列串行和汇总稳定。
   - 不做：跨请求积压合并（另起专题）。
2. 触发条件与状态流转：`handoff_queue -> evaluate -> summarize`
3. 代码锚点：
   - `app/ai/workflow/multi_agent_graph.py`
4. 关键字段：`handoff_queue/completed_handoffs/handoff_execution_trace`
5. 回滚锚点：关闭相关实验路径（回退到单路由响应）。
6. 验证命令：
   - `venv/bin/python -m pytest -q tests/unit/test_multi_intent_queue_flow.py`
7. 最小代码样例：

```python
if handoff_queue:
    next_handoff = handoff_queue.pop(0)
    return {"evaluation_route": "todo_expert", "pending_handoff": next_handoff}
```

---

### 4.8 P6-01 发布门禁与回滚演练

1. 目标与边界：
   - 做：形成自动判定验收报告，完成灰度与回滚脚本演练。
   - 不做：大规模文档债务一次性清零。
2. 触发条件与状态流转：`dev -> gray -> full`
3. 代码锚点：`tests/`、`scripts/docs_guard.py`、配置中心。
4. 关键字段：`pass/warn/fail`、`new_issue vs legacy_issue`
5. 回滚锚点：所有能力开关独立回退。
6. 验证命令：
   - `venv/bin/python -m pytest -q tests/unit/test_multi_agent_tool_governance_runtime.py tests/unit/test_chat_service_memory_flags.py tests/unit/test_multi_agent_skill_workflow.py tests/unit/test_multi_intent_queue_flow.py`
   - `venv/bin/python -m pytest -q tests/api/test_chat_api.py -k cancel`
   - `venv/bin/python scripts/docs_guard.py --strict`
7. 最小代码样例：

```python
if failed_count > 0:
    return "FAIL"
if legacy_doc_errors > 0:
    return "WARN"
return "PASS"
```

---

## 5. 分阶段路线图

1. 阶段 A（D1-D2）：P0 + P1（基线冻结、run 语义上线）
2. 阶段 B（D3-D4）：P2（Skill 迁移与切流）
3. 阶段 C（D5）：P3（工具治理配置落库）
4. 阶段 D（D6）：P4（记忆灰度上线）
5. 阶段 E（D7）：P5 + P6（队列稳定化、总体验收）

---

## 6. 跨模块依赖矩阵

| 模块 | 依赖上游 | 输出给下游 |
|---|---|---|
| run_control | 配置开关 | SSE/取消语义 |
| skill_service | DB 三层模型与迁移脚本 | preprocess skill 检索 |
| multi_agent_graph | skill/tool 配置 | 队列与汇总行为 |
| chat_service | memory/run 配置 | 对话流注入与终态事件 |
| config_resolver | t_system_config/ENV | 全局动态配置能力 |

---

## 7. 风险评估与回滚策略

1. Skill 切流后命中率下降：先灰度小流量，必要时回退开关。
2. 工具策略误配导致功能不可用：fail_mode 回退到 `compat`。
3. memory flush 误写导致偏好污染：先 recall 后 flush，问题时关闭 flush。
4. stopped 事件前端未适配：先关闭 stopped 开关保兼容。

---

## 8. 测试策略（TDD 前置）

```yaml
test_strategy:
  - feature_id: P1-01
    test_cases: [TC-OCF-01, TC-OCF-02]
    test_first: true
  - feature_id: P2-01
    test_cases: [TC-OCF-04, TC-OCF-05]
    test_first: true
  - feature_id: P3-01
    test_cases: [TC-OCF-03]
    test_first: true
  - feature_id: P4-01
    test_cases: [TC-OCF-06, TC-OCF-07]
    test_first: true
  - feature_id: P5-01
    test_cases: [TC-OCF-08]
    test_first: true
  - feature_id: P6-01
    test_cases: [TC-OCF-09]
    test_first: false
```

---

## 9. planning_contract（供 /jjk-vkplan 消费）

```yaml
planning_contract:
  execution_mode: serial
  card_order: [C00, C01, C02, C03, C04, C05, C06, G01, G02]
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
    inspection/question-card: policy_gate
  gate_contract:
    mode: as_cards
    gate_ids: [G01, G02]
    depends_on:
      G01: [C06]
      G02: [G01]
  cards:
    - card_id: C00
      wave: P0
      feature_ids: [P0-01]
      depends_on: []
      done_gate:
        - baseline snapshot generated
        - migration head confirmed
      acceptance_checks:
        - "venv/bin/alembic current"
      evidence_entry: "baseline snapshot"

    - card_id: C01
      wave: P1
      feature_ids: [P1-01]
      depends_on: [C00]
      done_gate:
        - cancel API idempotent
        - stopped/done semantics validated
      acceptance_checks:
        - "venv/bin/python -m pytest -q tests/api/test_chat_api.py -k cancel"
        - "venv/bin/python -m pytest -q tests/unit/test_run_control_service.py tests/unit/test_chat_service_cancel_stream.py tests/unit/test_chat_service_resume_after_cancel.py"
      evidence_entry: "run lifecycle and cancel tests"

    - card_id: C02
      wave: P2
      feature_ids: [P2-01, P2-02]
      depends_on: [C01]
      done_gate:
        - skill data migrated
        - retrieval switched with user binding support
      acceptance_checks:
        - "venv/bin/python -m pytest -q tests/unit/test_skill_service.py tests/unit/test_multi_agent_skill_workflow.py tests/api/test_skill_admin_api.py"
      evidence_entry: "skill migration and binding tests"

    - card_id: C03
      wave: P3
      feature_ids: [P3-01]
      depends_on: [C02]
      done_gate:
        - tool policy from config takes effect
      acceptance_checks:
        - "venv/bin/python -m pytest -q tests/unit/test_multi_agent_tool_governance_runtime.py"
      evidence_entry: "tool governance runtime tests"

    - card_id: C04
      wave: P4
      feature_ids: [P4-01]
      depends_on: [C03]
      done_gate:
        - recall and flush behavior validated
      acceptance_checks:
        - "venv/bin/python -m pytest -q tests/unit/test_user_preference_memory_service.py tests/unit/test_chat_service_memory_flags.py"
      evidence_entry: "memory service tests"

    - card_id: C05
      wave: P5
      feature_ids: [P5-01]
      depends_on: [C04]
      done_gate:
        - multi-intent queue summarize path stable
      acceptance_checks:
        - "venv/bin/python -m pytest -q tests/unit/test_multi_intent_queue_flow.py"
      evidence_entry: "queue and summary tests"

    - card_id: C06
      wave: P6
      feature_ids: [P6-01]
      depends_on: [C05]
      done_gate:
        - verify report generated
      acceptance_checks:
        - "venv/bin/python -m pytest -q tests/unit/test_multi_agent_tool_governance_runtime.py tests/unit/test_chat_service_memory_flags.py tests/unit/test_multi_agent_skill_workflow.py tests/unit/test_multi_intent_queue_flow.py"
        - "venv/bin/python -m pytest -q tests/api/test_chat_api.py -k cancel"
      evidence_entry: "auto verify report"

    - card_id: G01
      wave: G-1
      feature_ids: [G-1]
      depends_on: [C06]
      done_gate:
        - data/config consistency confirmed
      acceptance_checks:
        - "SELECT counts and config snapshots are consistent"
      evidence_entry: "consistency SQL snapshot"

    - card_id: G02
      wave: G-2
      feature_ids: [G-2]
      depends_on: [G01]
      done_gate:
        - end-to-end smoke and rollback drill passed
      acceptance_checks:
        - "venv/bin/python scripts/docs_guard.py --strict"
      evidence_entry: "release gate report"
```

