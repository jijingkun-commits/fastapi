# OpenClaw 全量迁移实施方案（总控）

> 文档状态：总控主计划（中度拆分版本）  
> 创建日期：2026-02-18  
> 适用范围：`docs/内部参考/迭代需求/` 及其关联实施文档

---

## 1. 目标与适用边界

本方案用于统一管理 OpenClaw 对标迁移的跨专题节奏与批次门禁，确保：

1. 各专题实施文档按同一批次口径推进；
2. 需求基线与实施方案保持可追溯；
3. 文档治理、实现治理、回滚治理在同一总控视图收口。

边界约束：

1. 继续采用“`requirements + implementation_plan`”成对结构，不做大规模文档合并。
2. Batch-0 仅做文档结构治理与分批挂载，不变更运行时 API/DB/SSE 契约；后续 Wave 允许按专题增量改造契约。
3. 目录保持单层，不新增日期分层归档。

---

## 2. 批次总览（Batch-0 ~ Batch-6）

| Batch | 批次目标 | 主责任专题 | 关键产出 |
|---|---|---|---|
| Batch-0 | 文档治理拆分与索引收敛 | 文档治理 | 入口化文档、附录化、总控映射、门禁通过 |
| Batch-1 | Agent 去特殊化收敛 | Agent 去特殊化 | 影子路径清理、契约收紧、路由回归 |
| Batch-2 | AI 工具治理一期 | AI 工具治理 | Registry + Policy + DB 策略接线 |
| Batch-3 | 问数双角色权限治理 | 问数双角色权限 | `data_role` 主体化、默认隔离、试跑审计 |
| Batch-4 | 用户偏好记忆接线 | 跨会话用户偏好记忆 | 记忆读写闭环、注入可控、发布可回退 |
| Batch-5 | 治理增强与容错扩展 | AI 工具治理（扩展） | Hook/事件升级、治理增强、观测补齐 |
| Batch-6 | 稳态收口与回滚演练 | 文档治理 + 各专题联动 | 全链路回归、回滚演练、终稿归档 |

---

## 2.1 执行波次（P1~P6）

为对齐当前研发优先级，新增执行波次视图（不替代 Batch）：

| Wave | 目标 | 对应实施文档 |
|---|---|---|
| P1 | 运行时可取消控制 | `runtime_cancel_control_implementation_plan.md` |
| P2 | 工具治理一期 | `ai_tools_governance_implementation_plan.md` |
| P3 | Skill 多用户版本治理 | `skill_multi_user_versioning_implementation_plan.md` |
| P4 | 记忆检索增强 | `user_preference_memory_implementation_plan.md` |
| P5 | 稳态增强（恢复/隔离/观测） | `迁移执行波次_implementation_plan.md` |
| P6 | 收口与回滚演练 | `docs_governance_implementation_plan.md` |

执行顺序以 P1~P6 为准，Batch 继续用于跨专题门禁管理。

## 3. Batch-0（当前批次）交付清单

### 3.1 必做项

1. `evaluation_report.md` 入口化，并拆出专题评估正文。
2. `fix_plan.md` 入口化，并拆出问题卡正文。
3. `agent_despecialization` 进展日志外移至独立文档。
4. `ai_tools_governance` 主计划 + 技术附录拆分。
5. `README.md` 与 `docs/SUMMARY.md` 同步新增索引。
6. 各专题 implementation 文档补“与总控迁移方案映射”短节。

### 3.2 验收标准

1. `python3 scripts/docs_guard.py --strict` 通过。
2. 新增/迁移文档在 `docs/SUMMARY.md` 可达，无断链。
3. 主计划与附录、入口与正文间双向引用完整。
4. 不存在失效来源引用（尤其 OpenClaw 来源文档）。

---

## 4. 各专题批次映射

| 专题 implementation 文档 | 批次映射 |
|---|---|
| `agent_despecialization_implementation_plan.md` | Batch-1 |
| `ai_tools_governance_implementation_plan.md` | Batch-2 / Batch-5 |
| `askdata_dual_role_permission_implementation_plan.md` | Batch-3 |
| `user_preference_memory_implementation_plan.md` | Batch-4 |
| `runtime_cancel_control_implementation_plan.md` | Batch-1 前置能力 |
| `skill_multi_user_versioning_implementation_plan.md` | Batch-2 / Batch-4 衔接 |
| `迁移执行波次_implementation_plan.md` | Wave 执行基线（跨 Batch） |
| `docs_governance_implementation_plan.md` | Batch-0 / Batch-6 |

---

## 5. 执行顺序（总控）

1. 先完成 Batch-0 文档拆分与索引收敛。
2. 实施阶段按 Wave 顺序执行：P1（运行时可取消）-> P2（工具治理一期）-> P3（Skill 多用户版本治理）-> P4（记忆检索增强）-> P5（稳态增强）。
3. Batch-1 ~ Batch-5 继续作为跨专题门禁与依赖管理视图。
4. 最后由 Batch-6 统一收口（回归、回滚演练、终稿归档）。

---

## 6. 风险与回滚总则

1. **风险一：索引漂移**  
   缓解：每次新增/迁移文档后立即更新 `docs/SUMMARY.md` 与专题 `README`。
2. **风险二：专题与总控口径不一致**  
   缓解：以本总控批次映射为准，专题文档只做局部扩展。
3. **风险三：拆分后信息丢失**  
   缓解：入口文档必须指向专题正文，旧内容不得直接删除。
4. **风险四：事件/状态扩展过快导致兼容与性能回退**  
   缓解：采用“少量新事件 + metadata/version 扩展”，并执行 state 轻量化约束（明细外置）。

回滚原则：

1. 本轮文档拆分不改运行时逻辑；回滚以文档路径和索引回退为主。
2. 任何专题若回滚，需同步回填本总控“批次状态”与“回滚原因”。

---

## 7. 批次状态看板

| Batch | 状态 | 最后更新 | 备注 |
|---|---|---|---|
| Batch-0 | 进行中 | 2026-02-18 | 文档拆分与索引同步 |
| Batch-1 | 待开始 | - | 依赖 Batch-0 完成 |
| Batch-2 | 待开始 | - | 依赖 Batch-1 稳定 |
| Batch-3 | 待开始 | - | 与 Batch-2 可部分并行 |
| Batch-4 | 待开始 | - | 依赖记忆链路门禁 |
| Batch-5 | 待开始 | - | 依赖 Batch-2 基线 |
| Batch-6 | 待开始 | - | 全专题收口批次 |
