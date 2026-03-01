---
description: 正式规划：默认产出专题前缀需求与技术方案，可选生成并行 card_seed
---

> 参考规则: @dual-database

# 规划工作流 (Planning Workflow)

将需求转化为正式文档，为后续开发提供“真理来源”。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 只需要需求与技术方案（不拆卡） | `/jjk-plan` ✅ |
| 需要后续并行拆解与看板落卡 | `/jjk-plan`（建议 `parallel`）后接 `/jjk-vkplan` ✅ |
| 只想快速澄清理解 | `/jjk-clarify` |
| 一站式从需求到交付 | `/jjk-feature` |

> **与 `/jjk-clarify` 的区别**: `/jjk-plan` 会产出 `<topic>_requirements.md` 与 `<topic>_implementation_plan.md`；`/jjk-clarify` 只做问答确认。

> **两层产物强制**: `/jjk-plan` 的完成态不是“有需求文档”，而是同时具备 WHAT（`requirements`）+ 工单级 HOW（`implementation_plan`）。

---

## 与 Superpowers / OMX 的分工（强制）

`/jjk-plan` 与插件是互补关系，不是替代关系：

1. `brainstorming`：负责澄清、方案比较、设计审批与 design 文档产出。
2. `writing-plans`：负责把设计拆成 2-5 分钟粒度的执行步骤。
3. `team`（OMX）：负责并行运行时编排（worker、状态、证据）。
4. `/jjk-plan`：负责项目内“需求/技术方案/机读契约”主产物与下游衔接。

约束：

1. 禁止在 `/jjk-plan` 里复制 `brainstorming` / `writing-plans` 的完整正文。
2. 插件可用时优先调用；插件不可用时必须显式 fallback，不得静默降级。
3. `/jjk-plan` 只维护“命令契约与产物桥接”，不重写插件方法论。

---

## 输入模式（新增）

### 0) Superpowers 产物对齐桥接（强制）

目标：让 Superpowers 产物“跟着 `jjk-*` 指令走”，而不是形成第二套孤立产物。

当本轮已使用 `brainstorming` / `writing-plans` 时，`/jjk-plan` 必须执行：

1. 从 `docs/plans/` 读取同主题设计与计划输入，并在 `<topic>_implementation_plan.md` 记录“输入来源清单”。
2. 把上游结论映射到本项目主产物：
   - `docs/内部参考/迭代需求/<topic>_requirements.md`
   - `docs/内部参考/迭代需求/<topic>_implementation_plan.md`
3. 若上游文档缺失或主题无法对齐，输出标记 `SUPERPOWERS_ARTIFACT_UNALIGNED`，并给出对齐修复步骤后再继续。
4. 下游执行链（`/jjk-vkplan`、`/jjk-vktodo`、`/jjk-imp-ws`）仅消费本项目主产物，不直接消费未经桥接的上游原文。

### 0.1) 设计审批门禁（强制）

`/jjk-plan` 在开始规划前，必须先确认“设计已获审批”：

1. 优先读取同主题 design：`docs/plans/YYYY-MM-DD-<topic>-design.md`。
2. design 中必须存在审批记录（至少包含：`design_approved: true` 与审批时间/轮次说明）。
3. 若未找到审批记录，`FAIL_FAST` 并输出标记 `DESIGN_APPROVAL_REQUIRED`，回退到 `/jjk-clarify`。
4. 若上游来自 `BRAINSTORM_UNAVAILABLE_FALLBACK`，需在本轮明确人工确认后再继续，并标记 `DESIGN_APPROVAL_FALLBACK_ACK`。

### 0.2) 执行意图门禁（新增，强制）

目标：防止“规划指令”被误扩展为“自动实施”。

规则：

1. `/jjk-plan` 默认模式为 `plan-only`：只产出 WHAT + HOW 文档与机读契约，不自动触发 `/jjk-vkplan`、`/jjk-vktodo`、`/jjk-imp`。
2. 用户若在当前轮未明确“执行/落地/开始实现”，必须停在规划输出，不进入实施链路。
3. 若用户仅回复“好的/继续”等弱确认词，输出标记 `PLAN_EXECUTION_INTENT_REQUIRED`，并给出下一步可选命令。
4. 仅当用户显式要求进入执行链时，才允许把 `next_step` 指向 `/jjk-vkplan` 或 `/jjk-imp`。

### 0.5) 大任务自动启用 Team（强制判定）

`/jjk-team-plan` 不再作为主入口。`/jjk-plan` 在任务规模较大时自动升级 Team 规划模式。

触发阈值默认复用 `/jjk-clarify` 的“0.5 大任务自动启用 Team”判定，避免双份维护。

补充：若本轮需要并行产出多个 `feature_id` / `card_seed` 分支并汇总裁决，也视为命中 Team 条件。

执行策略：

1. **有 Team 能力时**：自动启用 team 并行收集上下文与备选方案，Leader 汇总为单一 `planning_contract`。
2. **无 Team 能力时**：降级为单代理执行，并在输出标记 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束（新增，轻量）

1. Team 模式下必须启用抽检互审：至少抽检 `20%` 工作项（向上取整，最少 `1` 项）。
2. 每个抽检项必须包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
3. 抽检未通过的工作项不得推进到下一阶段，必须先复核并补齐证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。
3. 无论是否 Team，最终只允许产出一份主计划，禁止多个并行主计划同时生效。

### 0.6) 模板来源优先级（跨项目，强制）

为保证“换项目后工程化仍完整”，`/jjk-plan` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_plan_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_plan_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

### 0.7) WHAT + 工单级 HOW（强制）

为避免“方向正确但拆解不够细导致返工”，`/jjk-plan` 必须同时产出两层内容：

1. WHAT：`<topic>_requirements.md`（目标、边界、验收）。
2. HOW：`<topic>_implementation_plan.md`（可直接执行的工单级拆解）。

工单级 HOW 的最低标准（缺一不可）：

1. 每个 `feature_id` 至少绑定 1 条可执行 `task_id`。
2. 每条 `task_id` 必须包含：
   - `phase`
   - `file_paths`（文件级）
   - `symbols`（函数/类/模块级）
   - `change_type`（新增/修改/删除）
   - `acceptance_cmds`（可执行命令）
   - `rollback_point`（失败回退点）
   - `pr_id`（归属 PR 编号）
3. 若仅有“架构思路/阶段标题”而无上述字段，必须标记 `HOW_NOT_ACTIONABLE`，并继续细化，不得宣称“可直接实施”。
4. 文档末尾必须给出机读结论块：
   - `implementation_ready: true|false`
   - `blocked_by: []`
   - `next_step: /jjk-imp | /jjk-vkplan | /jjk-plan`

### 参数写法（新增）

支持“长参数”和“短参数”两种写法，语义完全一致：

1. `parallel` = `-p`
2. `hydrate` = `-h`

等价示例：

1. `/jjk-plan parallel hydrate`
2. `/jjk-plan -p -h`
3. `/jjk-plan -ph`
4. `/jjk-plan -hp`

解析规则：

1. `-p` 只表示“产出拆解种子”，不直接决定执行并行度。
2. `-h` 只表示“启用历史沉淀归一化”。
3. 若同时出现（任意顺序），按 `parallel + hydrate` 处理。
4. 若出现未知短参数，直接报错并提示可用参数：`-p`、`-h`。

### 命名对齐要求（新增）

`<topic>` 默认与任务拆解目录 `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/` 的 `<主题>` 对齐，优先使用中文主题短语。

1. 新增规划文档默认使用中文主题前缀：`<主题>_requirements.md`、`<主题>_implementation_plan.md`。
2. 若已存在同主题任务拆解目录，命名必须复用同一 `<主题>` 语义，不允许漂移。
3. `task_key` 的英文机读标识独立维护，不强制写入文件名前缀。

### 1) core 模式（默认）

`/jjk-plan` 或 `/jjk-plan core`

- 产出：`<topic>_requirements.md` + `<topic>_implementation_plan.md`
- 不强制产出 `card_seed`
- 适用于单人/单 AI 主导规划，改动范围可小可大（含跨模块/全局架构）
- 默认无需并行落卡；若后续需要多人并行再切换 `/jjk-plan parallel` + `/jjk-vkplan`
- 若属于全局改造，`<topic>_implementation_plan.md` 必须显式包含：分阶段路线图、跨模块依赖矩阵、回滚与观测方案
- core 模式同样必须满足“工单级 HOW”标准，不得仅输出架构叙述

### 2) parallel 模式（并行规划）

`/jjk-plan parallel`

- 产出：`<topic>_requirements.md` + `<topic>_implementation_plan.md` + 最小 `card_seed`
- 要求给出 `task_key`（后续卡片前缀）
- 适用于多人/多 AI/多 worktree 拆解准备
- 并行拆解与落卡前准备由后续 `/jjk-vkplan` 承接
- 并行模式的每个 `card_seed` 必须能追溯到至少 1 条 `task_id`（禁止空壳 seed）

### 3) hydrate 模式（旧文档沉淀注入）

`/jjk-plan hydrate` 或 `/jjk-plan parallel hydrate`

- 适用：已有大量历史方案、`output/**` 分析、专题计划，但执行链已跑偏或信息分散。
- 目标：把现有沉淀“压缩进”新的 `requirements + implementation_plan`，避免后续 `/jjk-vkplan` 丢信息。
- 约束：`hydrate` 只允许重组与对齐，不新增“第四类主文档”。

`hydrate` 时必须显式列出输入来源（建议写入 implementation plan 的“输入来源清单”）：

1. 总控/波次：`openclaw全量迁移_implementation_plan.md`、`迁移执行波次_implementation_plan.md`
2. 专题计划：P1~P6 对应 implementation 文档
3. 分析沉淀：`output/openclaw源码解析/**`（仅抽取与当前功能点直接相关的证据）
4. 历史并行拆解：`docs/内部参考/任务拆解/**`（仅复用可验证的结构与门禁，不继承失效口径）

### 4) 参数语义澄清（强制）

1. `parallel` 表示“为 `/jjk-vkplan` 产出拆解种子”，不等于最终一定并行执行。
2. 实际执行并行/串行由 `planning_contract.execution_mode` 决定：
   - `serial`：单卡推进；
   - `parallel`：可并行推进。
3. `hydrate` 表示“输入侧重组模式”：强制先做来源归一化与证据映射，再产出新计划。

### 5) hydrate 覆盖率门禁（强制）

当使用 `/jjk-plan hydrate`（含 `/jjk-plan parallel hydrate`）时，必须在 implementation plan 输出以下机读统计：

1. `source_atoms_total`：输入细节原子总数。
2. `source_atoms_mapped`：已映射到 `feature_id` 的原子数。
3. `source_atoms_unmapped`：未映射原子清单（含 `source_id` 与原因）。
4. `source_conflicts`：冲突条目与裁决结论。

硬门禁：

1. `source_atoms_unmapped` 非空时，计划状态必须标注 `BLOCKED`，不得进入 `/jjk-vkplan`。
2. 不允许以“摘要已覆盖”替代原子级映射。
3. 每个 `feature_id` 必须能反查到至少 1 条来源原子。

### 5.1) hydrate 特性映射闭环（强制，无新增参数）

当使用 `/jjk-plan hydrate`（含 `/jjk-plan -h`、`/jjk-plan -p -h`）时，除“原子级覆盖”外，还必须做 `FP -> implementation feature -> card` 闭环映射：

1. 从 `openclaw迁移_输入归一化草案.md` 的 `D. Feature Packet Draft` 提取 `fp_registry`（例如 `FP-01..FP-11`）。
2. 在 `<topic>_implementation_plan.md` 输出机读块 `hydrate_feature_linkage`，至少包含：
   - `fp_registry`
   - `fp_to_impl_feature_map`（每个 `FP-xx` 映射到至少 1 个实现 `feature_id`）
   - `fp_unmapped`
3. `fp_unmapped` 非空时，计划状态必须标注 `BLOCKED`，且不得进入 `/jjk-vkplan`。
4. 不允许用“已在叙述中覆盖/语义已包含”替代显式映射；必须可机读回查。
5. 参数维持不变，不新增命令参数；以上校验默认随 `hydrate` 自动生效。

---

## 1. 需求分析 (Requirement Analysis)

**产出**:
1. 迭代级概览：`docs/内部参考/迭代需求/<topic>_requirements.md`
2. 模块级需求（按需）：`docs/产品文档/<模块>需求.md`（仅在新增模块/业务接口变更/跨团队协作需要时产出）

### 索引同步（强制）

当 `/jjk-plan` 新增或重命名 `docs/内部参考/迭代需求/*_requirements.md` 或 `*_implementation_plan.md` 时，必须同步更新：

1. `docs/SUMMARY.md` 的“内部参考 -> 迭代需求”条目（新增可点击链接）。
2. 若已有同名条目，必须校验标题与路径一致，不允许悬挂旧链接。
3. 在 `/jjk-plan` 结束前执行 `python3 scripts/docs_guard.py --strict`；若命中 `summary_missing_doc`，本轮计划视为未完成。

**必须包含**:
1. **用户故事**: 谁？在什么场景？想要做什么？为什么？
2. **验收标准**:
   - 功能性: Happy Path
   - 异常/边界: 断网、非法输入、超长文本
   - 性能/稳定性: 关键路径耗时、重试/超时
3. **非功能需求**: 性能、安全、数据一致性
4. **关联测试**: 预留 TC 编号（便于追溯矩阵）
5. **场景约束**:
   - 业务域任务：结合银行工作场景（如贷款/存款/分行/合规约束）
   - 平台/架构迁移任务：改为运行场景与系统约束（如路由、状态契约、回滚策略）

## 2. 技术方案 (Technical Design)

**产出**: `docs/内部参考/迭代需求/<topic>_implementation_plan.md` (Artifact)

> **唯一产出路径**: `<topic>_implementation_plan.md` 统一放在 `docs/内部参考/迭代需求/`，不再使用仓库根目录路径。

**内容**:
1. **架构变更**: 涉及哪些模块？数据库要改吗？
2. **API 设计**: 接口定义
3. **风险评估**: 哪里容易出 Bug？

### 架构评审必查项

在输出 `docs/内部参考/迭代需求/<topic>_implementation_plan.md` 前，必须补充“架构影响与约束”，至少包含：

1. **模块边界**：策略属于哪个层（Prompt / Workflow / Node / Frontend），是否越层；避免同一决策分散在多个节点重复实现。
2. **状态契约**：关键字段 canonical 定义、来源优先级、生命周期（创建/合并/清理），是否存在别名漂移风险。
3. **路由闭环**：从意图分析到澄清/消歧/确认/执行的收敛路径，是否存在“回到同一追问”的循环风险。
4. **端到端链路**：前端上下文（如 `current_todo_id`）到后端状态注入的时序一致性，是否会在发送前被提前清理。
5. **可测试性**：以上四项是否有对应单测/联测覆盖，缺口需在计划中显式列出。

### 2.0 轻文档边界（强制）

目标保持“3+1”产物边界，不扩散主文档类型：

1. `docs/内部参考/迭代需求/<topic>_requirements.md`
2. `docs/内部参考/迭代需求/<topic>_implementation_plan.md`
3. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/...`（由 `/jjk-vkplan` 产出）
4. 其余仅允许作为“输入来源”被引用，不得升级为新的主计划文档类别。

### 2.A0 测试策略（TDD 前置，推荐）

借鉴 TDD 测试先行理念，在规划阶段为每个 feature_id 预定义测试用例，确保实现有明确的验收锚点。

`<topic>_implementation_plan.md` 推荐包含"测试策略"段：

1. 每个 `feature_id` 至少关联 1 个预期测试用例 ID（`TC-xxx-xx`）
2. 测试用例需明确：输入条件、预期行为、边界场景
3. 关键路径的测试用例应在编码前写好（Red），实现后验证通过（Green）
4. 测试策略段为推荐项，非强制；但涉及 AI 工作流或数据库变更时强烈建议填写

示例：

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_plan_templates.md`（`test_strategy` 段）。  
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_plan_templates.md`。

此段供 `/jjk-imp` 和 `/jjk-test` 消费：
- `/jjk-imp` 读取 `test_first: true` 的 feature，优先编写测试再实现
- `/jjk-test` 读取 `test_cases` 作为用例生成的输入

### 2.A 功能机制包（Feature Packet，必填）

`<topic>_implementation_plan.md` 必须包含“功能机制包总表”，每个功能点至少包含：

1. `feature_id`（建议 `P1-03` / `P2-01` 等稳定编号）
2. 目标与边界（本功能做什么 / 不做什么）
3. 触发条件与状态流转（包括异常分支）
4. 代码锚点（文件 + 函数/类，不允许只写行号）
5. 关键数据结构/契约字段
6. 回滚锚点（开关/降级策略）
7. 验证命令（最小 pytest/API/docs_guard）
8. 来源证据（来自 output 或既有专题文档的精确引用）

补充：每个 `feature_id` 至少给 1 个“最小代码样例”（可伪代码），用于约束实现形态。

### 2.A1 工单级任务包（Implementation Tasks，必填）

`<topic>_implementation_plan.md` 必须包含“任务拆解表”（可 YAML 或表格），用于约束可直接执行的 HOW 粒度。

每条任务至少包含：

1. `task_id`（建议 `T-01` 起）
2. `feature_id`（必须可回查到 2.A 的功能机制包）
3. `phase`
4. `file_paths`
5. `symbols`
6. `change_type`
7. `acceptance_cmds`
8. `rollback_point`

约束：

1. `task_id` 不允许只写“阶段说明”，必须是可执行动作。
2. `acceptance_cmds` 必须是可运行命令，禁止写“人工验证即可”。
3. `file_paths` 为空时，计划状态必须标注 `BLOCKED`。
4. `feature_id` 与 `task_id` 映射不完整时，禁止进入 `/jjk-imp`。

样例见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_plan_templates.md`（`implementation_tasks` 段）。  
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_plan_templates.md`。

### 2.A2 PR 映射契约（新增，必填）

`<topic>_implementation_plan.md` 必须提供 `task_to_pr_mapping`（表格或 YAML），确保“任务拆分”与“PR 粒度”一致。

每条映射至少包含：

1. `task_id`
2. `pr_id`（如 `PR-01`）
3. `pr_branch`（如 `codex/<topic>-<pr_id>`）
4. `pr_subject`（PR 标题摘要）
5. `pr_depends_on`（前置 PR，可空数组）
6. `acceptance_cmds`
7. `rollback_point`

硬约束：

1. 每个 `task_id` 必须且仅能映射 1 个 `pr_id`。
2. `acceptance_cmds` 不允许只写“人工验证”。
3. 缺失映射时必须标记 `PR_MAPPING_MISSING`，并阻断 `/jjk-imp` 与 `/jjk-create-pr`。
4. `pr_depends_on` 必须与 `cards[].depends_on` 语义一致，禁止双轨依赖口径。

### 2.B 与 `/jjk-vkplan` 的机读契约（必填）

`<topic>_implementation_plan.md` 必须在末尾给出 `planning_contract` YAML，供 `/jjk-vkplan` 直接消费。

最小必备字段：

1. `execution_mode`
2. `card_order`
3. `cards[].card_id`
4. `cards[].feature_ids`
5. `cards[].depends_on`
6. `cards[].done_gate`
7. `cards[].acceptance_checks`
8. `cards[].task_mode`
9. `cards[].merge_required`
10. `cards[].evidence_entry`
11. `task_to_pr_mapping[]`

完整样例见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_plan_templates.md`（`planning_contract` 段）。  
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_plan_templates.md`。

说明：

1. 若你要串行执行（自动执行场景），`execution_mode` 必须是 `serial`。
2. `card_id`/`feature_id` 一旦发布，不得在 `/jjk-vkplan` 阶段重命名。
3. `/jjk-vkplan` 只能细化，不能改写 `depends_on` 的硬依赖。
4. 若要启用自动 `inreview -> done`，必须在 `planning_contract` 明确 `auto_done_policy`，禁止执行期临时口头约定。
5. `auto_done_policy=hard_gate` 时，implementation card 自动收口必须满足：`source_chain_loaded=YES`、`feature_ids_matched=YES`、`serial_gate=PASS`、`evidence_binding=YES`、`acceptance_checks` 通过、ledger 追加成功。
6. `/jjk-plan` 只定义契约，不会生成真实看板卡片；若要让 OpenClaw 自动执行，后续仍需 `/jjk-vkplan -> /jjk-vktodo` 完成可执行落卡。
7. 若 implementation plan 中出现 `G-1~G-4`、`全局关卡`、`Gate` 等门禁目标，必须在 `planning_contract.gate_contract` 显式声明 `gate_ids` 与依赖链。
8. `gate_contract.mode=as_cards` 时，Gate 必须以独立卡片进入 `card_order`，禁止只写文档门禁而不出卡。
9. Gate 卡默认 `task_mode=inspection-card`、`merge_required=false`；若某 Gate 需要代码提交，必须单独写明 `merge_required=true` 与验收命令。
10. `gate_ids` 与 `card_order` 不一致时，计划状态必须标注 `BLOCKED`，不得进入 `/jjk-vkplan`。
11. `task_to_pr_mapping` 缺失或不完整时，计划状态必须标注 `BLOCKED`，不得进入 `/jjk-vkplan` 与 `/jjk-create-pr`。

### 2.C Gate 卡片化契约（强制，自动执行场景）

当任务目标是“自动跑完全链路”（尤其包含 `G-1~G-4`）时，`<topic>_implementation_plan.md` 必须满足：

1. Gate 不得仅存在于文字说明，必须实体化到 `planning_contract.cards`。
2. Gate 卡最小字段：`card_id`、`feature_ids`、`depends_on`、`done_gate`、`acceptance_checks`、`evidence_entry`。
3. `acceptance_checks` 必须是可执行命令，不接受“人工判断通过”。

Gate 样例见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_plan_templates.md`（`Gate 卡模板` 段）。  
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_plan_templates.md`。
详细字段校验与硬拦截交由 `/jjk-vkplan` 执行，避免在本命令重复维护。

### 2.1 主从文档机制

当某个子域存在“专项架构重构”且复杂度明显高于主计划时，采用“主计划 + 专项附录”模式：

1. 主计划固定为：`docs/内部参考/迭代需求/<topic>_implementation_plan.md`
2. 专项附录命名：`docs/内部参考/迭代需求/<topic>_<appendix>_implementation_plan.md`
3. 主计划必须新增“文档分层与引用关系”段，明确：
   - 主从关系
   - 执行顺序（先主计划门禁，再专项 phase）
   - 冲突裁决（主计划优先）
4. 专项附录顶部必须声明：
   - 文档定位（归属哪个 WS）
   - 从属关系（从属于主计划）
   - 使用方式（门禁前后顺序）

### 2.2 契约冻结要求（涉及 SSE / 跨端协议时）

若本轮涉及 SSE 或跨端字段契约，主计划必须明确“冻结字段清单”，至少覆盖：

1. `done`：必选 / 可选字段
2. `result`：必选 / 可选字段
3. `interrupt`：必选 / 可选字段

并要求 `/jjk-vkplan` 在 WS 文档中同步“契约 owner + 消费只读方”关系。

### 2.3 并行拆解种子（仅 parallel 模式必填）

仅当命令为 `/jjk-plan parallel` 时，`<topic>_implementation_plan.md` 必须追加“可拆解种子信息”。

最小字段：

1. `task_key`（全局唯一，建议 `PP-YYYYMMDD-主题`）
2. `card_seed`（YAML 或表格）
   - `card_id`
   - `title`
   - `feature_ids`
   - `hard_depends_on`
   - `soft_depends_on`
   - `file_scope`
   - `owner_fields`
   - `check_cmd`
   - `done_gate`

补充规则：

1. `hard_depends_on` 仅用于阻塞依赖；非阻塞引用写入 `soft_depends_on`。
2. `file_scope` 必须可映射到后续 WS 白名单。
3. 未提供 seed 时，`/jjk-vkplan` 可临时补齐，但必须在 `parallel_plan.md` 标注“seed 来源为 vkplan 推导”。

## 3. 与 `/jjk-vkplan` 的关系（澄清）

`/jjk-plan` 与 `/jjk-vkplan` **不是二选一的替代关系**，而是分工关系：

1. `/jjk-plan` 负责“需求与架构正确性”。
2. `/jjk-vkplan` 负责“并行拆包与可执行边界”。
3. 当走 `core` 模式时，可直接 `/jjk-imp`；当走 `parallel` 模式时，推荐 `/jjk-vkplan -> /jjk-vktodo -> /jjk-imp-ws`。

## 4. 信息不丢失要求（新增）

为避免“计划正确但执行跑偏”，`/jjk-plan` 输出时必须满足：

1. `implementation_plan` 的每个功能点都能映射到唯一 `feature_id`。
2. 每个 `feature_id` 都有：机制描述 + 代码锚点 + 验证命令 + 回滚锚点。
3. 每个卡片（`card_id`）都绑定明确 `feature_id` 列表，禁止“统一模型基线迁移”这类泛化标题替代。
4. 引用 `output/**` 时只允许“证据引用”，不允许把长篇分析原文直接复制到卡片描述。
5. 若存在历史执行偏差，需在计划中新增“偏差修复清单”，明确哪些旧卡作废、哪些卡重建。
6. 当开启 `hydrate` 时，归一化草案中的每个 `FP-xx` 必须显式映射到实现 `feature_id`（不得遗漏）。

## 5. 衔接下游

规划完成后：
- 并行场景：执行 `/jjk-vkplan` 进行并行拆解（继承主从关系、契约冻结与 `task_key/card_seed`）
- 看板场景：执行 `/jjk-vktodo` 直接落卡；其前置会自动完成 G0 基线校验
- 单任务实现：执行 `/jjk-imp`
- 测试设计：执行 `/jjk-test` 基于模块需求文档生成测试用例
- 若本轮命中大任务阈值且 Team 可用：优先以 Team 模式完成 `/jjk-plan`，再进入下游链路

---
*使用 `/jjk-plan` 触发。是开发周期的正式起点。*
---
