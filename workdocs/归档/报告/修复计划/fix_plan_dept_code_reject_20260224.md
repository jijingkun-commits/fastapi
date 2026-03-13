# FIX-20260224-01: 管理员用户缺少 dept_code 导致问数查询被拒绝

> 文档状态：已完成（修订版 v2）
> 创建时间：2026-02-24
> 修订时间：2026-02-24
> 严重程度：P1（核心功能不可用）

---

## 1. 问题摘要

### 问题描述

用户查询"2025年6月30日贷款余额前10名的客户"时，系统返回：

```
查询被拒绝：用户 1 缺少 dept_code，命中默认部门隔离策略，拒绝查询
```

管理员用户（ID=1）无法执行任何问数查询。

### 根本原因

问题由三层缺陷叠加导致：

**缺陷 1 — 种子数据不完整**：`app/db/init_db.py` 创建 admin 用户时未设置 `data_role`、`org_code`，导致 `data_role` 兜底为 `"staff"`、`dept_code = NULL`。

**缺陷 2 — head_president 权限配置缺失**：`head_president` 角色从未被配置过表级权限（`t_data_permission_table`），行级规则（026 脚本）使用 `user.dept_code` 作为过滤源，而总行行长无 `dept_code`，规则在运行时解析为 NULL 被跳过。

**缺陷 3 — 叠加效应**：admin 用户的 `data_role` 被兜底为 `staff`（`_resolve_user_data_role` 显式排除 `role="admin"` 作为降级来源），而 `staff` 角色也无显式行级规则，导致 `validate_query_context` 三个放行条件全部不满足。

调用链路：
```
data_graph.py:2615  evaluate_sql_policy(sql, user_id=1)
  -> sql_policy_decision.py:122  check_and_rewrite_sql(safe_sql, 1)
    -> sql_rewriter.py:79  service.validate_query_context(user_context)
      -> permission_service.py:248  ctx.has_dept_code() -> False
      -> permission_service.py:251  has_explicit_row_scope -> False
      -> permission_service.py:259  返回拒绝
```

### 影响范围

- 所有 `data_role` 未正确配置且缺少 `dept_code` 的用户无法执行问数查询
- 影响 data_graph 和 data_query_tools 两条查询路径
- 不影响非问数功能（聊天、待办等）

---

## 2. 修复方案（修订版 v2）

> **基线约束**：`sys_role` 不参与问数放行判定（问数引擎设计.md:332、问数助手需求.md:110、双角色需求.md:64）。
> 本方案严格通过 `data_role` + 权限配置体系解决，不引入 `sys_role` 直通。

### 方案概述

1. **种子数据修复**：admin 用户写入 `data_role="head_president"`、`org_code="0000"`
2. **权限配置补齐**：为 `head_president` 配置表级允许 + `user.org_code` 行级规则
3. **存量数据修补**：一次性 SQL 修补已有环境的 admin 用户和 head_president 权限

放行路径：`head_president` 有显式行级规则 -> `has_explicit_row_scope = True` -> `validate_query_context` 放行。

### 涉及文件

| 文件 | 变更类型 |
|------|---------|
| `app/db/init_db.py` | 种子数据补全 |
| `scripts/init_tables_ci.py` | CI 种子数据补全 |
| `install/scripts/init_postgres.sql/027_seed_head_president_permissions.sql` | 新增：权限配置 + 存量修补 |
| `tests/unit/test_permission_service.py` | 新增测试用例 |

### 修改点清单

#### [app/db/init_db.py](../../../app/db/init_db.py)

- [x] 补全 admin 用户的 `data_role="head_president"`、`org_code="0000"`、`org_name="总行"`

#### [scripts/init_tables_ci.py](../../../scripts/init_tables_ci.py)

- [x] 与 `init_db.py` 保持一致

#### [install/scripts/init_postgres.sql/027_seed_head_president_permissions.sql](../../../install/scripts/init_postgres.sql/027_seed_head_president_permissions.sql)

- [x] 表级权限：`head_president` 允许访问 `fdmdata.*` 和 `sdmdata.*`
- [x] 行级规则：`fdmdata.*` 通配规则改用 `user.org_code`（替代 `user.dept_code`）
- [x] 行级规则：精确表规则的 `filter_source` 改用 `user.org_code`
- [x] 存量 admin 用户数据修补（`data_role`、`org_code`、`org_name`）

#### 未修改的文件（基线保持）

- `app/services/permission_service.py` — `validate_query_context` 逻辑不变，不引入 `sys_role` 豁免
- `app/ai/utils/permission_context.py` — 不新增 `is_sys_admin()` 方法
- `_resolve_user_data_role` — 保持 `admin` 排除规则不变

### 执行后缓存生效

`PermissionService` 有 5 分钟缓存（`CACHE_TTL = 300`），执行 027 脚本后需重启服务或调用 `invalidate_cache()` 确保即时生效。

---

## 3. 风险评估

### 修复可能引入的新问题

1. `head_president` 的 `org_code` 过滤范围取决于数据表中 `org_code="0000"` 的覆盖情况；若业务数据不含总行级汇总记录，查询可能返回空结果
2. 026 脚本为 `head_president` 创建的 `user.dept_code` 行级规则被 027 覆盖为 `user.org_code`，需确认不影响其他 `head_president` 用户

### 需要特别注意的边界情况

1. `data_role` 缺失但 `dept_code` 非空的账号不受本次修补影响（条件为 `data_role IS NULL OR data_role = 'staff'`）
2. 非 admin 的 `head_president` 用户如果也没有 `org_code`，行级规则会解析为 NULL 被跳过，仍会被拒绝

### 回滚方案

1. 回退 027 脚本：删除 `head_president` 的表级权限，恢复行级规则为 `user.dept_code`
2. 回退种子数据：`init_db.py` 和 `init_tables_ci.py` 移除新增字段

---

## 4. 验证计划

### 单元测试

- [x] `test_validate_query_context_head_president_with_org_code_rules`: head_president 有显式 org_code 规则时放行
- [x] `test_validate_query_context_staff_no_dept_code_still_blocked`: staff 无 dept_code 仍被拒绝
- [x] `test_get_row_filters_head_president_uses_explicit_org_code_rule`: head_president 使用 org_code 规则，不注入 dept_code

### 集成测试

- [x] 执行 027 脚本后，admin 用户查询"2025年6月30日贷款余额前10名的客户"不再被拒绝（自动化回归：`tests/unit/test_sql_rewriter.py::TestRewriteSqlWithPermissions::test_head_president_loan_top10_query_should_be_allowed`）
- [x] staff 用户（无 dept_code）执行同一查询仍被拒绝（自动化回归：`tests/unit/test_sql_rewriter.py::TestRewriteSqlWithPermissions::test_staff_without_dept_loan_top10_query_should_be_rejected`）
- [x] 有 dept_code 的 staff 用户查询正常注入 dept_code 过滤（见 `fix_plan_cte_permission_reject_20260226.md` P1 证据链）

### 手动验证

1. 执行 `027_seed_head_president_permissions.sql`
2. 重启后端服务（或清缓存）
3. admin 账号登录，问数对话中查询，确认返回正常结果
4. 检查日志确认 `has_explicit_row_scope` 为 True

---

## 5. 预防措施

- [x] 种子用户包含完整权限字段（`data_role`、`org_code`）
- [x] 新增 `data_role` 时需同步配置表级 + 行级权限规则
- [x] 在 `validate_query_context` 拒绝日志中补充 `data_role` 信息，便于排查

---

## 6. 修订记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1 | 2026-02-24 | 初版：通过 `is_sys_admin()` 豁免部门隔离 |
| v2 | 2026-02-24 | 修订：回退 `sys_role` 豁免，改为 `data_role` 配置驱动（符合双角色基线） |

---

## 关联文档

- [x] 架构文档: `docs/开发文档/架构设计/AI模块设计.md`（权限子系统）
- [x] 需求基线: `workdocs/归档/正文/需求/askdata_dual_role_permission_requirements.md`
- [x] 产品需求: `docs/产品文档/问数助手需求.md`
- [x] 数据库设计: `docs/开发文档/架构设计/数据库设计.md`（t_user 表）
