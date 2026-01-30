---
description: ⚡️ 核心开发流：实现功能 -> 自动更新文档 -> 验证
---

# 🚀 自动实现工作流 (Implementation Workflow)

此工作流用于将 `requirements.md` 或 `implementation_plan.md` 转化为代码，并**强制执行**文档同步。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 1. 编码 (Coding)
**动作**: 读取计划，编写代码。
**关键**:
*   遵循 `rules.md` (中文注释, 最简逻辑)。
*   修改 API 时，同步修改 `docs/接口文档/`。
*   修改业务逻辑时，同步修改 `docs/功能详解/`。

## 2. 文档同步 (Doc Sync)
**动作**: 检查本次变更涉及的范围，**自动**更新对应的文档。
> **Checklist**:
> - [ ] API 变了吗？ -> 更新 `docs/API文档/接口文档.md`
> - [ ] 数据库变了吗？ -> 更新 `docs/开发文档/架构设计/数据库设计.md`
> - [ ] 配置变了吗？ -> 更新 `docs/开发文档/快速入门/配置说明.md`

## 3. 验证 (Verification)
**动作**: 运行测试。
```bash
python -m pytest tests/xxx
```
或者使用 `/test` 工作流。

---
*提示：这是 Vibe Coding 的"执行"阶段。使用 `/imp` 触发。*