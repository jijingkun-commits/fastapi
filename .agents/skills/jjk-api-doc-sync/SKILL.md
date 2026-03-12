---
name: jjk-api-doc-sync
description: "Use when you need `jjk-api-doc-sync` in this repository. Source intent: API 文档同步门禁：接口变化时始终自动同步 API 文档；产品/设计文档仅按发布标志扩展同步"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-api-doc-sync.md -->

# API 文档同步工作流（API Doc Sync）

`$jjk-api-doc-sync` 负责在接口契约变化时，先把**API 文档同步清单**说清楚。


## 核心规则

1. 命中 API / Route / DTO / Schema / OpenAPI 变化时，API 文档**始终自动同步**；
2. 正式产品/需求文档只在 `publish_product_doc=true` 时同步；
3. 正式设计/架构文档只在 `publish_design_doc=true` 时同步；
4. 内部 `requirements/design/plan/uat_cases` 不受本命令控制，它们本来就必须存在。

## 输入前置（强制）

至少提供以下输入之一：

1. 变更文件范围；
2. 明确的 API / Schema 变更说明；
3. `design.md` / `implementation_plan.md` 中的 API 影响说明。

失败时：

1. 无法判断是否命中 API 变化：`API_DOC_SYNC_SCOPE_UNCLEAR`
2. 命中 API 变化却无法映射 API 文档：`API_DOC_SYNC_MAPPING_MISSING`
3. 试图把 API 文档同步延后：`API_DOC_SYNC_ORDER_FORBIDDEN`

## 执行流程（强制顺序）

### 0) 上下文检查

至少检查：

1. 是否命中 `app/api/**`、`app/schemas/**`、前端 API 调用层；
2. 变更属于新增接口、字段变更、语义变更、错误码变化还是鉴权变化；
3. 是否要求发布正式产品/设计文档。

### 1) 建立同步清单

至少输出三栏：

1. `Must Update`
2. `Should Review`
3. `Not In Scope`

基础映射规则：

1. 命中 API 变化时，`docs/API文档/接口文档.md` 必须进入 `Must Update`；
2. 命中测试行为变化时，测试资产进入 `Must Update` 或 `Should Review`；
3. 仅当 `publish_product_doc=true` 时，正式产品/需求文档进入 `Must Update`；
4. 仅当 `publish_design_doc=true` 时，正式设计/架构文档进入 `Must Update`。

### 2) 输出同步判定

必须输出：

1. 受影响接口 / 文件范围；
2. `Must Update / Should Review / Not In Scope` 清单；
3. `api_doc_required=true|false`；
4. `publish_product_doc` / `publish_design_doc` 状态；
5. `sync_status=READY|BLOCKED|NOT_APPLICABLE`。

## 禁止项（强制）

1. 禁止把 API 文档自动同步降级为“后续再补”；
2. 禁止因为没带 `--doc` 就跳过 API 文档；
3. 禁止把正式产品/设计文档默认列为必改；
4. 禁止无映射依据地凭印象列文档清单。

## 推荐链路

`$jjk-design -> $jjk-api-doc-sync -> $jjk-plan`

`$jjk-imp -> $jjk-api-doc-sync -> $jjk-verify`

## 使用示例

```text
$jjk-api-doc-sync
```

---
*使用 `$jjk-api-doc-sync` 触发。目标是“API 文档自动同步、正式文档按发布标志扩展”，不是“一刀切全改”。*
