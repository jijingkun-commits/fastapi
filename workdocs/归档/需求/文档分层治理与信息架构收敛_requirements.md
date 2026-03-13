# 文档分层治理与信息架构收敛需求文档

> 更新时间：2026-03-10 21:44 +08:00
> 上游设计：`workdocs/归档/设计/2026-03-10-docs-governance-layering-design.md`
> 文档目标：定义 WHAT（需求合同、验收门禁、追溯矩阵），供 `文档分层治理与信息架构收敛_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 核心目标

- 冻结三层文档结构：稳定文档、过程文档、运行态产物分家。
- 把 `docs/内部参考/` 的终局方向冻结为长期有效内部知识区；本轮先停止新增混写，旧 `task_split` 兼容路径留待 `Phase 2` 收口。
- 让 `docs/README.md` 与 `docs/SUMMARY.md` 只服务稳定真理源。
- 建立“同主题只允许一份当前态真理源”的治理口径，阻断稳定区继续出现 `v2/v3/日期补丁`。

### 1.2 范围

- 稳定文档入口：`docs/README.md`、`docs/SUMMARY.md`
- 稳定文档目录：`docs/产品文档/**`、`docs/开发文档/**`、`docs/API文档/**`、`contracts/**`
- 内部知识目录：`docs/内部参考/**`
- 过程文档目录：`workdocs/**`、`docs/内部参考/迭代需求/**`、`docs/内部参考/任务拆解/**`
- 运行态目录：拟新增 `.artifacts/**`
- 守卫与同步：`scripts/docs_guard.py`、`scripts/check_doc_sync.sh`、`.cursor/rules/doc_sync.mdc`
- 长期决策：`memory-bank.md`

### 1.3 非范围

- 不在本轮重写全部历史正文。
- 不在本轮引入 Docusaurus、MkDocs 一类站点化改造。
- 不在本轮做多版本文档体系。
- 不改变产品/架构/API 事实，只调整文档归属、导航与门禁。
- 不在本轮直接迁移 `task_split` 机器契约与过程报告 JSON（如 `_active_task.json`、`vk_cards.json`、`preflight_status.json`、`consumption_report.json`）；该项留待 `Phase 2`。

### 1.4 分阶段边界

- 本轮交付定义为 `Phase 1`：稳定导航收口、真实运行态迁出 `docs/`、迁移期兼容口径冻结。
- `docs/内部参考/迭代需求/**`、`docs/内部参考/任务拆解/**` 当前仍允许作为迁移期旧过程路径存在，但不再作为主导航入口。
- `task_split` 下的 `_active_task.json`、`vk_cards.json`、`preflight_status.json`、`consumption_report.json` 等机器契约/过程报告 JSON 暂不强迁，以避免破坏 `jjk-cardrun`、`wt-flow`、`coder4_*` 读链路。
- `Phase 2` 再把上述机器契约与过程报告整体迁到 `workdocs/**`，并同步改造工作流脚本。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "文档分层治理与信息架构收敛"
  status: "approved"
  design_source: workdocs/归档/设计/2026-03-10-docs-governance-layering-design.md
  clarify_handoff_source: workdocs/归档/设计/2026-03-10-docs-governance-layering-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户明确触发 jjk-plan"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 4
    product_contract_ready: true
  owner: "doc-governance"
  approver: "jijingkun"
  updated_at: "2026-03-10 18:42 +08:00"
```

## 3. 产品契约矩阵（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - 仓库主维护者
    - 新加入的开发者 / AI 协作者
    - 文档治理与代码评审人员
  core_scenarios:
    - 读者快速找到当前真理源
    - 需求/设计/任务拆解进入过程层而不污染稳定区
    - 自动化真实运行态文件不再出现在 docs 主区
    - 内部参考终局方向冻结为长期有效知识，迁移期兼容路径后续收口
  business_goal_metrics:
    - stable_doc_navigation_coverage = 100%
    - runtime_artifact_file_count_under_docs = 0
    - new_topic_current_source_count = 1
    - reader_current_truth_hops <= 1
    - stable_zone_versioned_filename_count = 0
  non_goals:
    - 不建设版本化文档站点
    - 不一次性重写全部历史文档正文
    - 不保留稳定区继续混放过程文档的弹性口径
    - 不在本轮直接迁移 `task_split` 机器契约 / 过程报告 JSON 或打断 `jjk-cardrun` 主链
  acceptance_gates:
    - AG-01 三层目录职责冻结完成
    - AG-02 稳定区命名与导航规则冻结完成，新增过程文档默认进入 `workdocs/`
    - AG-03 docs_guard 能识别 doc_role 并阻断污染
    - AG-04 `docs/内部参考` 的终局方向冻结为长期内部知识区，迁移期旧过程路径不再进入主导航
    - AG-05 真实运行态文件迁出 docs 主区；`task_split` 契约/报告 JSON 走 `Phase 1` 兼容口径
    - AG-06 memory-bank 写入长期决策且规划对齐报告全绿
```

## 4. FR 合同矩阵（字段级）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    user_value: 文档一进仓就知道该放稳定区还是过程区，减少“先随手放进去”的混乱
    trigger: 新增或迁移文档
    input_contract:
      required_fields: [file_path, doc_role]
      source_of_truth: workdocs/归档/设计/2026-03-10-docs-governance-layering-design.md
    output_contract:
      required_fields: [canonical_doc_role, target_directory]
      consumer: 文档维护者
    failure_semantics: 角色无法确定时降级到 process，禁止直接进入稳定区
    observability_fields: [file_path, doc_role, reason]
    rollback_anchor: DOC_STABLE_PROCESS_SPLIT=false
    owner: doc-governance

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    user_value: 真实运行态和自动产物不再污染 docs，阅读目录时不会再看到 `.state/.jsonl/.lock` 等运行态文件；迁移期 `task_split` 契约/报告 JSON 走单独兼容口径
    trigger: 自动化任务产生运行态文件，或 docs_guard 扫描 docs/**
    input_contract:
      required_fields: [file_path, extension, file_name]
      source_of_truth: .artifacts + docs/内部参考/任务拆解
    output_contract:
      required_fields: [artifact_path, compatibility_decision]
      consumer: 自动化执行链与文档维护者
    failure_semantics: 真实运行态文件写入 docs/** 时直接阻断；迁移期仅允许 `task_split` 兼容 JSON 留在 `docs/内部参考/任务拆解/**`
    observability_fields: [file_path, extension, file_name, compatibility_decision]
    rollback_anchor: DOC_RUNTIME_OUTSIDE_DOCS=false
    owner: doc-governance

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    user_value: 主导航只暴露稳定区，读者不会再从 README/SUMMARY 误入过程区
    trigger: 更新导航入口
    input_contract:
      required_fields: [doc_role, path, title]
      source_of_truth: docs/README.md + docs/SUMMARY.md
    output_contract:
      required_fields: [stable_nav_entry]
      consumer: 所有文档读者
    failure_semantics: 过程文档误入主导航时直接阻断
    observability_fields: [path, doc_role, nav_section]
    rollback_anchor: DOC_STABLE_NAV_ONLY=false
    owner: doc-governance

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    user_value: 同一主题只有一份当前真理源，避免 plans / 内部参考 / 主文档三边抢口径
    trigger: 同主题文档新增或迁移
    input_contract:
      required_fields: [topic, doc_role]
      source_of_truth: docs + workdocs
    output_contract:
      required_fields: [current_source_path]
      consumer: 评审与实施维护者
    failure_semantics: 检测到多个当前态入口时直接阻断
    observability_fields: [topic, current_source_count]
    rollback_anchor: DOC_TOPIC_SINGLE_SOURCE=false
    owner: doc-governance

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    user_value: 内部参考的终局方向只保留长期有效的决策、专题设计和资料，迁移期旧过程路径不再继续扩散
    trigger: 维护 docs/内部参考 目录
    input_contract:
      required_fields: [file_path, content_role]
      source_of_truth: docs/内部参考 + workdocs
    output_contract:
      required_fields: [internal_reference_long_lived_only]
      consumer: 内部协作者
    failure_semantics: 新增当前迭代过程文件继续留在 docs/内部参考（不含迁移期 `task_split` 兼容路径）时直接阻断
    observability_fields: [file_path, content_role]
    rollback_anchor: DOC_INTERNAL_REF_LONG_LIVED_ONLY=false
    owner: doc-governance

  - fr_id: FR-06
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[5]
    user_value: 未上线阶段不再维护稳定区多版本文件名，减少版本碎片和假入口
    trigger: 稳定区新增文件
    input_contract:
      required_fields: [file_name, doc_role]
      source_of_truth: docs
    output_contract:
      required_fields: [stable_name_valid]
      consumer: 文档维护者与 review
    failure_semantics: 稳定区命中 v2/v3/日期补丁命名时直接阻断
    observability_fields: [file_name, doc_role]
    rollback_anchor: DOC_VERSIONING_DISABLED=false
    owner: doc-governance
```

## 5. NFR 合同矩阵（数字阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    name: stable_doc_navigation_coverage
    threshold: "100%"
    metric_source: docs_guard.stable_navigation_coverage
  - nfr_id: NFR-02
    name: runtime_artifact_file_count_under_docs
    threshold: "0"
    metric_source: docs_guard.runtime_artifact_pollution
  - nfr_id: NFR-03
    name: new_topic_current_source_count
    threshold: "1"
    metric_source: docs_guard.current_source_count
  - nfr_id: NFR-04
    name: reader_current_truth_hops
    threshold: "<=1"
    metric_source: docs_readme_summary.audit
  - nfr_id: NFR-05
    name: stable_zone_versioned_filename_count
    threshold: "0"
    metric_source: docs_guard.versioned_filename_count
```

## 6. 测试用例编号（TC）

```yaml
test_case_matrix:
  - tc_id: TC-DGL-01
    covers: [FR-01, FR-03, NFR-01]
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
  - tc_id: TC-DGL-02
    covers: [FR-02, NFR-02]
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
  - tc_id: TC-DGL-03
    covers: [FR-04, NFR-03]
    acceptance_cmd_ref: rg -n "chat-multi-session-concurrency|langgraph-v1-adoption|workflow-gate-retirement" docs workdocs
  - tc_id: TC-DGL-04
    covers: [FR-05]
    acceptance_cmd_ref: rg -n "目录结构|内容格式|内容同步|迁移收口" docs/开发文档/流程与工具/文档治理基线清单.md docs/开发文档/流程与工具/文档月度校准清单.md
  - tc_id: TC-DGL-05
    covers: [FR-06, NFR-05]
    acceptance_cmd_ref: test -z "$(find docs/产品文档 docs/开发文档 docs/API文档 contracts -type f | rg -v '测试报告|归档备份|防屎山记录手册' | rg '(_v[0-9]+|[-_ ]v[0-9]+|\d{4}-\d{2}-\d{2})' || true)"
```

## 7. 追溯矩阵（机读）

```yaml
traceability_matrix:
  - task_id: T01
    fr_id: FR-03
    nfr_ids: [NFR-01, NFR-04]
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
  - task_id: T02
    fr_id: FR-01
    nfr_ids: [NFR-03]
    acceptance_cmd_ref: test -d workdocs/需求 && test -d workdocs/设计 && test -d workdocs/任务拆解
  - task_id: T03
    fr_id: FR-02
    nfr_ids: [NFR-02]
    acceptance_cmd_ref: 'test -d .artifacts/runs && test -d .artifacts/states && test -d .artifacts/generated && test -z "$(find docs -type f | rg "[.](jsonl|lock)$|/[.]state/" || true)"'
  - task_id: T04
    fr_id: FR-04
    nfr_ids: [NFR-01, NFR-02, NFR-05]
    acceptance_cmd_ref: bash scripts/check_doc_sync.sh --diff-range origin/master...HEAD && PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
  - task_id: T05
    fr_id: FR-05
    nfr_ids: [NFR-04]
    acceptance_cmd_ref: rg -n "目录结构|内容格式|内容同步|迁移收口" docs/开发文档/流程与工具/文档治理基线清单.md docs/开发文档/流程与工具/文档月度校准清单.md
  - task_id: T06
    fr_id: FR-06
    nfr_ids: [NFR-05]
    acceptance_cmd_ref: rg -n "文档分层治理与信息架构收敛" memory-bank.md
```
