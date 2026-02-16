# 问数双角色权限实施方案（2026-02）

> 文档状态：实施基线（`/plan parallel`）
> 更新时间：2026-02-15
> 对应需求：`docs/内部参考/迭代需求/askdata_dual_role_permission_requirements.md`

---

## 1. 方案概览

本方案按“先契约、再引擎、后治理”分阶段实施，确保在“所有用户当前均为 admin”的现实前提下平滑切换到银行权限模型。

实施阶段：

1. **Phase 0（G0 冻结）**：冻结双角色契约、默认策略与优先级规则。
2. **Phase 1（模型与迁移）**：引入 `data_role`，完成历史用户回填与兼容。
3. **Phase 2（引擎收敛）**：移除 admin 默认放行，切换为 `data_role + dept_code`。
4. **Phase 3（治理能力）**：权限配置 API、SQL 试跑、审计日志。
5. **Phase 4（门禁与发布）**：回归测试、灰度发布、回滚预案。

---

## 2. 架构影响与约束

### 2.1 模块边界

1. **身份语义层**：`app/models/user.py`、`app/schemas/user.py` 只负责身份字段表达。
2. **策略解析层**：`app/services/permission_service.py` 统一解析权限规则与缓存。
3. **执行重写层**：`app/ai/utils/sql_rewriter.py` 负责 SQL 重写与注入。
4. **治理接口层**：`app/api/v1/endpoints/access_admin_api.py` 负责权限配置管理。

禁止跨层散落策略判断（例如在 workflow 节点临时拼权限条件）。

### 2.2 状态契约

1. 用户身份 canonical 字段：
   - `sys_role`（系统权限，当前保持 admin）
   - `data_role`（问数权限主体）
2. 数据角色枚举冻结：`head_president`、`department_gm`、`department_vgm`、`staff`。
3. 行级默认规则：`dept_code = user.dept_code`。
4. 优先级冻结：`deny > allow > role_template > default`。

### 2.3 路由闭环

权限闭环固定为：

`用户身份解析 -> 权限上下文构建 -> SQL 安全检查 -> 表/行/列权限判定 -> SQL 重写/拒绝 -> 审计日志`

禁止在闭环外新增旁路放行。

### 2.4 端到端链路

1. 前端仅提交用户身份上下文（token），不直接提交权限条件。
2. 后端从用户信息与权限配置生成最终 SQL 条件。
3. SQL 执行前必须经过统一策略入口 `evaluate_sql_policy`。

### 2.5 可测试性

1. 单测覆盖：角色映射、上下文构建、重写策略与拒绝路径。
2. API 测试覆盖：权限配置、试跑接口、错误码一致性。
3. 发布门禁：权限回归 + 文档门禁双通过。

---

## 3. 数据与接口设计

### 3.1 数据模型调整

1. 在 `t_user` 新增 `data_role`（字符串枚举，默认 `staff`）。
2. `role` 字段保留作为 `sys_role` 兼容入口（后续可重命名）。
3. 历史数据迁移：所有用户按规则回填 `data_role`，不得出现 NULL。

### 3.2 权限策略模型

沿用现有三张权限表：

1. `t_data_permission_table`（表级）
2. `t_data_permission_row`（行级）
3. `t_data_permission_column`（列级）

新增约束：角色值统一使用 `data_role` 枚举代码值。

### 3.3 API 设计（治理）

建议新增/扩展：

1. `GET /api/v1/access-admin/data-roles`：查询数据角色与策略摘要。
2. `PUT /api/v1/access-admin/data-roles/{role}`：更新角色策略模板。
3. `POST /api/v1/access-admin/sql-dry-run`：输入 `user_id + sql` 返回重写结果。

---

## 4. 分阶段实施任务

### 4.1 Phase 1：模型与迁移

1. 新增 `data_role` 字段及迁移脚本。
2. 回填策略：未设置用户统一 `staff`。
3. 同步 schema 与用户接口定义。

### 4.2 Phase 2：权限引擎与 SQL 重写

1. `permission_service` 改为优先读取 `data_role`。
2. 移除 `admin` 默认无限制逻辑。
3. `sql_rewriter` 默认注入 `dept_code` 条件。
4. 缺失 `dept_code` 返回明确拒绝原因。

### 4.3 Phase 3：治理与审计

1. 增加角色策略管理接口与输入校验。
2. 增加 SQL 试跑接口。
3. 增加策略命中审计字段与日志。

### 4.4 Phase 4：门禁与上线

1. 执行单测、接口测试、门禁脚本。
2. 灰度开关启用并验证命中率/误拒绝率。
3. 制定紧急回滚路径（回滚到旧策略版本）。

---

## 5. 风险评估

| 风险 | 级别 | 触发条件 | 缓解策略 |
|---|---|---|---|
| 误放权风险 | 高 | admin 直通未彻底移除 | Gate 强制覆盖 admin case |
| 误拒绝风险 | 中 | `dept_code` 缺失用户较多 | 迁移前补数据 + 观测告警 |
| 兼容风险 | 中 | 历史接口仍依赖 `role` 字段 | 分阶段兼容 + 明确废弃窗口 |
| 运维复杂度风险 | 中 | 策略维度增长 | 固化模板与试跑工具 |

---

## 6. 文档分层与引用关系

1. 主计划：本文档（实施阶段、边界、风险、门禁）。
2. 并行拆解：`docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md`。
3. 执行顺序：先按本文冻结契约，再按并行 WS 推进实现。
4. 冲突裁决：若 WS 文档与主计划冲突，以主计划为准。

---

## 7. 并行拆解种子信息（parallel 必填）

- `task_key`: `PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION`
- `card_seed`:

```yaml
card_seed:
  - cap_id: CAP-DP-01
    title: 用户模型与迁移改造
    hard_depends_on: []
    soft_depends_on: []
    file_scope:
      - app/models/user.py
      - app/schemas/user.py
      - app/repositories/user_repo.py
      - alembic/versions/
    owner_fields:
      - user.data_role
      - user.role_compat
    check_cmd:
      - venv/bin/python -m pytest -q tests/unit -k "user and role"
    dod:
      - data_role 字段与迁移回填完成

  - cap_id: CAP-DP-02
    title: 权限引擎与SQL重写收敛
    hard_depends_on:
      - CAP-DP-01
    soft_depends_on: []
    file_scope:
      - app/services/permission_service.py
      - app/ai/utils/permission_context.py
      - app/ai/utils/sql_rewriter.py
      - app/ai/utils/sql_policy_decision.py
    owner_fields:
      - permission_context.data_role
      - permission.default_dept_scope
      - permission.deny_overrides_allow
    check_cmd:
      - venv/bin/python -m pytest -q tests/unit/test_sql_policy_decision.py tests/unit/test_sql_rewriter.py
    dod:
      - admin 默认直通移除，dept_code 默认隔离生效

  - cap_id: CAP-DP-03
    title: 权限配置API与审计能力
    hard_depends_on:
      - CAP-DP-02
    soft_depends_on: []
    file_scope:
      - app/api/v1/endpoints/access_admin_api.py
      - app/schemas/
      - tests/api/test_access_admin_api.py
    owner_fields:
      - api.data_role_policy
      - api.sql_dry_run
      - audit.permission_hit
    check_cmd:
      - venv/bin/python -m pytest -q tests/api/test_access_admin_api.py
    dod:
      - 配置管理与试跑接口可用，并可追溯策略命中
```
