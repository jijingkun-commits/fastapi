# admin-overview-cockpit-slimming 需求文档

> 更新时间：2026-03-10 21:21 CST
> 上游设计：`workdocs/归档/正文/设计/2026-03-10-admin-overview-cockpit-slimming-design.md`
> 文档目标：定义 WHAT（首页精简后的需求合同、验收与追溯），供 `admin-overview-cockpit-slimming_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 用户故事

- 作为后台值班同学，我希望打开 `/admin` 后 3 秒内看懂“有没有业务样本、是不是慢了、是不是报错了、这页数据还能不能信”。
- 作为排障研发，我希望首页直接告诉我“问题集中在哪个模块”，而不是先看多个重复总分再自己猜。
- 作为后台产品使用者，我希望首页只保留真正有动作价值的信号，不被空占位块和伪指标干扰。

### 1.2 范围

- 首页结构收敛为：顶部状态条、4 张核心卡、2 个辅助面板。
- 核心卡固定为：`业务请求质量`、`提问链路健康`、`数据新鲜度`、`告警概览`。
- 辅助面板固定为：`模块健康矩阵`、`24h 流量趋势`。
- 首页移除：`系统状态`、`稳定性`、`容量与成本`、`关键变更`。
- `用户提问活跃度` 更名为 `提问链路健康`，直到真实活跃度/中断率接入前，不再展示伪活跃字段。

### 1.3 非范围

- 本轮不新增真实成本采集链路。
- 本轮不新增配置审计/关键变更流水。
- 本轮不重做分钟桶 schema 和写入链路。
- 本轮不改后台其他子页面。

### 1.4 发布约束

- 项目未上线，以设计合理和简洁为最高优先级。
- 新开关默认 `true`，需要回退时切到 `false`。
- 不允许把观察窗口成熟、时间流逝、TTL 到期写成阻断型验收门禁。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "admin-overview-cockpit-slimming"
  status: "approved"
  design_source: workdocs/归档/正文/设计/2026-03-10-admin-overview-cockpit-slimming-design.md
  clarify_handoff_source: workdocs/归档/正文/设计/2026-03-10-admin-overview-cockpit-slimming-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户明确触发：$jjk-plan"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 3
    product_contract_ready: true
  owner: "admin-platform"
  approver: "jijingkun"
  updated_at: "2026-03-10 21:21 CST"
```

## 3. product_contract_matrix

```yaml
product_contract_matrix:
  - bg_id: BG-01
    target_users: [后台值班/运营管理员]
    core_scenario: 首页 3 秒内判断业务是否异常
    business_goal_metric: first_screen_judgement_time_sec<=3
    acceptance_gates: [A-01, A-02, A-03]
    release_constraint: 首页只保留值班必需信号

  - bg_id: BG-02
    target_users: [后台值班/运营管理员, 排障研发]
    core_scenario: 快速定位异常模块并一跳进入对应模块
    business_goal_metric: module_location_success_rate>=95%
    acceptance_gates: [A-04, A-05]
    release_constraint: 模块矩阵必须保留 drill-down 能力

  - bg_id: BG-03
    target_users: [后台值班/运营管理员]
    core_scenario: 当数据已陈旧或实时链路降级时，首页先提示“数据不可信”
    business_goal_metric: stale_or_degraded_visibility_rate>=99%
    acceptance_gates: [A-03, A-06]
    release_constraint: `status` 必须由后端唯一产出

  - bg_id: BG-04
    target_users: [后台值班/运营管理员, 排障研发]
    core_scenario: 首页不再展示空占位块和未接真实数据字段
    business_goal_metric: placeholder_metric_count=0
    acceptance_gates: [A-07, A-08]
    release_constraint: 未接真实数据的块不得进入首页主视图
```

## 4. fr_contract_matrix

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    user_value: 顶部状态条统一表达实时链路状态、最新快照与陈旧提示
    trigger: 用户打开 `/admin` 首页
    input_contract:
      required_fields: [snapshot_at, realtime_status]
      optional_fields: [load_error]
      source_of_truth: web/src/components/admin/overview/AdminOverviewCockpit.tsx::header
    output_contract:
      required_fields: [top_status_bar]
      consumer: AdminOverviewCockpit
    failure_semantics: realtime_error_or_polling -> 页面继续可用且显式提示
    observability_fields: [snapshot_at, realtime_mode, freshness_status]
    rollback_anchor: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false
    linked_business_goals: [BG-01, BG-03]

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    user_value: 首页展示全业务 API 请求质量，而不是混杂总分
    trigger: 首页渲染业务请求质量卡
    input_contract:
      required_fields: [request_quality.status, request_quality.request_total, request_quality.qps, request_quality.success_rate, request_quality.error_5xx_rate, request_quality.latency_p95_ms]
      optional_fields: [request_quality.score]
      source_of_truth: app/services/admin_overview_query_service.py::_build_request_quality_card
    output_contract:
      required_fields: [request_quality_card]
      consumer: AdminOverviewCockpit
    failure_semantics: no_data -> 显示无业务样本，不输出误导性正常分
    observability_fields: [request_quality.status, error_5xx_rate, latency_p95_ms]
    rollback_anchor: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false
    linked_business_goals: [BG-01]

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    user_value: 首页单独展示提问链路健康，不再把“活跃度”和“中断率占位项”混在一起
    trigger: 首页渲染提问链路健康卡
    input_contract:
      required_fields: [question_health.status, question_health.question_total, question_health.question_qps, question_health.question_success_rate, question_health.question_latency_p95_ms]
      optional_fields: [question_health.score]
      source_of_truth: app/services/admin_overview_query_service.py::_build_question_health_card
    output_contract:
      required_fields: [question_health_card]
      consumer: AdminOverviewCockpit
    failure_semantics: no_data -> 显示暂无提问；未接真实数据字段不渲染
    observability_fields: [question_health.status, question_total, question_latency_p95_ms]
    rollback_anchor: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false
    linked_business_goals: [BG-01, BG-04]

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    user_value: 首页明确提示快照是否新鲜，避免陈旧数据误导判断
    trigger: 首页渲染数据新鲜度卡
    input_contract:
      required_fields: [freshness.status, freshness.delay_sec, freshness.max_delay_sec, freshness.source]
      optional_fields: []
      source_of_truth: app/services/admin_overview_query_service.py::_build_freshness_card
    output_contract:
      required_fields: [freshness_card]
      consumer: AdminOverviewCockpit
    failure_semantics: stale -> 页面显式标红并保留最后快照时间
    observability_fields: [freshness.status, delay_sec, source]
    rollback_anchor: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false
    linked_business_goals: [BG-01, BG-03]

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    user_value: 首页只展示可动作告警，不再把无样本信息噪音升级为首页主告警
    trigger: 查询层生成首页告警概览
    input_contract:
      required_fields: [request_quality, freshness, module_matrix]
      optional_fields: []
      source_of_truth: app/services/admin_overview_query_service.py::_build_alerts
    output_contract:
      required_fields: [alert_overview]
      consumer: AdminOverviewCockpit
    failure_semantics: no_actionable_alerts -> 渲染“当前无告警”空态
    observability_fields: [alert_code, alert_severity, alert_module]
    rollback_anchor: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false
    linked_business_goals: [BG-02, BG-03]

  - fr_id: FR-06
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[5]
    user_value: 首页按模块给出健康矩阵，并支持 drill-down
    trigger: 首页渲染模块健康矩阵
    input_contract:
      required_fields: [module_matrix]
      optional_fields: []
      source_of_truth: app/services/admin_overview_query_service.py::_build_module_matrix
    output_contract:
      required_fields: [module_matrix_panel]
      consumer: AdminOverviewCockpit
    failure_semantics: no_data -> 渲染模块空态，不回退稳定性总分
    observability_fields: [module_key, error_rate, latency_p95_ms, data_delay_sec]
    rollback_anchor: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false
    linked_business_goals: [BG-02]

  - fr_id: FR-07
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[6]
    user_value: 首页保留 24h 流量趋势，区分瞬时抖动与趋势性变化
    trigger: 首页渲染 24h 流量趋势面板
    input_contract:
      required_fields: [trends.windows.24h]
      optional_fields: []
      source_of_truth: /api/v1/admin-overview/trends
    output_contract:
      required_fields: [traffic_trends_panel]
      consumer: AdminOverviewCockpit
    failure_semantics: trends_unavailable -> 仅趋势面板降级，不影响核心卡
    observability_fields: [timestamp, request_qps, question_qps]
    rollback_anchor: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false
    linked_business_goals: [BG-01, BG-02]

  - fr_id: FR-08
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[7]
    user_value: 首页 contract 收敛后，前后端和 stream patch 只围绕新首页结构工作
    trigger: summary/trends/stream 首页 contract 收敛
    input_contract:
      required_fields: [summary_contract_v3_slim]
      optional_fields: [legacy_fields]
      source_of_truth: app/schemas/admin_overview.py
    output_contract:
      required_fields: [summary_contract_v3_slim, stream_patch_v3_slim]
      consumer: admin overview API + normalizer + cockpit
    failure_semantics: legacy_fields_only_in_read_path -> 允许短暂兼容读取，不允许继续写旧首页字段
    observability_fields: [meta.generated_at, meta.trace_id]
    rollback_anchor: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false
    linked_business_goals: [BG-03, BG-04]
```

## 5. nfr_contract_matrix

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    category: simplicity
    requirement: 首页主信息块数量必须 <= 6（不含顶部状态条）
    metric: primary_panels_count<=6
    linked_frs: [FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08]

  - nfr_id: NFR-02
    category: latency
    requirement: 首屏主要状态理解时间 <= 3 秒
    metric: first_screen_judgement_time_sec<=3
    linked_frs: [FR-01, FR-02, FR-03, FR-04]

  - nfr_id: NFR-03
    category: observability
    requirement: `stale/degraded` 可见率 >= 99%
    metric: stale_or_degraded_visibility_rate>=99%
    linked_frs: [FR-01, FR-04, FR-05, FR-08]

  - nfr_id: NFR-04
    category: data_truth
    requirement: 首页占位指标数量 = 0
    metric: placeholder_metric_count=0
    linked_frs: [FR-03, FR-05, FR-08]

  - nfr_id: NFR-05
    category: consistency
    requirement: `summary/trends/stream` 首页事实源漂移事件数 = 0
    metric: overview_fact_drift_incident_count=0
    linked_frs: [FR-07, FR-08]
```

## 6. traceability_matrix

```yaml
traceability_matrix:
  - design_item: D-01
    fr_id: FR-01
    bg_id: BG-01
    feature_id: P1-01
    task_id: T-01
    tc_id: TC-01
    acceptance_cmd_ref: 'rg -n "总览驾驶舱|提问链路健康|告警概览|24h 流量趋势" docs/产品文档/管理后台需求.md docs/API文档/接口文档.md docs/开发文档/架构设计/前端架构.md'

  - design_item: D-02
    fr_id: FR-02
    bg_id: BG-01
    feature_id: P2-01
    task_id: T-02
    tc_id: TC-02
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py -q'

  - design_item: D-03
    fr_id: FR-03
    bg_id: BG-04
    feature_id: P2-01
    task_id: T-02
    tc_id: TC-03
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py -q -k question'

  - design_item: D-04
    fr_id: FR-04
    bg_id: BG-03
    feature_id: P2-01
    task_id: T-02
    tc_id: TC-04
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/api/test_admin_overview_api.py -q -k freshness'

  - design_item: D-05
    fr_id: FR-05
    bg_id: BG-02
    feature_id: P2-01
    task_id: T-02
    tc_id: TC-05
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py -q -k alerts'

  - design_item: D-06
    fr_id: FR-06
    bg_id: BG-02
    feature_id: P3-01
    task_id: T-03
    tc_id: TC-06
    acceptance_cmd_ref: 'bash scripts/repo_python.sh >/dev/null && pnpm -C web exec tsc --noEmit'

  - design_item: D-07
    fr_id: FR-07
    bg_id: BG-02
    feature_id: P3-01
    task_id: T-03
    tc_id: TC-07
    acceptance_cmd_ref: 'bash scripts/repo_python.sh >/dev/null && eval "$(bash scripts/vk_ports.sh --export)" && PLAYWRIGHT_BASE_URL="$VK_FRONTEND_BASE_URL" E2E_API_BASE="$VK_BACKEND_BASE_URL" PLAYWRIGHT_REUSE_EXISTING_SERVER=false pnpm -C web exec playwright test e2e/features/admin-overview.feature.cjs --project=chromium'

  - design_item: D-08
    fr_id: FR-08
    bg_id: BG-03
    feature_id: P4-01
    task_id: T-04
    tc_id: TC-08
    acceptance_cmd_ref: 'python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/admin-overview-cockpit-slimming_requirements.md --implementation-path workdocs/归档/正文/实施计划/admin-overview-cockpit-slimming_implementation_plan.md --output workdocs/归档/报告/机读校验/admin-overview-cockpit-slimming_clarify_plan_alignment.json'
```
