# 实施方案（用户 Skill 严格用户源治理）

> 主题：用户 Skill 严格用户源治理
> 日期：2026-03-01
> 模式：`jjk-plan core`（plan-only）
> 对应需求：`/Users/jijingkun/bojxAI/fastapi/workdocs/归档/需求/用户Skill严格用户源治理_requirements.md`

---

## 0. 设计审批与输入来源（强制门禁）

### 0.1 设计审批校验

- 设计文档：`/Users/jijingkun/bojxAI/fastapi/workdocs/归档/设计/2026-03-01-user-skill-strict-runtime-design.md`
- 审批记录：`design_approved: true`（已存在）
- 审批时间：`2026-03-01 18:05 CST`
- 审批轮次：`round-2`

### 0.2 输入来源清单（Superpowers 桥接）

1. `workdocs/归档/设计/2026-03-01-user-skill-strict-runtime-design.md`
2. `app/services/skill_service.py`（检索路径/回退逻辑/绑定逻辑）
3. `app/services/user_service.py`（新用户创建链路）
4. `app/api/v1/endpoints/skill_admin_api.py`（管理 API 基线）
5. `web/src/components/admin/SkillAdminPanel.tsx`（当前前端能力边界）

---

## 1. 架构影响与约束（必查项）

### 1.1 模块边界

1. 策略开关与运行模式归属 `ConfigResolver + t_system_config`。
2. Skill 检索与候选拼装归属 `SkillService`，禁止在 workflow 节点重复实现策略分支。
3. 用户初始化归属 `user_service` 调用 `skill_bootstrap_service`，避免散落在 API 层。
4. 前端权限分层：管理员（模板/全员）与普通用户（本人配置）分离。

### 1.2 状态契约

1. 运行时 canonical 字段：`skill_id/effective_version/binding_status/user_id`。
2. 模板 canonical 来源：`skill.user_bootstrap_template`（DB 配置）。
3. 生命周期：
   - 创建用户 -> 初始化绑定
   - 用户更新 -> 覆盖配置
   - 管理员回滚 -> 回到模板默认
   - 版本发布 -> 更新默认可用版本

### 1.3 路由闭环

1. `chat preprocess` 始终传 `user_id` 给 `SkillService.search_skills_debug`。
2. strict_user 模式下检索不可回退 legacy。
3. 失败时显式日志 + 降级策略（compat 回切），禁止 silent fallback。

### 1.4 端到端链路一致性

1. 创建用户 API 成功后，绑定初始化异步/同步策略保持可观测。
2. 用户页修改后触发检索生效，确保同 session 可验证。
3. 管理员模板更新不强制覆盖已存在用户绑定，仅影响新用户与手动对齐流程。

### 1.5 可测试性

1. 服务层单测覆盖 strict/compat 双模式。
2. API 测试覆盖权限边界与越权场景。
3. 前端冒烟覆盖模板管理与用户自维护关键路径。

---

## 2. Feature Packet（功能机制包）

| feature_id | 目标与边界 | 触发与状态流转 | 代码锚点 | 契约字段 | 回滚锚点 | 验证命令 | 来源证据 |
|---|---|---|---|---|---|---|---|
| P0-01 | 完成版本层回填与模板配置；不改对话协议 | 启动回填脚本 -> definitions/versions 就绪 -> 写模板配置 | `scripts/data/import_skills.py`, `app/services/skill_service.py` | `skill.user_bootstrap_template`, `version` | `feature.enable_skill_versioning=false` | `venv/bin/python -m pytest tests/unit/test_skill_service.py -k version -q` | design §6/§10 |
| P1-01 | 新用户自动初始化绑定；不阻塞用户创建主流程 | `create_user` 成功 -> `bootstrap_user_skills`（内部负责开关判定） -> 写 bindings | `app/services/user_service.py`, `app/services/skill_bootstrap_service.py`(新增) | `user_id/skill_id/version/is_enabled/config_override` | 关闭初始化调用（保留用户创建） | `venv/bin/python -m pytest tests/unit/test_user_service_skill_bootstrap.py -q` | design §6.3 |
| P1-02 | strict_user 检索强制用户源；不允许 legacy 主路径 | 查询进来 -> runtime 视图 -> 候选合并 -> 注入 | `app/services/skill_service.py`, `app/core/config_contract.py` | `skill.runtime_source_mode`, `effective_version` | 切回 `compat` | `venv/bin/python -m pytest tests/unit/test_skill_service.py -k strict_user -q` | design §7 |
| P1-03 | 用户自维护 API（本人） | 用户请求 -> auth -> 仅 current_user 写入 -> 返回最新绑定 | `app/api/v1/endpoints/user_skill_api.py`(新增), `app/api/v1/router.py` | `current_user.id`, `binding_status` | 临时下线用户 API 路由 | `venv/bin/python -m pytest tests/api/test_user_skill_api.py -q` | requirements §5/§6 |
| P1-04 | 管理员模板与覆盖治理 API/UI | 管理员修改模板 -> 校验 -> 落库 -> 审计 | `app/api/v1/endpoints/skill_admin_api.py`, `web/src/components/admin/SkillAdminPanel.tsx` | `template_version`, `operator_id` | 模板写操作降级只读 | `venv/bin/python -m pytest tests/api/test_skill_admin_api.py -k template -q` | design §8 |
| P1-05 | 可观测与灰度回滚闭环 | 检索/初始化/模板更新均输出结构化日志 | `app/services/skill_service.py`, `app/services/user_service.py` | `runtime_source_mode`, `user_id`, `trace_id` | 切回 compat + 关闭用户绑定开关 | `venv/bin/python -m pytest tests/unit/test_skill_retrieval_log.py -q` | design §12 |

---

## 3. 最小代码样例（每个 feature 至少一条）

```python
# P1-01: 用户创建后初始化 Skill 绑定（示意）
def create_user(db: Session, data: UserCreate):
    user = user_repo.create_user(...)
    try:
        skill_bootstrap_service.bootstrap_user_skills(db, user_id=user.id)
    except Exception as exc:
        logger.warning("用户技能模板初始化失败 user_id=%s err=%s", user.id, exc)
    return user
```

```python
# P1-02: strict_user 模式禁用 legacy 回退（示意）
runtime_mode = ConfigResolver.get_string("skill.runtime_source_mode", "compat").lower()
if runtime_mode == "strict_user":
    disable_legacy_fallback = True
```

---

## 4. API 设计（增量）

### 4.1 用户侧（新增）

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/v1/user-skills` | GET | 查询当前用户绑定与生效版本 |
| `/api/v1/user-skills/{skill_id}` | PATCH | 更新本人 `is_enabled/priority_override/config_override` |
| `/api/v1/user-skills/{skill_id}/reset` | POST | 回滚到模板默认 |

### 4.2 管理侧（增强）

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/v1/skill-admin/bootstrap-template` | GET | 查询全员统一模板 |
| `/api/v1/skill-admin/bootstrap-template` | PUT | 更新全员统一模板 |
| `/api/v1/skill-admin/bindings` | GET | 查询用户覆盖（已有接口增强） |
| `/api/v1/skill-admin/users/{user_id}/sync-template` | POST | 对指定用户执行模板对齐 |

---

## 5. 测试策略（TDD 前置，推荐）

```yaml
test_strategy:
  - feature_id: P1-01
    test_cases:
      - TC-SKILL-01: 新用户创建后自动初始化绑定
      - TC-SKILL-01B: 初始化异常不阻塞用户创建
    test_first: true
  - feature_id: P1-02
    test_cases:
      - TC-SKILL-04: strict_user 下禁止 legacy 主路径
      - TC-SKILL-05: hybrid 分数合成稳定
    test_first: true
  - feature_id: P1-03
    test_cases:
      - TC-SKILL-02: 用户仅能修改本人配置
      - TC-SKILL-03: 越权访问返回 403
    test_first: true
  - feature_id: P1-04
    test_cases:
      - TC-SKILL-06: 管理员模板更新校验与落库成功
      - TC-SKILL-07: 用户 A/B 检索隔离不互串
    test_first: true
  - feature_id: P1-05
    test_cases:
      - TC-SKILL-08: strict_user 回滚到 compat 后链路恢复可用
    test_first: true
```

---

## 6. Implementation Tasks（工单级 HOW）

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: P0-01
    phase: Phase-0
    pr_id: PR-01
    file_paths:
      - app/services/skill_service.py
      - scripts/data/import_skills.py
    symbols:
      - import_all_skills
      - _sync_versioned_records
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_skill_service.py -k version -q
    rollback_point: feature.enable_skill_versioning=false

  - task_id: T-02
    feature_id: P1-01
    phase: Phase-1
    pr_id: PR-01
    file_paths:
      - app/services/user_service.py
      - app/services/skill_bootstrap_service.py
      - app/services/config_resolver.py
    symbols:
      - create_user
      - bootstrap_user_skills
      - get_json_dict
    change_type: add_modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_user_service_skill_bootstrap.py -q
    rollback_point: 关闭 create_user 中 skill bootstrap 调用

  - task_id: T-03
    feature_id: P1-02
    phase: Phase-1
    pr_id: PR-02
    file_paths:
      - app/core/config_contract.py
      - app/services/skill_service.py
    symbols:
      - CONFIG_SPECS
      - _build_runtime_source_sql
      - _fetch_vector_candidates
      - _fetch_lexical_candidates
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_skill_service.py -k strict_user -q
    rollback_point: skill.runtime_source_mode=compat

  - task_id: T-04
    feature_id: P1-03
    phase: Phase-2
    pr_id: PR-03
    file_paths:
      - app/api/v1/endpoints/user_skill_api.py
      - app/api/v1/router.py
      - app/schemas/user_skill.py
    symbols:
      - list_current_user_skills
      - patch_current_user_skill
      - reset_current_user_skill
    change_type: add_modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/api/test_user_skill_api.py -q
    rollback_point: 下线 /user-skills 路由

  - task_id: T-05
    feature_id: P1-04
    phase: Phase-2
    pr_id: PR-03
    file_paths:
      - app/api/v1/endpoints/skill_admin_api.py
      - web/src/lib/skill-admin-api.ts
      - web/src/components/admin/SkillAdminPanel.tsx
    symbols:
      - get_bootstrap_template
      - update_bootstrap_template
      - getAllSkills
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/api/test_skill_admin_api.py -k template -q
    rollback_point: 模板接口改回只读

  - task_id: T-06
    feature_id: P1-05
    phase: Phase-3
    pr_id: PR-04
    file_paths:
      - app/services/skill_service.py
      - app/services/user_service.py
      - docs/开发文档/快速入门/配置说明.md
    symbols:
      - _build_retrieval_log
      - create_user
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_skill_retrieval_log.py -q
      - python3 scripts/docs_guard.py --strict
    rollback_point: 关闭 strict_user 并恢复 compat
```

---

## 7. task -> PR 映射契约（项目强制）

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/user-skill-strict-pr-01
      pr_depends_on: []
      pr_subject: "Skill 版本基线回填与用户模板初始化"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_skill_service.py -k version -q
      rollback_point: feature.enable_skill_versioning=false

    - task_id: T-02
      pr_id: PR-01
      pr_branch: codex/user-skill-strict-pr-01
      pr_depends_on: []
      pr_subject: "用户创建链路接入 skill bootstrap"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_user_service_skill_bootstrap.py -q
      rollback_point: 移除 create_user 的 bootstrap 调用

    - task_id: T-03
      pr_id: PR-02
      pr_branch: codex/user-skill-strict-pr-02
      pr_depends_on:
        - PR-01
      pr_subject: "strict_user 运行模式与检索路径收敛"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_skill_service.py -k strict_user -q
      rollback_point: skill.runtime_source_mode=compat

    - task_id: T-04
      pr_id: PR-03
      pr_branch: codex/user-skill-strict-pr-03
      pr_depends_on:
        - PR-02
      pr_subject: "用户侧 Skills 自维护 API"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/api/test_user_skill_api.py -q
      rollback_point: 下线用户技能路由

    - task_id: T-05
      pr_id: PR-03
      pr_branch: codex/user-skill-strict-pr-03
      pr_depends_on:
        - PR-02
      pr_subject: "管理员模板治理 API 与后台页面增强"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/api/test_skill_admin_api.py -k template -q
      rollback_point: 模板编辑能力降级只读

    - task_id: T-06
      pr_id: PR-04
      pr_branch: codex/user-skill-strict-pr-04
      pr_depends_on:
        - PR-03
      pr_subject: "可观测收口与配置文档同步"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_skill_retrieval_log.py -q
        - python3 scripts/docs_guard.py --strict
      rollback_point: 关闭 strict_user 并恢复 compat
```

---

## 8. planning_contract（供后续 vkplan 消费）

```yaml
planning_contract:
  execution_mode: serial
  card_order: [C01, C02, C03, C04, G01]
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
    inspection/question-card: policy_gate
  gate_contract:
    mode: as_cards
    gate_ids: [G01]
    depends_on:
      G01: [C04]
  cards:
    - card_id: C01
      wave: P0
      feature_ids: [P0-01, P1-01]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 版本表回填完成并可查
        - 新用户创建路径初始化绑定可用
      acceptance_checks:
        - venv/bin/python -m pytest tests/unit/test_skill_service.py -k version -q
        - venv/bin/python -m pytest tests/unit/test_user_service_skill_bootstrap.py -q
      evidence_entry: workdocs/归档/实施计划/用户Skill严格用户源治理_implementation_plan.md

    - card_id: C02
      wave: P1
      feature_ids: [P1-02]
      depends_on: [C01]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - strict_user 模式检索主链无 legacy 依赖
      acceptance_checks:
        - venv/bin/python -m pytest tests/unit/test_skill_service.py -k strict_user -q
      evidence_entry: workdocs/归档/实施计划/用户Skill严格用户源治理_implementation_plan.md

    - card_id: C03
      wave: P2
      feature_ids: [P1-03]
      depends_on: [C02]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 用户仅可维护本人 Skills
      acceptance_checks:
        - venv/bin/python -m pytest tests/api/test_user_skill_api.py -q
      evidence_entry: workdocs/归档/实施计划/用户Skill严格用户源治理_implementation_plan.md

    - card_id: C04
      wave: P2
      feature_ids: [P1-04, P1-05]
      depends_on: [C03]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 管理员模板治理页可用
        - 结构化日志与文档同步完成
      acceptance_checks:
        - venv/bin/python -m pytest tests/api/test_skill_admin_api.py -k template -q
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/实施计划/用户Skill严格用户源治理_implementation_plan.md

    - card_id: G01
      wave: Gate
      feature_ids: [G-1]
      depends_on: [C04]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - 所有关键验收命令通过
        - 配置灰度与回滚SOP可执行
      acceptance_checks:
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/实施计划/用户Skill严格用户源治理_implementation_plan.md
```

---

## 9. 风险评估与回滚策略

| 风险 | 触发信号 | 处置策略 |
|---|---|---|
| strict_user 上线后召回骤降 | 命中率/召回率指标下降 | 立即切回 `skill.runtime_source_mode=compat` |
| 模板错误导致批量初始化异常 | 新用户绑定失败告警升高 | 暂停模板更新，回滚到上一个模板版本 |
| 用户覆盖越权 | 审计日志出现跨用户写入 | 关闭用户写接口并修复权限校验 |

---

## 10. implementation_readiness（机读结论）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: $jjk-vkplan
```

---

## 11. 执行意图门禁说明

当前文档为 `plan-only` 产物，不自动进入实施链；是否执行由后续显式命令决定。

---

## 12. execution_log（`$jjk-imp`）

```yaml
execution_log:
  - task_id: T-01
    feature_id: P0-01
    pr_id: PR-01
    file_paths:
      - app/services/skill_service.py
      - scripts/data/import_skills.py
      - app/core/config_contract.py
      - tests/unit/test_skill_service.py
      - docs/开发文档/快速入门/配置说明.md
    symbols:
      - import_all_skills
      - _build_user_bootstrap_template
      - _ensure_user_bootstrap_template_config
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_skill_service.py -k version -q
    result: PASS
    rollback_point: feature.enable_skill_versioning=false

  - task_id: T-02
    feature_id: P1-01
    pr_id: PR-01
    file_paths:
      - app/services/user_service.py
      - app/services/skill_bootstrap_service.py
      - app/core/config_contract.py
      - tests/unit/test_user_service_skill_bootstrap.py
      - docs/开发文档/快速入门/配置说明.md
    symbols:
      - create_user
      - bootstrap_user_skills
      - get_json_dict
    change_type: add_modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_user_service_skill_bootstrap.py -q
    result: PASS
    rollback_point: 关闭 create_user 中 skill bootstrap 调用

  - task_id: T-03
    feature_id: P1-02
    pr_id: PR-02
    file_paths:
      - app/services/skill_service.py
      - tests/unit/test_skill_service.py
    symbols:
      - _get_runtime_source_mode
      - _fetch_vector_candidates
      - _fetch_lexical_candidates
      - _build_retrieval_log
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_skill_service.py -k strict_user -q
    result: PASS
    rollback_point: skill.runtime_source_mode=compat

  - task_id: T-04
    feature_id: P1-03
    pr_id: PR-03
    file_paths:
      - app/api/v1/endpoints/user_skill_api.py
      - app/api/v1/router.py
      - app/schemas/user_skill.py
      - tests/api/test_user_skill_api.py
      - docs/API文档/接口文档.md
    symbols:
      - list_current_user_skills
      - patch_current_user_skill
      - reset_current_user_skill
    change_type: add_modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/api/test_user_skill_api.py -q
    result: PASS
    rollback_point: 下线 /user-skills 路由

  - task_id: T-05
    feature_id: P1-04
    pr_id: PR-03
    file_paths:
      - app/api/v1/endpoints/skill_admin_api.py
      - web/src/lib/skill-admin-api.ts
      - web/src/components/admin/SkillAdminPanel.tsx
      - tests/api/test_skill_admin_api.py
      - docs/API文档/接口文档.md
    symbols:
      - get_bootstrap_template
      - update_bootstrap_template
      - sync_user_template
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/api/test_skill_admin_api.py -k template -q
    result: PASS
    rollback_point: 模板接口改回只读

  - task_id: T-06
    feature_id: P1-05
    pr_id: PR-04
    file_paths:
      - app/services/skill_service.py
      - tests/unit/test_skill_retrieval_log.py
      - workdocs/归档/实施计划/用户Skill严格用户源治理_implementation_plan.md
      - docs/SUMMARY.md
    symbols:
      - _build_retrieval_log
      - _search_skills_internal
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_skill_retrieval_log.py -q
      - python3 scripts/docs_guard.py --strict
    result: PASS
    rollback_point: 关闭 strict_user 并恢复 compat
```

## 13. blocked_items（执行后）

```yaml
blocked_items: []
```

## 14. pr_ready_manifest（PR-01 ~ PR-04）

```yaml
pr_ready_manifest:
  - task_id: T-01
    pr_id: PR-01
    card_id: C01
    changed_files:
      - app/services/skill_service.py
      - scripts/data/import_skills.py
      - app/core/config_contract.py
      - tests/unit/test_skill_service.py
      - docs/开发文档/快速入门/配置说明.md
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_skill_service.py -k version -q
    rollback_point: feature.enable_skill_versioning=false

  - task_id: T-02
    pr_id: PR-01
    card_id: C01
    changed_files:
      - app/services/user_service.py
      - app/services/skill_bootstrap_service.py
      - app/core/config_contract.py
      - tests/unit/test_user_service_skill_bootstrap.py
      - docs/开发文档/快速入门/配置说明.md
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_user_service_skill_bootstrap.py -q
    rollback_point: 关闭 create_user 中 skill bootstrap 调用

  - task_id: T-03
    pr_id: PR-02
    card_id: C02
    changed_files:
      - app/services/skill_service.py
      - tests/unit/test_skill_service.py
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_skill_service.py -k strict_user -q
    rollback_point: skill.runtime_source_mode=compat

  - task_id: T-04
    pr_id: PR-03
    card_id: C03
    changed_files:
      - app/api/v1/endpoints/user_skill_api.py
      - app/api/v1/router.py
      - app/schemas/user_skill.py
      - tests/api/test_user_skill_api.py
      - docs/API文档/接口文档.md
    acceptance_cmds:
      - venv/bin/python -m pytest tests/api/test_user_skill_api.py -q
    rollback_point: 下线用户技能路由

  - task_id: T-05
    pr_id: PR-03
    card_id: C04
    changed_files:
      - app/api/v1/endpoints/skill_admin_api.py
      - web/src/lib/skill-admin-api.ts
      - web/src/components/admin/SkillAdminPanel.tsx
      - tests/api/test_skill_admin_api.py
      - docs/API文档/接口文档.md
    acceptance_cmds:
      - venv/bin/python -m pytest tests/api/test_skill_admin_api.py -k template -q
    rollback_point: 模板编辑能力降级只读

  - task_id: T-06
    pr_id: PR-04
    card_id: C04
    changed_files:
      - app/services/skill_service.py
      - tests/unit/test_skill_retrieval_log.py
      - workdocs/归档/实施计划/用户Skill严格用户源治理_implementation_plan.md
      - docs/SUMMARY.md
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_skill_retrieval_log.py -q
      - python3 scripts/docs_guard.py --strict
    rollback_point: 关闭 strict_user 并恢复 compat
```
