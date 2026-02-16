# 迭代需求目录说明与命名规范

> 生效日期：2026-02-14
> 适用范围：`docs/内部参考/迭代需求/`

---

## 1. 目录定位

本目录用于维护**当前有效**的迭代需求基线与实施方案，服务研发、评审与门禁回溯。

约束：

1. 目录保持单层结构，不新增日期分层归档。
2. 文档按“需求基线 + 实施方案 + 评估报告”组织。
3. 历史沉淀通过任务拆解与测试报告体系追溯，不在本目录再引入第二套归档规则。

---

## 2. 命名规范

### 2.1 通用入口（可选）

仅在“单一主线迭代”场景允许使用以下文件名：

- `requirements.md`
- `implementation_plan.md`

### 2.2 专项前缀（默认）

并行主题或长期维护场景，必须使用专题前缀：

- 需求基线：`<topic>_requirements.md`
- 实施方案：`<topic>_implementation_plan.md`

兼容说明：历史文件中的 `<topic>_plan.md` 继续保留，不强制重命名；新增文件优先采用 `<topic>_implementation_plan.md`。

### 2.3 主题命名建议

`<topic>` 建议采用小写蛇形命名，保持语义可读并避免缩写歧义，例如：

- `skill_admin_frontend`
- `docs_governance`

---

## 3. 索引治理规则

1. 本目录新增、重命名或删除文档时，必须同步更新 `docs/SUMMARY.md`。
2. `docs/SUMMARY.md` 中本目录入口文案统一为：
   - `需求基线（<主题>）`
   - `实施方案（<主题>）`
   - `评估报告（通用入口）` 或 `评估报告（<主题>）`
3. 每次索引调整后，执行 `python3 scripts/docs_guard.py --strict`，确保覆盖率与断链检查通过。

---

## 4. 当前索引清单（2026-02-16）

- `skill_admin_frontend_requirements.md`
- `skill_admin_frontend_plan.md`（历史兼容命名）
- `docs_governance_requirements.md`
- `docs_governance_implementation_plan.md`
- `askdata_dual_role_permission_requirements.md`
- `askdata_dual_role_permission_implementation_plan.md`
- `user_preference_memory_requirements.md`
- `user_preference_memory_implementation_plan.md`
- `evaluation_report.md`

附注：`requirements.md`、`implementation_plan.md`、`fix_plan.md` 作为本地可选入口，当前默认不纳入版本管理（见 `.gitignore`）。
