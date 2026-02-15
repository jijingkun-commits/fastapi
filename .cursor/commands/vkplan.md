---
description: 并行拆解入口（前提：已完成 /plan）
---

> 参考规则: @dual-database

# VKPlan 工作流 (Parallel Split Shortcut)

用于在 `/plan` 完成后执行并行拆解，产出可直接供 `/vktodo` 落卡的结果。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 定位

- 前置要求：必须先完成 `/plan`
- 核心目标：完成并行拆解与 G0 冻结，生成 `vk_cards.json` 供 `/vktodo` 直接使用

---

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 已完成 `/plan`，准备并行拆解 | `/vkplan` ✅ |
| 尚未完成需求与技术方案 | 先 `/plan` |
| 已有完整拆解产物，仅需重落卡 | `/vktodo` |

---

## 执行阶段

1. 读取 `/plan` 产物（`requirements.md`、`implementation_plan.md`）。
2. 生成并行拆解（`parallel_plan.md` + `workstreams/WS-*.md`）。
3. 在拆解阶段完成 G0（`WS-00`）冻结与机读契约。
4. 生成 `vk_cards.json` 与 `vk_import_prompt.txt`（默认落卡范围不含 `WS-00`）。

若任一阶段失败，立即停止并给出系统性修复建议（含架构归因与维护性影响）。

---

## 必做产出

1. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/parallel_plan.md`
2. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-*.md`
3. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/vk_cards.json`
4. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/vk_import_prompt.txt`

---

## 下游链路

推荐极简链路：`/plan -> /vkplan -> /vktodo（或 /vkkb） -> /imp-ws`

- `/vktodo`：直接落卡/推进（多 worktree 场景默认执行 `/vksync` 硬拦截）
- `/imp-ws`：从并行层 WS 开始执行（`WS-00` 已由前置阶段完成）

手工分步链路（调试用）：`/plan -> /vkplan -> /vksync -> /vk -> /vktodo`

---
*使用 `/vkplan` 触发。用于“完成拆解后直接进入 `/vktodo`”。*
---
