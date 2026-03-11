# 自动化大型任务开发（主机方案）串行拆解计划

> 计划 ID: PP-20260228-AUTO-LARGE-TASK-HOST
> 主题: 自动化大型任务开发_主机方案
> 输入来源: `docs/内部参考/迭代需求/自动化大型任务开发_主机方案_requirements.md` / `docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md`

## -1. 执行策略

- execution_mode: `serial`
- single_active_card: `true`
- card_order: ['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'G01', 'G02', 'G03', 'G04']
- gate_contract:
  - mode: `as_cards`
  - gate_ids: `[G01, G02, G03, G04]`
  - depends_on:
    - `G01: [C07]`
    - `G02: [G01]`
    - `G03: [G02]`
    - `G04: [G03]`
- auto_done_policy:
  - implementation-card: `hard_gate`
  - inspection/question-card: `policy_gate`
- 与 planning_contract 一致性: `PASS`（说明：C00 作为 preflight，默认不进入落卡序列）

### -1.1 automation_contract

```yaml
automation_contract:
  source_of_truth: workdocs/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/_active_task.json
  required_fields:
    - project_id
    - task_split_dir
    - task_key
    - execution_mode
    - single_active_card
    - auto_done_policy
    - preflight_required
  scope_match_rule:
    - title_contains_[task_key]
    - labels_contains_task_key
    - card_key_prefix_task_key
```

## 0. G0 协议冻结

- 冻结范围: `done/result/interrupt/stopped`
- required/optional:
  - required: `done/result/interrupt/stopped`
  - optional: `metadata.version`
- 兼容策略: `stopped` 作为取消终态事件，不影响既有 done 链路消费。
- 协议机读文件: `workdocs/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/sse_events_v1.json`

## 1. seed 来源

- task_key: `PP-20260228-AUTO-LARGE-TASK-HOST`
- 来源: `plan`
- card_seed 来源: `自动化大型任务开发_主机方案_implementation_plan.md::planning_contract`
- 推导依据与风险: 严格继承 feature/card 契约；风险集中在仓外规则迁移遗漏与并发触发重复执行。

### 1.1 功能机制包映射

| card_id | wave | feature_ids | 机制摘要 | 代码锚点 | 验证命令 | 回滚锚点 |
|---|---|---|---|---|---|---|
| C01 | P0 | P0-02 | 执行级互斥锁保证同一时间窗口仅一轮推进 | scripts/coder4/coder4_bootstrap_kernel.py::with_run_lock | python3 scripts/coder4/coder4_bootstrap_kernel.py --help | DISABLE_RUN_LOCK |
| C02 | P1 | P1-01 | task-runner-state 使用 write-to-temp + rename 原子写入 | scripts/coder4/coder4_bootstrap_kernel.py::atomic_write_json | python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --active-task workdocs/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/_active_task.json | task-runner-state.json.bak |
| C03 | P1 | P1-02 | load_context 在 local-mode 下只读取本地状态 | scripts/coder4/coder4_bootstrap_kernel.py::build_kernel_context | python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --apply-bootstrap --active-task workdocs/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/_active_task.json | DISABLE_AUTO_WAKE |
| C04 | P1 | P1-03 | 新增 next/verify/list 子命令支撑串行推进 | scripts/coder4/wt-flow.sh::cmd_create | bash scripts/coder4/wt-flow.sh status | WT_FLOW_ALLOW_AUTOCOMMIT=0 |
| C05 | P1 | P1-04 | 每轮执行将 gate/merge 证据内联写入 task-runner-state | scripts/coder4/coder4_bootstrap_kernel.py::record_attempt_evidence | test -f .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-runner-state.json || true | restore_attempts_archive |
| C06 | P2 | P2-01 | 将 3000 字符 payload 拆分迁移到 AGENTS/WORKFLOW/PROMPTS | docs/内部参考/迭代需求/自动化大型任务开发设计方案.md::附录 B.4 | python3 scripts/docs_guard.py --strict | scripts/coder4_external_restore.sh |
| C07 | P3 | P3-01 | 状态变更后异步 fire-and-forget 推送 VK | scripts/coder4/coder4_vk_sync.py::sync_to_vk | python3 scripts/coder4/coder4_vk_sync.py --dry-run | DISABLE_VK_SYNC |
| G01 | Gate | G-1 | 汇总 hooks token/监听地址/进程权限安全门禁 | docs/内部参考/迭代需求/自动化大型任务开发设计方案.md::17.2 | python3 scripts/docs_guard.py --strict | NO_GO_IF_SECURITY_FAIL |
| G02 | Gate | G-2 | 验证 seed->activate->dispatch->done 全链路闭环 | scripts/coder4/coder4_bootstrap_kernel.py::decide_action | python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --active-task workdocs/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/_active_task.json | FREEZE_ON_CHAIN_FAIL |
| G03 | Gate | G-3 | 校验 payload 迁移 31 项映射完整性 | docs/内部参考/迭代需求/自动化大型任务开发设计方案.md::附录 B.4 | grep -n "待迁移" docs/内部参考/迭代需求/自动化大型任务开发设计方案.md || true | ROLLBACK_TO_PLAN_IF_MISMATCH |
| G04 | Gate | G-4 | 执行备份->注入故障->恢复->复验闭环演练 | scripts/coder4_external_backup.sh | bash scripts/coder4_external_backup.sh | NO_GO_IF_RESTORE_FAIL |

## 2. 目标与边界

- 目标:
  1. 产出可直接供 `/jjk-vktodo` 落卡与自动执行器消费的串行卡片。
  2. 保证主机部署安全基线、执行闭环、迁移一致性、回滚演练四个 Gate 可独立验收。
- 非目标:
  1. 本阶段不引入外部工作流引擎。
  2. 不迁移代码执行阵地到 VPS。
- 约束:
  1. 单活串行推进（single_active_card=true）。
  2. 不重命名 implementation plan 既有 feature_id。

## 3. 架构冻结项

- 模块边界: 触发层（hooks）/编排层（kernel）/执行层（wt-flow）/状态层（state）/展示层（VK 只读）。
- 状态契约: `_active_task.json > vk_cards.json > task-runner-state.json` 层级不变。
- 路由闭环: wake/agent/cron -> kernel -> wt-flow -> done_gate -> ledger -> wake。
- 前后端链路时序: 主机本地执行，不新增跨机调用链。

## 4. 工作包总览

| WS | 名称 | 类型 | 可并行 | 依赖 |
|---|---|---|---|---|
| WS-00 | G0 协议冻结 | foundation | 否 | 无 |
| WS-C01 | P0 hooks互斥与幂等治理 | parallel | 否 | 无 |
| WS-C02 | P1 状态文件原子写与锁保护 | parallel | 否 | C01 |
| WS-C03 | P1 kernel本地模式收口 | parallel | 否 | C02 |
| WS-C04 | P1 wt-flow扩展与done_gate白名单 | parallel | 否 | C03 |
| WS-C05 | P1 attempt与ledger本地化 | parallel | 否 | C04 |
| WS-C06 | P2 payload迁移与仓外规则重写 | parallel | 否 | C05 |
| WS-C07 | P3 VK只读同步与对账 | parallel | 否 | C06 |
| WS-G01 | G-1 安全门禁闭环 | gate | 否 | C07 |
| WS-G02 | G-2 执行链路闭环 | gate | 否 | G01 |
| WS-G03 | G-3 迁移一致性闭环 | gate | 否 | G02 |
| WS-G04 | G-4 回滚演练闭环 | gate | 否 | G03 |

## 5. 合并策略

- 合并顺序: C01 -> C02 -> C03 -> C04 -> C05 -> C06 -> C07 -> G01 -> G02 -> G03 -> G04
- 回归门禁: 每卡按 acceptance_checks 执行并回填 evidence_entry。
- 回滚策略: 单卡按 rollback_anchors 回退，不跨卡混合回退。

## 6. FAIL_FAST 字段校验结果

- 校验字段: `feature_ids/mechanism_summary/code_anchor_refs/acceptance_checks/rollback_anchors/evidence_entry/task_mode/merge_required`
- 结果: `PASS`
- 缺失字段: `[]`

## 7. 双向覆盖校验结果

- forward: `PASS`（每张卡至少 1 个 feature）
- reverse: `PASS`（implementation feature 全量映射）
- orphan: `PASS`（无遗漏 feature）
- duplicate: `PASS`（无重复 feature 漂移）

## 8. 看板导出索引

- task_key: `PP-20260228-AUTO-LARGE-TASK-HOST`
- 拆解目录 ID: `2026-02-28_自动化大型任务开发_主机方案`
- cards: `C01~C07 + G01~G04`（C00 作为 preflight，默认不落卡）
- 默认列流转: `Backlog -> Doing -> Review -> Gate -> Done`
- single_active_card: `true`

## 9. 信息防丢失检查

- [x] 每个 `feature_id` 均落入某张卡（含 Gate）
- [x] 每张卡均有机制摘要 + 代码锚点 + 验收命令 + 回滚锚点
- [x] 每张卡均绑定 `evidence_entry`
- [x] `done_gate` 与 implementation_plan 主线一致
- [x] Gate 以独立卡片写入 `card_order`
