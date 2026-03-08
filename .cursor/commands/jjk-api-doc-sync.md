---
description: API 文档同步门禁：命中路由/schema/DTO/OpenAPI/接口语义变更时，先列文档映射并阻断代码-文档漂移
---

# API 文档同步工作流 (API Doc Sync)

`/jjk-api-doc-sync` 是 `jjk-*` 体系里的文档前置门禁，负责把 API / Schema / Route / DTO / 接口语义变更对应的文档、测试资产与接口说明一次列清，避免“代码先改、文档后补”导致的漂移。

> **中文主导**：无论是思考过程（CoT）还是最终输出，**永远使用中文**。
>
> **原则来源**：`AGENTS.md` Layer1 第 `5` 条 + `.cursor/rules/doc_sync.mdc`。

## 输入前置（强制）

至少提供以下输入之一：

1. 变更文件范围（如 `app/api/**`、`app/schemas/**`、`web/src/lib/*api*`）；
2. 明确的接口 / 契约 / Schema 变更说明；
3. `implementation_plan` / `review_report` / diff 摘要中可追溯的 API 改动证据。

硬约束：

1. 无法判断 API 变更范围，`FAIL_FAST` 输出 `API_DOC_SYNC_SCOPE_UNCLEAR`。
2. 命中接口或契约变更却无法映射到必改文档，`FAIL_FAST` 输出 `API_DOC_SYNC_MAPPING_MISSING`。
3. 试图采用“代码先合、文档下轮补”的顺序，`FAIL_FAST` 输出 `API_DOC_SYNC_ORDER_FORBIDDEN`。
4. 接口文档、测试案例或测试用例库缺少同步项，`FAIL_FAST` 输出 `API_DOC_SYNC_DOC_SET_INCOMPLETE`。
5. 命中管理后台 Skill API、用户 Skill API、跨端契约字段变更但未补齐专项文档，`FAIL_FAST` 输出 `API_DOC_SYNC_SPECIAL_MAPPING_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. 变更是否命中 `app/api/**`、`app/schemas/**`、前端 API 调用层、测试资产或接口文档；
2. 本次变更属于新增接口、字段增删、语义变更、错误码变化、鉴权变化中的哪一类；
3. 是否命中 `.cursor/rules/doc_sync.mdc` 的专项映射（尤其是产品运行时 Skill 专项映射）。

### 1) 建立文档映射清单（强制）

至少输出三栏：

1. `Must Update`：本轮必须同步修改；
2. `Should Review`：建议复核但不一定改动；
3. `Not In Scope`：经判定本轮不涉及。

基础映射要求：

1. 命中 `app/api/**` 时，必须覆盖 `docs/API文档/接口文档.md`；
2. 命中模块级接口语义变化时，必须补对应产品需求/设计/测试文档；
3. 命中测试行为变化时，必须补 `docs/开发文档/测试管理/<模块>测试案例.md` 与 `docs/开发文档/测试管理/测试用例库.md`；
4. 命中 Skill 管理接口时，必须同时覆盖 `docs/API文档/接口文档.md`、`docs/产品文档/技能系统需求.md`、`docs/开发文档/测试管理/管理后台测试案例.md`。

### 2) 校验同步顺序（强制）

1. 文档必须先更新，或至少与代码在同一轮改动中完成；
2. 禁止把文档同步降级为“备注”“TODO”或“后续补”；
3. 若专项映射要求多份文档，禁止只更新其中一份充数。

### 3) 输出同步判定（强制）

必须输出：

1. 受影响接口 / 文件范围；
2. `Must Update / Should Review / Not In Scope` 清单；
3. `sync_status`（`READY` / `BLOCKED`）；
4. 阻断原因（如有）；
5. `next_step`（仅限 `/jjk-imp`、`/jjk-review`、`/jjk-verify` 之一或组合）。

放行规则：

1. `READY`：文档映射齐全，且不存在顺序问题；
2. `BLOCKED`：映射不全、专项文档缺失、测试资产未回填、接口说明未覆盖。

### 4) 与实现/审查/验收的分工（强制）

1. `/jjk-api-doc-sync` 只负责说清楚“本轮应该改哪些文档”；
2. 代码实现仍由 `/jjk-imp` 或 `/jjk-wtimp` 负责；
3. 文档一致性复核由 `/jjk-review` 与 `/jjk-verify` 继续收口；
4. 若命中结构性边界争议，应先回到 `/jjk-arch-gate`。

## 输出模板（推荐）

至少包含以下标题：

1. `## 变更范围`
2. `## Must Update`
3. `## Should Review`
4. `## Not In Scope`
5. `## Sync Status`
6. `## Next Step`

## 禁止项（强制）

1. 禁止只更新 `接口文档.md` 而漏掉测试资产或产品文档。
2. 禁止把文档同步理解为“审查阶段再说”。
3. 禁止在 `Must Update` 未清空时宣称可进入验收。
4. 禁止无映射依据地凭印象列文档清单。

## 推荐链路

`/jjk-arch-gate -> /jjk-api-doc-sync -> /jjk-imp`

`/jjk-review -> /jjk-api-doc-sync -> /jjk-verify`

## 使用示例

```text
/jjk-api-doc-sync
```

```text
/jjk-api-doc-sync @app/api/v1/endpoints/user_skill_api.py
```

---
*使用 `/jjk-api-doc-sync` 触发。目标是“先把文档同步清单讲清楚再动手”，不是“靠记忆补文档”。*
