# 迁移执行波次实施方案（P1~P6）

> 文档状态：实施基线（`/jjk-plan core`）
> 更新时间：2026-02-25
> 对应总控：`docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`

---

## 1. 目标与定位

本方案用于把现有 Batch 计划和实际研发优先级对齐，形成可执行的 P1~P6 波次清单。

执行原则：

1. 先完成“可中断运行时”（P1），再推进治理增强。
2. 不做重写，全部在现有 FastAPI + LangGraph 代码入口增量接线。
3. 所有波次必须有：代码入口、契约影响、测试清单、回滚锚点。

---

## 2. 与现有专题文档融合映射

| Wave | 主目标 | 主要落点文档 | 与 Batch 映射 |
|---|---|---|---|
| P1 | 运行时可取消（run control） | `runtime_cancel_control_implementation_plan.md` | Batch-1 前置增强 |
| P2 | 工具治理一期（Registry/Policy/Broker） | `ai_tools_governance_implementation_plan.md` | Batch-2 |
| P3 | Skill 多用户版本治理 | `skill_multi_user_versioning_implementation_plan.md` | Batch-2/4 衔接 |
| P4 | 记忆检索增强（Hybrid Recall） | `user_preference_memory_implementation_plan.md` | Batch-4 |
| P5 | 稳态增强（恢复/隔离/观测） | 本文 + 各专题附录 | Batch-5 |
| P6 | 全链路收口与回滚演练 | `docs_governance_implementation_plan.md` | Batch-6 |

说明：Batch 保留用于跨专题治理，P1~P6 用于研发执行优先级。
补充：插件治理是增强项，执行上按“先 Tool Registry/Policy，后 Plugin Registry”推进，不阻塞 P1~P4。

### 2.1 评审修订（已采纳）

1. 证据门禁按任务类型启用：仅对执行型任务启用强 evidence gate；闲聊/问答不强制。
2. 模型容错以 scene 为边界：fallback 接在 scene 解析链路上，不绕开 `LLMSceneService.resolve_model_code`。
3. 事件协议增量演进：先少量新事件，再通过 `metadata` 扩展并带 `version` 字段。
4. 状态轻量化：state 仅存摘要与引用，明细 ledger 落库或外部存储。
5. 插件化后置：先把 Tool Registry/Policy 与运行时稳定性打牢，再推进 Plugin Registry。

### 2.2 C00 预检卡（迁移前置门禁）

在进入 `C01/P1-01` 前，必须先完成 `C00`，用于固化“四风险修订”并防止执行跑偏。

1. R1 证据门禁收敛：`evidence` 由一刀切改为按 `task_mode/requires_evidence` 启用。
2. R2 模型 fallback 接线：统一收敛到 `LLMSceneService.resolve_model_code` 链路。
3. R3 插件后置：`Plugin Registry` 不得阻塞 `P1~P4` 主线。
4. R4 引用锚点修订：实现文档优先使用函数/模块锚点，避免行号漂移。

`C00` 完成定义（DoD）：

1. 变更文件：总控文档 + 波次文档 + P1 专题文档同步完成。
2. 测试与校验：至少完成一次 `python3 scripts/docs_guard.py --strict`。
3. 回滚开关：P1 仍以 `ENABLE_RUN_CONTROL` 与 `ENABLE_SSE_STOPPED_EVENT` 为唯一回滚锚点。
4. 证据链接：Gate 看板、专题工单、回查四元组可相互追踪。

### 2.3 C00 执行记录（2026-02-20）

1. [x] 三份文档同步：`openclaw全量迁移_implementation_plan.md`、`迁移执行波次_implementation_plan.md`、`runtime_cancel_control_implementation_plan.md`。
2. [x] 口径统一：取消接口统一为 `POST /api/v1/chat/runs/{run_id}/cancel`。
3. [x] 引用规范：改为“函数/模块锚点优先”。
4. [x] 校验通过：`python3 scripts/docs_guard.py --strict`（errors=0, warnings=0）。
5. [x] 证据回填：Gate 看板与 P1 工单模板已挂接 C00 与 Gate 关联。

结论：`C00` 已通过，可进入 `C01/P1-01`。
结论（门禁判定口径）：C00 已通过，可进入 C01/P1-01。

### 2.4 进度回填协议（唯一入口）

1. 执行进度唯一回填入口：本文 `11.5 本周 Gate 状态看板` + 当前卡执行记录区。
2. 总控文档仅做状态镜像，不作为执行同学的主回填位置。
3. 专题文档仅回填实现细节与测试证据，不更新跨波次总状态。
4. 若出现状态不一致，以本文为准，并要求 24 小时内完成镜像同步。

---

## 3. P1 运行时可取消（最高优先）

### 3.1 目标

1. 后端具备可终止 run 的控制面。
2. 终止后不再回灌历史 token/队列。
3. SSE 对前端提供明确 stopped 信号。

### 3.2 代码入口

1. `app/models/chat_run.py`（新增 run 状态模型）。
2. `app/services/run_control_service.py`（取消控制与状态流转）。
3. `app/services/chat_service.py`（`stream` / `sse_stream` / `sse_resume_stream` 接线）。
4. `app/ai/workflow/multi_agent_graph.py`（关键节点取消检查）。
5. `app/schemas/chat.py`（补 `run_id` 字段）。
6. `app/api/v1/endpoints/chat_api.py`（`POST /api/v1/chat/runs/{run_id}/cancel`，权威口径）。

### 3.3 契约与测试

1. SSE 新增 `stopped` 事件（兼容既有 `done/result/interrupt`）。
2. API 取消接口幂等。
3. 测试：
   - `tests/api/test_chat_api.py`
   - `tests/unit/test_run_control_service.py`
   - `tests/unit/test_chat_service_cancel_stream.py`
   - `tests/unit/test_chat_service_resume_after_cancel.py`

### 3.4 回滚锚点

1. `ENABLE_RUN_CONTROL`
2. `ENABLE_SSE_STOPPED_EVENT`

---

## 4. P2 工具治理一期

### 4.1 目标

1. 工具装配从 workflow 硬编码收敛到治理管线。
2. `settings` 默认 + DB 策略覆盖生效。
3. 保持对现有主流程兼容。

### 4.2 代码入口

1. `app/ai/tools/` 注册中心与元数据收敛。
2. `app/services/config_resolver.py`、`app/core/config_contract.py`（策略读取）。
3. `app/ai/workflow/multi_agent_graph.py`：`_get_common_tools()`、`_get_supervisor_tools()` 接 Broker。

### 4.3 回滚锚点

1. `ENABLE_TOOL_GOVERNANCE`
2. `TOOL_POLICY_FAIL_MODE`

### 4.4 证据门禁（修订）

1. 增加 `task_mode`（如 `chat` / `execute`）或等价字段。
2. `requires_evidence=true` 仅在执行型任务生效。
3. 执行型任务未满足证据门禁时返回澄清/补全，不直接 `complete`。
4. 闲聊任务默认不触发强制工具调用，避免“为过门禁而乱调工具”。

---

## 5. P3 Skill 多用户版本治理

### 5.1 目标

1. Skill 定义、版本、用户绑定解耦。
2. 用户覆盖不影响其他用户。
3. 发布/回滚可追溯。

### 5.2 代码入口

1. `app/models/agent_skill.py`（保留兼容）+ 新增版本/绑定模型。
2. `app/services/skill_service.py`（发布、回滚、按 `user_id` 解析）。
3. `app/api/v1/endpoints/skill_admin_api.py`（用户绑定与版本控制接口）。

### 5.3 回滚锚点

1. `ENABLE_SKILL_VERSIONING`
2. `ENABLE_USER_SKILL_BINDING`

---

## 6. P4 记忆检索增强

### 6.1 目标

1. 从偏好 KV 注入升级到混合检索（关键词 + 向量）。
2. 压缩前 durable flush，减少长对话遗忘。
3. 注入保持可追溯。

### 6.2 代码入口

1. `app/services/user_preference_memory_service.py`（保留并扩展分层注入）。
2. `app/services/chat_service.py`（recall 与 flush 接线）。
3. 记忆存储与检索服务新增模块（按 `user_id` 隔离）。

### 6.3 回滚锚点

1. `ENABLE_MEMORY_RECALL`
2. `ENABLE_PRE_COMPACTION_FLUSH`

---

## 7. P5 稳态增强

### 7.1 目标

1. run/queue 状态持久化与重启恢复。
2. 中断成功率、回灌率、恢复时延可观测。
3. 异常降级不阻断主对话。

### 7.2 关键动作

1. 增加恢复任务与 orphan 清理。
2. 补齐审计指标与告警阈值。
3. 固化灰度开关矩阵。

### 7.3 插件扩展治理（P4.5/P5 过渡）

1. 先完成 `Tool Registry + Policy Pipeline` 后，再引入 `Plugin Registry`。
2. 首期仅做最小骨架：插件元数据、注册/禁用、生命周期状态（loaded/blocked/failed）。
3. 插件策略纳入工具治理：支持 `group:plugins` 与插件 allowlist 防误杀规则。
4. 插件加载失败必须降级到核心工具集，不中断主流程。

### 7.4 模型容错接线（修订）

1. fallback 入口挂在 scene 解析链路，保持场景约束一致性。
2. 以 `LLMSceneService.resolve_model_code` 为主入口，不新增绕行解析路径。
3. fallback 候选链必须继承 scene 白名单/类型校验与审计字段。

### 7.5 回滚锚点

1. `ENABLE_RUNTIME_RECOVERY`
2. `ENABLE_PLUGIN_REGISTRY`

---

## 8. P6 全链路收口

### 8.1 目标

1. 文档、代码、测试三线收口。
2. 回滚演练完成并留痕。
3. 版本发布清单可复用。

### 8.2 收口门禁

1. `python3 scripts/docs_guard.py --strict` 通过。
2. 关键 API/SSE/DB 契约回归通过。
3. 每个 Wave 有完成记录与回滚记录。

### 8.3 C06 收口执行记录（2026-02-25）

1. docs 收口：`11.2`、`11.5` 与 `11.6 WAVE_ROLLBACK_DRILL_MATRIX` 已完成统一回填。
2. code 收口：`scripts/docs_guard.py` 新增 Gate 与回滚矩阵强校验。
3. test 收口：`python3 scripts/docs_guard.py --strict` 通过（errors=0，warnings=0）。

### 8.4 G01 证据闭环执行记录（2026-02-25）

1. evidence 四元组（`task_id/turn_id/process_id/status`）已固化到 `WS-G01` 并完成非空核验。
2. 证据绑定关系复核通过：`target_task_id == evidence_task_id`。
3. 执行留痕入口：`docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/workstreams/WS-G01_G1_实测证据闭环.md`。

---

## 9. 文档优先执行清单（仅计划/文档）

1. 更新总控文档，补 P1~P6 映射入口。
2. 核对 P1、P3 两份专题实施方案文档（已存在），补齐“与总控映射”、回滚锚点与更新时间。
3. 扩展 P2、P4 现有专题文档中的“与总控映射”和回滚锚点。
4. 同步 `docs/内部参考/迭代需求/README.md` 与 `docs/SUMMARY.md`。
5. 同步契约权威文档：`docs/API文档/接口文档.md`、`docs/开发文档/代码解读/SSE事件协议.md`、`docs/开发文档/架构设计/数据库设计.md`。
6. 每周仅维护一个状态看板入口（本文），统一更新 Wave 状态、风险与回滚记录。
7. 统一取消接口权威口径为 `POST /api/v1/chat/runs/{run_id}/cancel`，并将实现引用从“行号”迁移为“函数/模块锚点”。

---

## 10. 与总控迁移方案映射

对应总控文档：`docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`

1. 本文不替代 Batch，总控仍以 Batch 管理跨专题门禁。
2. 本文补充研发执行顺序（P1~P6），用于落地排期与工单拆解。
3. 若 Batch 与 Wave 冲突，以“先满足 P1 可取消运行时”为执行优先。

---

## 11. OpenClaw 源码解读完成度关卡（执行门禁）

目标：避免“解读文档持续膨胀但落地证据不足”，把“已吃透”从主观判断改为可核验门禁。

### 11.1 判定规则

1. 对外宣称“源码已吃透，可进入全量迁移拍板”前，必须通过本节全部硬性关卡。
2. 每个关卡都必须附证据：执行日期、责任人、证据链接、失败样例与修复记录。
3. 未通过全部关卡前，阶段性结论仅允许表述为“足够推进 P1/P2，不足以全量拍板”。

### 11.2 关卡清单（硬性）

| Gate | 必过条件 | 最低量化标准 | 证据产物（留痕位置） | 当前状态 |
|---|---|---|---|---|
| G-1 实测证据闭环（B0/B1-B2） | `B0-1/B0-2/B0-3/B1-B2` 从“手册”变为“已实跑” | 每个子项至少 1 次通过记录 + 1 条异常样例复盘 | `output/openclaw源码解析/OpenClaw吃透度补强-*.md` 的执行记录区 + 工单链接 | 已通过（2026-02-25） |
| G-2 复合任务编排实证 | 覆盖“三问合一/跨工具/跨轮次”复合任务 | 用例数 >= 20；通过率 >= 85%；失败复盘 >= 3 条 | `output/openclaw源码解析/OpenClaw源码解析-长期主档.md` 的实测章节 + 测试报告 | 已通过（2026-02-25） |
| G-3 契约一致性证据 | API/SSE/DB 文档与实现逐项对齐 | 契约差异项 = 0；随机抽检 >= 10 项 | `docs/API文档/接口文档.md`、`docs/开发文档/代码解读/SSE事件协议.md`、`docs/开发文档/架构设计/数据库设计.md` 的回填记录 | 已通过（2026-02-25） |
| G-4 回滚演练证据（P1） | 至少完成 1 轮真实回滚演练并复原 | 演练 >= 1 次；回滚成功率 100%；恢复后核心链路回归通过 | `runtime_cancel_control_implementation_plan.md` 回滚记录 + 发布日志 | 已通过（2026-02-25） |

### 11.3 通过口径

1. G-1 ~ G-4 全部通过，才可将状态更新为“源码解读足够，进入全量迁移拍板”。
2. 任一 Gate 回退为失败时，总体状态自动回到“仅支撑 P1/P2 推进”。
3. 每周状态会统一在本文更新，不再新增并行“解读结论文档”。

### 11.4 定向回查规则（强制）

1. 回查触发条件（满足任一条即可）：
   - 实现卡点持续超过 30 分钟；
   - 同类失败出现 >= 2 次；
   - 关卡指标下滑（通过率、回滚成功率、契约一致性任一项异常）。
2. 回查范围限制：单次仅允许回查 `output/openclaw源码解析/` 中与卡点直接相关的 1~2 篇文档。
3. 回查产出强制：每次回查必须回填“四元组”——`卡点`、`回查来源`、`结论`、`代码改动`。
4. 禁止事项：
   - 禁止新增泛解读文档；
   - 禁止将证据层结论直接替代执行层决策；
   - 禁止未回填证据就宣称“已吃透”。
5. 执行门禁：工单若无回查四元组（触发时）或未更新 Gate 状态，不得标记为完成。

### 11.5 本周 Gate 状态看板（唯一入口）

> 统计周期：2026-02-25（C06 收口周）

| Gate | 责任人 | 目标日期 | 当前状态 | 证据链接 | 下一步 |
|---|---|---|---|---|---|
| G-1 实测证据闭环 | 纪景锟 | 2026-02-25 | 已通过 | `output/openclaw源码解析/OpenClaw吃透度补强-*.md`、`11.6 WAVE_ROLLBACK_DRILL_MATRIX`、`WS-G01_G1_实测证据闭环.md` | 进入周检，若指标回退按 11.4 回查 |
| G-2 复合任务编排实证 | 纪景锟 | 2026-02-25 | 已通过 | `output/openclaw源码解析/OpenClaw源码解析-长期主档.md`、`11.6 WAVE_ROLLBACK_DRILL_MATRIX` | 维持复合用例滚动统计与失败复盘 |
| G-3 契约一致性证据 | 纪景锟 | 2026-02-25 | 已通过 | `docs/API文档/接口文档.md`、`docs/开发文档/代码解读/SSE事件协议.md`、`docs/开发文档/架构设计/数据库设计.md`、`8.3 C06 收口执行记录` | 保持契约周检，发现漂移即回填 |
| G-4 P1 回滚演练证据 | 纪景锟 | 2026-02-25 | 已通过 | `runtime_cancel_control_implementation_plan.md`（第 7 节回滚记录）、`11.6 WAVE_ROLLBACK_DRILL_MATRIX` | 纳入发布前固定回滚演练清单 |

### 11.6 WAVE_ROLLBACK_DRILL_MATRIX（波次级回滚演练矩阵）

| Wave | 组合回滚锚点 | 演练批次 | 恢复结果 | 证据链接 |
|---|---|---|---|---|
| P1 | `ENABLE_RUN_CONTROL` + `ENABLE_SSE_STOPPED_EVENT` | 2026-02-25-DRILL-01 | 通过（核心链路恢复） | `runtime_cancel_control_implementation_plan.md` 第 7 节 |
| P2 | `ENABLE_TOOL_GOVERNANCE` + `TOOL_POLICY_FAIL_MODE` | 2026-02-25-DRILL-02 | 通过（治理链路恢复） | `ai_tools_governance_implementation_plan.md` 第 4 节 |
| P3 | `ENABLE_SKILL_VERSIONING` + `ENABLE_USER_SKILL_BINDING` | 2026-02-25-DRILL-03 | 通过（版本/绑定恢复） | `skill_multi_user_versioning_implementation_plan.md` 第 6 节 |
| P4 | `ENABLE_MEMORY_RECALL` + `ENABLE_PRE_COMPACTION_FLUSH` | 2026-02-25-DRILL-04 | 通过（记忆注入恢复） | `user_preference_memory_implementation_plan.md` 第 7 节 |
| P5 | `ENABLE_RUNTIME_RECOVERY` + `ENABLE_PLUGIN_REGISTRY` | 2026-02-25-DRILL-05 | 通过（恢复/插件链路恢复） | `openclaw迁移重建基线_implementation_plan.md` 第 4.10 节 |
| P6 | `WAVE_ROLLBACK_DRILL_MATRIX` + `python3 scripts/docs_guard.py --strict` | 2026-02-25-DRILL-06 | 通过（docs/code/test 收口） | `8.3 C06 收口执行记录` |

#### 11.6.1 G04（G-4）复核记录（2026-02-26）

1. 复核范围：`11.6 WAVE_ROLLBACK_DRILL_MATRIX` 与 `openclaw迁移重建基线_implementation_plan.md` 第 4.11 节。
2. 完整性判定：矩阵包含 `P1~P6` 全量 6 行，且每行均包含“组合回滚锚点 / 演练批次 / 恢复结果 / 证据链接”四要素，无占位符。
3. 可执行性判定：`11.5` 中 `G-4` 状态已通过且“下一步”固定为发布前回滚清单；`4.11` 已以 `WAVE_ROLLBACK_DRILL_MATRIX` 作为回滚锚点并绑定 `python3 scripts/docs_guard.py --strict` 校验。
4. 结论：`G04` 检查通过，发布前回滚演练可按矩阵批次直接执行。
