# 多智能体补齐缺口可见性收敛设计

## 结论

- 覆盖率缺口属于**编排内部状态**，不再通过 `clarification` 事件要求用户回复“继续”。
- 单目标银行问数若模型主判定退化为 `general.reply`，必须由规则层在**单目标强语义**场景下纠偏回 `data.query`。
- 前端不再直接展示 `assign_to_data_expert`、`assign_to_todo_expert`、`decompose_goals`、`load_skills` 等编排型工具名。

## 背景问题

截图场景“查询 2025 年 6 月 30 日各机构的贷款余额分布”本质是明确的数据查询，但链路里出现了三类设计泄露：

1. planner 模型主判定可能把强数据语义单目标退化成 `general.reply`；
2. coverage gate 把“内部补齐缺口”错当成“需要用户继续确认”；
3. 前端把编排型工具调用名原样展示给用户。

这三者叠加后，用户看到的是“问题回复 / 回复继续 / assign_to_data_expert”，而不是数据查询结果或明确失败说明。

## 目标

1. 让单目标强数据语义至少落到 `data.query`，避免 `问题回复` 兜底污染运行态合同；
2. coverage gate 只做内部完整性判定，不再生成用户交互问题；
3. UI 仅展示用户可理解的结果与状态，不暴露编排工具名。

## 方案对比

| 方案 | 做法 | 优点 | 缺点 | 结论 |
| --- | --- | --- | --- | --- |
| A | 只改 planner prompt | 改动小 | 依赖模型稳定性，无法兜住回归 | 否 |
| B | 只改前端隐藏内部工具 | 立刻止血 | 根因仍在，`继续补齐` 仍会出现 | 否 |
| C | 同时收敛 planner 单目标纠偏、coverage 输出语义、前端工具脱敏 | 同时修复根因与外显症状 | 需改前后端与测试 | 是 |

## 最终方案

### 1. 单目标强语义纠偏

- 继续保留“模型主判定优先”；
- 当模型给出单目标 `general.reply`，而规则兜底给出单目标专家型目标（如 `data.query` / `todo.query`）时，执行单目标纠偏；
- 该纠偏只发生在**单目标**且**兜底更具体**的场景，避免把“查询一下待办”重新误扩成 `data.query`。

### 2. Coverage Gate 职责收敛

- `coverage_gate` / `final_composer` 对内部缺口不再发 `clarification`；
- 缺口说明改为结果性文案：已返回当前可确认内容，剩余部分请稍后重试；
- 真正的用户澄清仍由 intent/data clarify 节点触发，coverage 不再承担交互职责。

### 3. 前端展示脱敏

- 编排型工具调用和工具结果默认隐藏：
  - `assign_to_data_expert`
  - `assign_to_todo_expert`
  - `decompose_goals`
  - `load_skills`
- 保留结构化结果卡片与状态文案，避免用户误把内部路由名当成产品语义。

## 影响范围

- 后端：`app/ai/workflow/multi_agent_graph.py`、`app/ai/prompts/agent_prompts.py`
- 前端：`web/src/components/chat/messages/ai.tsx`、`web/src/components/chat/messages/tool-calls.tsx`
- 测试：`tests/unit/test_intent_plan_model_primary.py`、`tests/unit/test_multi_intent_queue_flow.py`
- 文档：需求、设计、测试案例、防屎山记录、memory-bank

## 风险与回退

| 风险 | 控制手段 | 回退路径 |
| --- | --- | --- |
| 单目标纠偏过度 | 仅在“模型=general + 兜底=专家型单目标”触发 | 回退到仅 prompt 调整 |
| 缺口提示过于保守 | 保留 status 与 final answer 双层可见信息 | 回退为旧提示文案，但不恢复 clarification |
| 隐藏工具影响调试 | 保留 `hideToolCalls=false` 以外的状态文案和结构化结果 | 临时回退前端过滤集合 |

### 4. Runtime Goals 真理源补口

- 除 `decompose_goals` 显式工具路径外，**单目标 supervisor 直接委派**在进入 `router_guard` 前也必须冻结同一份 `decomposed_goals`。
- 不能出现“supervisor 已识别为 data_expert，但 router_guard 仍按 `general.reply` 的 allowed_agents 校验”的双真理源状态。
- 运行态只允许一份活动目标：`preprocess/planner` 冻结 -> `supervisor` 复用 -> `router_guard` 校验 -> `coverage_gate` 对账。
