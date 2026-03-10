# Multi-Agent Coverage Gap Visible Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复单目标强数据语义退化、内部补齐缺口外露与编排型工具名泄露，恢复用户可理解的问答体验。

**Architecture:** 保持“模型主判定优先 + 规则兜底”主链不变；新增单目标强语义纠偏，收回 coverage gate 的用户交互职责，并在前端过滤编排型工具展示。所有改动都围绕运行态合同与用户可见 contract 收敛，避免再加兼容壳。

**Tech Stack:** FastAPI、LangGraph、Pydantic、Next.js/React、TypeScript、pytest

---

### Task 1: 先补文档真理源

**Files:**
- Modify: `docs/产品文档/聊天系统需求.md`
- Modify: `docs/产品文档/问数助手需求.md`
- Modify: `docs/开发文档/架构设计/AI模块设计.md`
- Modify: `docs/开发文档/架构设计/问数引擎设计.md`
- Modify: `docs/开发文档/测试管理/聊天系统测试案例.md`
- Modify: `docs/开发文档/测试管理/问数引擎测试案例.md`
- Modify: `docs/开发文档/架构设计/防屎山记录手册.md`
- Modify: `memory-bank.md`

**Step 1: 写入增量需求与设计冻结**

- 记录“coverage 缺口不再触发 clarification”与“单目标强数据语义纠偏”。

**Step 2: 写入测试追溯**

- 为后端回归测试与前端展示回归补用例映射。

### Task 2: 先写失败测试（RED）

**Files:**
- Modify: `tests/unit/test_intent_plan_model_primary.py`
- Modify: `tests/unit/test_multi_intent_queue_flow.py`

**Step 1: 写 planner 单目标纠偏失败用例**

- 模拟模型输出 `general.reply`，断言单目标银行问数仍会被纠偏为 `data.query`。

**Step 2: 写 coverage 文案失败用例**

- 断言缺口提示不再要求用户回复“继续”。
- 断言 partial/final answer 不再出现“如果你愿意，我可以继续补齐”。

**Step 3: 运行定向 pytest 验证 RED**

Run: `bash scripts/pytest_targeted.sh tests/unit/test_intent_plan_model_primary.py tests/unit/test_multi_intent_queue_flow.py -q`
Expected: 新增断言失败，证明测试命中缺陷。

### Task 3: 收敛后端运行态合同

**Files:**
- Modify: `app/ai/prompts/agent_prompts.py`
- Modify: `app/ai/workflow/multi_agent_graph.py`

**Step 1: 调整 planner prompt**

- 把“数据域”示例扩展到余额/金额/数量/贷款/存款/分布等银行问数语义。

**Step 2: 新增单目标强语义纠偏**

- 在 `_resolve_decomposed_goals_for_query` 中，当模型单目标为 `general.reply` 且规则兜底为专家型单目标时，用更具体的兜底目标替换。

**Step 3: 删除 coverage clarification 输出**

- `coverage_gate` 与 `final_composer` 不再调用 `_build_coverage_clarification_questions` / `emit_clarification`。
- 缺口文案改为结果性提示，不再要求用户“继续”。

### Task 4: 收敛前端工具展示

**Files:**
- Modify: `web/src/components/chat/messages/ai.tsx`
- Modify: `web/src/components/chat/messages/tool-calls.tsx`

**Step 1: 定义编排型工具集合**

- 过滤 `assign_to_data_expert`、`assign_to_todo_expert`、`decompose_goals`、`load_skills`。

**Step 2: 同时过滤 tool call 与 tool result 面板**

- 避免灰色进行中条和绿色结果条继续暴露内部工具名。

### Task 5: 运行 GREEN 与收口验证

**Files:**
- Test: `tests/unit/test_intent_plan_model_primary.py`
- Test: `tests/unit/test_multi_intent_queue_flow.py`

**Step 1: 运行定向回归**

Run: `bash scripts/pytest_targeted.sh tests/unit/test_intent_plan_model_primary.py tests/unit/test_multi_intent_queue_flow.py -q`
Expected: PASS

**Step 2: 运行前端类型检查/构建验证**

Run: `pnpm --dir web exec tsc --noEmit`
Expected: PASS

**Step 3: 整理删除清单与残余风险**

- 明确删除了哪些“继续补齐”交互与相关测试断言；
- 记录未补前端自动化测试的原因与残余风险。

### Task 3B: 补齐 single-handoff runtime goals 真理源

**Files:**
- Modify: `app/ai/workflow/multi_agent_graph.py`
- Modify: `tests/unit/test_multi_agent_streaming_helpers.py`

**Step 1: 写直派路径失败测试**

- 当本轮没有 `decompose_goals` ToolMessage，但 supervisor 已直派 `data_expert` 时，dispatcher 必须先解析并写回 `decomposed_goals`，再进入 router guard。

**Step 2: 在 values dispatcher 中补冻结逻辑**

- `ctx.node_name == "supervisor"` 且 handoff_batch 非空、活动目标为空或仅为 `general.reply` 时，调用 `_resolve_decomposed_goals_for_query()` 解析当前用户问题并写回 `final_state["decomposed_goals"]`。

**Step 3: 验证 direct handoff 不再被错误拦截**

Run: `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -q`
Expected: PASS
