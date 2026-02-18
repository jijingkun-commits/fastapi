# 实施方案（Agent 去特殊化收敛）

> 文档状态：`/plan core` 产物  
> 创建日期：2026-02-18  
> 对应需求：`docs/内部参考/迭代需求/agent_despecialization_requirements.md`

---

## 1. 目标与原则

本批次遵循“先收敛结构、后重构能力”：

1. 仅做无行为变更改造，优先移除未接线路径与过期兼容层。
2. 不改动 `preprocess/postprocess` 行为，不触碰 prompt 语义。
3. 文档与代码同步更新，保持可追溯。

---

## 2. 架构影响与约束（必查）

### 2.1 模块边界

1. 本批次仅修改：
   - `app/ai/workflow/multi_agent_graph.py`
   - `app/ai/llm_util.py`
2. 不新增跨层依赖，不将工作流策略下沉到 API/Service 层。

### 2.2 状态契约

1. 不新增/删除 `State` 字段。
2. 不改变 `pending_handoff`、`messages`、`turn_act` 生命周期。

### 2.3 路由闭环

1. `pending_handoff -> data_expert/todo_expert/postprocess` 闭环保持不变。
2. 删除未接线 `_classify_intent` / `route_by_intent`，消除影子路由。

### 2.4 端到端链路

1. 前端传入 `current_todo_id` 的注入时序保持不变。
2. SSE 事件契约不变，不触及 `events.py` 协议字段。

### 2.5 可测试性

1. 增加 `llm_util` 新契约测试（禁止旧 `scene` 参数）。
2. 增加/补强 `multi_agent_graph` 路由判定测试。

---

## 3. 变更清单

### 3.1 代码改造

1. `app/ai/workflow/multi_agent_graph.py`
   - 删除未接线意图函数定义。
   - 移除无效依赖导入（如未使用的 schema helper）。
   - 路由目标使用单点常量映射，去掉散落字面量判断。

2. `app/ai/llm_util.py`
   - 删除 `_map_legacy_scene` 及 `scene` 兼容参数。
   - `get_scene_llm` 契约收紧为必须传 `scene_key`。

### 3.2 测试

1. 新增/更新：
   - `tests/unit/test_llm_scene_enforcement.py`（scene 参数下线）
   - `tests/unit/test_multi_agent_fallback.py`（路由判定回归）

### 3.3 文档同步

1. `docs/开发文档/架构设计/AI模块设计.md`
   - 增加“去特殊化收敛（2026-02）”说明。
2. `docs/开发文档/架构设计/防屎山记录手册.md`
   - 更新 SP-017 状态与最后更新日期。
   - 更新 SP-013 进展备注（本批次结构收敛）。
3. `docs/SUMMARY.md`
   - 增加本专题需求与方案索引。

---

## 4. 风险评估

| 风险 | 级别 | 描述 | 缓解 |
|---|---|---|---|
| 外部调用兼容中断 | 中 | 仓库外仍传 `scene=` | 发布说明+必要时快速回滚 `llm_util.py` |
| 路由回归 | 中 | 清理代码后误改分支判定 | 补单测 + 重点回归 `pending_handoff` 分支 |
| 文档漂移 | 低 | 改码后未同步 SP | 强制同步防屎山与 AI 模块文档 |

---

## 5. 验证计划

1. 单测：
   - `pytest tests/unit/test_llm_scene_enforcement.py`
   - `pytest tests/unit/test_multi_agent_fallback.py`
2. 静态检查：
   - `rg` 确认无 `get_scene_llm(scene=` 调用残留。
3. 文档校验：
   - `python3 scripts/docs_guard.py --strict`

---

## 6. 回滚方案

1. 代码回滚最小单元：
   - `app/ai/llm_util.py`
   - `app/ai/workflow/multi_agent_graph.py`
2. 文档回滚：
   - SP-017 状态回退为“跟踪中”，并注明回滚原因。


---

## 7. 进展记录入口

1. 本专题持续收敛进展已外移到：`docs/内部参考/迭代需求/agent_despecialization_progress_log.md`。
   - 当前已回填至：`Batch-20`。
2. 主计划仅保留稳定策略（目标、约束、风险、验证、回滚）；批次流水统一在进展日志按日期追加。
3. 回填规则：每次 `/imp` 完成后，先更新进展日志，再回填本文件中的风险与验证结论。

---

## 8. 与总控迁移方案映射

对应总控文档：`docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`

1. 批次映射：本专题对应 **Batch-1（Agent 去特殊化收敛）**。
2. 进入条件：Batch-0 文档治理拆分完成，索引与门禁通过。
3. 本批产出：
   - 清理未接线与过期兼容层；
   - 稳定 `get_scene_llm(scene_key)` 契约；
   - 维护专题进展日志与回归证据。
4. 退出条件：
   - 章节 5 验证计划全部通过；
   - 进展日志完成批次回填；
   - 未新增 SSE 契约变更。
5. 回滚锚点：
   - `app/ai/llm_util.py`
   - `app/ai/workflow/multi_agent_graph.py`
