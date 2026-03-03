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

### 2.1 通用入口（不推荐）

仅在“本地临时草稿”场景允许使用以下文件名（不建议纳入版本管理）：

- `requirements.md`
- `implementation_plan.md`

### 2.2 专项前缀（默认）

并行主题或长期维护场景，必须使用专题前缀：

- 需求基线：`<topic>_requirements.md`
- 实施方案：`<topic>_implementation_plan.md`

兼容说明：历史文件中的 `<topic>_plan.md` 继续保留，不强制重命名；新增文件优先采用 `<topic>_implementation_plan.md`。

### 2.3 主题命名建议（与任务拆解对齐）

`<topic>` 默认与任务拆解目录 `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/` 的 `<主题>` 对齐，优先使用中文主题短语。

规则：

1. 新增迭代需求文件时，优先使用中文主题前缀：
   - `<主题>_requirements.md`
   - `<主题>_implementation_plan.md`
2. 若同一需求已存在任务拆解目录，`<topic>` 必须与该目录名中的 `<主题>` 保持一致（仅允许语序微调，不允许改语义）。
3. 中文主题建议控制在 4~12 字，避免空格与特殊字符；必要时可用下划线分隔（如 `问数权限治理`、`文档治理执行`）。
4. `task_key` 所需英文机读标识独立维护，不强制写入文件名前缀。
5. 历史英文前缀文件继续保留，不强制批量重命名；从本规则生效后新增文件按中文对齐执行。

---

## 3. 索引治理规则

1. 本目录默认存放过程文档，新增、重命名或删除文档时，不再要求逐条同步到 `docs/SUMMARY.md`。
2. `docs/SUMMARY.md` 在本目录仅保留入口级导航（目录说明），详细条目在各主题目录内部维护。
3. 每次索引或文件结构调整后，执行 `python3 scripts/docs_guard.py --strict`，确保断链检查通过。

---

## 4. 当前索引清单（2026-02-18）

- `skill_admin_frontend_requirements.md`
- `skill_admin_frontend_plan.md`（历史兼容命名）
- `ai_tools_governance_requirements.md`
- `ai_tools_governance_implementation_plan.md`
- `ai_tools_governance_implementation_appendix.md`
- `docs_governance_requirements.md`
- `docs_governance_implementation_plan.md`
- `askdata_dual_role_permission_requirements.md`
- `askdata_dual_role_permission_implementation_plan.md`
- `user_preference_memory_requirements.md`
- `user_preference_memory_implementation_plan.md`
- `agent_despecialization_requirements.md`
- `agent_despecialization_implementation_plan.md`
- `agent_despecialization_progress_log.md`
- `agent_despecialization_evaluation_report.md`
- `openclaw全量迁移_implementation_plan.md`
- `迁移执行波次_implementation_plan.md`
- `runtime_cancel_control_implementation_plan.md`
- `skill_multi_user_versioning_implementation_plan.md`
- `evaluation_report.md`
- `skill_retrieval_evaluation_report_20260213.md`
- `fix_plan.md`
- `fix_plan_todo_reject_clarify_20260218.md`

附注：`requirements.md` 与 `implementation_plan.md` 已迁移为专题前缀命名；`fix_plan.md` 调整为纳管入口文档，具体问题卡按 `fix_plan_<topic>_<date>.md` 追加维护。
