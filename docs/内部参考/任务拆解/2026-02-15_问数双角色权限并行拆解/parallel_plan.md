# 并行计划书：问数双角色权限收敛

> 计划 ID: PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION
> 主题: 问数权限从通用角色模型切换为银行双角色模型（sys_role/data_role）
> 输入来源: `docs/内部参考/迭代需求/askdata_dual_role_permission_requirements.md` / `docs/内部参考/迭代需求/askdata_dual_role_permission_implementation_plan.md`

---

## 0. G0 协议冻结

### 0.1 冻结目标

在并行开发前冻结“身份语义 + 权限优先级 + 默认行级策略”，避免后续工作包出现策略漂移。

### 0.2 冻结范围

1. 双角色契约：`sys_role` 与 `data_role`。
2. 数据角色枚举：`head_president` / `department_gm` / `department_vgm` / `staff`。
3. 权限优先级：`deny > allow > role_template > default`。
4. 默认行级策略：`dept_code = user.dept_code`。

### 0.3 required/optional 与兼容约束

#### 身份契约

- required：`t_user.role`（系统角色兼容）、`t_user.data_role`（数据权限主体）
- optional：`org_code`、`org_name`、`dept_name`
- 兼容策略：历史用户无 `data_role` 时回填 `staff`。

#### 权限判定契约

- required：拒绝优先；未命中显式规则时使用默认行级策略。
- optional：按配置放大到机构/指定列表范围。
- 兼容策略：仅允许扩展 scope 类型，不允许改变优先级顺序。

### 0.4 机读契约

- 协议文件：`docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/contracts/data_permission_contract_v1.json`

---

## 1. seed 来源

- `task_key`: `PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION`
- 来源：`plan parallel`
- `card_seed` 来源：`askdata_dual_role_permission_implementation_plan.md` 第 7 节
- 推导依据与风险：基于“先模型、后引擎、再治理”拆分；风险在于 WS-02 与 WS-03 可能产生接口字段对齐耦合。

---

## 2. 目标与边界

### 2.1 目标

1. 完成双角色模型落地，解除 admin 与数据可见范围耦合。
2. 完成 `dept_code` 默认行级隔离。
3. 完成可配置放权与可观测审计的交付路径。

### 2.2 非目标

1. 不改造全部业务 API 的鉴权模型。
2. 不在本轮引入组织树自动推导。

### 2.3 约束（架构/性能/合规）

1. 问数 SQL 执行必须经过统一策略决策入口。
2. 默认最小权限，不得出现“未配置即放开”。
3. 双数据库约束不变：问数查询继续走分析库链路。

---

## 3. 架构冻结项（并行前必须确认）

1. 模块边界：
   - 用户模型与迁移由 WS-01 负责。
   - 权限引擎与 SQL 重写由 WS-02 负责。
   - 权限配置 API 与审计由 WS-03 负责。
2. 状态契约：
   - `user.data_role` 为唯一数据角色来源。
   - `permission_context.role` 迁移为 `permission_context.data_role`（保留兼容字段）。
3. 路由闭环：
   - `sql_policy_decision -> sql_rewriter -> permission_service` 保持单入口。
4. 前后端链路时序：
   - 前端仅展示角色中文映射，不参与策略计算。

---

## 4. 工作包总览

| WS | 名称 | 类型 | 可并行 | 依赖 |
|---|---|---|---|---|
| WS-00 | G0 数据权限契约冻结 | foundation | 否 | 无 |
| WS-01 | 用户模型与迁移改造 | parallel | 是 | WS-00 |
| WS-02 | 权限引擎与 SQL 重写收敛 | parallel | 是 | WS-01 |
| WS-03 | 权限配置 API 与审计能力 | parallel | 是 | WS-02 |
| WS-G1 | 集成回归门禁 | gate | 否 | WS-01, WS-02, WS-03 |
| WS-G2 | 文档终稿门禁 | gate | 否 | WS-G1 |

---

## 5. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|---|---|---|---|
| `app/models/user.py` | WS-01 | 否 | 单所有者 |
| `app/services/permission_service.py` | WS-02 | 否 | 单所有者 |
| `app/api/v1/endpoints/access_admin_api.py` | WS-03 | 否 | 单所有者 |
| `permission_context.data_role` 语义 | WS-02 | 只读 | 由 G0 冻结 |

---

## 6. 依赖图与里程碑

- 依赖图：`WS-00 -> WS-01 -> WS-02 -> WS-03 -> WS-G1 -> WS-G2`
- 里程碑：
  1. M1：完成 `data_role` 模型与迁移（WS-01）
  2. M2：完成引擎收敛与默认 dept 隔离（WS-02）
  3. M3：完成治理 API 与审计（WS-03）
  4. M4：Gate 收口并发布（WS-G1/WS-G2）

---

## 7. 合并策略

1. 合并顺序：`WS-01 -> WS-02 -> WS-03 -> WS-G1 -> WS-G2`
2. 回归门禁：G1 执行单测/API/文档门禁。
3. 回滚策略：按 WS 颗粒回滚，优先回滚策略层（WS-02/WS-03）。

---

## 8. 串行回退说明（若触发）

- 是否触发：否（初始）
- 触发条件：
  1. `data_role` 字段契约变更未达成一致。
  2. WS-02 与 WS-03 出现共享接口冲突无法在 1 次迭代内收敛。
- 串行路线：`WS-01 -> WS-02 -> WS-03` 单线推进。

---

## 9. 看板导出索引

- `task_key`: `PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION`
- 拆解目录 ID: `2026-02-15_问数双角色权限并行拆解`
- WS 总数: 6（其中 Gate 2，Foundation 1）
- Gate 总数: 2
- 默认列流转：`Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则：`<task_key>::<WS-ID>`
- 卡片标题规则：`<WS-ID> <标题> [<task_key>]`

---

## 10. Gate 执行状态

### 10.1 WS-G1 结果（自动回填：2026-02-16 15:28）

- `pytest`：通过
- `tsc`：通过
- `lint`：通过（0 warning）
- `docs_guard`：通过（0 error, 0 warning）

### 10.2 WS-G2 预期动作

1. 同步产品/架构/测试文档。
2. 更新 `docs/SUMMARY.md` 索引。
3. 复跑 `docs_guard` 并归档结论。

---

## 11. Gate 收口结果（自动回填：2026-02-16 15:28）

1. `WS-G1` 已执行：
   - `pytest` 通过
   - `tsc` 通过
   - `lint` 通过（0 warning）
   - `docs_guard` 通过（0 error, 0 warning）
2. `WS-G2` 已执行：
   - `docs_guard --strict` 通过（0 error, 0 warning）
3. Gate 结论：
   - 业务与文档门禁通过，可关闭本轮 Gate。
