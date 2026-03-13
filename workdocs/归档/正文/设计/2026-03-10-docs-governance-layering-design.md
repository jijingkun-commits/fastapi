# 文档分层治理与信息架构收敛设计说明

> 文档版本：v1.1
> 更新时间：2026-03-10
> 设计状态：`approved`
> 关联方案：`workdocs/归档/正文/设计/2026-03-08-doc-single-source-dynamic-governance-design.md`

## 0. 结论先行

- 本方案冻结为**三层文档治理**：`docs/` 只放长期有效、给人读的真理源；`workdocs/` 只放需求/方案/任务拆解/评审等过程文档；`.artifacts/` 只放运行态与自动生成产物。本轮实施定义为 `Phase 1`：先迁真实运行态，`task_split` 机器契约与过程报告 JSON 先保留迁移期兼容路径，`Phase 2` 再整体迁出。
- `docs/内部参考/` 的终局职责收敛为**长期有效的内部知识**，只保留 `决策记录 / 专题设计 / 资料库` 三类；本轮先冻结方向与主导航边界，迁移期旧过程路径由 `Phase 2` 继续收口。
- 导航冻结为**主导航只覆盖稳定文档**：`docs/README.md` + `docs/SUMMARY.md` 仅服务长期有效文档；过程文档不再逐条挂进主导航。
- “单一真理源”冻结为：**同一主题只允许一份当前态文档**。设计推导、计划、评审、验证都进入过程层，不再和当前态文档并存抢口径。
- 版本策略冻结为：**未上线前不做文档版本化**，禁止在稳定区继续新增 `v2/v3/最新版/日期补丁` 这类文件名。
- 迁移策略冻结为：**先止血、再搬运、后收口**。先阻断新污染，再迁移运行态和过程文档，最后重写导航与目录说明。

## 0.0 分阶段交付说明

- 本次交付冻结为 `Phase 1`：主导航只暴露稳定区、真实运行态迁出 `docs/`、旧过程路径转为迁移期兼容入口。
- 历史设计目录已迁到 `workdocs/归档/正文/设计/`；过程正文统一进入 `workdocs/归档/正文/`；`task_split` 下的 `_active_task.json`、`vk_cards.json`、`preflight_status.json`、`consumption_report.json` 等机器契约/过程报告 JSON 统一进入 `workdocs/任务拆解/`。
- `Phase 2` 再把上述机器契约与过程报告迁到 `workdocs/**`，并同步改造 `jjk-cardrun`、`wt-flow`、`coder4_*` 的读取根目录。

## 0.1 最佳实践依据

| 来源 | 吸收结论 | 落地决策 |
|---|---|---|
| [Diátaxis](https://diataxis.fr/start-here/) | 不同类型文档不要混写 | 稳定文档与过程文档彻底分层 |
| [Google: Organizing large documents](https://developers.google.com/tech-writing/two/large-docs) | 大文档需要清晰导航和渐进披露 | 主导航只保留稳定区，过程区不全量展开 |
| [Google: Documentation Best Practices](https://google.github.io/styleguide/docguide/best_practices.html) | 小而准的文档优于大而乱的文档堆 | 删除重复主题，禁止稳定区继续堆日期补丁 |
| [Write the Docs: Docs as Code](https://www.writethedocs.org/guide/docs-as-code.html) | 文档要跟代码一样纳入评审与门禁 | 目录角色、导航、命名全部纳入守卫 |
| [Docusaurus: Versioning](https://docusaurus.io/docs/next/versioning) | 多数项目并不需要版本化 | 未上线阶段明确禁止文档版本化 |

## 1. scope_contract

- 目标:
  - 把当前文档体系从“稳定内容 + 过程材料 + 运行态文件混住”收敛为职责明确的三层结构。
  - 缩短“找到当前口径”的路径，让读者判断一件事时最多只需要进入一个稳定入口。
  - 把 `docs/内部参考` 从“资料仓 + 过程仓 + 状态仓”收口成“长期内部知识仓”。
- 范围:
  - `docs/README.md`
  - `docs/SUMMARY.md`
  - `docs/内部参考/**`
  - `workdocs/归档/正文/设计/**`
  - 新增目录：`workdocs/**`、`.artifacts/**`
  - 守卫与规则：`scripts/docs_guard.py`、`scripts/check_doc_sync.sh`、`.cursor/rules/doc_sync.mdc`
- 边界:
  - 本轮不重写所有历史文档正文，只做职责分层和入口收口。
  - 本轮不引入新的文档站点工具或复杂前端展示层。
  - 本轮不做多版本文档体系，不为历史版本保留并行稳定目录。
  - 本轮不改变产品/API/架构事实本身，只调整文档的归档位置与治理约束。
- 成功标准:
  - `docs/` 稳定区与主导航不再出现 `.state/.jsonl/.lock` 等真实运行态文件；迁移期 `task_split` 契约/报告 JSON 按 `Phase 1` 兼容口径管理。
  - `docs/SUMMARY.md` 只覆盖稳定文档，稳定文档导航覆盖率达到 `100%`。
- 新增主题不再同时出现在 `workdocs/设计/`、`workdocs/归档/正文/`、稳定文档三个位置表达“当前态”。
  - `docs/内部参考` 的终局方向冻结为长期内部知识；迁移期旧过程路径不再进入主导航，并由 `Phase 2` 继续迁出。

## 2. product_contract（PRD-Lite）

- target_users:
  - 仓库主维护者
  - 新加入的开发者 / AI 协作者
  - 评审与验收人员
- core_scenarios:
  - 快速找到“当前到底以哪份文档为准”
  - 记录需求/设计/任务拆解时不污染主文档
  - 查历史决策时进入内部参考，而不是在稳定区翻过程痕迹
  - 自动化执行产生的状态文件不再干扰文档阅读
- business_goals（含可量化 KPI）:
  - `stable_doc_navigation_coverage = 100%`
  - `runtime_artifact_file_count_under_docs = 0`
  - `new_topic_current_source_count = 1`
  - `reader_current_truth_hops <= 1`
  - `stable_zone_versioned_filename_count = 0`
- non_goals:
  - 不在本轮把所有旧文档逐字重写成 Diátaxis 四象限
  - 不在本轮建设对外官网或版本化文档门户
  - 不保留“稳定区也能放过程文档”的弹性口径
  - 不在本轮直接迁移 `task_split` 机器契约 / 过程报告 JSON；该项留待 `Phase 2`
- acceptance_gates:
  - `DG-AC-01`：稳定区只保留给人读的长期文档
  - `DG-AC-02`：新增过程文档统一进入 `workdocs/`，旧 `docs/**` 过程路径仅保留迁移期兼容入口
  - `DG-AC-03`：真实运行态统一进入 `.artifacts/`
  - `DG-AC-04`：`docs/README.md` 与 `docs/SUMMARY.md` 只导航稳定区
  - `DG-AC-05`：`docs/内部参考/` 的终局方向冻结为长期有效内部知识，`task_split` 兼容路径留待 `Phase 2` 收口
  - `DG-AC-06`：未上线阶段禁止文档版本化与稳定区 `v2/v3` 命名
- release_constraints:
  - `DOC_STABLE_PROCESS_SPLIT=true`
  - `DOC_RUNTIME_OUTSIDE_DOCS=true`
  - `DOC_INTERNAL_REF_LONG_LIVED_ONLY=true`
  - `DOC_STABLE_NAV_ONLY=true`
  - `DOC_TOPIC_SINGLE_SOURCE=true`
  - `DOC_VERSIONING_DISABLED=true`

## 3. architecture_contract

### 3.1 模块边界与职责

| 模块 | 职责 | 典型内容 |
|---|---|---|
| 稳定文档层 | 表达当前有效事实 | 产品文档、开发文档、API 文档、长期内部知识 |
| 过程文档层 | 沉淀需求、设计、任务拆解与过程证据 | `workdocs/需求`、`workdocs/设计`、`workdocs/任务拆解`、`workdocs/归档` |
| 运行态产物层 | 保存机器状态与自动化输出 | `.artifacts/runs`、`.artifacts/states`、`.artifacts/generated` |
| 导航层 | 提供稳定区入口 | `docs/README.md`、`docs/SUMMARY.md` |
| 门禁层 | 检查角色、命名、污染与漂移 | `scripts/docs_guard.py`、`scripts/check_doc_sync.sh` |

### 3.2 端到端数据流

1. 新需求先进入 `workdocs/需求/`。
2. 设计冻结进入 `workdocs/设计/`，实施与拆解进入 `workdocs/任务拆解/`。
3. 代码落地后，只把最终稳定结论吸收入 `docs/` 对应真理源。
4. 真实运行态产生的 `json/jsonl/lock/.state` 一律落入 `.artifacts/`；迁移期 `task_split` 契约/报告 JSON 暂保留在旧过程路径，`Phase 2` 再统一迁出。
5. `docs/README.md` 与 `docs/SUMMARY.md` 只暴露稳定区入口，不暴露过程明细。

### 3.3 状态生命周期

- `draft`：尚未冻结的内容，只能在 `workdocs/`。
- `active-process`：正在执行的需求、设计、任务拆解、评审、验证，优先留在 `workdocs/`；迁移期旧过程路径仅作兼容入口。
- `absorbed`：已转化为当前事实的内容，被吸收入 `docs/` 真理源。
- `archived`：只为追溯保留的旧过程材料，继续留在 `workdocs/` 或 `docs/archive/`。
- `ephemeral`：自动执行状态、锁文件、生成结果，留在 `.artifacts/`，可定期清理。

### 3.4 异常语义与降级策略

- 若无法判断某份文档属于稳定区还是过程区，默认先放 `workdocs/`，待事实冻结后再提升到 `docs/`。
- 若同一主题发现多个“当前态”入口，保留一份稳定真理源，其余改为过程证据或归档。
- 若目录迁移导致短期断链，允许在原路径保留极薄入口页或索引说明，但不得继续追加正文。
- 若守卫与存量债务冲突，允许受控 allowlist 短时放行，但必须写明过期清理对象。

### 3.5 契约源唯一化

- 单一契约源冻结为：**目录角色即契约源**。
- 角色判定只依赖路径与目录职责，不再额外维护第二套“这份文件到底算什么”的平行口径。
- 具体冻结规则：
  - `docs/` = 稳定文档
  - `workdocs/` = 过程文档
  - `.artifacts/` = 运行态/生成物

### 3.6 回放归一字段

- 结构化治理结果的 canonical 字段冻结为：`doc_role`。
- 无论来自守卫脚本、巡检脚本还是迁移清单，统一输出 `doc_role=stable|process|artifact|archive`。
- 历史字段若存在 `doc_type/category/layer`，执行“读旧写新”：读时兼容，写时只写 `doc_role`。

## 4. 最终方案

### 4.1 目标目录

```text
/docs
  稳定真理源（只给人读）
/workdocs
  过程文档（需求/方案/任务拆解/评审/验证）
/.artifacts
  运行态与生成物
```

### 4.2 关键决策

1. `docs/` 不再承担“什么都放”的仓库角色，只保留稳定文档。
2. 历史设计与历史需求/实施计划统一归档到 `workdocs/归档/正文/`，不再双轨并存。
3. `task_split` 机器契约、过程报告与正文统一收口到 `workdocs/任务拆解/`。
4. `docs/内部参考/` 收敛为长期知识，不再承载当前执行态。
5. `json/jsonl/lock/.state` 一律移出 `docs/`，进入 `.artifacts/`。
6. 未上线阶段明确不做文档版本化，不再在稳定区保留 `v2/v3` 命名演进。

### 4.3 与现有 `2026-03-08` 方案的关系

- 保留：`主文档只表达当前态`、`过程文档留在过程层`、`触达即融合` 这些规则继续有效。
- 新增：本方案把治理粒度从“正文更新规则”上提到“目录信息架构与状态归属”。
- 取舍：不覆盖旧方案的正文融合规则，而是为它补上“文件应该放哪儿”的上位约束。

## 5. 决策权衡（仅放弃原因）

- 放弃路径：继续保留 `docs/` 单目录承载稳定文档、过程文档和运行态文件。
  - 放弃原因：读者无法快速判断当前口径，目录会持续膨胀，守卫难以做角色化治理。
- 放弃路径：只改 `README/SUMMARY`，不改目录归属。
  - 放弃原因：这是导航补丁，不是根因修复；过程与运行态仍会继续污染稳定区。
- 放弃路径：直接上多版本文档体系。
  - 放弃原因：项目尚未上线，版本化只会增加维护成本和目录复杂度。
- 放弃路径：再维护一份额外的文档角色清单总表作为人工真理源。
  - 放弃原因：会引入第二套契约源，和“目录角色即契约源”冲突。

## 6. requirement_seeds

| design_item | fr_id | trigger | input_contract | output_contract | failure_semantics | observability_fields | rollback_anchor | acceptance_cmd_ref |
|---|---|---|---|---|---|---|---|---|
| D-01-stable-process-split | FR-01 | 新增或迁移文档 | `file_path`,`doc_role` | 稳定/过程角色唯一归属 | 角色无法确定时默认降到 `process`，禁止进入稳定区 | `file_path`,`doc_role`,`reason` | `DOC_STABLE_PROCESS_SPLIT=false` | `python3 scripts/docs_guard.py --strict` |
| D-02-runtime-outside-docs | FR-02 | 生成运行态文件，或 `docs_guard` 扫描 `docs/**` | `file_path`,`extension`,`file_name` | 真实运行态进入 `.artifacts/`；迁移期 `task_split` JSON 需给出兼容判定 | 真实运行态命中 `docs/**` 直接阻断；迁移期仅允许 `task_split` 兼容 JSON 留在旧路径 | `file_path`,`extension`,`file_name`,`compatibility_decision` | `DOC_RUNTIME_OUTSIDE_DOCS=false` | `python3 scripts/docs_guard.py --strict` |
| D-03-stable-nav-only | FR-03 | 更新导航入口 | `doc_role`,`path`,`title` | `README/SUMMARY` 仅纳入稳定区 | 过程文档误入主导航时阻断 | `path`,`doc_role`,`nav_section` | `DOC_STABLE_NAV_ONLY=false` | `python3 scripts/docs_guard.py --strict` |
| D-04-topic-single-source | FR-04 | 同主题文档新增 | `topic`,`doc_role` | 同主题仅一份当前态真理源 | 发现多个当前态时阻断 | `topic`,`current_source_count` | `DOC_TOPIC_SINGLE_SOURCE=false` | `rg -n "chat-multi-session-concurrency|langgraph-v1-adoption|workflow-gate-retirement" docs workdocs` |
| D-05-internal-ref-reduce | FR-05 | 调整 `内部参考` 目录 | `file_path`,`content_role` | `内部参考` 终局只保留长期内部知识；迁移期旧 `task_split` 路径不再扩散 | 新增当前迭代过程文件继续留在 `docs/内部参考`（不含迁移期 `task_split` 兼容路径）时阻断 | `file_path`,`content_role` | `DOC_INTERNAL_REF_LONG_LIVED_ONLY=false` | `python3 scripts/docs_guard.py --strict` |
| D-06-no-versioning-prelaunch | FR-06 | 稳定区新增文件 | `file_name`,`doc_role` | 稳定区禁用 `v2/v3/日期补丁` | 命中版本化命名直接阻断 | `file_name`,`doc_role` | `DOC_VERSIONING_DISABLED=false` | `find docs -type f | rg '(_v[0-9]+|[-_ ]v[0-9]+|\\d{4}-\\d{2}-\\d{2})'` |

## 7. implementation_seeds

| task_id | blocked_by | file_paths | symbols | change_type |
|---|---|---|---|---|
| T01 | [] | `docs/README.md`,`docs/SUMMARY.md` | `stable_navigation`,`role_entrypoints` | modify |
| T02 | [T01] | `docs/内部参考/**`,`workdocs/需求/**`,`workdocs/设计/**`,`workdocs/任务拆解/**` | `process_layer_rehome`,`internal_reference_reduction` | refactor |
| T03 | [T02] | `.artifacts/runs/**`,`.artifacts/states/**`,`.artifacts/generated/**`,`workdocs/任务拆解/**` | `runtime_artifact_rehome`,`state_file_cleanup` | refactor |
| T04 | [T01,T02,T03] | `scripts/docs_guard.py`,`.cursor/rules/doc_sync.mdc` | `doc_role_guard`,`stable_nav_guard`,`runtime_pollution_guard` | modify |
| T05 | [T02,T03,T04] | `docs/开发文档/流程与工具/文档治理基线清单.md`,`docs/开发文档/流程与工具/文档月度校准清单.md` | `governance_checklist_updates` | modify |
| T06 | [T04,T05] | `memory-bank.md` | `docs_governance_decision_record` | modify |

## 8. execution_chain_seed

```yaml
execution_chain_seed:
  preferred_mode: core
  task_key: PP-20260310-docs-governance-layering
  card_seed: [T01, T02, T03, T04, T05, T06]
  execution_contract_hint:
    delivery_mode: staged
    execution_unit: per_task
    commit_policy: single_commit
    stop_boundary: per_task
```

## 9. risk_rollback_contract

| risk_id | 关键风险 | 触发信号 | 回退锚点 | 回退动作 |
|---|---|---|---|---|
| R01 | 目录大搬迁导致历史链接短期失效 | `docs_guard` 断链激增 | `DOC_STABLE_PROCESS_SPLIT` | 先回退目录迁移，只保留入口文档收口与污染阻断 |
| R02 | 稳定/过程边界定义不清，导致团队写错位置 | 新文档持续落错层 | `DOC_TOPIC_SINGLE_SOURCE` | 暂时保留薄入口页 + 强制模板提示，补齐角色说明后再收紧 |
| R03 | 运行态迁出后，脚本仍写旧路径 | 自动化执行报路径错误 | `DOC_RUNTIME_OUTSIDE_DOCS` | 保留读旧写新适配期，逐步切换输出路径 |
| R04 | `内部参考` 收缩过猛，误删长期有效资料入口 | 长期知识检索路径中断 | `DOC_INTERNAL_REF_LONG_LIVED_ONLY` | 暂时保留 `资料迁移索引`，完成映射后再删除旧入口 |

## 10. 推荐实施拆分（四步）

### 第一步：目录结构

先把“东西应该放哪儿”定死，这是根因层。

1. 冻结三层职责：`docs/`、`workdocs/`、`.artifacts/`。
2. 冻结 `docs/内部参考/` 的终局方向为长期有效内部知识；迁移期旧过程路径由 `Phase 2` 收口。
3. 明确 `docs/plans`、`docs/内部参考/迭代需求`、`docs/内部参考/任务拆解` 属于过程层，而不是稳定层。

为什么第一步必须先做：

- 如果目录角色没定，后面的格式规范和同步门禁都会建立在错误归属上。
- 你现在最乱的根因不是“写得不统一”，而是“不同生命周期的文件放在了一起”。

### 第二步：内容格式

目录定完后，再定“每一层怎么写”。

1. 稳定区文档统一成当前态写法，不再接受 `v2/v3/日期补丁/实现进展` 追加模式。
2. 过程区文档统一模板：需求、方案、任务拆解、评审、验证各自一套固定结构。
3. 守卫脚本统一输出 `doc_role`，把“这份文件属于哪层”变成结构化结果。

为什么第二步排在同步前：

- 如果还没冻结格式，直接上同步规则，只会把旧混乱放大成新门禁。
- 先定格式，才能知道“哪些变更算同步，哪些只是追加噪音”。

### 第三步：内容同步

在结构和格式稳定后，再上同步与门禁。

1. `docs/README.md` 与 `docs/SUMMARY.md` 只导航稳定区。
2. `docs_guard` 检查稳定区污染、命名违规、导航缺口、角色越界。
3. `check_doc_sync` 只要求代码变更同步到对应稳定真理源，不再把过程文档当成功替代。

为什么第三步才做：

- 同步规则本质上是在执行前两步的约束，不是先导条件。
- 先同步后分层，会把错误目录关系永久化。

### 第四步：迁移收口

最后才做存量搬运和旧入口清理。

1. 先止血：阻断新过程文件、新运行态文件继续进入 `docs/`。
2. 再搬运：把存量过程文档迁到 `workdocs/`，把运行态迁到 `.artifacts/`。
3. 再收口：重写 `docs/README.md`、`docs/SUMMARY.md`、目录说明。
4. 最后归档：对旧入口保留短期索引说明，确认稳定后删除。

一句话顺序：

- **目录结构 → 内容格式 → 内容同步 → 迁移收口**

如果反过来做，最常见结果就是：

- 先修导航，结果导航继续引用脏目录；
- 先做同步，结果门禁帮你固化了旧屎山；
- 只做搬运，不定格式，最后只是把乱文件换个地方继续乱。

## 11. 设计冻结回执（机读）

```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 4
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 6
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```

## 12. clarify_handoff_contract（机读）

```yaml
clarify_handoff_contract:
  version: v2
  topic: 文档分层治理与信息架构收敛
  design_source: workdocs/归档/正文/设计/2026-03-10-docs-governance-layering-design.md
  handoff_ready: true
  required:
    product_contract_summary:
      target_users: [仓库主维护者, 新加入开发者, AI协作者, 评审与验收人员]
      core_scenarios:
        - 快速找到当前真理源
        - 过程文档与稳定文档分家
        - 运行态文件不再污染 docs
        - 内部参考终局方向冻结为长期有效知识，迁移期兼容路径后续收口
      business_goal_metrics:
        - stable_doc_navigation_coverage=100%
        - runtime_artifact_file_count_under_docs=0
        - new_topic_current_source_count=1
        - reader_current_truth_hops<=1
        - stable_zone_versioned_filename_count=0
      non_goals:
        - 不建设版本化文档站点
        - 不一次性重写全部旧文档正文
        - 不保留稳定区可混放过程文档的弹性口径
      acceptance_gates:
        - DG-AC-01
        - DG-AC-02
        - DG-AC-03
        - DG-AC-04
        - DG-AC-05
        - DG-AC-06
    requirement_seeds:
      - design_item: D-01-stable-process-split
        fr_id: FR-01
        trigger: 新增或迁移文档
        input_contract:
          required_fields: [file_path, doc_role]
        output_contract:
          required_fields: [canonical_doc_role, target_directory]
        failure_semantics: role_undecided -> process_only
        observability_fields: [file_path, doc_role, reason]
        rollback_anchor: DOC_STABLE_PROCESS_SPLIT=false
        acceptance_cmd_ref: python3 scripts/docs_guard.py --strict
      - design_item: D-02-runtime-outside-docs
        fr_id: FR-02
        trigger: 生成运行态文件，或 docs_guard 扫描 docs/**
        input_contract:
          required_fields: [file_path, extension, file_name]
        output_contract:
          required_fields: [artifact_path, compatibility_decision]
        failure_semantics: runtime_artifact_under_docs -> blocked; phase1_task_split_json -> compatibility_only
        observability_fields: [file_path, extension, file_name, compatibility_decision]
        rollback_anchor: DOC_RUNTIME_OUTSIDE_DOCS=false
        acceptance_cmd_ref: python3 scripts/docs_guard.py --strict
      - design_item: D-03-stable-nav-only
        fr_id: FR-03
        trigger: 更新导航入口
        input_contract:
          required_fields: [doc_role, path, title]
        output_contract:
          required_fields: [stable_nav_entry]
        failure_semantics: process_doc_in_summary -> blocked
        observability_fields: [path, doc_role, nav_section]
        rollback_anchor: DOC_STABLE_NAV_ONLY=false
        acceptance_cmd_ref: python3 scripts/docs_guard.py --strict
      - design_item: D-04-topic-single-source
        fr_id: FR-04
        trigger: 同主题文档新增或迁移
        input_contract:
          required_fields: [topic, doc_role]
        output_contract:
          required_fields: [current_source_path]
        failure_semantics: multi_current_source -> blocked
        observability_fields: [topic, current_source_count]
        rollback_anchor: DOC_TOPIC_SINGLE_SOURCE=false
        acceptance_cmd_ref: rg -n "chat-multi-session-concurrency|langgraph-v1-adoption|workflow-gate-retirement" docs workdocs
      - design_item: D-05-internal-ref-reduce
        fr_id: FR-05
        trigger: 调整内部参考目录
        input_contract:
          required_fields: [file_path, content_role]
        output_contract:
          required_fields: [internal_reference_long_lived_only]
        failure_semantics: new_active_process_under_internal_ref -> blocked; phase1_task_split_path -> compatibility_only
        observability_fields: [file_path, content_role]
        rollback_anchor: DOC_INTERNAL_REF_LONG_LIVED_ONLY=false
        acceptance_cmd_ref: python3 scripts/docs_guard.py --strict
      - design_item: D-06-no-versioning-prelaunch
        fr_id: FR-06
        trigger: 稳定区新增文件
        input_contract:
          required_fields: [file_name, doc_role]
        output_contract:
          required_fields: [stable_name_valid]
        failure_semantics: versioned_filename_in_stable_zone -> blocked
        observability_fields: [file_name, doc_role]
        rollback_anchor: DOC_VERSIONING_DISABLED=false
        acceptance_cmd_ref: find docs -type f | rg '(_v[0-9]+|[-_ ]v[0-9]+|\d{4}-\d{2}-\d{2})'
    implementation_seeds:
      - task_id: T01
        feature_id: DOC-IA-01
        blocked_by: []
        file_paths:
          - docs/README.md
          - docs/SUMMARY.md
        symbols:
          - stable_navigation
          - role_entrypoints
        change_type: modify
      - task_id: T02
        feature_id: DOC-IA-02
        blocked_by: [T01]
        file_paths:
          - docs/内部参考
          - workdocs/需求
          - workdocs/设计
          - workdocs/任务拆解
        symbols:
          - process_layer_rehome
          - internal_reference_reduction
        change_type: refactor
      - task_id: T03
        feature_id: DOC-IA-03
        blocked_by: [T02]
        file_paths:
          - .artifacts/runs
          - .artifacts/states
          - .artifacts/generated
          - docs/内部参考/任务拆解
        symbols:
          - runtime_artifact_rehome
          - state_file_cleanup
        change_type: refactor
      - task_id: T04
        feature_id: DOC-IA-04
        blocked_by: [T01, T02, T03]
        file_paths:
          - scripts/docs_guard.py
          - .cursor/rules/doc_sync.mdc
        symbols:
          - doc_role_guard
          - stable_nav_guard
          - runtime_pollution_guard
        change_type: modify
      - task_id: T05
        feature_id: DOC-IA-05
        blocked_by: [T02, T03, T04]
        file_paths:
          - docs/开发文档/流程与工具/文档治理基线清单.md
          - docs/开发文档/流程与工具/文档月度校准清单.md
        symbols:
          - governance_checklist_updates
        change_type: modify
      - task_id: T06
        feature_id: DOC-IA-06
        blocked_by: [T04, T05]
        file_paths:
          - memory-bank.md
        symbols:
          - docs_governance_decision_record
        change_type: modify
    execution_chain_seed:
      preferred_mode: core
      task_key: PP-20260310-docs-governance-layering
      card_seed: [T01, T02, T03, T04, T05, T06]
      execution_contract_hint:
        delivery_mode: staged
        execution_unit: per_task
        commit_policy: single_commit
        stop_boundary: per_task
    alignment_contract:
      strict_match: true
      requirement_seed_ids:
        - D-01-stable-process-split
        - D-02-runtime-outside-docs
        - D-03-stable-nav-only
        - D-04-topic-single-source
        - D-05-internal-ref-reduce
        - D-06-no-versioning-prelaunch
      implementation_task_ids: [T01, T02, T03, T04, T05, T06]
      card_seed_ids: [T01, T02, T03, T04, T05, T06]
  extended:
    observability_hints:
      - 所有守卫脚本统一输出 doc_role
      - 稳定区污染项单独输出 summary.pollution_count
      - 迁移阶段输出 broken_link_count 与 orphan_stable_doc_count
    risk_counterexample_map:
      - risk_id: R01
        counterexample: 目录搬迁后稳定文档断链
        verify_cmd: python3 scripts/docs_guard.py --strict
      - risk_id: R02
        counterexample: 新文档继续写进 docs/内部参考/迭代需求
        verify_cmd: find docs/内部参考 -type f | rg 'implementation_plan|requirements|vk_cards|preflight_status'
      - risk_id: R03
        counterexample: 自动化脚本继续把 lock/state 写进 docs
        verify_cmd: find docs -type f | rg '\.(jsonl|lock)$|/\.state/'
      - risk_id: R04
        counterexample: 稳定区新增 v2/v3/日期补丁文件名
        verify_cmd: find docs -type f | rg '(_v[0-9]+|[-_ ]v[0-9]+|\d{4}-\d{2}-\d{2})'
    assumptions:
      - 项目当前未上线，可以优先优化结构，不必为了兼容旧路径保留长期双轨
      - docs/plans 与 docs/内部参考/迭代需求 都属于过程层，而不是稳定真理源
      - 现有 2026-03-08 文档治理方案继续保留正文融合规则，本方案只补充目录分层约束
```

## 13. 一致性自检（机读）

```yaml
clarify_consistency_check:
  clarify_phase: approval
  current_round: 2
  question_mode: single
  open_questions_count: 0
  product_contract_ready: true
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  fail_fast_codes: []
```

## 14. 审批记录
```yaml
approval_record:
  design_approved: true
  approved_at: 2026-03-10T18:42:44+08:00
  approved_round: v1-freeze-2026-03-10
  approval_evidence: 用户明确触发 jjk-plan
  approval_mode: approved
  go_no_go: GO
```

补充镜像（供 `/jjk-plan` 校验脚本读取）：
- design_approved: true
- approved_at: 2026-03-10T18:42:44+08:00
- approved_round: v1-freeze-2026-03-10
- approval_evidence: 用户明确触发 jjk-plan
