# 并行计划书（模板）

> 计划 ID: PP-YYYYMMDD-XXX  
> 主题: <需求主题>  
> 输入来源: `docs/内部参考/迭代需求/requirements.md` / `docs/内部参考/迭代需求/implementation_plan.md`

## 0. G0 协议冻结

- 冻结范围：`done/result/interrupt`
- required/optional：
- 枚举与空值约束：
- 兼容策略：
- 协议机读文件：`contracts/sse_events_v1.json`

## 1. seed 来源

- `task_key`:
- 来源：`plan` / `vkplan 推导`
- `card_seed` 来源：
- 推导依据与风险：

## 2. 目标与边界

- 目标：
- 非目标：
- 约束（架构/性能/合规）：

## 3. 架构冻结项（并行前必须确认）

- 模块边界：
- 状态契约（关键字段 canonical + 来源优先级）：
- 路由闭环（分析→消歧→确认→执行）：
- 前后端链路时序：

## 4. 工作包总览

> 建议先按“并行交付层”与“串行门禁层”分组，避免把回归和终稿文档放到并行阶段。

| WS | 名称 | 类型 | 负责人 | 可并行 | 依赖 |
|----|------|------|--------|--------|------|
| WS-00 | G0 协议冻结 | Foundation |  | 否 | 无 |
| WS-01 |  | Backend |  | 是 | WS-00 |
| WS-02 |  | Frontend |  | 是 | WS-00 |
| WS-G1 | 集成回归门禁 | Gate |  | 否 | WS-01, WS-02 |
| WS-G2 | 文档终稿门禁 | Gate |  | 否 | WS-G1 |

## 5. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|------|----------|------------------|------|
| 文件: `app/ai/workflow/todo_graph.py` | WS-01 | 否 | 单所有者 |
| 字段: `pending_operation.data.title` | WS-01 | 否 | 单写入权 |
| 接口: `/api/v1/chat/stream` | WS-02 | 只读 | 契约冻结 |

## 6. 依赖图与里程碑

- 依赖图：
- 里程碑：

## 7. 合并策略

- 合并顺序：并行交付层 -> 串行门禁层
- 回归门禁：
- 回滚策略：

## 8. 串行回退说明（若触发）

- 是否触发：
- 触发原因：
- 串行执行路线：

## 9. 看板导出索引

- `task_key`:
- 拆解目录 ID:
- WS 总数:
- Gate 总数:
- 默认列流转：`Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则：`<task_key>::<WS-ID>`
- 卡片标题规则：`<WS-ID> <标题> [<task_key>]`

## 10. Gate 执行状态

### 10.1 WS-G1 结果

- `pytest`：
- `tsc`：
- `lint`：
- `docs_guard`：

### 10.2 WS-G2 预期动作

1.
2.
3.

## 11. Gate 收口结果

1. `WS-G1` 已执行：
2. `WS-G2` 已执行：
3. Gate 结论：
