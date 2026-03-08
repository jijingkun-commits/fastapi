# 文档单一真相源与动态融合治理设计说明

> 文档版本：v1.0  
> 更新时间：2026-03-08  
> 设计状态：`pending_approval`

## 0. 结论先行

- 本方案冻结为**单轨文档治理**：`主文档只表达当前态`，`历史与决策只留在过程文档`，不再允许主文档通过“增量需求 / 实现进展 / 日期补充”持续堆叠。
- 主文档的唯一真相源冻结为：`对应功能文档中的原始章节正文`，而不是增量章节、时间线段落或实现进展附录。
- 过程文档的唯一职责冻结为：记录设计推导、实施拆解、风险与审批证据，落点固定在 `docs/plans/`、`docs/内部参考/迭代需求/`、`docs/内部参考/决策记录.md` 等内部参考层。
- 治理方式冻结为：`角色分类 + 守卫阻断 + 触达即融合（touch-once merge）`。即一旦触达某份主文档，必须把对应增量内容吸收进原章节，不允许继续追加并存版本。
- 迁移策略冻结为：不做一次性全量重写；先治理高污染主文档，再对后续触达文档执行“读旧写新、删旧归档”。

## 0.1 可审批摘要

| 维度 | 冻结结论 |
|---|---|
| 主文档职责 | 仅表达当前有效产品/架构/API 口径 |
| 历史文档职责 | 仅保留设计过程、实施计划、审计与风险轨迹 |
| 单一契约源 | 主文档原章节正文 |
| 历史迁移语义 | 读旧写新，迁移后删除主文档中的增量堆叠段 |
| 守卫策略 | `docs_guard + check_doc_sync + 角色清单` 三层阻断 |
| 迁移节奏 | 代表性脏点先治理，后续触达即融合 |
| 回退方式 | 受控 allowlist 降级，仅允许针对存量债务短时放行 |

## 1. scope_contract

- 目标:
  - 把仓库文档体系从“持续追加型”收敛为“动态融合型”。
  - 明确主文档、过程文档、审计文档的职责边界，消除口径漂移。
  - 让文档门禁从“检查有没有文档”升级到“检查文档是不是当前态”。
- 范围:
  - `docs/产品文档/*.md`
  - `docs/开发文档/架构设计/*.md`
  - `docs/API文档/*.md`
  - 文档治理脚本与门禁：`scripts/docs_guard.py`、`scripts/check_doc_sync.sh`、`.cursor/rules/doc_sync.mdc`
  - 治理说明文档：`docs/开发文档/工作流/开发工作流.md`
- 边界:
  - 不在本方案内重写全部历史文档。
  - 不取消 `docs/plans/` 与 `docs/内部参考/迭代需求/`，它们保留为过程层。
  - 不把测试报告、故障手册、防屎山记录手册强行改造成“当前态主文档”。
- 成功标准:
  - 主文档新增改动不再出现 `增量需求 / 实现进展 / 日期补充` 形式堆叠。
  - 代码变更必须更新对应主文档，而不是仅更新过程文档。
  - 触达过的高污染主文档完成同位融合，读者无需翻到文末找“最新补充”。

## 2. product_contract

### 2.1 target_users

- 仓库主维护者：需要快速确认某模块“当前到底怎么设计”。
- 需求/实现代理：需要知道应该更新哪类文档，以及更新到哪里。
- Code review / 验收人员：需要判断文档是否真正同步，而不是仅追加了一段说明。

### 2.2 core_scenarios

- 新功能上线时，开发者直接修改主文档对应章节，不再往末尾追加增量节。
- 架构规则调整时，历史原因放进 `docs/plans/` 或 `内部参考`，主文档只保留冻结后的最终口径。
- Review 时，守卫能直接指出“你改的是过程文档，不是主文档”或“你又往主文档尾部堆了增量段”。
- 老文档继续维护时，开发者能按规则把已有增量内容融回原章节，而不是越堆越长。

### 2.3 business_goals

- `current_state_doc_incremental_heading_count = 0`：治理范围内主文档禁止新增增量堆叠标题。
- `current_state_doc_timestamp_coverage = 100%`：治理范围内主文档必须带 `更新时间`。
- `doc_sync_escape_count = 0`：主文档应更新而未更新的 PR 不得通过门禁。
- `reader_latest_path_length <= 1`：读者确认“当前口径”时，最多只需打开一份主文档，不应再跳转到多个补充段落。

### 2.4 non_goals

- 不在本轮把所有历史增量一次性归并完。
- 不把防屎山记录、测试报告、审计报告这类历史型文档改成当前态说明。
- 不引入多套并行文档标准，也不保留“当前态或增量态二选一”的弹性口径。

### 2.5 acceptance_gates

- 主文档不再出现新的 `## 增量需求`、`## 实现进展`、`（YYYY-MM-DD）补充` 类型标题。
- 代表性脏点文档至少完成 3 份融合治理：`聊天系统需求`、`管理后台需求`、`AI模块设计`。
- `docs_guard` 能区分文档角色并按角色套用规则。
- `check_doc_sync` 能阻断“只更新过程文档、不更新主文档”的提交。

### 2.6 发布约束

- 新守卫默认开启。
- 对存量历史债务仅允许使用受控 allowlist 临时降级，默认值为空，且必须注明过期清理对象。
- 治理说明必须先落文档，再收紧门禁。

## 3. architecture_contract

### 3.1 模块边界

| 模块 | 职责 | 典型位置 |
|---|---|---|
| 当前态主文档层 | 描述产品/架构/API 的当前有效口径 | `docs/产品文档/`、`docs/开发文档/架构设计/`、`docs/API文档/` |
| 过程与决策层 | 记录设计推导、方案冻结、实施计划、审批证据 | `docs/plans/`、`docs/内部参考/迭代需求/` |
| 审计与历史层 | 记录故障、兼容补丁、测试报告、排障轨迹 | `docs/开发文档/架构设计/防屎山记录手册.md`、测试报告 |
| 门禁与规则层 | 识别文档角色、执行阻断、输出错误原因 | `.cursor/rules/doc_sync.mdc`、`scripts/docs_guard.py`、`scripts/check_doc_sync.sh` |

### 3.2 端到端数据流

1. 代码变更发生。
2. `doc_sync` 根据变更路径判定应该更新哪份主文档。
3. 开发者先在主文档原章节融入事实变更。
4. 若存在设计推导、风险论证或实施拆解，再补充到 `docs/plans/` 或 `内部参考/迭代需求/`。
5. `docs_guard` 校验主文档是否仍为当前态表达，是否混入增量堆叠或缺失更新时间。
6. `check_doc_sync` 校验本次提交是否只改了过程文档而漏掉主文档。
7. 通过后进入 review / merge。

### 3.3 状态生命周期

| 状态 | 载体 | 允许内容 |
|---|---|---|
| explore | `docs/plans/*-design.md` | 设计讨论、边界冻结、风险论证 |
| approved | `docs/plans/*-design.md` + 审批记录 | 冻结后的最终单方案 |
| implemented | 主文档对应章节 | 当前有效事实与约束 |
| archived | `内部参考` / 历史记录文档 | 变更来龙去脉、审计与排障证据 |

### 3.4 状态与回放语义

- `replay_canonical_field` 冻结为：`main_doc.section_body`。
- 旧式历史字段冻结为：`增量需求`、`实现进展`、`补充段`、带日期的主文档专题节。
- 迁移语义冻结为：`读旧写新`。
  - 读：允许从旧增量段中提炼事实。
  - 写：只允许写回主文档原章节正文。
  - 收口：写回完成后，旧增量段删除或迁移到过程文档。

### 3.5 异常语义

- 若主文档缺少承接章节：允许新增稳定子章节，但禁止以“增量需求（日期）”命名。
- 若变更只更新过程文档未更新主文档：`FAIL_FAST`，不得合并。
- 若主文档出现新的日期增量标题：`FAIL_FAST`，不得合并。
- 若某历史型文档天然需要时间线：必须通过角色清单或 allowlist 明确豁免，不允许靠口头约定跳过。

### 3.6 契约源唯一化

- 产品真相源：`docs/产品文档/*.md` 对应主文档章节。
- 架构真相源：`docs/开发文档/架构设计/*.md` 对应主文档章节。
- API 真相源：`docs/API文档/*.md`。
- 设计与过程真相源：`docs/plans/*.md` 与 `docs/内部参考/迭代需求/*.md`。
- 单一规则：过程层永远不能反向替代主文档成为“当前口径”。

## 4. requirement_seeds

| design_item | fr_id | trigger | input_contract | output_contract | failure_semantics | observability_fields | rollback_anchor | acceptance_cmd_ref |
|---|---|---|---|---|---|---|---|---|
| D-01-main-doc-current-state-only | FR-01 | 修改产品/架构/API 主文档 | 命中文档角色=`current_state` | 原章节正文吸收新事实，无增量段追加 | `incremental_heading_detected -> fail_fast` | `file`,`heading`,`doc_role`,`rule_id` | `legacy_allowlist` | `python3 scripts/docs_guard.py --strict` |
| D-02-history-layer-isolation | FR-02 | 需要记录设计推导或实施拆解 | 存在设计/实施证据 | 证据写入 `docs/plans/` 或 `内部参考` | `history_written_into_main_doc -> fail_fast` | `file`,`doc_role`,`evidence_type` | `process_doc_redirect` | `python3 scripts/docs_guard.py --strict` |
| D-03-touch-once-merge | FR-03 | 触达已污染主文档 | 旧增量段可读取 | 新事实融入原章节，旧段删除/迁移 | `touched_main_doc_kept_legacy_increment -> fail_fast` | `file`,`legacy_heading_count`,`migration_mode` | `legacy_allowlist` | `rg -n "增量需求|实现进展" docs/产品文档 docs/开发文档/架构设计` |
| D-04-role-based-guard | FR-04 | 执行文档守卫 | 文档角色清单可解析 | 按角色执行不同规则 | `doc_role_unknown -> fail_fast` | `file`,`doc_role`,`reason` | `doc_role_manifest` | `python3 scripts/docs_guard.py --strict` |
| D-05-timestamp-and-traceability | FR-05 | 变更主文档 | 主文档存在标准头部 | 具备 `更新时间` 与可追溯入口 | `timestamp_missing -> fail_fast` | `file`,`updated_at`,`doc_role` | `timestamp_policy` | `rg -n '^> 更新时间：' docs/产品文档 docs/开发文档/架构设计 docs/API文档` |
| D-06-main-doc-sync-required | FR-06 | 代码变更触发 doc sync | 存在路径映射 | 对应主文档必须变更 | `process_doc_only_update -> fail_fast` | `changed_code`,`required_docs`,`missing_docs` | `doc_sync_mapping` | `bash scripts/check_doc_sync.sh --diff-range origin/master...HEAD` |

## 5. implementation_seeds

| task_id | blocked_by | file_paths | symbols | change_type | verification |
|---|---|---|---|---|---|
| T01 | [] | `.cursor/rules/doc_sync.mdc`,`docs/开发文档/工作流/开发工作流.md` | `main_doc_role_policy`,`touch_once_merge_policy` | modify | `rg -n "主文档|当前态|增量需求|touch-once" .cursor/rules/doc_sync.mdc docs/开发文档/工作流/开发工作流.md` |
| T02 | [T01] | `scripts/docs_guard.py` | `current_state_doc_checks`,`doc_role_manifest`,`legacy_allowlist` | modify | `python3 scripts/docs_guard.py --strict` |
| T03 | [T01,T02] | `scripts/check_doc_sync.sh`,`.githooks/pre-commit`,`.github/workflows/doc-sync.yml` | `main_doc_sync_gate` | modify | `bash scripts/check_doc_sync.sh --diff-range origin/master...HEAD` |
| T04 | [T01] | `docs/产品文档/聊天系统需求.md`,`docs/产品文档/管理后台需求.md` | `current_state_sections` | modify | `rg -n "增量需求|实现进展" docs/产品文档/聊天系统需求.md docs/产品文档/管理后台需求.md` |
| T05 | [T01] | `docs/开发文档/架构设计/AI模块设计.md` | `current_state_architecture_sections` | modify | `rg -n "实现进展|增量需求" docs/开发文档/架构设计/AI模块设计.md` |
| T06 | [T01,T02,T03,T04,T05] | `docs/plans/2026-03-08-doc-single-source-dynamic-governance-design.md` | `design_freeze_sections` | add | `python3 scripts/docs_guard.py --strict` |

## 6. execution_chain_seed

```yaml
execution_chain_seed:
  preferred_mode: core
  task_key: PP-20260308-doc-single-source-dynamic-governance
  card_seed: [T01, T02, T03, T04, T05, T06]
  execution_contract_hint:
    delivery_mode: staged
    execution_unit: per_task
    commit_policy: single_commit
    stop_boundary: per_pr
```

## 7. risk_rollback_contract

| risk_id | 关键风险 | 触发信号 | 回退锚点 | 回退动作 |
|---|---|---|---|---|
| R01 | 新守卫过严，短期内阻塞大量存量文档提交 | 文档门禁误报激增、团队无法提交 | `legacy_allowlist` | 临时将已识别存量脏点加入 allowlist，限文档级、限时放行，迁移完成后移除 |
| R02 | 融合迁移时把历史事实删丢 | 主文档内容变短但过程证据缺失 | `docs/plans/` + `内部参考` | 先把历史事实迁入过程文档，再删除主文档旧增量段；若缺失则回退该文档改动 |
| R03 | 主文档与过程文档职责重新混淆 | review 中继续出现“只改过程文档”行为 | `doc_sync_mapping` | 收紧 `check_doc_sync`，阻断过程文档替代主文档的提交 |
| R04 | 角色分类不清导致历史型文档被误判 | `防屎山记录手册`、测试报告被错误拦截 | `doc_role_manifest` | 将角色定义显式化，按角色治理，不再按路径粗暴一刀切 |

## 8. 决策权衡

- 不做一次性全量重写，因为这会把“治理问题”变成“大规模文案工程”，风险大且很难验收。
- 不允许继续保留主文档增量堆叠，因为这正是当前质量退化的根因。
- 采用“角色清单 + 守卫 + 触达即融合”，是唯一同时满足可执行性、长期稳定性、仓库现状兼容性的方案。

## 9. 设计冻结回执（机读）

```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 4
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 6
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```

## 10. clarify_handoff_contract（机读）

```yaml
clarify_handoff_contract:
  version: v2
  topic: 文档单一真相源与动态融合治理
  design_source: docs/plans/2026-03-08-doc-single-source-dynamic-governance-design.md
  handoff_ready: true
  required:
    product_contract_summary:
      target_users: [仓库主维护者, 需求实现代理, review与验收人员]
      core_scenarios:
        - 新功能上线时直接更新主文档原章节
        - 架构调整时把历史推导留在过程文档
        - review阶段阻断只改过程文档不改主文档
        - 老文档触达时执行同位融合而不是继续堆叠
      business_goal_metrics:
        - current_state_doc_incremental_heading_count=0
        - current_state_doc_timestamp_coverage=100%
        - doc_sync_escape_count=0
        - reader_latest_path_length<=1
      non_goals:
        - 不一次性重写所有历史文档
        - 不把历史型文档强行改成当前态主文档
        - 不保留主文档双轨表达
      acceptance_gates:
        - 主文档禁止新增增量标题
        - 代表性脏点文档完成融合治理
        - docs_guard支持角色化规则
        - check_doc_sync阻断过程文档替代主文档
    requirement_seeds:
      - design_item: D-01-main-doc-current-state-only
        fr_id: FR-01
        trigger: 修改产品架构API主文档
        input_contract:
          required_fields: [doc_role, section_body]
        output_contract:
          required_fields: [section_body_updated]
        failure_semantics: incremental_heading_detected -> fail_fast
        observability_fields: [file, heading, doc_role, rule_id]
        rollback_anchor: legacy_allowlist
        acceptance_cmd_ref: python3 scripts/docs_guard.py --strict
      - design_item: D-02-history-layer-isolation
        fr_id: FR-02
        trigger: 需要记录设计推导或实施拆解
        input_contract:
          required_fields: [change_reason, design_evidence]
        output_contract:
          required_fields: [process_doc_written]
        failure_semantics: history_written_into_main_doc -> fail_fast
        observability_fields: [file, doc_role, evidence_type]
        rollback_anchor: process_doc_redirect
        acceptance_cmd_ref: python3 scripts/docs_guard.py --strict
      - design_item: D-03-touch-once-merge
        fr_id: FR-03
        trigger: 触达已污染主文档
        input_contract:
          required_fields: [legacy_increment_sections]
        output_contract:
          required_fields: [merged_section_body, legacy_section_removed]
        failure_semantics: touched_main_doc_kept_legacy_increment -> fail_fast
        observability_fields: [file, legacy_heading_count, migration_mode]
        rollback_anchor: legacy_allowlist
        acceptance_cmd_ref: rg -n "增量需求|实现进展" docs/产品文档 docs/开发文档/架构设计
      - design_item: D-04-role-based-guard
        fr_id: FR-04
        trigger: 执行文档守卫
        input_contract:
          required_fields: [doc_role_manifest]
        output_contract:
          required_fields: [role_specific_check_result]
        failure_semantics: doc_role_unknown -> fail_fast
        observability_fields: [file, doc_role, reason]
        rollback_anchor: doc_role_manifest
        acceptance_cmd_ref: python3 scripts/docs_guard.py --strict
      - design_item: D-05-timestamp-and-traceability
        fr_id: FR-05
        trigger: 更新主文档
        input_contract:
          required_fields: [doc_header]
        output_contract:
          required_fields: [updated_at]
        failure_semantics: timestamp_missing -> fail_fast
        observability_fields: [file, updated_at, doc_role]
        rollback_anchor: timestamp_policy
        acceptance_cmd_ref: rg -n '^> 更新时间：' docs/产品文档 docs/开发文档/架构设计 docs/API文档
      - design_item: D-06-main-doc-sync-required
        fr_id: FR-06
        trigger: 代码变更触发doc sync
        input_contract:
          required_fields: [changed_code, required_docs]
        output_contract:
          required_fields: [all_required_main_docs_changed]
        failure_semantics: process_doc_only_update -> fail_fast
        observability_fields: [changed_code, required_docs, missing_docs]
        rollback_anchor: doc_sync_mapping
        acceptance_cmd_ref: bash scripts/check_doc_sync.sh --diff-range origin/master...HEAD
    implementation_seeds:
      - task_id: T01
        file_paths: [.cursor/rules/doc_sync.mdc, docs/开发文档/工作流/开发工作流.md]
        symbols: [main_doc_role_policy, touch_once_merge_policy]
        change_type: modify
      - task_id: T02
        file_paths: [scripts/docs_guard.py]
        symbols: [current_state_doc_checks, doc_role_manifest, legacy_allowlist]
        change_type: modify
      - task_id: T03
        file_paths: [scripts/check_doc_sync.sh, .githooks/pre-commit, .github/workflows/doc-sync.yml]
        symbols: [main_doc_sync_gate]
        change_type: modify
      - task_id: T04
        file_paths: [docs/产品文档/聊天系统需求.md, docs/产品文档/管理后台需求.md]
        symbols: [current_state_sections]
        change_type: modify
      - task_id: T05
        file_paths: [docs/开发文档/架构设计/AI模块设计.md]
        symbols: [current_state_architecture_sections]
        change_type: modify
      - task_id: T06
        file_paths: [docs/plans/2026-03-08-doc-single-source-dynamic-governance-design.md]
        symbols: [design_freeze_sections]
        change_type: add
    execution_chain_seed:
      preferred_mode: core
      task_key: PP-20260308-doc-single-source-dynamic-governance
      card_seed: [T01, T02, T03, T04, T05, T06]
      execution_contract_hint:
        delivery_mode: staged
        execution_unit: per_task
        commit_policy: single_commit
        stop_boundary: per_pr
    alignment_contract:
      strict_match: true
      requirement_seed_ids:
        - D-01-main-doc-current-state-only
        - D-02-history-layer-isolation
        - D-03-touch-once-merge
        - D-04-role-based-guard
        - D-05-timestamp-and-traceability
        - D-06-main-doc-sync-required
      implementation_task_ids: [T01, T02, T03, T04, T05, T06]
      card_seed_ids: [T01, T02, T03, T04, T05, T06]
  extended:
    observability_hints:
      - 记录主文档增量标题命中数
      - 记录doc_role识别结果
      - 记录主文档更新时间覆盖率
    risk_counterexample_map:
      - R01: 过严门禁阻塞存量债务提交
      - R02: 融合迁移时误删历史事实
      - R03: review阶段继续只改过程文档
      - R04: 历史型文档被误判为主文档
    assumptions:
      - 过程文档体系保留，不做废弃
      - 主文档治理优先覆盖高污染文档
      - allowlist默认空且只用于迁移窗口
```

## 11. clarify_consistency_check（机读）

```yaml
clarify_consistency_check:
  clarify_phase: approval
  current_round: 1
  question_mode: package
  open_questions_count: 0
  product_contract_ready: true
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  fail_fast_codes: []
```

## 12. execution_notes

```yaml
execution_notes:
  fallback:
    brainstorming: false
    team: false
  template:
    missing: false
    source: "docs/内部参考/迭代需求/_templates/jjk_clarify_templates.md"
  question_mode: "package"
  degrade_reason: ""
  alternative_tool: ""
  verification: "repo scan + docs_guard + spot review"
```
