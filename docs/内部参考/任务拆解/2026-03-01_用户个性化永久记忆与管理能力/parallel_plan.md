# 用户个性化永久记忆与管理能力串行拆解计划

> 计划 ID: PP-20260301-USER-MEMORY-ADMIN
> 主题: 用户个性化永久记忆与管理能力
> 输入来源: `docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_requirements.md` / `docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md`

## -1. 执行策略

- execution_mode: `serial`
- single_active_card: `true`
- card_order: `['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'G01', 'IG01']`
- gate_contract:
  - mode: `as_cards`
  - gate_ids: `['G01', 'IG01']`
  - depends_on: `{'G01': ['C06'], 'IG01': ['G01']}`
- auto_done_policy:
  - implementation-card: `hard_gate`
  - inspection/question-card: `policy_gate`
- 与 planning_contract 一致性: `PASS`（继承 `docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md`）

### -1.1 automation_contract

```yaml
automation_contract:
  source_of_truth: docs/内部参考/任务拆解/_active_task.json
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
  - required: `card_id/feature_ids/acceptance_checks/rollback_anchors`
  - optional: `example_refs/handoff_artifacts`
- 枚举与空值约束: `task_mode` 只允许 `implementation-card|inspection-card|question-card`
- 兼容策略: 新增字段仅追加，不破坏既有 card_id 与 depends_on
- 协议机读文件: `docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/contracts/sse_events_v1.json`

## 1. seed 来源

- `task_key`: `PP-20260301-USER-MEMORY-ADMIN`
- 来源: `plan`
- `card_seed` 来源: `docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md::planning_contract`
- 推导依据与风险: 严格继承 `card_order/depends_on/gate_contract`，不重命名 `card_id/feature_id`

### 1.1 功能机制包映射（必填）

| card_id | wave | feature_ids | 机制摘要 | 代码锚点 | 验证命令 | 回滚锚点 |
|---|---|---|---|---|---|---|
| C01 | P1 | P1-01,P1-02 | 查询与详情链路 | memory_admin_api/document_memory_repo | pytest memory list/detail | 关闭 admin api |
| C02 | P2 | P1-03,P2-01,P2-02 | 调试/归档/删除治理 | memory_admin_api/memory_admin_service | pytest search_debug/archive/delete | 下线管理动作路由 |
| C03 | P3 | P3-01 | 审计落库 | memory_admin_audit model/service | pytest audit + alembic | feature.enable_document_memory_admin_audit |
| C04 | P4 | P4-01 | 向量状态看板增强 | embedding status repo/api | pytest embedding_status | 回退旧统计结构 |
| C05 | P5 | P5-01,P5-02 | 后台页面与交互 | web admin memory panel | npm lint | 隐藏 admin 菜单 |
| C06 | P6 | P6-01 | 配置+文档+测试收口 | config_contract/init sql/docs | pytest + docs_guard | 全量开关关闭 |
| G01 | Gate | G-1 | 全链路流程门禁 | scope_guard + gate_result 聚合 | scope_guard + gate_result 校验 | 停止落卡执行 |
| IG01 | Gate | IG-1 | 主干集成门禁 | merge_result + baseline 祖先校验 | check_integration_gate | 阻断最终完成态 |

## 2. 目标与边界

- 目标:
  1. 生成可直接供 `/jjk-vktodo` 消费的 `vk_cards.json`。
  2. 完整承接 implementation plan 的 `card_order`、`depends_on`、`task_to_pr_mapping`。
  3. 将 `G01/IG01` 双 Gate 以独立卡片纳入串行执行末端。
- 非目标:
  1. 本阶段不直接修改业务代码。
  2. 不新增第四类主文档。
- 约束（架构/性能/合规）:
  1. 禁止重命名 `card_id/feature_id`。
  2. 禁止弱化硬依赖 `depends_on`。
  3. 管理能力拆解不得影响主对话 recall 链路。

## 3. 架构冻结项（并行前必须确认）

- 模块边界: API 只做校验/权限，Service 做治理编排，Repo 只做数据访问。
- 状态契约: `document.status` 与 `chunk.embedding_status` 为 canonical。
- 路由闭环: `list/detail/chunks/search_debug/archive/delete/rebuild/retry_failed`。
- 前后端链路时序: 页面筛选 -> 列表 -> 详情抽屉 -> 操作反馈，失败分支需可解释。

## 4. 工作包总览

| WS | 名称 | 类型 | 负责人 | 可并行 | 依赖 |
|----|------|------|--------|--------|------|
| WS-00 | C00 预检门禁冻结 | Foundation | 待定 | 否 | 无 |
| WS-C01 | C01 P1 查询能力（列表/详情/chunks） | Backend | 待定 | 否 | 无 |
| WS-C02 | C02 P2 管理动作（调试/归档/删除） | Backend | 待定 | 否 | C01 |
| WS-C03 | C03 P3 管理审计落库 | Backend | 待定 | 否 | C02 |
| WS-C04 | C04 P4 向量状态看板增强 | Backend | 待定 | 否 | C01 |
| WS-C05 | C05 P5 管理后台页面（列表+详情+操作） | Frontend | 待定 | 否 | C01,C02 |
| WS-C06 | C06 P6 配置、迁移、文档与测试收口 | Backend | 待定 | 否 | C03,C04,C05 |
| WS-G01 | G01 Gate 全链路验收门禁 | Gate | 待定 | 否 | C06 |
| WS-IG01 | IG01 集成门禁（主干可见） | Gate | 待定 | 否 | G01 |

## 5. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|------|----------|------------------|------|
| `app/api/v1/endpoints/memory_admin_api.py` | WS-C01/WS-C02/WS-C04 | 否 | 串行独占，按 card_order 推进 |
| `app/services/memory_admin_service.py` | WS-C01/WS-C02/WS-C03 | 否 | 单卡独占写 |
| `web/src/components/admin/MemoryAdminPanel.tsx` | WS-C05 | 否 | 前端卡独占 |
| `docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md` | WS-C06/WS-G01/WS-IG01 | 否 | Gate 卡独占回填证据 |

## 6. 依赖图与里程碑

- 依赖图: `C01 -> C02 -> C03 -> C06 -> G01 -> IG01`，侧支 `C01 -> C04 -> C06`，`C01,C02 -> C05 -> C06`。
- 里程碑:
  1. M1: 查询与管理动作完成（C01~C02）
  2. M2: 审计与可观测完成（C03~C04）
  3. M3: 前端与收口完成（C05~C06）
  4. M4: 流程门禁通过（G01）
  5. M5: 集成门禁通过（IG01）

## 7. 合并策略

- 合并顺序: 按 `card_order` 串行提交。
- 回归门禁: 每卡 `acceptance_checks` 通过后方可合并。
- 回滚策略: 优先卡级回滚锚点，禁止跨卡混退。

## 8. 看板导出索引

- `task_key`: `PP-20260301-USER-MEMORY-ADMIN`
- 拆解目录 ID: `2026-03-01_用户个性化永久记忆与管理能力`
- WS 总数: `9`（含 `WS-00`）
- Gate 总数: `2`
- 默认列流转: `Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则: `<task_key>::<WS-ID>`
- 卡片标题规则: `<CARD-ID> <标题> [<task_key>]`

## 9. Gate 执行状态

### 9.1 WS-G01 结果

- `scope_guard`: 待执行
- `gate_result 聚合校验`: 待执行

### 9.2 WS-G01 预期动作

1. 执行 `python3 scripts/coder4_scope_guard.py ...` 校验作用域绑定与 active_task 一致。
2. 聚合检查 `.omc/state/attempts/C01~C06/gate_result.json` 均为 `passed=true`。
3. 若任一前置卡缺失 gate_result 或失败，立即阻断并暂停后续落卡执行。

### 9.3 WS-IG01 结果

- `merge_result 校验`: 待执行
- `master 可见性校验`: 待执行

### 9.4 WS-IG01 预期动作

1. 执行 `python3 scripts/check_integration_gate.py --task-split-dir "2026-03-01_用户个性化永久记忆与管理能力" --baseline master`。
2. 校验 `.omc/state/attempts/C01~C06/merge_result.json` 完整，且 `merge_commit` 均可追溯。
3. 若任一实现卡缺失 merge 证据或 `master` 不可见，保持整体状态非最终完成。

## 10. 信息防丢失检查

- [x] 每个 `feature_id` 均落入某张卡
- [x] 每张卡含机制摘要 + 代码锚点 + 最小样例引用
- [x] 每张卡含可执行 `acceptance_checks`
- [x] 卡片 `DoD` 与 implementation plan `done_gate` 对齐
- [x] `output/**` 仅作为证据引用，未直接复制长文
- [x] `gate_contract.mode=as_cards` 且 gate_ids 全量实体化

## 11. mapping_checks（机读）

```yaml
mapping_checks:
  forward_check: PASS
  reverse_check: PASS
  orphan_features: []
  duplicate_features: []
  pr_mapping_check: PASS
  pr_mapping_errors: []
```

## 12. active_task_alignment（机读）

```yaml
active_task_alignment:
  task_key_match: true
  task_split_dir_match: true
  project_id_present: true
```
