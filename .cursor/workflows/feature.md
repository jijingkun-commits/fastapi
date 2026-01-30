---
description: ⚡️ 全流程开发引擎：规划(Opus) -> 实现(Opus) -> 审查/自测(Sonnet) -> 验证(Sonnet)
---

# 🚂 全特性开发 (Feature Development)

这是 Antigravity 的**旗舰工作流**。一个指令，完成从需求到交付的全过程。
它**隐式包含**了 `/plan`, `/implement` 和文档规范的要求。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。


## 阶段 1: 规划与契约 (Planning & Contract)

1.  **需求分析**: 
    -   询问用户意图。
    -   生成/更新 `docs/内部参考/迭代需求/requirements.md`。
    -   **Check**: 必须包含 User Stories 和 Acceptance Criteria。

2.  **技术设计**:
    -   如果任务复杂，生成 `implementation_plan.md` (Artifact)。
    -   决定是否需要编写 **ADR** (记录到 `docs/内部参考/决策记录.md`)。

3.  **用户确认**: 
    -   只有用户对 `requirements.md` 满意后，才进入下一阶段。

## 阶段 2: 编码与同步 (Coding & Sync)

1.  **Vibe Coding**:
    -   读取 `requirements.md` 作为真理来源。
    -   遵循 `rules.md` (中文注释, 最简, 无冗余)。
    -   **禁止**: 自作聪明地修改需求，除非经过确认。

2.  **文档自动同步 (Doc-as-Code)**:
    -   **API 变更** ➡️ 更新 `docs/API文档/接口文档.md`。
    -   **数据库变更** ➡️ 更新 `docs/开发文档/架构设计/数据库设计.md`。
    -   **配置变更** ➡️ 更新 `docs/开发文档/快速入门/配置说明.md`。
    -   **重要**: 编码完成后，不要立刻自行纠错，交由 Review 阶段进行低成本测试。

## 阶段 3: 审查与自测 (Review & Self-Test)
> **注意**: 建议人工切换到性价比更高的模型进行此阶段，以节省成本。由 Reviewer 承担“运行代码”和“检查错误”的职责。

1.  **自测 (Self-Testing)**:
    -   **位置**: 在代码生成后，人工审查前。
    -   **动作**: 运行单元测试、启动服务验证或编写简单的验证脚本。
    -   *策略*: 如果发现简单语法/运行错误，由此模型直接修复。
    -   *异常*: 如果发现严重逻辑错误，暂停并报告，可能需要切回 Opus。

2.  **代码审查 (Code Review)**:
    -   检查代码可读性、最简原则。
    -   检查文档是否已同步。
    -   确认是否符合 `rules.md`。

## 阶段 4. 验证与日志/数据验收 (Verification & Inspection)
**模型**: ⚡️ **Review Model (Sonnet)**

1.  **无报错确认**:
    -   检查 `logs/assistant.log`，确保测试期间没有 `ERROR` 或 `CRITICAL` 日志。
    -   *指令*: `grep -C 5 "ERROR" logs/assistant.log`

2.  **数据持久化确认**:
    -   查询数据库，确认数据已正确写入/更新。
    -   *连接*: `postgresql://postgres:postgres@localhost:5432/chat_db`

3.  **生成报告**: 
    -   汇总测试结果和数据验证情况，交付给用户。

---

## 🚦 如何使用
直接输入：
```
/feature 我想做一个 [xxx] 功能
```
或者在已有上下文时：
```
/feature 完成 requirements.md 里定义的剩余工作
```
