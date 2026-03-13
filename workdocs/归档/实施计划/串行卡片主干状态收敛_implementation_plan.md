# 实施方案（串行卡片主干状态收敛）

## 0. 计划元信息
- topic: 串行卡片主干状态收敛
- mode: parallel（plan-only）
- task_key: PP-20260303-CARDRUN-MASTER-SERIAL
- planning_intent: 将“流程串行”收敛为“主干状态串行”，确保前置依赖必须先合入 `master`。

## 1. 输入来源清单（Superpowers 对齐桥接）

1. 命令契约基线
   `workdocs/归档/需求/串行卡片主干状态收敛_requirements.md`
2. 串行执行命令
   `.cursor/commands/jjk-cardrun.md`
   `.agents/skills/jjk-cardrun/SKILL.md`
3. 落卡命令
   `.cursor/commands/jjk-vktodo.md`
   `.agents/skills/jjk-vktodo/SKILL.md`
4. 拆解命令
   `.cursor/commands/jjk-vkplan.md`
5. 执行脚本锚点
   `scripts/coder4/wt-flow.sh`
   `scripts/coder4/coder4_bootstrap_kernel.py`

> 设计审批说明：本轮来源为用户明确串行策略收敛指令，按 `DESIGN_APPROVAL_FALLBACK_ACK` 处理并进入 plan-only。

## 2. 架构影响与约束

### 2.1 模块边界
1. `vkplan` 负责契约与静态一致性，不负责执行态推进。
2. `vktodo` 负责 create-only 幂等建卡，不负责 move/作用域切换。
3. `cardrun` 负责执行态主流程（实现、验证、提交、合并、清理、续跑）。

### 2.2 状态契约
1. 实现卡状态收敛：`todo -> in_progress -> verified -> done`。
2. `done` 严格定义：`verify_passed && merged_to_master`。
3. `verify_passed` 但未合并时状态不得写 `done`。

### 2.3 路由闭环
1. 每卡必须完成 `verify -> merge` 才能激活下一卡。
2. `merge` 阶段失败时必须阻断循环并给出失败证据。

### 2.4 端到端链路
1. `vktodo` create-only 用于看板可见性与追踪，不参与执行推进。
2. 实际执行推进、依赖解锁与工作树切换全部由 `cardrun` 驱动。

### 2.5 可测试性
1. 单测/脚本验证覆盖 `verify` 与 `merge` 分离语义。
2. 集成门禁新增 IG01 校验“主干可见完成态”。
3. 显式 TC 覆盖补齐：`TC-001`、`TC-002`、`TC-003`、`TC-004`、`TC-005`。

## 3. 功能机制包（Feature Packet）

| feature_id | 目标与边界 | 触发条件与状态流转 | 代码锚点 | 关键契约字段 | 回滚锚点 | 验证命令 | 来源证据 |
|---|---|---|---|---|---|---|---|
| F1 | Gate 契约双层化（G01 流程门禁 + IG01 集成门禁） | `vkplan` 生成契约时固化 gate 模式 | `/Users/jijingkun/.codex/engineering/templates/jjk_vkplan_templates.md` `workdocs/_templates/jjk_vkplan_templates.md` | `gate_contract.gate_ids` `cards[].merge_required` | 回退到旧 gate 模板 | `python3 scripts/check_gate_contract_consistency.py --task-split-dir <dir>` | 本轮需求基线 |
| F2 | `vktodo` 收敛为 create-only | 调用 `vktodo action=move` 时直接阻断 | `.cursor/commands/jjk-vktodo.md` `.agents/skills/jjk-vktodo/SKILL.md` | `allowed_actions: [create]` | 临时恢复 legacy move（仅应急） | `python3 scripts/docs_guard.py --strict` | 本轮职责重划 |
| F3 | `cardrun` 主流程加入 per-card commit+merge | 每卡 `verify` 后进入 merge，再进入 done | `.cursor/commands/jjk-cardrun.md` `.agents/skills/jjk-cardrun/SKILL.md` | `done_definition` `merge_required` | 恢复 verify 即 done 旧逻辑（不推荐） | `bash scripts/coder4/wt-flow.sh verify C01` + `bash scripts/coder4/wt-flow.sh merge` | 当前串行断层问题 |
| F4 | `wt-flow` 状态机支持 `verified` 中间态 | verify pass 仅写 verified；merge 成功写 done | `scripts/coder4/wt-flow.sh` | `card_status_map` `last_action_result` | 回退状态机改造 | `bash scripts/coder4/wt-flow.sh status` | 脚本状态机收敛 |
| F5 | 执行证据化：子代理 + 提交合并证据 | 每卡执行后写 ledger 证据 | `scripts/coder4/coder4_bootstrap_kernel.py` | `subagent_id` `ws_file` `commit_sha` `merge_sha` | 字段降级为可选 | `python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --output -` | 可观测需求 |
| F6 | dirty 判定统一化 | preflight 和 merge 阶段采用同一白名单策略 | `scripts/coder4/wt-flow.sh` `scripts/coder4/coder4_bootstrap_kernel.py` `.cursor/commands/jjk-cardrun.md` | `dirty_policy_version` `dirty_whitelist` | 关闭白名单回退严格策略 | `git status --porcelain` 双场景验证 | 当前三处口径不一致 |
| F7 | 新增 IG01 集成门禁 | 全部实现卡 done 后执行 master 集成验收 | `scripts/coder4/check_integration_gate.py`（新增） | `integration_gate.passed` | 删除 IG01 并回退人工验收 | `python3 scripts/coder4/check_integration_gate.py --task-split-dir <dir> --baseline master` | 主干可见性诉求 |
| F8 | 新增 Gate 契约一致性校验脚本 | 计划与拆解产物生成后执行一致性检查 | `scripts/check_gate_contract_consistency.py`（新增） | `contract_consistency.passed` | 删除脚本回退人工校验 | `python3 scripts/check_gate_contract_consistency.py --task-split-dir <dir>` | 契约一致性需求 |

## 4. 最小代码样例（约束实现形态）

```python
# cardrun per-card 串行闭环（伪代码）
card = select_next_card()
dispatch_subagent(card.ws_file)
verify_ok = run_verify(card.card_id)
if not verify_ok:
    block("verify_failed")
mark_status(card.card_id, "verified")
merge_ok, merge_sha = merge_card_worktree(card.card_id)
if not merge_ok:
    block("merge_blocked")
mark_done_with_merge(card.card_id, merge_sha)
activate_next_card()
```

```bash
# vktodo create-only（伪代码）
if [[ "${action}" != "create" ]]; then
  echo "VKTODO_ACTION_NOT_ALLOWED"
  exit 1
fi
create_cards_idempotent
```

## 5. 工单级任务包（Implementation Tasks）

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: F1
    pr_id: PR-01
    phase: Phase-1
    file_paths:
      - /Users/jijingkun/.codex/engineering/templates/jjk_vkplan_templates.md
      - workdocs/_templates/jjk_vkplan_templates.md
    symbols:
      - gate_contract
      - gate_cards
    change_type: modify
    acceptance_cmds:
      - python3 scripts/check_gate_contract_consistency.py --task-split-dir <dir>
    rollback_point: 回退模板版本到变更前 tag

  - task_id: T-02
    feature_id: F2
    pr_id: PR-01
    phase: Phase-1
    file_paths:
      - .cursor/commands/jjk-vktodo.md
      - .agents/skills/jjk-vktodo/SKILL.md
    symbols:
      - 输入前置
      - 执行流程
      - 禁止项
    change_type: modify
    acceptance_cmds:
      - python3 scripts/docs_guard.py --strict
    rollback_point: 恢复 vktodo 旧动作定义

  - task_id: T-03
    feature_id: F3
    pr_id: PR-02
    phase: Phase-2
    file_paths:
      - .cursor/commands/jjk-cardrun.md
      - .agents/skills/jjk-cardrun/SKILL.md
    symbols:
      - 执行流程
      - 循环推进策略
      - 输出模板
    change_type: modify
    acceptance_cmds:
      - python3 scripts/docs_guard.py --strict
    rollback_point: 恢复 verify 通过即 done 语义

  - task_id: T-04
    feature_id: F4
    pr_id: PR-02
    phase: Phase-2
    file_paths:
      - scripts/coder4/wt-flow.sh
    symbols:
      - cmd_verify
      - cmd_merge
      - card_status_map
    change_type: modify
    acceptance_cmds:
      - bash scripts/coder4/wt-flow.sh verify C01
      - bash scripts/coder4/wt-flow.sh status
    rollback_point: 回退 wt-flow 状态机变更

  - task_id: T-05
    feature_id: F5
    pr_id: PR-03
    phase: Phase-3
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
    symbols:
      - record_attempt_evidence
      - apply_action
      - result.applied
    change_type: modify
    acceptance_cmds:
      - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --output -
    rollback_point: 去除新增证据字段，保留旧结构

  - task_id: T-06
    feature_id: F6
    pr_id: PR-03
    phase: Phase-3
    file_paths:
      - scripts/coder4/wt-flow.sh
      - scripts/coder4/coder4_bootstrap_kernel.py
      - .cursor/commands/jjk-cardrun.md
    symbols:
      - _ensure_clean
      - inspect_repo_clean
      - 工作区洁净校验
    change_type: modify
    acceptance_cmds:
      - python3 scripts/docs_guard.py --strict
    rollback_point: 关闭白名单恢复 fail-fast

  - task_id: T-07
    feature_id: F7
    pr_id: PR-04
    phase: Phase-4
    file_paths:
      - scripts/coder4/check_integration_gate.py
    symbols:
      - check_merged_cards
      - check_master_visibility
    change_type: add
    acceptance_cmds:
      - python3 scripts/coder4/check_integration_gate.py --task-split-dir <dir> --baseline master
    rollback_point: 删除 IG01 脚本并回退人工验收

  - task_id: T-08
    feature_id: F8
    pr_id: PR-04
    phase: Phase-4
    file_paths:
      - scripts/check_gate_contract_consistency.py
    symbols:
      - compare_gate_contract
      - compare_card_mapping
    change_type: add
    acceptance_cmds:
      - python3 scripts/check_gate_contract_consistency.py --task-split-dir <dir>
    rollback_point: 删除一致性校验脚本并改为人工检查
```

## 6. PR 映射契约（task_to_pr_mapping）

```yaml
task_to_pr_mapping:
  - task_id: T-01
    pr_id: PR-01
    pr_branch: codex/cardrun-master-serial-pr-01
    pr_depends_on: []
    pr_subject: "契约重划：双层 Gate 与 vktodo create-only"
    acceptance_cmds:
      - python3 scripts/check_gate_contract_consistency.py --task-split-dir <dir>
    rollback_point: 回退模板与命令文档改动
  - task_id: T-02
    pr_id: PR-01
    pr_branch: codex/cardrun-master-serial-pr-01
    pr_depends_on: []
    pr_subject: "vktodo 收敛为 create-only"
    acceptance_cmds:
      - python3 scripts/docs_guard.py --strict
    rollback_point: 恢复 vktodo 旧行为
  - task_id: T-03
    pr_id: PR-02
    pr_branch: codex/cardrun-master-serial-pr-02
    pr_depends_on:
      - PR-01
    pr_subject: "cardrun 执行链收敛：每卡 verify+merge 才可 done"
    acceptance_cmds:
      - bash scripts/coder4/wt-flow.sh verify C01
      - bash scripts/coder4/wt-flow.sh status
    rollback_point: 回退 cardrun/wt-flow 语义
  - task_id: T-04
    pr_id: PR-02
    pr_branch: codex/cardrun-master-serial-pr-02
    pr_depends_on:
      - PR-01
    pr_subject: "wt-flow 状态机中间态与合并后 done 收敛"
    acceptance_cmds:
      - bash scripts/coder4/wt-flow.sh status
    rollback_point: 回退状态机改造
  - task_id: T-05
    pr_id: PR-03
    pr_branch: codex/cardrun-master-serial-pr-03
    pr_depends_on:
      - PR-02
    pr_subject: "执行证据化：子代理与合并证据落账"
    acceptance_cmds:
      - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --output -
    rollback_point: 移除新增证据字段
  - task_id: T-06
    pr_id: PR-03
    pr_branch: codex/cardrun-master-serial-pr-03
    pr_depends_on:
      - PR-02
    pr_subject: "dirty 策略统一化"
    acceptance_cmds:
      - python3 scripts/docs_guard.py --strict
    rollback_point: 关闭白名单策略
  - task_id: T-07
    pr_id: PR-04
    pr_branch: codex/cardrun-master-serial-pr-04
    pr_depends_on:
      - PR-03
    pr_subject: "IG01 集成门禁脚本"
    acceptance_cmds:
      - python3 scripts/coder4/check_integration_gate.py --task-split-dir <dir> --baseline master
    rollback_point: 删除 IG01 脚本
  - task_id: T-08
    pr_id: PR-04
    pr_branch: codex/cardrun-master-serial-pr-04
    pr_depends_on:
      - PR-03
    pr_subject: "Gate 契约一致性脚本"
    acceptance_cmds:
      - python3 scripts/check_gate_contract_consistency.py --task-split-dir <dir>
    rollback_point: 删除一致性脚本
```

## 7. 机读执行契约（planning_contract）

```yaml
planning_contract:
  execution_mode: serial
  strict_single_active_card: true
  done_definition: verify_passed_and_merged
  auto_done_policy:
    implementation-card: hard_gate
    inspection-card: policy_gate
  gate_contract:
    mode: as_cards
    gate_ids: [G01, IG01]
    depends_on:
      G01: [C05]
      IG01: [G01]
  card_order: [C01, C02, C03, C04, C05, G01, IG01]
  cards:
    - card_id: C01
      feature_ids: [F1, F2]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 契约模板与命令职责重划完成
      acceptance_checks:
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/实施计划/串行卡片主干状态收敛_implementation_plan.md
    - card_id: C02
      feature_ids: [F3]
      depends_on: [C01]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - cardrun 新流程文档与执行约束已生效
      acceptance_checks:
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/实施计划/串行卡片主干状态收敛_implementation_plan.md
    - card_id: C03
      feature_ids: [F4]
      depends_on: [C02]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - verify 不直接 done，merge 成功后 done
      acceptance_checks:
        - bash scripts/coder4/wt-flow.sh status
      evidence_entry: workdocs/归档/实施计划/串行卡片主干状态收敛_implementation_plan.md
    - card_id: C04
      feature_ids: [F5]
      depends_on: [C03]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - ledger 具备子代理与提交合并证据
      acceptance_checks:
        - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --output -
      evidence_entry: workdocs/归档/实施计划/串行卡片主干状态收敛_implementation_plan.md
    - card_id: C05
      feature_ids: [F6]
      depends_on: [C04]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - dirty 策略三处口径一致
      acceptance_checks:
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/实施计划/串行卡片主干状态收敛_implementation_plan.md
    - card_id: G01
      feature_ids: [F8]
      depends_on: [C05]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - Gate 契约一致性校验通过
      acceptance_checks:
        - python3 scripts/check_gate_contract_consistency.py --task-split-dir <dir>
      evidence_entry: workdocs/归档/实施计划/串行卡片主干状态收敛_implementation_plan.md
    - card_id: IG01
      feature_ids: [F7]
      depends_on: [G01]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - 实现卡已合并主干且主干回归通过
      acceptance_checks:
        - python3 scripts/coder4/check_integration_gate.py --task-split-dir <dir> --baseline master
      evidence_entry: workdocs/归档/实施计划/串行卡片主干状态收敛_implementation_plan.md
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/cardrun-master-serial-pr-01
      pr_depends_on: []
      pr_subject: "契约重划：双层 Gate 与 vktodo create-only"
      acceptance_cmds:
        - python3 scripts/docs_guard.py --strict
      rollback_point: 回退模板与命令文档
    - task_id: T-03
      pr_id: PR-02
      pr_branch: codex/cardrun-master-serial-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "cardrun 每卡提交并合并主干"
      acceptance_cmds:
        - bash scripts/coder4/wt-flow.sh status
      rollback_point: 回退 cardrun/wt-flow 语义
    - task_id: T-05
      pr_id: PR-03
      pr_branch: codex/cardrun-master-serial-pr-03
      pr_depends_on: [PR-02]
      pr_subject: "执行证据化与 dirty 策略统一"
      acceptance_cmds:
        - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --output -
      rollback_point: 回退 kernel 证据字段与 dirty 策略
    - task_id: T-07
      pr_id: PR-04
      pr_branch: codex/cardrun-master-serial-pr-04
      pr_depends_on: [PR-03]
      pr_subject: "IG01 集成门禁与契约一致性校验"
      acceptance_cmds:
        - python3 scripts/coder4/check_integration_gate.py --task-split-dir <dir> --baseline master
        - python3 scripts/check_gate_contract_consistency.py --task-split-dir <dir>
      rollback_point: 删除新增门禁脚本并回退文档契约
```

## 8. 交付执行契约（execution_contract）

```yaml
execution_contract:
  delivery_mode: staged
  execution_unit: per_card
  commit_policy: per_card
  merge_policy: per_card_to_master
  stop_boundary: per_card
  stop_on_blocked: true
```

## 9. 实施就绪结论

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: $jjk-vkplan
  execution_contract_ready: true
```
