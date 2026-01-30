---
description: 执行全链路测试：环境准备 -> 需求锁定 -> 用例生成 -> 执行验证 -> 报告产出
---

# 测试执行脚本 (Test Execution Protocol)
**模型**: ⚡️ **Review/Test Model (Sonnet)**
本阶段由 Review/Test 模型全权负责，专注于覆盖率与缺陷发现。

此文件定义了 Agent 执行测试的**严格步骤**。请按顺序执行，不要跳过。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

> [!IMPORTANT]
> **模型限制**: 测试对话时只能使用**数据库默认模型** (即 `t_llm_provider` 表中 `is_default=true` 的模型)，禁止手动切换到高成本模型。

## 🔴 Step 0: 环境准备 (Environment Setup)

**指令**: 在开始测试前，确保前后端服务正常运行。

### 端口配置

| 服务 | 端口 | 检查命令 |
|------|------|----------|
| 前端 (Next.js) | `3000` | `lsof -i :3000` |
| 后端 (FastAPI) | `8000` | `lsof -i :8000` |

### 启动流程

1. **检查后端 (8000)**:
   ```bash
   # 检查端口是否被占用
   lsof -i :8000
   # 如果无输出，启动后端
   cd /Users/jijingkun/bojxAI/fastapi && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **检查前端 (3000)**:
   ```bash
   # 检查端口是否被占用
   lsof -i :3000
   # 如果无输出，启动前端
   cd /Users/jijingkun/bojxAI/fastapi/web && npm run dev
   ```

3. **验证服务**: 确认 http://localhost:3000 和 http://localhost:8000/docs 可访问。

### 测试账号

| 用户名 | 密码 | 用途 |
|--------|------|------|
| `jjk` | (空) | 默认测试账号 |

> **注意**: 如果端口已被占用且服务正常，直接进入下一步；无需重启。

---

## 🔴 Step 1: 锁定测试依据 (Acquire Context)
**指令**: 在开始测试前，必须明确"预期结果"来自哪里。
1.  检查是否存在 `requirements.md` (由 `/plan` 生成)。
2.  **检查测试用例库**: 查看 `docs/测试管理/测试用例库.md` 是否有相关已存用例。
3.  若无，询问用户："请提供功能需求描述或文档路径"。
4.  若用户未提供，**必须**先阅读代码 (`view_file`)，然后基于代码逻辑反推需求。

## 🔴 Step 2: 生成测试矩阵 (Generate Test Cases)
**指令**: 创建 Artifact `test_cases.md`。并不是简单的列表，必须包含以下两部分：

1.  **功能验证 (Functional)**: 覆盖正常业务流 (Happy Path)。
2.  **破坏性测试 (Destructive)**: 必须包含至少 3 个异常场景：
    *   **幻觉陷阱**: 询问不存在的数据。
    *   **安全注入**: 尝试 Prompt 攻击。
    *   **边界压力**: 极限输入长度或并发。

*在文件中显式定义预期数据状态 (e.g., `SELECT count(*) FROM t_todo WHERE ...`)。*

## 🔴 Step 3: 执行与深度验证 (Execute & Verify)
**指令**: 依次执行用例。对于每个用例，执行严格的三重验证：

1.  **UI/API 层**:
    *   验证响应状态码及 JSON 结构。
    *   如果涉及前端，检查 Playwright 截图差异。
2.  **数据层 (Deep verify)**:
    *   使用 `mcp_postgres_query` 查询数据库。
    *   **判定规则**: 如果 UI 显示成功但 DB 无数据 -> **FAIL (Fake Positive)**。
3.  **系统层 (Log Audit)**:
    *   检查日志: `grep -i "error" logs/assistant.log` (或 docker logs)。
    *   要求: **零 Error**。任何报错必须解释。

## 🔴 Step 4: 产出报告 (Final Report)
**指令**: 创建 Artifact `test_report.md`。

**内容必须包含**:
1.  **Executive Summary**: 一句话结论 (PASS / FAIL / WARN)。
2.  **Defect List**: 发现的所有问题（含日志片段、截图链接）。
3.  **Trace Matrix**: 对比表 (用例ID | UI结果 | DB结果 | 最终状态)。

## 🔴 Step 5: 沉淀资产 (Sediment Assets)
**指令**: 形成 **"使用 -> 验证 -> 沉淀"** 的闭环。
1.  **更新用例库**: 将本次测试中新发现的有效用例、边界条件补充到 `docs/开发文档/测试管理/测试用例库.md`。
2.  **标记覆盖率**: 如果本次补充了自动化脚本，在用例库中更新 "自动化覆盖" 状态为 ✅。

---
*Run with `/test`*
