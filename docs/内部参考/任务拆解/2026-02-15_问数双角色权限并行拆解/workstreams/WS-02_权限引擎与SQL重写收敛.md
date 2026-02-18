# 工作包说明

> WS 编号: WS-02
> 名称: 权限引擎与 SQL 重写收敛
> 类型: parallel

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION`
- 来源主计划：`docs/内部参考/迭代需求/askdata_dual_role_permission_implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md`

---

## 1. 目标

- 本包目标：权限判定统一改为 `data_role` 驱动，并默认启用 `dept_code` 隔离。
- 完成定义（DoD）：
  1. `admin` 默认直通逻辑移除。
  2. 默认注入 `dept_code = user.dept_code`。
  3. `dept_code` 缺失时给出明确拒绝原因。

---

## 2. 文件边界

### 可修改（白名单）

- `app/services/permission_service.py`
- `app/ai/utils/permission_context.py`
- `app/ai/utils/sql_rewriter.py`
- `app/ai/utils/sql_policy_decision.py`
- `tests/unit/test_sql_policy_decision.py`
- `tests/unit/test_sql_rewriter.py`
- `tests/unit/test_permission_context.py`

### 禁止修改（黑名单）

- `app/models/user.py`
- `alembic/versions/`
- `app/api/v1/endpoints/access_admin_api.py`

---

## 3. 状态与契约

- 可写字段：`permission_context.data_role`、`permission.default_dept_scope`。
- 只读字段：`data_role` 枚举集合与优先级顺序（G0 冻结）。
- 外部契约：`contracts/data_permission_contract_v1.json`。

---

## 4. 实施步骤

1. 调整 `permission_service` 读取 `data_role` 并兼容旧字段。
2. 移除 `ctx.is_admin()` 的默认放行分支。
3. 在 SQL 重写流程注入默认 `dept_code` 行级条件。
4. 补齐单测覆盖拒绝路径与兼容路径。

---

## 5. 测试与验收

- 最小测试集：
  - `venv/bin/python -m pytest -q tests/unit/test_sql_policy_decision.py tests/unit/test_sql_rewriter.py tests/unit/test_permission_context.py`
- 验收标准：
  1. 非放权场景仅可访问本 `dept_code`。
  2. admin 不再默认全量放行。

### 5.1 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：否
- 触发依据（命中项）：后端策略逻辑，不涉及 UI 变更。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因：不涉及浏览器交互。

---

## 6. 风险与回滚

- 主要风险：误拒绝导致业务查询不可用。
- 回滚点：恢复旧权限上下文判定逻辑。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
- 是否修改了白名单外文件（是/否）：
- 测试命令与结果：
- 已知风险点：
- 回滚建议：

---

## 8. card_export（机读，必填）

```yaml
card_export:
  id: WS-02
  card_key: PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION::WS-02
  title: 权限引擎与 SQL 重写收敛
  type: parallel
  lane: lane-backend-permission
  hard_depends_on:
    - WS-01
  soft_depends_on: []
  depends_on:
    - WS-01
  file_whitelist:
    - app/services/permission_service.py
    - app/ai/utils/permission_context.py
    - app/ai/utils/sql_rewriter.py
    - app/ai/utils/sql_policy_decision.py
    - tests/unit/test_sql_policy_decision.py
    - tests/unit/test_sql_rewriter.py
    - tests/unit/test_permission_context.py
  readonly_scope:
    - app/models/user.py
    - alembic/versions/
  owner_fields:
    - permission_context.data_role
    - permission.default_dept_scope
    - permission.no_admin_bypass
  check_cmd:
    - venv/bin/python -m pytest -q tests/unit/test_sql_policy_decision.py tests/unit/test_sql_rewriter.py tests/unit/test_permission_context.py
  handoff_artifacts:
    - tests/unit/test_sql_policy_decision.py
    - tests/unit/test_sql_rewriter.py
  dod:
    - admin 默认直通移除，dept_code 默认隔离生效
```
