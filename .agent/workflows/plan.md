---
description: 核心规划流程：需求澄清 -> 编写需求文档(PRD) -> 技术方案设计
---

# 规划工作流 (Planning Workflow)

此工作流是开发周期的起点。
**核心目标**：将模糊的想法转化为明确的文档，为后续的 **Coding** 和 **Testing** 提供“真理来源 (Source of Truth)”。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 1. 需求分析 (Requirement Analysis)
**动作**: 与用户对话，澄清目标。
**产出**: 创建/更新 `docs/内部参考/迭代需求/requirements.md` (Artifact)。

**`requirements.md` 必须包含**：
1.  **用户故事 (User Stories)**: 谁？在什么场景？想要做什么？
2.  **验收标准 (Acceptance Criteria)**:
    *   **功能性**: 必须实现什么（Happy Path）。
    *   **异常/边界**: 必须处理什么（如：断网、非法输入、超长文本）。 -> *这对 /test 编写异常用例至关重要*。
3.  **非功能需求**: 性能（响应时间）、安全（权限）、数据一致性。

> **注意**: `requirements.md` 用于当前迭代。如果涉及**新增模块**或**核心功能变更**，必须同步更新 `docs/产品文档/产品概述.md`。

## 2. 技术方案 (Technical Design)
**动作**: 基于需求，设计实现路径。
**产出**: 创建 `implementation_plan.md` (Artifact)。

**内容要求**：
1.  **架构变更**: 涉及哪些模块？数据库表结构要改吗？API 接口怎么定义？
2.  **MCP 工具**: 涉及哪些 AI 工具的调用？
3.  **风险评估**: 哪里容易出 Bug？（即重点测试区域）。

## 3. 衔接测试 (Handover to Test)
在完成本工作流后，你将拥有明确的 `requirements.md`。
此时执行 `/test` 工作流，Agent 将直接读取 `requirements.md` 作为“需求来源”，从而自动生成高覆盖率的测试用例。

---
*提示：使用 `/plan` 触发此工作流。*
