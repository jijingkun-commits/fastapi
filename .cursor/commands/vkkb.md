---
description: VK 看板一体命令（前置完成 /vkplan 后自动补导出并落卡）
---

# VK 看板一体命令

`/vkkb` 默认一条命令完成“导出 + 落卡”（含自动基线校验）：

1. 读取 `<任务拆解目录>/vk_cards.json`
2. 若缺失，先自动执行 `/vk <任务拆解目录> strict` 生成导出产物
3. 自动执行 `/vktodo <任务拆解目录> create` 批量落卡
4. 如指定 `move <状态>`，继续推进状态
5. 若命中 G0 自动完成条件，自动将 `WS-00` 推进到 `Done`

推荐最短链路：`/plan -> /vkplan -> /vkkb`

请按以下文件中的规范执行（按优先级）：

- `.cursor/commands/vk.md`
- `.cursor/commands/vktodo.md`

示例（推荐无参数名）：

```text
/vkkb 2026-02-12_文档治理
```

```text
/vkkb 2026-02-12_文档治理 move Doing
```
