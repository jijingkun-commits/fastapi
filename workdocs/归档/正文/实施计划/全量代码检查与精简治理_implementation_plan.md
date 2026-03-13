# 实施方案（全量代码检查与精简治理）

> 主题：全量代码检查与精简治理
> 日期：2026-03-02
> 模式：`jjk-plan core`（plan-only）
> 对应需求：`/Users/jijingkun/bojxAI/fastapi/workdocs/归档/正文/需求/全量代码检查与精简治理_requirements.md`

---

## 0. 设计审批与输入来源（强制门禁）

### 0.1 设计审批校验

- 设计文档：`/Users/jijingkun/bojxAI/fastapi/workdocs/归档/正文/设计/2026-03-02-full-code-audit-slimming-design.md`
- 审批记录：`design_approved: true`
- 审批时间：`2026-03-02 16:40 CST`
- 审批轮次：`round-2`
- `DESIGN_APPROVAL_FALLBACK_ACK`: false

### 0.2 输入来源清单（Superpowers 产物桥接）

1. `workdocs/归档/正文/设计/2026-03-02-full-code-audit-slimming-design.md`
2. `docs/开发文档/规范/bugfix-minimal-change.md`
3. `scripts/ci/check_bugfix_budget.py`
4. `.github/workflows/bugfix-guard.yml`
5. `.github/workflows/doc-sync.yml`
6. 热点代码锚点：
   - `app/ai/workflow/multi_agent_graph.py`
   - `app/services/chat_service.py`
   - `app/ai/workflow/data_graph.py`
   - `app/ai/workflow/todo_graph.py`
   - `web/src/components/admin/overview/AdminOverviewCockpit.tsx`
   - `web/src/hooks/useSSEStream.ts`

`SUPERPOWERS_ARTIFACT_UNALIGNED`: false

### 0.3 执行意图门禁

- 用户当前指令为“编写需求和执行计划”，本轮仅输出 WHAT + HOW，不进入实施。
- `plan_mode`: `plan-only`
- 不自动触发：`$jjk-vkplan`、`$jjk-vktodo`、`$jjk-imp`

### 0.4 Team 判定与交叉质检（摘要）

- `module_count=5`、`boundary_count=4`、`uncertainty_count=3`、`estimated_file_count>=20`，命中大任务阈值。
- 抽检互审（20% 最少 1 项）：
  1. 质疑点：`feature/refactor` 缺少硬门禁是否会持续“只加不减”
  2. 验证命令：`python3 scripts/ci/check_bugfix_budget.py --diff-range origin/master...HEAD --mode auto`
  3. 结论：通过（确认仅 bugfix 命中，feature/refactor 需补强）

---

## 1. 架构影响与约束（必查项）

### 1.1 模块边界

1. 治理策略归属 `rules + CI + PR 模板`，禁止散落到业务代码随机分支。
2. 工作流重构归属 `app/ai/workflow/*`，服务层只保留编排接口，不重复策略实现。
3. SSE 链路收敛归属 `app/services/chat_service.py` 与 `web/src/hooks/useSSEStream.ts`，前后端保持单一事件语义。
4. 前端管理台拆分归属 `web/src/components/admin/*` 与 `web/src/lib/*-api.ts`，禁止组件与适配层重复兜底。

### 1.2 状态契约

1. fallback canonical 字段：`fallback_route`、`fallback_reason`、`reason_code`。
2. 流式 canonical 字段：`thread_id`、`run_id`、`status`、`interrupt_state`。
3. 门禁 canonical 字段：`pr_type`、`changed_files`、`added`、`deleted`、`net_added`、`retirement_checklist`。

### 1.3 路由闭环

1. 规划入口：`requirements -> implementation_plan -> planning_contract`。
2. 执行入口（后续显式指令才开启）：`vkplan -> vktodo -> imp-ws/imp`。
3. 回滚入口：每个 task 都必须定义 `rollback_point`，不得口头回滚。

### 1.4 端到端链路一致性

1. 后端 stream/resume 与前端 submit/resume 保持同构事件生命周期。
2. fallback 仅作为保底路径，禁止漂移成主路径。
3. CI 门禁失败时阻断合并，避免“先合并后修治理”。

### 1.5 可测试性

1. 每个 feature_id 至少 1 条最小验收命令。
2. 每条 task 至少 1 条可执行 `acceptance_cmds`。
3. Gate 卡必须使用可执行命令，不允许“人工判断通过”。

---

## 2. 方案决策（规划层）

| 方案 | 优点 | 缺点 | 成本 | 推荐度 |
|---|---|---|---|---|
| A. 报告优先，不改门禁 | 交付快 | 无法防反弹 | 低 | ⭐⭐⭐ |
| B. 轻门禁 + 局部重构 | 风险可控 | 收敛深度有限 | 中 | ⭐⭐⭐⭐ |
| C. 强门禁 + 分波次重构（采用） | 历史债务与未来反弹一起治理 | 对执行纪律要求高 | 高 | ⭐⭐⭐⭐⭐ |

---

## 3. Feature Packet（功能机制包，必填）

| feature_id | card_id | 目标与边界 | 触发条件与状态流转 | 代码锚点（文件+符号） | 契约字段 | 回滚锚点 | 验证命令 | 来源证据 |
|---|---|---|---|---|---|---|---|---|
| P1-01 | C01 | 全量热点审计台账；不改业务逻辑 | 扫描执行 -> 输出热点分级 -> 固化台账 | `scripts/ci/check_change_budget.py`（新增）；`workdocs/归档/正文/设计/2026-03-02-full-code-audit-slimming-design.md` | `module/type/risk/evidence` | 回退到只读报告模式 | `python3 scripts/ci/check_change_budget.py --mode always --strict --diff-range origin/master...HEAD` | design §1.2 |
| P1-02 | C01 | 兜底分支登记与退役机制；不改业务接口 | 新增 fallback -> 必须登记 -> 到期退役 | `docs/开发文档/架构设计/防屎山记录手册.md`；`.cursor/rules/doc_sync.mdc` | `fallback_id/owner/expire_at` | 关闭强制登记开关并恢复旧流程 | `python3 scripts/check_special_doc_sync.py --strict` | design §4.2 |
| P2-01 | C02 | multi_agent/chat 主链减法重构 | 拆分编排 -> 统一事件分发 -> 收敛 fallback 出口 | `app/ai/workflow/multi_agent_graph.py:create_multi_agent_graph`；`app/services/chat_service.py:stream`；`app/services/chat_service.py:sse_resume_stream` | `fallback_route/reason_code/run_id` | 开关回退 legacy dispatcher | `venv/bin/python -m pytest -q tests/unit/test_multi_agent_fallback.py tests/unit/test_chat_service_resume_after_cancel.py` | design §4.5 W1 |
| P2-02 | C03 | data/todo 节点切片与策略单点化 | 切分意图与执行节点 -> 合并降级策略 -> 回归 | `app/ai/workflow/data_graph.py:analyze_data_intent`；`app/ai/workflow/data_graph.py:sql_execute`；`app/ai/workflow/todo_graph.py:analyze_intent` | `intent_mode/recovery_policy/state_patch` | 切回旧节点路由 | `venv/bin/python -m pytest -q tests/unit/test_data_graph_clarify_guard.py tests/unit/test_todo_graph_semantic_guard.py` | design §4.5 W2 |
| P3-01 | C04 | 前端 Admin/SSE/API 去冗余 | 拆组件与 hooks -> 统一 requestJson -> 类型收紧 | `web/src/components/admin/overview/AdminOverviewCockpit.tsx`；`web/src/hooks/useSSEStream.ts`；`web/src/lib/data-admin-api.ts` | `loading_state/stream_status/error_shape` | 组件拆分回滚到 monolith 版本 | `cd web && pnpm lint` | design §4.5 W3 |
| P4-01 | C05 | feature/refactor 强门禁上线 | PR 触发 -> 预算与减法检查 -> 通过/阻断 | `.github/workflows/change-balance.yml`（新增）；`scripts/ci/check_change_budget.py`（新增）；`.github/pull_request_template.md` | `pr_type/added/deleted/net_added/retirement_checklist` | 暂时降级为 warning 模式 | `python3 scripts/ci/check_change_budget.py --mode always --strict --diff-range origin/master...HEAD` | design §4.2 |
| P4-02 | C05 | 规则同步与提示词收敛 | AGENTS/rules 更新 -> hook 同步 -> docs_guard 校验 | `AGENTS.md`；`.cursor/rules/bugfix-minimal-change.mdc`；`scripts/sync_rules_to_cc.py` | `policy_version/effective_scope` | 回滚规则提交并保留旧门禁 | `python3 scripts/sync_rules_to_cc.py && python3 scripts/docs_guard.py --strict` | design §3 |
| P5-01 | G01 | 全链路回归与证据归档 | 核心测试 + docs_guard + Gate 卡放行 | `tests/unit/*`；`docs/SUMMARY.md`；`workdocs/归档/正文/实施计划/全量代码检查与精简治理_implementation_plan.md` | `gate_result/evidence_entry` | Gate 不通过则阻断后续实施 | `venv/bin/python -m pytest -q tests/unit/test_multi_agent_fallback.py tests/unit/test_chat_service_done_payload.py tests/unit/test_data_graph_semantic_guard.py` | design §4.4 |

---

## 4. 最小代码样例（每个 feature 至少一条）

```python
# P1-01: 统一预算检查入口（示意）
def evaluate_change_budget(diff_stats: dict, pr_type: str) -> dict:
    rules = load_budget_rules(pr_type)
    return {"passed": check_rules(diff_stats, rules), "violations": collect_violations(diff_stats, rules)}
```

```python
# P2-01: stream/resume 共用分发器（示意）
def dispatch_stream_event(event, ctx):
    handlers = build_common_handlers(ctx)
    return handlers.get(event.type, handle_unknown)(event)
```

```python
# P2-02: data/todo 降级策略单点化（示意）
def apply_recovery_policy(state, reason_code):
    policy = RecoveryPolicyRegistry.resolve(reason_code)
    return policy.patch(state)
```

```ts
// P3-01: 前端统一请求适配（示意）
export async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(url, init);
  if (!res.ok) throw await normalizeApiError(res);
  return (await res.json()) as T;
}
```

```yaml
# P4-01: PR 退场清单校验（示意）
retirement_check:
  required: true
  fields: [removed_paths, no_delete_reason, debt_card, deadline]
```

```yaml
# P5-01: Gate 放行（示意）
gate_result:
  id: G01
  status: PASS
  evidence:
    - tests_green
    - docs_guard_green
```

---

## 5. 测试策略（TDD 前置，推荐）

```yaml
test_strategy:
  - feature_id: P2-01
    test_cases:
      - TC-SLIM-01: fallback 路由收敛后 reason_code 保持一致
      - TC-SLIM-02: stream/resume 共用分发器后 done 事件不重复
    test_first: true
  - feature_id: P2-02
    test_cases:
      - TC-SLIM-03: data_graph 节点切片后空结果恢复策略不漂移
      - TC-SLIM-04: todo_graph 意图收敛后状态迁移保持一致
    test_first: true
  - feature_id: P3-01
    test_cases:
      - TC-SLIM-05: Admin 组件拆分后 loading/error 状态一致
      - TC-SLIM-06: requestJson 统一后错误透传一致
    test_first: false
```

---

## 6. Implementation Tasks（工单级 HOW，必填）

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: P1-01
    phase: Phase-0
    pr_id: PR-01
    file_paths:
      - scripts/ci/check_change_budget.py
      - workdocs/归档/正文/实施计划/全量代码检查与精简治理_implementation_plan.md
    symbols:
      - evaluate_change_budget
      - summarize_budget
    change_type: add
    acceptance_cmds:
      - python3 scripts/ci/check_change_budget.py --mode always --strict --diff-range origin/master...HEAD
    rollback_point: 临时切回 scripts/ci/check_bugfix_budget.py 单脚本门禁

  - task_id: T-02
    feature_id: P1-02
    phase: Phase-0
    pr_id: PR-01
    file_paths:
      - docs/开发文档/架构设计/防屎山记录手册.md
      - .cursor/rules/doc_sync.mdc
    symbols:
      - fallback_registry
      - special_case_sync_policy
    change_type: modify
    acceptance_cmds:
      - python3 scripts/check_special_doc_sync.py --strict
    rollback_point: 回退 fallback 强制登记段落并保留历史记录

  - task_id: T-03
    feature_id: P2-01
    phase: Phase-1
    pr_id: PR-02
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/services/chat_service.py
    symbols:
      - create_multi_agent_graph
      - stream
      - sse_resume_stream
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_multi_agent_fallback.py tests/unit/test_chat_service_resume_after_cancel.py
    rollback_point: 切回 legacy dispatcher 与旧 fallback 路由

  - task_id: T-04
    feature_id: P2-01
    phase: Phase-1
    pr_id: PR-02
    file_paths:
      - app/services/chat_service.py
      - tests/unit/test_chat_service_done_payload.py
    symbols:
      - _dispatch_stream_event
      - _finalize_stream_result
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_service_resume_after_cancel.py
    rollback_point: 关闭 shared_dispatcher 开关并回退到双路径逻辑

  - task_id: T-05
    feature_id: P2-02
    phase: Phase-2
    pr_id: PR-03
    file_paths:
      - app/ai/workflow/data_graph.py
      - app/ai/workflow/todo_graph.py
    symbols:
      - analyze_data_intent
      - sql_execute
      - analyze_intent
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_data_graph_clarify_guard.py tests/unit/test_todo_graph_semantic_guard.py
    rollback_point: 回退到 pre-split graph 版本

  - task_id: T-06
    feature_id: P3-01
    phase: Phase-3
    pr_id: PR-04
    file_paths:
      - web/src/components/admin/overview/AdminOverviewCockpit.tsx
      - web/src/hooks/useSSEStream.ts
      - web/src/lib/data-admin-api.ts
    symbols:
      - AdminOverviewCockpit
      - useSSEStream
      - requestJson
    change_type: modify
    acceptance_cmds:
      - cd web && pnpm lint
    rollback_point: 回退组件拆分提交并恢复原调用路径

  - task_id: T-07
    feature_id: P4-01
    phase: Phase-4
    pr_id: PR-05
    file_paths:
      - .github/workflows/change-balance.yml
      - scripts/ci/check_change_budget.py
      - .github/pull_request_template.md
    symbols:
      - check_change_budget
      - retirement_checklist
    change_type: add_modify
    acceptance_cmds:
      - python3 scripts/ci/check_change_budget.py --mode always --strict --diff-range origin/master...HEAD
    rollback_point: 将 change-balance workflow 降级为 non-blocking

  - task_id: T-08
    feature_id: P4-02
    phase: Phase-4
    pr_id: PR-05
    file_paths:
      - AGENTS.md
      - .cursor/rules/bugfix-minimal-change.mdc
      - scripts/sync_rules_to_cc.py
    symbols:
      - policy_contract
      - bugfix_budget_rules
    change_type: modify
    acceptance_cmds:
      - python3 scripts/sync_rules_to_cc.py
      - python3 scripts/docs_guard.py --strict
    rollback_point: 回退规则变更并恢复旧版指令

  - task_id: T-09
    feature_id: P5-01
    phase: Phase-5
    pr_id: PR-06
    file_paths:
      - docs/SUMMARY.md
      - workdocs/归档/正文/需求/全量代码检查与精简治理_requirements.md
      - workdocs/归档/正文/实施计划/全量代码检查与精简治理_implementation_plan.md
    symbols:
      - planning_contract
      - implementation_readiness
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_multi_agent_fallback.py tests/unit/test_chat_service_done_payload.py tests/unit/test_data_graph_semantic_guard.py
      - python3 scripts/docs_guard.py --strict
    rollback_point: 保留执行证据并撤销本轮治理发布
```

---

## 7. task_to_pr_mapping（必填）

```yaml
task_to_pr_mapping:
  - task_id: T-01
    pr_id: PR-01
    pr_branch: codex/full-code-slim-pr-01
    pr_subject: "P1 基线：全量审计脚本与兜底登记机制"
    pr_depends_on: []
    acceptance_cmds:
      - python3 scripts/ci/check_change_budget.py --mode always --strict --diff-range origin/master...HEAD
    rollback_point: 回退到 bugfix-only 门禁

  - task_id: T-02
    pr_id: PR-01
    pr_branch: codex/full-code-slim-pr-01
    pr_subject: "P1 基线：防屎山登记口径收敛"
    pr_depends_on: []
    acceptance_cmds:
      - python3 scripts/check_special_doc_sync.py --strict
    rollback_point: 回退 doc_sync 特殊处理校验

  - task_id: T-03
    pr_id: PR-02
    pr_branch: codex/full-code-slim-pr-02
    pr_subject: "P2 后端主链：multi_agent + chat_service 收敛"
    pr_depends_on: [PR-01]
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_multi_agent_fallback.py tests/unit/test_chat_service_resume_after_cancel.py
    rollback_point: 恢复 legacy dispatcher

  - task_id: T-04
    pr_id: PR-02
    pr_branch: codex/full-code-slim-pr-02
    pr_subject: "P2 后端主链：stream/resume 分发统一"
    pr_depends_on: [PR-01]
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_chat_service_done_payload.py
    rollback_point: 回退 shared_dispatcher

  - task_id: T-05
    pr_id: PR-03
    pr_branch: codex/full-code-slim-pr-03
    pr_subject: "P2 数据与待办：节点切片与恢复策略单点化"
    pr_depends_on: [PR-02]
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_data_graph_clarify_guard.py tests/unit/test_todo_graph_semantic_guard.py
    rollback_point: 回退 pre-split graph

  - task_id: T-06
    pr_id: PR-04
    pr_branch: codex/full-code-slim-pr-04
    pr_subject: "P3 前端：Admin/SSE/API 去冗余"
    pr_depends_on: [PR-03]
    acceptance_cmds:
      - cd web && pnpm lint
    rollback_point: 回退前端拆分提交

  - task_id: T-07
    pr_id: PR-05
    pr_branch: codex/full-code-slim-pr-05
    pr_subject: "P4 流程：change-balance CI 门禁"
    pr_depends_on: [PR-04]
    acceptance_cmds:
      - python3 scripts/ci/check_change_budget.py --mode always --strict --diff-range origin/master...HEAD
    rollback_point: 将 workflow 改回 warning

  - task_id: T-08
    pr_id: PR-05
    pr_branch: codex/full-code-slim-pr-05
    pr_subject: "P4 流程：规则与提示词收敛"
    pr_depends_on: [PR-04]
    acceptance_cmds:
      - python3 scripts/sync_rules_to_cc.py
      - python3 scripts/docs_guard.py --strict
    rollback_point: 回退规则版本

  - task_id: T-09
    pr_id: PR-06
    pr_branch: codex/full-code-slim-pr-06
    pr_subject: "P5 收口：回归证据与文档归档"
    pr_depends_on: [PR-05]
    acceptance_cmds:
      - python3 scripts/docs_guard.py --strict
    rollback_point: 阻断发布并保留修复窗口
```

---

## 8. planning_contract（供后续 vkplan 消费）

```yaml
planning_contract:
  execution_mode: serial
  card_order: [C01, C02, C03, C04, C05, G01]
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
    inspection/question-card: policy_gate
  gate_contract:
    mode: as_cards
    gate_ids: [G01]
    depends_on:
      G01: [C05]
  cards:
    - card_id: C01
      wave: P1
      feature_ids: [P1-01, P1-02]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 全量热点审计台账完成
        - fallback 登记机制可执行
      acceptance_checks:
        - python3 scripts/ci/check_change_budget.py --mode always --strict --diff-range origin/master...HEAD
        - python3 scripts/check_special_doc_sync.py --strict
      evidence_entry: workdocs/归档/正文/实施计划/全量代码检查与精简治理_implementation_plan.md

    - card_id: C02
      wave: P2
      feature_ids: [P2-01]
      depends_on: [C01]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - multi_agent 与 chat_service 主链收敛
      acceptance_checks:
        - venv/bin/python -m pytest -q tests/unit/test_multi_agent_fallback.py tests/unit/test_chat_service_resume_after_cancel.py
      evidence_entry: workdocs/归档/正文/实施计划/全量代码检查与精简治理_implementation_plan.md

    - card_id: C03
      wave: P2
      feature_ids: [P2-02]
      depends_on: [C02]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - data/todo 节点完成切片并通过回归
      acceptance_checks:
        - venv/bin/python -m pytest -q tests/unit/test_data_graph_clarify_guard.py tests/unit/test_todo_graph_semantic_guard.py
      evidence_entry: workdocs/归档/正文/实施计划/全量代码检查与精简治理_implementation_plan.md

    - card_id: C04
      wave: P3
      feature_ids: [P3-01]
      depends_on: [C03]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - Admin/SSE/API 去冗余完成
      acceptance_checks:
        - cd web && pnpm lint
      evidence_entry: workdocs/归档/正文/实施计划/全量代码检查与精简治理_implementation_plan.md

    - card_id: C05
      wave: P4
      feature_ids: [P4-01, P4-02]
      depends_on: [C04]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - change-balance CI 门禁上线
        - 规则同步与文档校验通过
      acceptance_checks:
        - python3 scripts/ci/check_change_budget.py --mode always --strict --diff-range origin/master...HEAD
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/正文/实施计划/全量代码检查与精简治理_implementation_plan.md

    - card_id: G01
      wave: Gate
      feature_ids: [P5-01]
      depends_on: [C05]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - 核心回归与 docs_guard 全绿
        - 证据归档完成
      acceptance_checks:
        - venv/bin/python -m pytest -q tests/unit/test_multi_agent_fallback.py tests/unit/test_chat_service_done_payload.py tests/unit/test_data_graph_semantic_guard.py
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/正文/实施计划/全量代码检查与精简治理_implementation_plan.md

  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/full-code-slim-pr-01
      pr_subject: "P1 基线：审计脚本与兜底登记"
      pr_depends_on: []
      acceptance_cmds:
        - python3 scripts/ci/check_change_budget.py --mode always --strict --diff-range origin/master...HEAD
      rollback_point: 回退到 bugfix-only 门禁
    - task_id: T-02
      pr_id: PR-01
      pr_branch: codex/full-code-slim-pr-01
      pr_subject: "P1 基线：特殊处理登记收敛"
      pr_depends_on: []
      acceptance_cmds:
        - python3 scripts/check_special_doc_sync.py --strict
      rollback_point: 回退 doc_sync 特殊处理校验
    - task_id: T-03
      pr_id: PR-02
      pr_branch: codex/full-code-slim-pr-02
      pr_subject: "P2 后端主链收敛"
      pr_depends_on: [PR-01]
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_multi_agent_fallback.py tests/unit/test_chat_service_resume_after_cancel.py
      rollback_point: 恢复 legacy dispatcher
    - task_id: T-04
      pr_id: PR-02
      pr_branch: codex/full-code-slim-pr-02
      pr_subject: "P2 流式事件分发统一"
      pr_depends_on: [PR-01]
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_chat_service_done_payload.py
      rollback_point: 回退 shared_dispatcher
    - task_id: T-05
      pr_id: PR-03
      pr_branch: codex/full-code-slim-pr-03
      pr_subject: "P2 data/todo 节点切片"
      pr_depends_on: [PR-02]
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_data_graph_clarify_guard.py tests/unit/test_todo_graph_semantic_guard.py
      rollback_point: 回退 pre-split graph
    - task_id: T-06
      pr_id: PR-04
      pr_branch: codex/full-code-slim-pr-04
      pr_subject: "P3 前端 Admin/SSE/API 去冗余"
      pr_depends_on: [PR-03]
      acceptance_cmds:
        - cd web && pnpm lint
      rollback_point: 回退前端拆分提交
    - task_id: T-07
      pr_id: PR-05
      pr_branch: codex/full-code-slim-pr-05
      pr_subject: "P4 change-balance CI 门禁"
      pr_depends_on: [PR-04]
      acceptance_cmds:
        - python3 scripts/ci/check_change_budget.py --mode always --strict --diff-range origin/master...HEAD
      rollback_point: workflow 改回 warning
    - task_id: T-08
      pr_id: PR-05
      pr_branch: codex/full-code-slim-pr-05
      pr_subject: "P4 规则同步与提示词收敛"
      pr_depends_on: [PR-04]
      acceptance_cmds:
        - python3 scripts/sync_rules_to_cc.py
        - python3 scripts/docs_guard.py --strict
      rollback_point: 回退规则版本
    - task_id: T-09
      pr_id: PR-06
      pr_branch: codex/full-code-slim-pr-06
      pr_subject: "P5 回归证据收口"
      pr_depends_on: [PR-05]
      acceptance_cmds:
        - python3 scripts/docs_guard.py --strict
      rollback_point: 阻断发布并进入修复窗口
```

---

## 9. execution_contract（必填）

```yaml
execution_contract:
  delivery_mode: one_shot
  execution_unit: all_tasks
  commit_policy: single_commit
  stop_boundary: none
  stop_on_blocked: true
```

---

## 10. implementation_readiness（机读结论）

```yaml
implementation_readiness:
  implementation_ready: false
  blocked_by:
    - PLAN_EXECUTION_INTENT_REQUIRED
  next_step: $jjk-plan
  execution_contract_ready: true
```

---

## 11. 规划结论与下一步

1. WHAT + HOW 主产物已齐备，可用于后续执行拆解。
2. 当前停在规划阶段，不自动进入实施链。
3. 若用户明确“开始执行/落地”，再进入 `$jjk-vkplan` 或 `$jjk-imp`。

