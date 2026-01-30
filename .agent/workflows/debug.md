---
description: 🕵️‍♀️ 标准排查流 (Debug Model)：重现 -> 定位 -> 修复 -> 记录
---

# 🕵️‍♀️ 问题排查工作流 (Investigation Workflow)

此工作流专门用于 **修复 Bug** 或 **排查疑难杂症**。使用擅长分析日志和上下文的模型。

核心原则：**先重现，再修复** (Reproduce first, fix later)。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 阶段 1: 定义与重现 (Define & Reproduce)

1.  **收集证据**:
    -   `@Logs`: 粘贴报错日志。
    -   `@Context`: 提供相关代码。
    
2.  **最小重现 (Minimal Reproduction)**:
    -   编写一个独立的脚本 `reproduce_issue.py` 或测试用例。
    -   **目标**: 能够稳定触发 Bug。
    -   *如果无法重现，就无法确认修复。*

## 阶段 2: 分析与定位 (Analyze & RCA)

1.  **假设驱动**: 提出假设 -> 验证假设。
2.  **日志分析**:
    -   检查应用日志: `tail -n 100 logs/assistant.log` (默认位置)
    -   检查系统/容器日志: `docker compose logs postgres`
3.  **数据库分析**:
    -   默认连接: `postgresql+psycopg://postgres:postgres@localhost:5432/chat_db`
    -   使用 `postgres_query` 工具查询异常数据。

## 阶段 3: 修复与验证 (Fix & Verify)

1.  **实施修复**: 修改代码。
2.  **验证修复**: 再次运行 `reproduce_issue.py`，确保 Bug 消失。
3.  **回归测试**: 运行相关模块的测试，确保没引入新 Bug。

## 阶段 4: 记录与沉淀 (Record)

1.  **更新文档**: 如果是逻辑变更，更新对应的架构或产品文档。
2.  **补充用例**: 将 `reproduce_issue.py` 转化为永久的测试用例，补充到 `docs/开发文档/测试管理/测试用例库.md`。

---

## 🚦 如何使用
直接输入：
```
/debug 生产环境出现 500 错误，日志如下...
```
