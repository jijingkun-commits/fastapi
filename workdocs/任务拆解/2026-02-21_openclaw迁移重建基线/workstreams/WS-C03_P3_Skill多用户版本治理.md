# 工作包说明

> WS 编号: WS-C03
> 名称: P3 Skill 多用户版本治理
> 类型: parallel
> 对应 feature_id: P3-01

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: C03
- 来源主计划: `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md`

## 1. 目标

- 本包目标: P3 Skill 多用户版本治理 的可执行落地。
- 完成定义（DoD）:
  - Skill 版本发布/回滚/用户绑定回归通过
  - 多用户并发绑定与检索隔离回归通过（无跨用户污染）
  - ENABLE_SKILL_VERSIONING 与 ENABLE_USER_SKILL_BINDING 回滚验证通过

### 1.1 功能机制

  - Skill 定义、版本、用户绑定三层解耦
  - 支持用户级绑定、生效与回滚
  - 避免跨用户污染

### 1.2 代码锚点

  - app/models/agent_skill.py::AgentSkill
  - app/services/skill_service.py::search_skills
  - app/api/v1/endpoints/skill_admin_api.py::list_skills

- 本卡新增实体目标（C03 实现阶段创建）:
  - app/services/skill_service.py（bind_user_skill）
  - app/api/v1/endpoints/skill_admin_api.py（bind_skill）

- 来源证据:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.8

## 2. 文件边界

### 可修改（白名单）
  - app/models/agent_skill.py
  - app/services/skill_service.py
  - app/api/v1/endpoints/skill_admin_api.py
  - tests/unit/test_skill_service.py
  - tests/api/test_skill_admin_api.py

### 禁止修改（黑名单）
- 其他 card_id 对应白名单外文件

## 3. 串行门禁

- 前置卡: C02
- 解锁条件: 前置卡 `done_gate` 全部通过
- 本 WS 不得推进条件: 前置卡存在 `TODO/IN_PROGRESS/BLOCKED`

## 4. 测试与验收

- 先决要求:
  - 若 `tests/api/test_skill_admin_api.py` 不存在，在本卡内补齐 API 级绑定/回滚用例
- 验收命令:
  - PYTHONPATH=. pytest tests/unit/test_skill_service.py -k "version or binding"
  - PYTHONPATH=. pytest tests/api/test_skill_admin_api.py -k "binding or rollback"

## 5. 风险与回滚

- 回滚锚点:
  - ENABLE_SKILL_VERSIONING
  - ENABLE_USER_SKILL_BINDING

## 6. card_export

```yaml
card_export:
  id: WS-C03
  card_id: C03
  feature_ids: [P3-01]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-C03
  title: P3 Skill 多用户版本治理
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: [C02]
  depends_on: [C02]
  file_whitelist:
  - app/models/agent_skill.py
  - app/services/skill_service.py
  - app/api/v1/endpoints/skill_admin_api.py
  - tests/unit/test_skill_service.py
  - tests/api/test_skill_admin_api.py
  mechanism_summary:
  - Skill 定义、版本、用户绑定三层解耦
  - 支持用户级绑定、生效与回滚
  - 避免跨用户污染
  code_anchor_refs:
  - app/models/agent_skill.py::AgentSkill
  - app/services/skill_service.py::search_skills
  - app/api/v1/endpoints/skill_admin_api.py::list_skills
  acceptance_checks:
  - PYTHONPATH=. pytest tests/unit/test_skill_service.py -k "version or binding"
  - PYTHONPATH=. pytest tests/api/test_skill_admin_api.py -k "binding or rollback"
  rollback_anchors:
  - ENABLE_SKILL_VERSIONING
  - ENABLE_USER_SKILL_BINDING
  evidence_entry: docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.8
  done_gate:
  - Skill 版本发布/回滚/用户绑定回归通过
  - 多用户并发绑定与检索隔离回归通过
  - ENABLE_SKILL_VERSIONING 与 ENABLE_USER_SKILL_BINDING 回滚验证通过
```
