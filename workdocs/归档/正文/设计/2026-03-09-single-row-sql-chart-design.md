# Single-row SQL Chart Design

**Goal:** 当 `sql_result` 仅返回 1 条记录时，聊天页不渲染图表，保留文本摘要与结果表格；多条结果继续保留图表。

## 背景
- 当前单条机构结果会生成一根铺满画布的柱状图，信息增益低，用户容易误判为图表异常。
- 后端 `sql_result.chart` contract 已稳定，问题在前端展示策略，不应反向改动后端生成逻辑。

## 设计决策
1. 单条结果不渲染 `SqlResultChart`，把该场景视为正常降级而不是错误。
2. 多条柱状图保留，但补齐展示细节：优先使用中文/友好轴标签、少量类目时限制柱宽、给柱顶增加数值标签。
3. SSE / SQL / chart payload contract 不变，避免把 UI 特判扩散到后端。

## 影响范围
- `web/src/components/chat/messages/sql-result-chart.tsx`
- `web/src/components/chat/messages/ai.tsx`
- `docs/产品文档/问数助手需求.md`
- `docs/开发文档/测试管理/问数引擎测试案例.md`

## 验收口径
- 单条结果：无图表、有表格、有结果摘要，不再出现图表坐标轴技术字段名。
- 多条结果：图表继续展示，且轴标签与数据标签更友好。
