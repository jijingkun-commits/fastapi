---
description: 发散澄清入口（探索优先）：沉淀方案快照并回传 /jjk-clarify 收敛
---

# Ask - 发散澄清与方案探索

`/ask` 用于“需求还很模糊、先要打开思路”的场景。  
它不是执行链入口，标准收敛出口是 `/jjk-clarify`。

## 何时使用

1. 需求刚出现，约束还不完整；
2. 需要先看 2-3 个方向再选；
3. 用户明确要求“先头脑风暴，不急着落地”。

## 与 `/jjk-clarify` 的边界

1. `/ask`：发散探索，输出“探索快照”。
2. `/jjk-clarify`：冻结设计，输出 `design_freeze_summary + clarify_handoff_contract`。
3. 若用户在 `/ask` 阶段直接要求落地，必须切换到 `/jjk-clarify` 再进入下游。

---

## 执行流程（简化）

### 1) 理解问题

聚焦三件事：
1. 真实目标；
2. 硬约束（时间/风险/兼容）；
3. 可量化成功标准。

### 2) 方案发散（可取点保留）

提出 2-3 个候选方向（不超过 3 个）：
1. 稳健方案（低风险）；
2. 平衡方案（默认推荐）；
3. 激进方案（高收益高改动，可选）。

每个方向仅保留：
1. 核心思路；
2. 优势；
3. 主要风险；
4. 预估工作量。

### 3) 收敛结论

输出单一推荐方向，并明确：
1. 为什么选它；
2. 为什么放弃其余方向（简述）；
3. 下一步建议切换 `/jjk-clarify` 进行冻结。

---

## 输出产物（探索快照）

默认不强制落盘；用户要求落盘时可写入 `docs/plans/YYYY-MM-DD-<topic>-brainstorm.md`，内容仅含：

```yaml
ask_output:
  topic: "<topic>"
  selected_direction: "<direction>"
  alternatives_considered: ["A", "B"]
  key_constraints: []
  open_questions: []
  recommended_next_command: "/jjk-clarify"
```

---

## 完成门禁（强制）

1. 至少讨论 2 个候选方向，否则输出 `ASK_BRAINSTORM_INSUFFICIENT`。
2. 必须有单一推荐方向，否则输出 `ASK_DECISION_MISSING`。
3. 若用户要求直接执行，必须先切换 `/jjk-clarify`，否则输出 `ASK_TO_CLARIFY_REQUIRED`。

---

## 禁止项（强制）

1. 禁止在 `/ask` 阶段直接进入 `/jjk-imp` 或 `/jjk-vkplan`。
2. 禁止把探索对比表直接写入 `design.md`、`*_requirements.md`、`*_implementation_plan.md`。
3. 禁止以“发散讨论”替代字段级契约冻结。

---

*使用 `/ask` 触发。目标是“高质量发散”，并把收敛动作交给 `/jjk-clarify`。*
