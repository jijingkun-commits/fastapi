# 工作包说明

> WS 编号: WS-03
> 名称: 权限配置 API 与审计能力
> 类型: parallel

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION`
- 来源主计划：`docs/内部参考/迭代需求/askdata_dual_role_permission_implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md`

---

## 1. 目标

- 本包目标：提供数据角色策略管理能力与 SQL 试跑能力，并补审计追踪。
- 完成定义（DoD）：
  1. 数据角色策略 CRUD 可用。
  2. SQL 试跑接口可返回“重写 SQL + 拒绝原因”。
  3. 审计日志可定位策略命中与拒绝阶段。

---

## 2. 文件边界

### 可修改（白名单）

- `app/api/v1/endpoints/access_admin_api.py`
- `app/schemas/`
- `app/services/permission_service.py`
- `tests/api/test_access_admin_api.py`
- `tests/unit/test_permission_service.py`

### 禁止修改（黑名单）

- `app/models/user.py`
- `alembic/versions/`

---

## 3. 状态与契约

- 可写字段：`api.data_role_policy`、`api.sql_dry_run`、`audit.permission_hit`。
- 只读字段：`data_role` 枚举与默认策略（G0 冻结）。
- 外部契约：`contracts/data_permission_contract_v1.json`。

---

## 4. 实施步骤

1. 扩展 `access_admin_api` 增加数据角色策略接口。
2. 增加 SQL 试跑接口（输入用户 + SQL，输出策略结果）。
3. 在权限服务中补策略命中审计字段。
4. 补齐 API 与单测。

---

## 5. 测试与验收

- 最小测试集：
  - `venv/bin/python -m pytest -q tests/api/test_access_admin_api.py`
  - `venv/bin/python -m pytest -q tests/unit/test_permission_service.py`
- 验收标准：
  1. 管理员可维护数据角色策略。
  2. 试跑结果可解释且可追溯。

### 5.1 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：否
- 触发依据（命中项）：本包只交付后端 API。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因：前端联调在后续任务执行。

---

## 6. 风险与回滚

- 主要风险：配置接口误用导致策略异常放大。
- 回滚点：接口入口加只读开关与策略版本回滚。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
- 是否修改了白名单外文件（是/否）：
- 测试命令与结果：
- 已知风险点：
- 回滚建议：

---

## 8. card_export（/vk 机读，必填）

```yaml
card_export:
  id: WS-03
  card_key: PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION::WS-03
  title: 权限配置 API 与审计能力
  type: parallel
  lane: lane-backend-api
  hard_depends_on:
    - WS-02
  soft_depends_on: []
  depends_on:
    - WS-02
  file_whitelist:
    - app/api/v1/endpoints/access_admin_api.py
    - app/schemas/
    - app/services/permission_service.py
    - tests/api/test_access_admin_api.py
    - tests/unit/test_permission_service.py
  readonly_scope:
    - app/models/user.py
    - alembic/versions/
  owner_fields:
    - api.data_role_policy
    - api.sql_dry_run
    - audit.permission_hit
  check_cmd:
    - venv/bin/python -m pytest -q tests/api/test_access_admin_api.py
    - venv/bin/python -m pytest -q tests/unit/test_permission_service.py
  handoff_artifacts:
    - tests/api/test_access_admin_api.py
  dod:
    - 配置管理与试跑接口可用，并可追溯策略命中
```
