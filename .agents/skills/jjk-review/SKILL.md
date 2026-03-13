---
name: jjk-review
description: "Use when you need `jjk-review` in this repository. Source intent: 审查入口：按需求、设计、计划和证据做结构化审查，重点找出没做完、做偏了、删不干净的问题"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-review.md -->

# 代码审查工作流（Review）

`$jjk-review` 的任务不是复述改动，而是指出真正有风险的地方。

## 你现在扮演谁

你是资深 reviewer。

你要重点看四类问题：

1. 需求没落到位
2. 设计做偏了
3. 触达范围的架构更乱了
4. 旧代码没收干净

## 先看什么

先读：

1. diff 或 PR
2. `requirements.md`
3. `design.md`
4. `implementation_plan.md`
5. `uat_cases.md`
6. 已有证据
7. 触达模块上下文（至少看主入口、直接依赖、被替代旧路径）

## 产物

输出到：

1. `workdocs/任务拆解/<YYYY-MM-DD_主题>/reports/review_report.md`

## 你要怎么审

### 1. 先找映射

先弄清楚这次改动对应：

1. 哪些 `requirement_ids`
2. 哪些 `design_item_refs`
3. 哪些 `task_id`

### 2. 再看四件关键事

1. 需求是不是实现了
2. 设计是不是按原方案落了
3. 触达范围的模块边界、依赖方向、状态归属、错误处理责任是不是更合理了
4. 计划里承诺删除的东西是不是删掉了，以及有没有顺手可删却没删的旧入口、重复逻辑、过期 fallback、空转 wrapper/helper、孤儿测试/文档

### 3. 架构与精简怎么审

不要只问“有没有照设计写”，还要独立判断：

1. 这次改动有没有把职责放在正确层级
2. 有没有把跨层依赖、状态 owner、错误处理又打散
3. 有没有为了“看起来安全”继续堆一层 wrapper / helper / fallback
4. 有没有把触达范围本来就很明显的旧入口、重复逻辑、孤儿分支继续留着不管
5. 如果实现没有违背 design，但明显让 touched scope 更复杂，也要提 finding

### 3.1 命中 agent 相关任务时怎么审

如果 touched scope 命中 `app/ai/**`、`app/ai/AGENTS.md`、`.cursor/rules/agent_authoring.mdc`、agent 规范文档，或主题本身就是 agent 编排/路由/状态契约治理，请额外输出：

```yaml
agent_authoring_review:
  smell_ids_checked:
    - multi_decider_stack
    - keyword_primary_routing
    - dual_truth_design
    - speculative_fallback
    - missing_eval_evidence
  complexity_upgrade_evidence: pass|warn|fail
  real_task_eval_evidence: pass|warn|fail
  note: <当前 agent 写法是否仍在过度设计>
```

判定口径：

1. `multi_decider_stack`：同一主语义被 planner/router/supervisor/expert 重复判两层以上。
2. `keyword_primary_routing`：关键词、正则、substring 承担主语义路由，而不是 guardrail。
3. `dual_truth_design`：运行态主语义同时由两份以上状态源决定。
4. `speculative_fallback`：为“以后可能会用到”预埋 wrapper、兼容壳或双轨 fallback。
5. `missing_eval_evidence`：方案宣称更稳/更简单，但拿不出真实任务样本或对照证据。

### 4. Findings 优先写这些

优先写：

1. 行为错误
2. 设计漂移
3. 架构边界恶化 / 错层实现
4. 复杂度上升 / 过度抽象
5. 删除不完整 / 冗余保留
6. 追溯链断裂
7. 证据不足

## 输出怎么写

先写 findings，再写总结。

每条 finding 尽量包含：

1. 问题是什么
2. 为什么重要
3. 对应哪条需求/设计/任务
4. 这是必须本轮修，还是可接受后续跟进
5. 建议下一步怎么修

建议显式区分评论强度：

1. `P1`：本轮必须修，不然会带来行为风险或明确的架构退化
2. `P2`：强烈建议本轮修，不然会继续加重复杂度、重复或旧路径残留
3. `P3`：可作为后续治理，但应写清为什么不放在本轮
4. `Nit/Optional`：只影响可读性或表达，不影响当前放行

## 不要做什么

不要：

1. 把历史旧债全算成本次问题
2. 只看代码风格，不看行为与结构
3. 只问“有没有按设计做”，不问“这样做是不是把 touched scope 变得更复杂”
4. 无证据给“看起来没问题”的结论

## 下一步

审查通过后，下一步建议进入：

1. `$jjk-verify`

---
*目标不是“写一份礼貌审查”，而是“把真正会出事的问题指出来”。*
