---
description: VK 看板命令别名（并行规划推荐先 /vkplan，再 /rwfj -> /vk，落地失败再 /vktodo）
---

# VK 看板命令别名

`/vkkb` 推荐三阶段执行：

1. （可选）先走 `/vkplan`：在规划阶段直接产出 `task_key/card_seed`
2. 再走 `/vk`：从 `/rwfj` 产物生成“建卡内容 + 导入提示词”
3. 如导入失败，再走 `/vktodo`：MCP/本地后端兜底落卡

请按以下文件中的规范执行（按优先级）：

- `.cursor/commands/vk.md`
- `.cursor/commands/vktodo.md`

示例（推荐无参数名）：

```text
/vkkb 2026-02-12_文档治理
```

```text
/vkkb auto
```
