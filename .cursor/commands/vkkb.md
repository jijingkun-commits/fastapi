---
description: VK 看板命令别名（优先 /vk 生成内容，落地失败再 /vktodo）
---

# VK 看板命令别名

`/vk看板` 推荐两阶段执行：

1. 先走 `/vk`：从 `/rwfj` 产物生成“建卡内容 + 导入提示词”
2. 如导入失败，再走 `/vktodo`：MCP/本地后端兜底落卡

请按以下文件中的规范执行（按优先级）：

- `.cursor/commands/vk.md`
- `.cursor/commands/vktodo.md`

示例（推荐无参数名）：

```text
/vk看板 2026-02-12_文档治理
```

```text
/vk看板 auto
```
