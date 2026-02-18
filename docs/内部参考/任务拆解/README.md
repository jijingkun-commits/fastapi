# 任务拆解目录说明

本目录用于沉淀“并行执行计划书”，服务于多人协作与复杂需求拆分。

## 目录结构

```text
docs/内部参考/任务拆解/
├── README.md
├── _templates/
│   ├── parallel_plan_template.md
│   ├── workstream_template.md
│   └── merge_checklist_template.md
└── <YYYY-MM-DD_主题>/
    ├── parallel_plan.md
    ├── workstreams/
    │   ├── WS-00_*.md
    │   ├── WS-01_*.md
    │   └── WS-G1_*.md
    └── merge_checklist.md
```

## 使用建议

1. 先执行 `/plan`（或并行场景用 `/vkplan`），确认需求与架构边界。
2. 再执行 `/vkplan`，基于模板输出 `WS-00 + WS-N` 并行工作包。
3. 执行 `/vktodo` 读取 `vk_cards.json` 批量落卡（卡片自动带 `task_key` 前缀）。
4. 每个工作包按 `/imp-ws` 独立实施。

## 并行前 3 秒判断法

凡是“必须等别人先做完才能开始”的任务，一律不作为并行 WS。

- 可独立开始 + 可独立交付 + 无共享写冲突 → 可并行
- 其余情况 → 不并行（改为单任务 `/imp` 或先解耦再拆）

## 无总控协作流程（默认）

1. 拆解后由需求方将 `WS-*.md` 一对一分配给协作者。
2. 协作者仅修改各自白名单文件，不跨 WS 改动。
3. 协作者在各自 WS 文档末尾填写“协作者自检卡”并回传。
4. 仅当出现共享文件/共享字段冲突时，启用 `merge_checklist.md` 汇总检查。
