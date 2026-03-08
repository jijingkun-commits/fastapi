# 文档单一真相源与动态融合治理需求文档

> 更新时间：2026-03-08 14:35 +08:00
> 上游设计：`docs/plans/2026-03-08-doc-single-source-dynamic-governance-design.md`
> 文档目标：定义 WHAT（需求合同、验收门禁、追溯矩阵），供 `文档单一真相源与动态融合治理_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 核心目标

- 将仓库文档治理从“增量追加型”收敛为“动态融合型”。
- 固定主文档职责为“只表达当前态”，禁止再用增量章节承载最新口径。
- 固定过程文档职责为“记录设计、计划、审批与风险证据”，不得反向替代主文档。
- 固定门禁职责为“自动阻断主文档堆叠、漏同步、缺更新时间”，不再依赖人工 review 兜底。

### 1.2 范围

- 主文档层：`docs/产品文档/*.md`、`docs/开发文档/架构设计/*.md`、`docs/API文档/*.md`
- 过程文档层：`docs/plans/*.md`、`docs/内部参考/迭代需求/*.md`
- 规则与门禁：`.cursor/rules/doc_sync.mdc`、`scripts/docs_guard.py`、`scripts/check_doc_sync.sh`
- 治理手册与索引：`docs/开发文档/工作流/开发工作流.md`、`docs/SUMMARY.md`

### 1.3 非范围

- 不在本轮一次性清洗所有历史主文档。
- 不废弃 `docs/plans/` 与 `docs/内部参考/迭代需求/`。
- 不将测试报告、故障报告、防屎山记录手册强制改造成当前态主文档。

## 2. requirements_contract（机读）

```yaml
requirements_contract:
  topic: "文档单一真相源与动态融合治理"
  status: approved
  design_source: docs/plans/2026-03-08-doc-single-source-dynamic-governance-design.md
  clarify_handoff_source: docs/plans/2026-03-08-doc-single-source-dynamic-governance-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户明确回复‘确认’"
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
  owner: "doc-governance"
  approver: "jijingkun"
  updated_at: "2026-03-08 14:35 +08:00"
```

## 3. product_contract_matrix（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - 仓库主维护者
    - 需求/实现代理
    - review 与验收人员
  core_scenarios:
    - 新功能上线时直接更新主文档原章节
    - 架构调整时把设计推导写入过程文档而不是主文档补充段
    - review 阶段阻断“只改过程文档不改主文档”
    - 触达存量污染主文档时执行同位融合
  business_goal_metrics:
    - current_state_doc_incremental_heading_count=0
    - current_state_doc_timestamp_coverage=100%
    - doc_sync_escape_count=0
    - reader_latest_path_length<=1
  non_goals:
    - 一次性重写所有历史文档
    - 废弃过程文档体系
    - 把历史型文档强制纳入当前态主文档治理
  acceptance_gates:
    - DSG-AC-01
    - DSG-AC-02
    - DSG-AC-03
    - DSG-AC-04
    - DSG-AC-05
    - DSG-AC-06
  release_constraints:
    - DOC_DYNAMIC_MERGE_GUARD 默认 true，回退为 false
    - DOC_PROCESS_LAYER_ENFORCED 默认 true，回退为 false
    - DOC_TOUCH_ONCE_MERGE 默认 true，回退为 false
    - DOC_ROLE_GUARD 默认 true，回退为 false
    - DOC_TIMESTAMP_REQUIRED 默认 true，回退为 false
    - DOC_SYNC_MAIN_DOC_REQUIRED 默认 true，回退为 false
```

## 4. fr_contract_matrix（字段级功能需求）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    business_goal_refs:
      - current_state_doc_incremental_heading_count=0
      - reader_latest_path_length<=1
    user_value: 主文档永远只呈现当前有效口径，读者不需要再翻增量章节找最新事实
    trigger: 修改产品/架构/API 主文档
    input_contract:
      required_fields: [doc_role, section_body]
      source_of_truth: .cursor/rules/doc_sync.mdc
    output_contract:
      required_fields: [section_body_updated]
      consumer: docs/产品文档/*.md + docs/开发文档/架构设计/*.md + docs/API文档/*.md
    failure_semantics: 发现新增增量标题或实现进展段时直接阻断
    observability_fields: [file, heading, doc_role, rule_id]
    rollback_anchor: DOC_DYNAMIC_MERGE_GUARD=false
    owner: doc-governance

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    business_goal_refs:
      - doc_sync_escape_count=0
      - reader_latest_path_length<=1
    user_value: 设计推导、实施计划、审批证据留在过程文档，不再污染主文档正文
    trigger: 需要记录设计推导、实施拆解或审批证据
    input_contract:
      required_fields: [change_reason, design_evidence]
      source_of_truth: docs/plans/*.md + docs/内部参考/迭代需求/*.md
    output_contract:
      required_fields: [process_doc_written]
      consumer: 设计审阅与实施执行链
    failure_semantics: 过程内容写入主文档时直接阻断
    observability_fields: [file, doc_role, evidence_type]
    rollback_anchor: DOC_PROCESS_LAYER_ENFORCED=false
    owner: doc-governance

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    business_goal_refs:
      - current_state_doc_incremental_heading_count=0
      - reader_latest_path_length<=1
    user_value: 对存量污染文档执行一次触达即融合，避免文档越修越长
    trigger: 触达已存在增量需求、实现进展或日期补充段的主文档
    input_contract:
      required_fields: [legacy_increment_sections]
      source_of_truth: docs/产品文档/*.md + docs/开发文档/架构设计/*.md
    output_contract:
      required_fields: [merged_section_body, legacy_section_removed]
      consumer: 主文档读者与后续维护者
    failure_semantics: 触达后仍保留旧增量段则阻断
    observability_fields: [file, legacy_heading_count, migration_mode]
    rollback_anchor: DOC_TOUCH_ONCE_MERGE=false
    owner: doc-governance

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    business_goal_refs:
      - current_state_doc_incremental_heading_count=0
      - current_state_doc_timestamp_coverage=100%
    user_value: 守卫能按文档角色执行不同规则，不再把历史型文档与主文档混为一谈
    trigger: 执行文档守卫
    input_contract:
      required_fields: [doc_role_manifest]
      source_of_truth: scripts/docs_guard.py
    output_contract:
      required_fields: [role_specific_check_result]
      consumer: pre-commit、CI、review
    failure_semantics: 无法识别文档角色时直接阻断
    observability_fields: [file, doc_role, reason]
    rollback_anchor: DOC_ROLE_GUARD=false
    owner: doc-governance

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    business_goal_refs:
      - current_state_doc_timestamp_coverage=100%
    user_value: 任何主文档都能明确看出当前更新时间，降低“口径是否过期”的认知成本
    trigger: 主文档新增或改写
    input_contract:
      required_fields: [doc_header]
      source_of_truth: docs/产品文档/*.md + docs/开发文档/架构设计/*.md + docs/API文档/*.md
    output_contract:
      required_fields: [updated_at]
      consumer: 主文档读者
    failure_semantics: 缺少更新时间时直接阻断
    observability_fields: [file, updated_at, doc_role]
    rollback_anchor: DOC_TIMESTAMP_REQUIRED=false
    owner: doc-governance

  - fr_id: FR-06
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[5]
    business_goal_refs:
      - doc_sync_escape_count=0
      - current_state_doc_incremental_heading_count=0
    user_value: 代码变更必须同步到对应主文档，不能只更新过程文档自我安慰
    trigger: 代码路径命中文档映射规则
    input_contract:
      required_fields: [changed_code, required_docs]
      source_of_truth: scripts/check_doc_sync.sh
    output_contract:
      required_fields: [all_required_main_docs_changed]
      consumer: 提交门禁与 CI
    failure_semantics: 仅更新过程文档或漏更主文档时直接阻断
    observability_fields: [changed_code, required_docs, missing_docs]
    rollback_anchor: DOC_SYNC_MAIN_DOC_REQUIRED=false
    owner: doc-governance
```

## 5. nfr_contract_matrix（数字阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    name: current_state_doc_timestamp_coverage
    threshold: "主文档更新时间覆盖率 = 100%"
    metric_source: docs_guard.timestamp_coverage
  - nfr_id: NFR-02
    name: current_state_doc_incremental_heading_count
    threshold: "治理范围内主文档新增增量标题数 = 0"
    metric_source: docs_guard.incremental_heading_scan
  - nfr_id: NFR-03
    name: doc_sync_escape_rate
    threshold: "主文档漏同步逃逸率 = 0%"
    metric_source: check_doc_sync.missing_required_docs
  - nfr_id: NFR-04
    name: role_guard_false_positive
    threshold: "历史型文档被误判为主文档的误报数 <= 1/次规则调整"
    metric_source: docs_guard.doc_role_audit
  - nfr_id: NFR-05
    name: reader_latest_path_length
    threshold: "定位当前口径所需跳转文档数 <= 1"
    metric_source: 人工抽检 + 主文档结构审计
```

## 6. 测试用例编号（TC）

- `TC-DSG-01`: 主文档新增增量标题时被守卫阻断
- `TC-DSG-02`: 过程文档新增不替代主文档更新
- `TC-DSG-03`: 触达 `聊天系统需求` 后完成同位融合并删除旧增量段
- `TC-DSG-04`: 触达 `管理后台需求` 后完成同位融合并删除旧增量段
- `TC-DSG-05`: 触达 `AI模块设计` 后完成专题段收敛，移除实现进展型表述
- `TC-DSG-06`: `docs_guard` 能识别文档角色并放过历史型文档
- `TC-DSG-07`: `check_doc_sync` 阻断“只改过程文档不改主文档”
- `TC-DSG-08`: 新建 requirements/implementation_plan 与脚本链路证据注册表已被 `docs/SUMMARY.md` 收录

## 7. traceability_matrix（机读）

```yaml
traceability_matrix:
  - design_item: D-01-main-doc-current-state-only
    fr_id: FR-01
    feature_id: F1-main-doc-current-state
    task_id: T01
    tc_id: TC-DSG-01
    acceptance_cmd_ref: PYTHON_BIN=$(bash scripts/repo_python.sh) && "$PYTHON_BIN" scripts/docs_guard.py --strict
    evidence_entry: docs/内部参考/迭代需求/文档单一真相源与动态融合治理_implementation_plan.md

  - design_item: D-02-history-layer-isolation
    fr_id: FR-02
    feature_id: F2-history-layer-isolation
    task_id: T02
    tc_id: TC-DSG-02
    acceptance_cmd_ref: PYTHON_BIN=$(bash scripts/repo_python.sh) && "$PYTHON_BIN" scripts/docs_guard.py --strict
    evidence_entry: docs/内部参考/迭代需求/文档单一真相源与动态融合治理_implementation_plan.md

  - design_item: D-03-touch-once-merge
    fr_id: FR-03
    feature_id: F3-main-doc-merge-migration
    task_id: T04
    tc_id: TC-DSG-03
    acceptance_cmd_ref: rg -n "增量需求|实现进展" docs/产品文档/聊天系统需求.md docs/产品文档/管理后台需求.md docs/开发文档/架构设计/AI模块设计.md
    evidence_entry: docs/内部参考/迭代需求/文档单一真相源与动态融合治理_implementation_plan.md

  - design_item: D-04-role-based-guard
    fr_id: FR-04
    feature_id: F4-role-based-guard
    task_id: T02
    tc_id: TC-DSG-06
    acceptance_cmd_ref: PYTHON_BIN=$(bash scripts/repo_python.sh) && "$PYTHON_BIN" scripts/docs_guard.py --strict
    evidence_entry: docs/内部参考/迭代需求/文档单一真相源与动态融合治理_implementation_plan.md

  - design_item: D-05-timestamp-and-traceability
    fr_id: FR-05
    feature_id: F5-timestamp-and-index
    task_id: T04
    tc_id: TC-DSG-08
    acceptance_cmd_ref: rg -n 更新时间： docs/产品文档 docs/开发文档/架构设计 docs/API文档 --glob \*.md
    evidence_entry: docs/内部参考/迭代需求/文档单一真相源与动态融合治理_implementation_plan.md

  - design_item: D-06-main-doc-sync-required
    fr_id: FR-06
    feature_id: F6-main-doc-sync-gate
    task_id: T03
    tc_id: TC-DSG-07
    acceptance_cmd_ref: bash scripts/check_doc_sync.sh --diff-range origin/master...HEAD
    evidence_entry: docs/内部参考/迭代需求/文档单一真相源与动态融合治理_implementation_plan.md

  - design_item: D-07-memory-bank-decision
    fr_id: FR-02
    feature_id: F7-decision-persistence
    task_id: T05
    tc_id: TC-DSG-02
    acceptance_cmd_ref: rg -n "文档单一真相源与动态融合治理|主文档只表达当前态" memory-bank.md
    evidence_entry: docs/内部参考/迭代需求/文档单一真相源与动态融合治理_implementation_plan.md

  - design_item: D-08-plan-alignment-gate
    fr_id: FR-06
    feature_id: F8-plan-alignment-gate
    task_id: T06
    tc_id: TC-DSG-07
    acceptance_cmd_ref: PYTHON_BIN=$(bash scripts/repo_python.sh) && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/文档单一真相源与动态融合治理_requirements.md --implementation-path docs/内部参考/迭代需求/文档单一真相源与动态融合治理_implementation_plan.md --output docs/内部参考/迭代需求/文档单一真相源与动态融合治理_clarify_plan_alignment.json
    evidence_entry: docs/内部参考/迭代需求/文档单一真相源与动态融合治理_implementation_plan.md
```
