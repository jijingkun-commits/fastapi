# 修复计划：问数查询权限、CTE 误判、参数占位符与流式字段缺失四问题

> 创建时间: 2026-02-26
> 严重程度: **高**

## 问题总览

| 编号 | 问题 | 严重程度 | 状态 | 现象 |
|------|------|---------|------|------|
| P1 | 第一次查询权限范围验证 | 需确认 | 已确认无泄露 | staff 用户查询贷款余额前10名，行级过滤已生效 |
| P2 | CTE 名称被误判为未授权表 | 高 | 已修复 | 查询"各机构的贷款余额分布"报错 `public.params` 无权访问 |
| P3 | LLM 生成参数占位符导致执行失败 | 高 | 已修复 | P2 修复后暴露：SQL 含 `$1::date` 导致 `UndefinedParameter` |
| P4 | SSE 流式 result 事件缺少 total_rows 导致前端崩溃 | 高 | 已修复 | 前端 `totalRows.toLocaleString()` 报 TypeError |

---

## P1: 第一次查询权限范围验证

### 问题描述

用户（id=2, username=jjk, data_role=staff, org_code=00808, dept_code=00808）查询"查询2025年6月30日贷款余额前10名的客户"，成功返回了10条记录。需要确认数据范围是否正确受限。

### 诊断结论：行级过滤已生效，无数据泄露

**证据链：**

1. SQL 来源为 `metric`（指标模板匹配），非 LLM 生成
2. 查询表为 `fdmdata.f_mid_loan_k_tb`（有 `dept_cd` 字段）
3. 行级过滤规则 `fdmdata.*` 配置了 `dept_cd = user.dept_code`
4. 最终执行 SQL 已注入 `WHERE (f_mid_loan_k_tb.dept_cd = '00808')`
5. 数据验证：
   - `f_mid_loan_k_tb` 全量（data_dt=20250630）：**1,579,387 行**
   - 过滤 `dept_cd = '00808'` 后：**104,949 行**（仅 6.6%）
6. `00808` 对应组织树中 level 5 的"金融市场部"，非全行数据

**结论：staff 用户只看到了金融市场部范围内的数据，权限过滤正确生效。**

### 潜在风险（非本次问题，记录备查）

`f_mid_loan_tb`（注意：不是 `f_mid_loan_k_tb`）没有 `dept_cd` 字段。如果 LLM 生成的 SQL 使用了 `f_mid_loan_tb`，行级过滤会走兼容字段映射 `dept_cd → org_cd`（`COMPATIBLE_FILTER_COLUMNS` 配置）。但 `org_cd` 与 `dept_cd` 的语义可能不完全一致（机构码 vs 部门码），需要业务确认映射是否准确。当前 `f_mid_loan_tb` 为空表，暂无实际影响。

---

## P2: CTE 名称被误判为未授权表

### 问题描述

用户查询"查询2025年6月30日各机构的贷款余额分布"时，前端直接报错：
`查询被拒绝：数据角色 staff 无权访问表 public.params`

### 根本原因

`sql_rewriter.py:_extract_tables_with_schema()` 使用 `sqlglot.find_all(exp.Table)` 提取表名时，**未排除 CTE（WITH 子句）定义的临时表名**。

LLM 生成的 SQL（来源：应用日志 2026-02-26 14:20:08）：
```sql
WITH params AS (
    SELECT DATE '2025-06-30' AS data_dt
),
cust_bal AS (
    SELECT ... FROM fdmdata.f_mid_loan_tb ...
),
ranked AS (
    SELECT ... FROM cust_bal ...
)
SELECT ... FROM ranked ...
```

sqlglot 解析提取到的"表"（日志原文）：
```
{'params', 'ranked', 'fdmdata.f_mid_loan_tb', 'cust_bal'}
```

`_extract_tables_with_schema()` 对无 schema 的表名默认填 `"public"`（L134），因此 `params` → `public.params`。

权限检查链路：
```
_check_table_permissions() 遍历所有表
  → permission_service.check_table_access(ctx, "public", "params")
    → _evaluate_table_access(): denied_tables 未命中 → allowed_tables 未命中
    → default_deny: "数据角色 staff 无权访问表 public.params"
```

staff 角色白名单只有 `fdmdata.*` 和 `sdmdata.*`，`public.params` 不在白名单中，第一个遇到的未授权表就触发拒绝返回。

### 影响范围

- 所有含 CTE 的问数查询都会被误拒（LLM 经常生成 WITH 子句）
- 同一问题存在于三个函数：
  - `sql_rewriter.py:_extract_tables_with_schema()` — 权限检查（直接导致拒绝）
  - `sql_rewriter.py:_extract_table_qualifiers()` — 行级过滤注入（可能误注入到 CTE 引用）
  - `sql_parser.py:_extract_tables_sqlglot()` — **影响面广**：被 `sql_safety.py`（敏感表检查、schema 白名单）、`permission_service.py`（权限命中轨迹）、`sql_evaluator.py`（SQL 质量评估）、`data_graph.py`（可用性检查）、`data_access_control.py`（旧版访问控制）、`metric_service.py`（指标表提取）等多处复用，CTE 名称混入会导致误报敏感表、误判 schema 越权等连锁问题

### 严重程度

**高** — 直接阻断用户正常查询，且 LLM 生成 CTE 是常见模式。

---

## 修复方案

### 方案概述

在 sqlglot 提取表名后，收集 CTE 定义的名称集合，**仅排除"无显式 schema 且命中 CTE 名"的引用**。带 schema 前缀的表引用（如 `fdmdata.params`）即使与 CTE 同名也保留，避免误伤真实表的权限检查。三个函数同步修复。

### 排除条件（关键约束）

```
排除当且仅当：table.db 为空（即 sqlglot 未解析到 schema）且 table.name 命中 CTE 名称集合
保留当：table.db 非空（如 fdmdata.params），即使 table.name 命中 CTE 名称
```

### 作用域说明

当前实现采用**全局收集 CTE 名称**（顶层 WITH 子句），不区分嵌套子查询中的 CTE 作用域。这在绝大多数场景下是正确的（LLM 生成的 SQL 极少出现嵌套 CTE 与外层同名的情况）。后续如遇到嵌套 CTE 作用域冲突，可按 sqlglot AST 层级做精细化排除，当前先加防回归用例覆盖。

### 涉及文件

#### [app/ai/utils/sql_rewriter.py](file:///Users/jijingkun/bojxAI/fastapi/app/ai/utils/sql_rewriter.py)
- [x] `_extract_tables_with_schema()` (L119-142): 收集 CTE 名称，仅排除无 schema 的 CTE 引用
- [x] `_extract_table_qualifiers()` (L146-177): 同步排除无 schema 的 CTE 引用

#### [app/ai/utils/sql_parser.py](file:///Users/jijingkun/bojxAI/fastapi/app/ai/utils/sql_parser.py)
- [x] `_extract_tables_sqlglot()` (L54-84): 同步排除无 schema 的 CTE 引用（影响面广：敏感表检查、schema 白名单、权限轨迹、SQL 评估等）

### 修改点详情

**核心修复 — `_extract_tables_with_schema()`:**

```python
def _extract_tables_with_schema(sql: str) -> List[Tuple[str, str]]:
    """提取 SQL 中的真实表名（含 Schema），排除 CTE 定义名称。

    排除条件：仅排除无显式 schema 且命中 CTE 名的引用。
    带 schema 前缀的同名表（如 fdmdata.params）保留。
    """
    tables = []
    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")

        # 收集 CTE 定义的名称
        cte_names = set()
        for cte in parsed.find_all(exp.CTE):
            if cte.alias:
                cte_names.add(cte.alias.lower())

        for table in parsed.find_all(exp.Table):
            table_name = table.name
            if not table_name:
                continue
            has_explicit_schema = bool(table.db)
            # 仅排除无显式 schema 且命中 CTE 名的引用
            if not has_explicit_schema and table_name.lower() in cte_names:
                continue
            schema = table.db or "public"
            tables.append((schema.lower(), table_name.lower()))

    except ParseError:
        tables = _extract_tables_regex(sql)

    return list(set(tables))
```

**同步修复 — `_extract_table_qualifiers()`:**

```python
# 在 parsed = sqlglot.parse_one(...) 之后，for table in ... 之前，加入：
cte_names = set()
for cte in parsed.find_all(exp.CTE):
    if cte.alias:
        cte_names.add(cte.alias.lower())

# 在 for table in parsed.find_all(exp.Table): 循环内，加入过滤：
has_explicit_schema = bool(table.db)
if not has_explicit_schema and table_name in cte_names:
    continue
```

**同步修复 — `_extract_tables_sqlglot()`:**

```python
# 在每个 statement 内，先收集 CTE 名称：
cte_names = set()
for cte in statement.find_all(exp.CTE):
    if cte.alias:
        cte_names.add(cte.alias.lower())

# 在 for table in statement.find_all(exp.Table): 循环内，加入过滤：
has_explicit_schema = bool(table.db)
bare_name = table.name.lower() if table.name else ""
if not has_explicit_schema and bare_name in cte_names:
    continue
```

---

## 风险评估

| 风险 | 说明 | 缓解措施 |
|------|------|---------|
| CTE 名称与真实表名重名（带 schema） | 如 `fdmdata.params` 是真实表，CTE 也叫 `params` | 排除条件仅针对无 schema 引用，带 schema 的保留，不会误伤 |
| 全局收集 CTE 名在嵌套查询中过度排除 | 子查询内定义的 CTE 名被全局收集后，可能排除外层同名真实表引用 | 当前 LLM 生成的 SQL 极少出现此场景；已加防回归用例，后续按需按 AST 层级优化 |
| 子查询别名误排除 | `find_all(exp.CTE)` 只匹配 WITH 子句，不影响子查询别名 | 无需额外处理 |
| 正则降级路径未修复 | `_extract_tables_regex()` 也可能提取 CTE 名称 | 可后续优化，当前正则路径仅在 sqlglot 解析失败时触发 |

### 回滚方案

修改仅涉及表名提取逻辑，回滚只需 `git revert` 对应 commit。

---

## 验证计划

### 单元测试

新增测试用例覆盖 CTE 场景：

```python
# tests/unit/test_sql_rewriter.py
def test_extract_tables_excludes_cte_names():
    """CTE 名称不应被当作真实表。"""
    sql = """
    WITH params AS (SELECT DATE '2025-06-30' AS dt),
         cust_bal AS (SELECT * FROM fdmdata.f_mid_loan_tb)
    SELECT * FROM cust_bal
    """
    tables = _extract_tables_with_schema(sql)
    assert ("fdmdata", "f_mid_loan_tb") in tables
    assert ("public", "params") not in tables
    assert ("public", "cust_bal") not in tables

def test_extract_tables_no_cte():
    """无 CTE 的普通查询应正常提取。"""
    sql = "SELECT * FROM fdmdata.f_mid_loan_tb WHERE data_dt = '20250630'"
    tables = _extract_tables_with_schema(sql)
    assert tables == [("fdmdata", "f_mid_loan_tb")]

def test_extract_tables_nested_cte():
    """嵌套 CTE 引用不应被当作真实表。"""
    sql = """
    WITH a AS (SELECT 1), b AS (SELECT * FROM a)
    SELECT * FROM fdmdata.f_mid_dep_tb, b
    """
    tables = _extract_tables_with_schema(sql)
    assert ("fdmdata", "f_mid_dep_tb") in tables
    assert ("public", "a") not in tables
    assert ("public", "b") not in tables

def test_extract_tables_cte_name_same_as_real_table_with_schema():
    """带 schema 的同名表不应被 CTE 排除误伤。"""
    sql = """
    WITH params AS (SELECT 1 AS x)
    SELECT * FROM fdmdata.params, params
    """
    tables = _extract_tables_with_schema(sql)
    # fdmdata.params 是真实表，应保留
    assert ("fdmdata", "params") in tables
    # 无 schema 的 params 是 CTE 引用，应排除
    assert ("public", "params") not in tables
```

```python
# tests/unit/test_sql_parser.py — 补充 CTE 排除断言
def test_cte_with_clause_excludes_cte_names(self):
    """CTE 名称不应出现在提取结果中（防回归）。"""
    sql = """
    WITH active_users AS (
        SELECT id FROM users WHERE status = 'active'
    )
    SELECT * FROM active_users JOIN orders ON active_users.id = orders.user_id
    """
    tables = extract_tables_from_sql(sql)
    self.assertIn("users", tables)
    self.assertIn("orders", tables)
    # CTE 名称不应被当作真实表
    self.assertNotIn("active_users", tables)

def test_cte_with_schema_table_same_name(self):
    """带 schema 的同名表不应被 CTE 排除误伤。"""
    sql = """
    WITH params AS (SELECT 1)
    SELECT * FROM fdmdata.params
    """
    tables = extract_tables_from_sql(sql)
    self.assertIn("fdmdata.params", tables)
    self.assertNotIn("params", tables)

def test_nested_cte_global_scope(self):
    """全局 CTE 收集的防回归用例：嵌套引用场景。"""
    sql = """
    WITH a AS (SELECT 1), b AS (SELECT * FROM a)
    SELECT * FROM b JOIN fdmdata.f_mid_dep_tb t ON 1=1
    """
    tables = extract_tables_from_sql(sql)
    self.assertIn("fdmdata.f_mid_dep_tb", tables)
    self.assertNotIn("a", tables)
    self.assertNotIn("b", tables)
```

### 集成验证

- 重新执行"查询2025年6月30日各机构的贷款余额分布"，确认不再被拒绝
- 执行"查询2025年6月30日贷款余额前10名的客户"，确认仍然正常
- 确认行级过滤只注入到真实表（不注入到 CTE 引用）

### 手动验证

1. 构造多种 CTE 结构的 SQL，验证表提取结果
2. 确认权限检查只针对真实表
3. 确认前端不再显示 `public.params` 相关错误

---

## 预防措施

- 补充 CTE 场景的单元测试（上述测试用例）
- 在 `_extract_tables_with_schema` 函数 docstring 中明确标注"排除 CTE 定义名称"
- 考虑统一 `sql_rewriter.py` 和 `sql_parser.py` 的表提取逻辑为单一函数，避免两处代码各自维护

---

## 实施建议

- **优先级**: P0（直接阻断用户查询）
- **实施顺序**: `sql_rewriter.py` → `sql_parser.py` → 单元测试 → 集成验证
- **预计工作量**: 小（核心改动 < 30 行）
- **无需分阶段实施**

---

## P3: LLM 生成参数占位符导致 SQL 执行失败

### 问题描述

P2 修复后，CTE 权限检查不再误拒，SQL 进入执行阶段。但 LLM 生成的 SQL 包含 PostgreSQL 参数占位符 `$1::date`，系统直接执行（非参数化绑定），导致：
```
psycopg.errors.UndefinedParameter: there is no parameter $1
```

### 根本原因

**双因素叠加：**

1. `SQL_GENERATION_PROMPT`（`app/ai/prompts/data_prompts.py:112`）第 5 条规则：
   > "如果涉及时间范围，使用参数化查询或 CURRENT_DATE"

   这条规则引导 LLM 生成 `$1::date` 占位符，但系统通过 `vanna.run_sql()` 直接执行 SQL，不支持参数绑定。

2. `sql_safety.py` 的安全检查不包含对 `$1`、`$2` 等参数占位符的检测，也没有在 `_extract_sql_from_response()` 中清理占位符。

### LLM 生成的 SQL（日志原文）

```sql
SELECT
    t.data_dt AS "业务日期",
    t.org_cd AS "机构编码",
    t.level7_val AS "机构名称",
    SUM(COALESCE(t.prin_bal, 0)) AS "贷款余额"
FROM fdmdata.f_mid_loan_tb AS t
WHERE (t.org_cd = '00808') AND t.data_dt = $1::date  -- 参数：业务日期
GROUP BY t.data_dt, t.org_cd, t.level7_val
ORDER BY "贷款余额" DESC, t.org_cd LIMIT 1000
```

### 影响范围

- 所有涉及时间参数的问数查询都可能触发（LLM 遵循 prompt 指令生成占位符）
- 第一次执行失败后会触发重试（第 2 次 sql_generate），但重试不一定能修正

### 修复方案

#### 方案 A：修正 Prompt（治本）

修改 `SQL_GENERATION_PROMPT` 第 5 条规则，禁止参数占位符：

#### [app/ai/prompts/data_prompts.py](file:///Users/jijingkun/bojxAI/fastapi/app/ai/prompts/data_prompts.py)
- [x] 第 112 行：将 `"如果涉及时间范围，使用参数化查询或 CURRENT_DATE"` 改为 `"时间条件必须使用字面值（如 '2025-06-30'）或 CURRENT_DATE，禁止使用 $1、$2 等参数占位符"`

#### 方案 B：安全检查兜底（防御性）

在 SQL 提取或安全检查阶段检测并清理参数占位符：

#### [app/ai/utils/sql_safety.py](file:///Users/jijingkun/bojxAI/fastapi/app/ai/utils/sql_safety.py)
- [x] 在 `check_sql_safety()` 中新增检查：检测 `$\d+` 模式，拒绝含参数占位符的 SQL 并返回明确错误信息，触发 LLM 重新生成

#### 建议

两个方案同时实施：Prompt 修正减少 LLM 生成占位符的概率，安全检查兜底确保漏网的占位符不会到达执行阶段。

---

## P4: SSE 流式 result 事件缺少 total_rows 导致前端崩溃

### 问题描述

P2、P3 修复后，SQL 查询成功执行并返回结果。但前端在渲染流式 result 事件时崩溃：
```
Runtime TypeError: Cannot read properties of undefined (reading 'toLocaleString')
```
错误发生在 `sql-result-table.tsx:105`。

### 根本原因

**后端 SSE 流式 result 事件与持久化消息的字段不一致。**

后端有两处构建 `sql_result` 数据：

1. **持久化消息**（`_build_sql_result_additional_kwargs`，`data_graph.py:3611-3627`）：
   ```python
   data={
       "sql": sql,
       "display_sql": display_sql,
       "columns": columns,
       "column_display_names": column_display_names,
       "rows": result_data[:100],
       "total_rows": len(result_data),  # ✅ 有
       "sql_source": sql_source,
       "iterations": iterations,
       "chart": chart_payload,
       "permission_scope_applied": permission_rewritten,
       "permission_scope_summary": permission_scope_summary,
   }
   ```

2. **SSE 流式 result 事件**（`stream_result_payload`，`data_graph.py:3797-3809`）：
   ```python
   data={
       "rows": result_data[:20],
       "columns": columns,
       "column_display_names": column_display_names,
       "display_sql": display_sql,
       "chart": chart_payload,
       "permission_scope_applied": permission_rewritten,
       "permission_scope_summary": permission_scope_summary,
       # ❌ 缺少 "total_rows" 和 "sql"
   }
   ```

前端处理链路：
```
SSE result 事件 → onResult(data) → storeStructuredResultToMessage(aiId, data)
  → setMessages: additional_kwargs = { data_type: "sql_result", data: data.data }
  → ai.tsx: sqlResultData = responseData (即 data.data)
  → sqlResultData.total_rows → undefined
  → SqlResultTable: totalRows={undefined as number}
  → totalRows.toLocaleString() → TypeError
```

**关键时序问题**：SSE 流式 result 事件先于持久化消息到达前端。前端在收到流式事件后立即渲染 `SqlResultTable`，此时 `total_rows` 为 `undefined`。即使后续持久化消息包含 `total_rows`，但组件已经崩溃。

### 影响范围

- 所有问数查询成功返回结果时，前端都会崩溃
- 用户看到白屏或错误提示，无法查看查询结果
- 刷新页面后加载历史消息（走持久化数据）可以正常显示

### 严重程度

**高** — 查询成功但前端无法展示结果，用户体验完全中断。

### 修复方案

#### 方案概述

双端修复：后端补齐流式事件缺失字段（治本），前端增加 undefined 防御（防御性）。

#### 涉及文件

##### [app/ai/workflow/data_graph.py](file:///Users/jijingkun/bojxAI/fastapi/app/ai/workflow/data_graph.py)
- [x] L3799: `stream_result_payload` 的 `data` 字典中补充 `"total_rows": len(result_data)` 和 `"sql": sql`

##### [web/src/components/chat/messages/sql-result-table.tsx](file:///Users/jijingkun/bojxAI/fastapi/web/src/components/chat/messages/sql-result-table.tsx)
- [x] L17: `totalRows: number` 改为 `totalRows?: number`（可选属性）
- [x] L105: `totalRows.toLocaleString()` 改为 `(totalRows ?? 0).toLocaleString()`
- [x] L106: `rows.length < totalRows` 改为 `totalRows != null && rows.length < totalRows`

##### [web/src/components/chat/messages/ai.tsx](file:///Users/jijingkun/bojxAI/fastapi/web/src/components/chat/messages/ai.tsx)
- [x] L223: `totalRows={sqlResultData.total_rows as number}` 改为 `totalRows={sqlResultData.total_rows}`（去掉强制类型断言，配合 props 改为可选）

#### 修改点详情

**后端 — `data_graph.py` L3799:**

```python
stream_result_payload = build_streaming_result_payload_from_fields(
    data_type="sql_result",
    data={
        "rows": result_data[:20],
        "columns": columns,
        "column_display_names": column_display_names,
        "display_sql": display_sql,
        "total_rows": len(result_data),   # 新增
        "sql": sql,                        # 新增
        "chart": chart_payload,
        "permission_scope_applied": permission_rewritten,
        "permission_scope_summary": permission_scope_summary,
    },
    message=interpretation,
)
```

**前端 — `sql-result-table.tsx`:**

```typescript
// L17: props 改为可选
interface SqlResultTableProps {
  columns: string[];
  columnDisplayNames?: string[];
  rows: Record<string, any>[];
  totalRows?: number;  // 改为可选
  sql?: string;
  permissionScopeApplied?: boolean;
  permissionScopeText?: string;
}

// L105-106: 增加 undefined 防御
<span>
  共 {(totalRows ?? 0).toLocaleString()} 条
  {totalRows != null && rows.length < totalRows ? `（已展示前 ${rows.length} 条）` : ""}
</span>
```

**前端 — `ai.tsx` L223:**

```typescript
totalRows={sqlResultData.total_rows}
```

### 风险评估

| 风险 | 说明 | 缓解措施 |
|------|------|---------|
| 流式事件数据量增大 | 新增 `total_rows`（整数）和 `sql`（字符串），增量极小 | 无需额外处理 |
| `totalRows` 为 0 时显示"共 0 条" | 空结果场景正常行为 | 已有空结果提示逻辑（L36-50），不会走到底栏 |
| 历史消息兼容性 | 旧消息已有 `total_rows`，不受影响 | 前端 `??0` 兜底确保旧数据也安全 |

### 验证计划

#### 手动验证

1. 执行问数查询，确认前端不再崩溃，表格正常渲染
2. 确认底栏显示正确的总行数和"已展示前 N 条"提示
3. 确认 SQL 折叠按钮正常工作
4. 刷新页面，确认历史消息加载后表格仍正常

#### 回归验证

- 确认空结果查询仍显示空结果提示
- 确认图表渲染不受影响

---

## 关联文档

- 需求文档: [问数助手需求.md](file:///Users/jijingkun/bojxAI/fastapi/docs/产品文档/问数助手需求.md)
- 架构文档: [AI模块设计.md](file:///Users/jijingkun/bojxAI/fastapi/docs/开发文档/架构设计/AI模块设计.md)
- 测试案例: [问数引擎测试案例.md](file:///Users/jijingkun/bojxAI/fastapi/docs/开发文档/测试管理/问数引擎测试案例.md)
- 权限设计: [问数助手需求.md](file:///Users/jijingkun/bojxAI/fastapi/docs/产品文档/问数助手需求.md)
