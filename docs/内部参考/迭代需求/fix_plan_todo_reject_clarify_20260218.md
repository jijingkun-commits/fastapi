# FIX-20260218-01: 待办补充“答非所问”修复计划

> 文档状态：已完成（含复现证据）
> 创建时间：2026-02-18
> 最后更新：2026-02-28
> 严重程度：P1

---

## 1. 问题摘要

### 现象

在待办创建/编辑流程中，当用户先拒绝确认卡，再补充信息（如时间、地点、同行人）时，系统偶发进入不相关回答或错误路由，出现“答非所问”。

### 影响

1. 多轮上下文连贯性下降。
2. 用户需要重复输入目标信息。
3. 待办确认链路稳定性受影响。

---

## 2. 目标与范围

### 目标

1. 拒绝后补充信息优先回到同一待办上下文。
2. 不再触发无关闲聊回复或错误意图跳转。
3. 保持确认卡行为与 SSE 状态同步一致。

### 非目标

1. 不扩展新业务意图类型。
2. 不改动待办 CRUD 数据结构。

---

## 3. 待办清单

- [x] 复现实例并补充最小可复现日志（含输入轮次、路由决策、节点输出）。
- [x] 明确“拒绝后补充”判定优先级，固化到待办路由决策逻辑。
- [x] 增加单元测试覆盖：拒绝后补充应恢复同一草稿上下文。
- [x] 增加场景测试覆盖：包含“拒绝 -> 补充时间/地点 -> 再确认”完整链路。
- [x] 回填测试报告与文档索引状态。

### 3.1 测试回填记录（2026-02-27）

1. 新增/补强测试：
   - `tests/unit/test_todo_nodes.py::TestTodoRejectSupplementRecovery::test_merge_create_draft_with_supplement_should_override_time_location_and_append_desc`
   - `tests/unit/test_todo_nodes.py::TestTodoRejectSupplementRecovery::test_reject_then_supplement_should_recover_create_draft`
   - `tests/unit/test_todo_nodes.py::TestTodoRejectSupplementRecovery::test_reject_then_supplement_time_location_should_keep_same_create_draft`
2. 执行命令：
   - `PYTHONPATH=. pytest --no-cov tests/unit/test_todo_nodes.py -k "TestTodoRejectSupplementRecovery and (merge_create_draft_with_supplement_should_override_time_location_and_append_desc or reject_then_supplement_should_recover_create_draft or reject_then_supplement_time_location_should_keep_same_create_draft)"`
3. 结果：
   - `3 passed, 37 deselected, 8 warnings in 0.06s`

### 3.2 最小可复现日志（拒绝 -> 补充 -> 再确认）

1. 复现实例 A（补充描述）：
   - 输入轮次：
     - R1 用户：`明天上午9点去陆家嘴和张三开会`
     - R2 用户：`拒绝`
     - R3 用户：`需要带纸和笔`
   - 路由决策（INFO）：
     - `LLM 分析结果: intent='update', action_state='need_clarify'`
     - `恢复最近取消的创建草稿: keys=['title', 'time', 'due_date', 'location', 'description']`
     - `补充轮恢复: 命中最近取消的创建草稿，自动转为 create/need_confirm`
   - 节点输出（INFO）：
     - `todo意图内核: ... action_state=need_confirm, missing=[]`
     - `需要确认: create`
2. 复现实例 B（补充时间/地点）：
   - 输入轮次：
     - R1 用户：`明天上午9点和张三在陆家嘴开会`
     - R2 用户：`拒绝`
     - R3 用户：`改到明天下午3点，在会议室A开会`
   - 路由决策与节点输出同 A，最终进入 `create/need_confirm`。
3. 复现实验命令（带日志）：
   - `PYTHONPATH=. pytest --no-cov tests/unit/test_todo_nodes.py -k "reject_then_supplement_should_recover_create_draft or reject_then_supplement_time_location_should_keep_same_create_draft" -o log_cli=true --log-cli-level=INFO`
4. 复现实验结果：
   - `2 passed, 38 deselected, 8 warnings in 0.09s`

### 3.3 判定优先级（已固化到路由逻辑）

当前 `analyze_intent` 的补充分支优先级如下（代码锚点：`app/ai/workflow/todo_graph.py`）：

1. **补充轮合并优先**：若存在历史 `pending_operation`，先走 `_merge_pending_operation_by_supplement`（约 L1048）。
2. **取消后恢复次优先**：若 `need_clarify` 且无 `pending_operation` 且缺 `todo_target`，命中最近“创建后取消”草稿则强制恢复为 `create/need_confirm`（约 L1073-L1110）。
3. **澄清状态收敛**：恢复成功后清空缺项并写入 `clarify_fsm_state=done`、`clarify_round=0`（约 L1112-L1120）。

该优先级保证“拒绝后补充”不再误落到通用闲聊/错误目标待办分支，符合本问题修复目标。

---

## 4. 验证标准

1. 拒绝后补充信息时，系统进入待办补充分支而非通用聊天分支。
2. 多轮上下文中 `current_todo_id` / 草稿上下文连续性正确。
3. 对应自动化测试通过且结果可复现。

---

## 5. 回滚与风险

### 风险

1. 路由优先级调整可能影响其他待办边界意图。
2. 过于激进的“补充恢复”规则可能误吞正常问答请求。

### 回滚

1. 保留路由判定开关，必要时回退到上一版判定策略。
2. 通过新增测试用例定位具体回归点后再灰度恢复。
