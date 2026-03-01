---
description: API 文档入口（消费 review/manifest）：契约抽取、示例校验与文档落盘，支持大范围自动 Team
---

> 参考规则: @dual-database

# API 文档工作流 (API Docs Workflow)

`/jjk-api-docs` 是 `jjk-*` 体系里的 API 文档入口，负责把代码中的接口契约沉淀为可追溯、可交付的文档资产。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `/jjk-review`：提供本次变更范围、风险边界与优先关注接口。
2. `/jjk-test`：提供已验证的请求/响应证据，避免文档示例与真实行为偏差。
3. `deepsearch` / `analyze`：用于抽取路由、Schema、错误分支等契约信息。
4. `team`（OMX）：大规模接口并行梳理与文档汇总。
5. `/jjk-api-docs`：负责输入映射校验、契约矩阵生成、示例补全、文档落盘与一致性检查。

约束：

1. 禁止在 `/jjk-api-docs` 复制上游 skill 正文；只保留调用契约与本地增强。
2. 禁止在文档阶段“顺手改业务逻辑”；实现修复应回退 `/jjk-debug` 或 `/jjk-imp(-ws)`。
3. `/jjk-team-api-docs` 不再作为主入口，统一由 `/jjk-api-docs` 按规模自动升级 Team。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-api-docs`
2. Codex：`/prompts:jjk-api-docs`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 模板来源优先级（跨项目，强制）

`/jjk-api-docs` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_api_docs_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_api_docs_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。
`GLOBAL_TEMPLATE_MISSING` 属于全局预检失败标记，可与命令级 `FAIL_FAST` 标记并存。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 功能完成后需要补齐/更新 API 文档 | `/jjk-api-docs` ✅ |
| 只做代码审查与风险分级 | `/jjk-review` |
| 文档是否漏更检查 | `/jjk-doc-check` |
| 需要最终验收结论 | `/jjk-verify` |

---

## 输入前置（强制）

至少提供以下输入之一：

1. `review_report_<topic>.md`；
2. `pr_ready_manifest` / `pr_ready_manifest_ws`；
3. 可追溯到 `task_id`（`pr_id` 可选）的变更 diff + 目标模块/接口范围。

硬约束：

1. 若无法解析 `task_id`（`pr_id` 可选），`FAIL_FAST` 输出 `API_DOCS_INPUT_INCOMPLETE`。
2. 若无法锁定接口范围（模块/路由/版本），`FAIL_FAST` 输出 `API_DOCS_SCOPE_UNCLEAR`。
3. 若路由/Schema/错误处理契约来源缺失，`FAIL_FAST` 输出 `API_DOCS_SOURCE_MISSING`。
4. 执行结束仍未产出文档文件，`FAIL_FAST` 输出 `API_DOCS_OUTPUT_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. 变更范围与接口边界（版本、模块、公开/内部接口）。
2. 路由、请求模型、响应模型、异常分支、鉴权策略来源。
3. 现有文档基线（`docs/API文档/**`）与待更新段落。
4. 是否有可复用测试证据（示例请求、典型错误码、返回样例）。

### 0.5) 大范围文档自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 待文档化接口 `>= 15`；
2. 同时覆盖 `HTTP + WebSocket/SSE` 两类协议；
3. 涉及模块 `>= 3`；
4. 需要并行生成多版本或多语言文档。

执行策略：

1. **有 Team 能力时**：按模块或接口组并行梳理，Leader 汇总统一产物。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 1) 锁定文档范围与目标产物

1. 明确本轮是增量更新还是模块重建。
2. 生成“接口清单 -> 文档章节”映射，避免遗漏。

### 2) 抽取接口契约矩阵

每个接口至少包含：

1. `method + path + summary + auth`；
2. 请求参数（path/query/header/body）与字段约束；
3. 成功响应结构与关键字段说明；
4. 错误码（4xx/5xx）及触发条件。

### 3) 生成示例与异常说明

1. 至少提供 `cURL` 示例；按需补充 Python/TypeScript。
2. 示例参数优先复用测试数据或真实可执行样例。
3. 关键错误码需给“场景 -> 错误响应”映射。

### 4) 一致性校验（代码 vs 文档）

1. 校验路由定义与文档字段是否一致。
2. 校验响应模型与文档 JSON 示例是否一致。
3. 不确定项必须显式标记 `API_DOCS_EVIDENCE_GAP`，禁止臆造。

### 5) 落盘与回填

必须至少更新以下之一：

1. `docs/API文档/接口文档.md`
2. 模块化 API 文档（如 `docs/API文档/<模块>.md`）

并记录：

1. 本次覆盖接口数；
2. 未覆盖接口与原因；
3. 后续命令建议（`/jjk-doc-check`、`/jjk-verify`）。

---

## 输出模板（推荐）

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_api_docs_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_api_docs_templates.md`。

## 禁止项（强制）

1. 禁止未核对代码契约就生成“看起来正确”的接口文档。
2. 禁止遗漏错误码与鉴权信息。
3. 禁止文档阶段顺手修改路由行为。
4. 禁止无产物结束流程。

## 推荐链路

`/jjk-review -> /jjk-api-docs -> /jjk-doc-check -> /jjk-verify`

## 使用示例

```text
/jjk-api-docs
```

```text
/jjk-api-docs @docs/内部参考/迭代需求/review_report_<topic>.md
```

---
*使用 `/jjk-api-docs` 触发。目标是“代码契约与文档一致”，不是一次性拼接 Markdown。*
