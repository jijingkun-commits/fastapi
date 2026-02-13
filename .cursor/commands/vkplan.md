---
description: 并行规划快捷命令：等价于 /plan parallel，产出可供 /rwfj 直读的 seed
---

> 参考规则: @dual-database

# VKPlan 工作流 (Parallel Planning Shortcut)

用于在规划阶段直接产出“可拆解、可落卡”的最小结构化种子，避免 `/rwfj` 只能基于纯文字推断。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 定位

`/vkplan` = `/plan parallel`

- 保留完整规划产物：`requirements.md` + `implementation_plan.md`
- 额外强制：`task_key` + 最小 `card_seed`
- 目标：给 `/rwfj` 提供 machine-readable 输入

---

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 需要多人/多 AI/多 worktree 并行 | `/vkplan` ✅ |
| 只需技术方案，不拆卡 | `/plan` |
| 已有拆解文档，直接落卡 | `/vk` |

---

## 必做产出

1. `docs/内部参考/迭代需求/requirements.md`
2. `docs/内部参考/迭代需求/implementation_plan.md`
3. 在 `implementation_plan.md` 中新增并行种子区块：
   - `task_key`
   - `card_seed[]`（每项至少包含 `cap_id/title/hard_depends_on/soft_depends_on/file_scope/owner_fields/check_cmd/dod`）

### 最小示例（YAML）

```yaml
task_key: PP-20260213-TODO-REFINE
card_seed:
  - cap_id: CAP-01
    title: 后端意图路由收敛
    hard_depends_on: [WS-00]
    soft_depends_on: []
    file_scope: [app/ai/workflow/**, app/ai/state.py]
    owner_fields: [turn_act, clarify_fsm_state]
    check_cmd: [venv/bin/python -m pytest -q tests/unit -k todo_graph]
    dod:
      - 路由可收敛且无重复澄清循环
  - cap_id: CAP-02
    title: SSE 协议 owner 对齐
    hard_depends_on: [WS-00]
    soft_depends_on: [CAP-01]
    file_scope: [app/api/**, app/services/**]
    owner_fields: [sse.done, sse.result, sse.interrupt]
    check_cmd: [venv/bin/python -m pytest -q tests/api -k chat]
    dod:
      - done/result/interrupt 与冻结契约一致
```

---

## 下游链路

推荐链路：`/vkplan -> /rwfj -> /vk -> /imp-ws`

1. `/rwfj` 基于 `task_key/card_seed` 生成 `WS-00 + WS-*.md`。
2. `/vk` 读取 `card_export` 落看板，卡片标题自动带 `task_key` 前缀。
3. `/imp-ws` 按单 WS 白名单执行。

---
*使用 `/vkplan` 触发。用于“规划即并行”。*
---
