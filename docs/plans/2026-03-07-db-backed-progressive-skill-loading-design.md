# DB 驱动的渐进式 Skill Loader 澄清设计说明（CC-like Progressive Loading）

## 1. scope_contract
- 目标:
  - 将当前“后端 hybrid 检索后直接注入 skill_context”的主运行模式，收敛为“固定 Skill Loader 工具 + 渐进式加载”的单一运行模式。
  - 让 LLM 在正式回答前始终先看到“当前用户可见的 Skill 描述目录”，再根据用户问题自行决定是否加载具体 Skill 正文。
  - 保留你项目现有数据库治理能力（definition/version/binding/template/admin），只替换运行时选择机制，不退回文件直读模式。
- 范围:
  - 后端运行时：`app/services/skill_service.py`、`app/ai/workflow/multi_agent_graph.py`、`app/ai/state.py`
  - Tool Calling 装配：Supervisor / 共享工具注册位
  - 配置与文档：`app/core/config_contract.py`、`docs/API文档/接口文档.md`、`docs/内部参考/AI技能库.md`
  - 测试：Skill catalog 构建、Skill loader tool、会话注入与回放一致性
- 边界:
  - 不把每个 Skill 变成一个独立 tool；固定只保留“Skill Loader 类工具”，避免 tools 数量与 skills 数量耦合。
  - 不废弃现有数据库 Skill 三层治理模型（`definition/version/binding`）；`app/ai/skills` 继续作为作者态导入源，而不是运行时真理源。
  - 不在本轮引入“Skill 自动改写 / 自动发布”；仍保持人工编辑、人工发布、人工回滚。
  - 不讨论工程自身 `.agents/.codex/.cursor` 下的 skills，仅讨论业务系统内 Skill 机制。
- 成功标准:
  - 每次 LLM 主调用前，都会注入“当前用户可见 Skill 描述目录”，但不注入完整 Skill 正文。
  - LLM 可通过固定工具按需加载一个或多个 Skill 正文，并在同一会话中继续推理。
  - 聊天主运行时热路径为 zero-embedding：不依赖 embedding/FTS/hybrid 召回来决定 Skill 命中；这些能力仅保留为治理/调试/后台搜索能力。
  - 用户绑定、版本发布、模板初始化仍然生效，且命中的 Skill 内容来自数据库运行时视图而非文件系统。

## 2. product_contract（PRD-Lite）
- target_users:
  - 平台管理员：维护 Skill 内容、版本、模板与用户覆盖
  - 终端用户：在聊天中获得与当前问题强相关的 Skill 能力增强
  - Agent 运行时：以固定工具协议稳定调用 Skill 加载能力
- core_scenarios:
  - 场景1：用户发起聊天，请求进入 Supervisor 前先注入“Skill 描述目录”
  - 场景2：LLM 判断需要某个 Skill，主动调用 `load_skills` 工具加载正文后继续回答
  - 场景3：同一用户切换版本绑定后，新会话只看到该用户生效版本的目录与正文
  - 场景4：管理员发布/回滚 Skill 版本后，不修改代码即可影响后续会话的可见目录与加载内容
- business_goals（含 KPI）:
  - 主链路一致性：聊天主路径 100% 使用统一 Skill Loader 机制，不再出现“有的会话走 hybrid 注入、有的会话走 tool load”双轨运行
  - 可解释性：90% 以上命中会话可在日志中追溯 `catalog_visible_count / loaded_skill_ids / effective_versions`
  - 上下文效率：默认会话初始 Skill 注入体积控制在固定预算内，仅注入描述目录，不预装 Skill 全文
  - 多租户正确性：不同用户对同一 `skill_id` 的绑定版本互不污染，验收口径为 100% 用户隔离
  - 规模约束：按当前产品预期，单用户同时可见 Skill 数量上限 `< 20`，因此首轮 catalog 采用全量描述注入，不需要热路径预筛
- non_goals:
  - 本轮不把 Skill 直接编译为真正业务工具（如 SQL 工具、文件工具）
  - 本轮不做 Skill 自动训练、自动 embedding 更新闭环
  - 本轮不保留 runtime hybrid 检索作为默认主路径
  - 本轮不引入新的 Skill 数据表
  - 本轮不要求保留聊天主链路向量索引依赖
- acceptance_gates:
  - 无论是否命中 Skill，LLM 首轮都能看到同一结构的 Skill 描述目录
  - 若命中 Skill，必须通过固定工具调用加载，而不是后端静默替模型决定
  - 若 LLM 请求的 `skill_id` 不存在/不可见/已禁用，工具返回受控错误，不得偷偷 fallback 到其他 Skill
  - 会话回放能够还原“当时加载了哪些 Skill 版本”，即使不持久化 Skill 全文，也能根据版本重新构造
- release_constraints:
  - 默认通过运行时开关灰度发布，不能一次性硬切所有聊天路径
  - 保留现有 admin/version/binding API，不引入破坏性接口删除
  - 文档先行，配置键与回退路径必须先冻结再进入开发计划

## 3. architecture_contract
- 模块边界与职责:
  - **Skill Authoring / Governance**
    - `app/ai/skills/*/SKILL.md` 仅作为作者态来源
    - `t_agent_skill_definitions / t_agent_skill_versions / t_user_skill_bindings` 作为数据库治理层
    - 责任：发布、回滚、模板、用户覆盖、版本隔离
  - **Skill Runtime Catalog Provider**
    - 从数据库运行时视图构造“当前用户可见的 Skill 描述目录”
    - 只输出轻量描述，不输出正文
    - 责任：按 `user_id` 过滤、合并 effective version、生成 prompt-safe catalog
    - 元数据口径对齐 Anthropic Skills：首轮仅暴露 `name + description(+可选简短 when_to_use)` 这一层 progressive disclosure 信息
  - **Skill Loader Tool**
    - 作为固定工具暴露给 LLM，例如 `load_skills(skill_ids[])`
    - 责任：校验 skill_id 可见性、去重、限制加载数量、拉取正文、返回受控格式
  - **Prompt Assembler / Session State**
    - 在 LLM 调用前注入 `skill_catalog_context`
    - 在命中后把 Skill 正文写入本轮/本会话上下文，并记录 canonical runtime trace
    - 责任：上下文预算、重复加载抑制、回放一致性
  - **Admin Search / Evaluation**
    - 继续保留当前 embedding/FTS/hybrid 检索作为后台调试、搜索测试、离线评估能力
    - 责任：帮助运营定位 Skill，不参与聊天主运行时命中决策

- 贴近 CC 的运行时原则（冻结）:
  1. 元数据优先：模型先看 Skill 名称与描述，而不是正文。
  2. 正文按需：只有模型判断需要时，才加载完整 Skill。
  3. 工具固定：固定 tool surface，不让 skills 数量膨胀为 tools 数量。
  4. 正文二级展开：正文加载后继续作为上下文参与推理，而不是在首轮统一预装。
  5. 热路径去检索化：聊天主路径不先做 embedding 命中，再替模型做选择。

- 端到端数据流:
  1. 应用启动：预热 published Skill 描述缓存（可选），仅缓存轻量 descriptor，不缓存完整正文到 system prompt。
  2. 会话预处理：根据 `user_id` 从 runtime view 构造 `skill_catalog_manifest`。
  3. Prompt 组装：将 manifest 转为 `skill_catalog_context` 注入首轮 `SystemMessage`。
  4. LLM 首次推理：模型阅读用户问题 + Skill 描述目录，自主判断是否调用 `load_skills`。
  5. Tool 执行：后端校验并从 DB 读取正文，返回 `loaded_skills` 结果，同时把 `loaded_skill_ids/effective_versions` 写入会话状态。
  6. LLM 继续推理：模型基于 ToolMessage + 会话上下文生成最终回答或继续路由。
  7. 回放/恢复：通过 `additional_kwargs.skill_runtime` 中的 canonical 字段恢复当时加载的 Skill 版本，再从 DB 重建正文。

- 状态生命周期:
  - 作者态：`SKILL.md`
  - 治理态：`definition -> version -> binding`
  - 运行态目录：`skill_catalog_manifest`
  - 会话态：`skill_catalog_context -> loaded_skill_ids -> loaded_skill_context`
  - 回放态：`additional_kwargs.skill_runtime`
  - 生命周期约束:
    - 描述目录可缓存，正文按需加载
    - 正文加载后在当前会话去重，不重复调用同一 `skill_id + version`
    - 持久化 canonical 字段只记录“加载了什么版本”，不强制持久化整篇 Skill 正文

- 异常语义与降级策略:
  - 目录构建失败：允许从 DB 直查一次后继续；若仍失败，则本轮不注入 catalog，并记录 `skill_catalog_unavailable`
  - Tool 请求非法 Skill：工具返回 `not_visible` / `not_found` / `disabled` 的结构化错误，不做 silent fallback
  - Skill 正文过长：统一按 `max_chars/max_sections` 裁剪为可注入版本，并返回 `truncated=true`
  - DB 暂时不可用：若 catalog 已缓存则允许用缓存目录继续；正文加载失败则工具报错，由模型继续无 Skill 回答
  - 回放缺正文：依据 `loaded_skill_ids + effective_versions` 二次回源 DB；若对应版本已失效，则标记 `replay_skill_version_missing`

## 4. 最终方案
- 方案描述:
  - 将业务系统内 Skill 主运行时改为“DB 驱动的渐进式 Skill Loader”。
  - 会话开始前只向模型提供“可用 Skill 描述目录”；完整 Skill 正文只在模型认为有必要时，通过固定工具显式加载。
  - 数据来源保持数据库运行时视图，文件系统仅作为作者态导入源。
- 关键决策:
  - 决策1：**运行时命中决策由 LLM 负责，不再由 hybrid 检索主导。**
  - 决策2：**固定工具数量与 skills 数量解耦。**只提供 `load_skills`（必要时附加只读 `get_loaded_skills_state`），不为每个 Skill 注册独立 tool。
  - 决策3：**目录描述与正文分离。**目录始终预装，正文严格按需加载，采用 progressive disclosure。
  - 决策4：**数据库运行时视图是唯一契约源。**`app/ai/skills` 不直接参与聊天运行时读取。
  - 决策5：**回放 canonical 字段统一为 `additional_kwargs.skill_runtime`。**

### 4.1 与 Claude / Claude Code 的对齐结论
- 已确认的官方公开机制（事实）:
  - Anthropic 官方 Skills 说明明确采用 progressive disclosure：初始化只加载 Skill 名称与描述；命中后再加载完整指令；更深层资源继续按需读取。
  - Claude Code 官方说明明确支持自定义 Skills，且以文件系统技能包方式自动发现。
- 对 Claude Code 内部实现的推断（推断，非官方源代码披露）:
  - 官方未公开 Claude Code 的完整内部 system prompt 组装细节；但从 Skills 总览与自定义 Skills 文档看，设计语义与渐进加载机制是一致的。
- 因此本方案冻结为：
  - **对齐 Anthropic Skills 的渐进加载语义**
  - **保留你项目的数据库治理与多租户能力**
  - **不强依赖文件系统作为运行时源**

### 4.2 固定 Tool 契约
| 字段 | 说明 |
|---|---|
| tool_name | `load_skills` |
| 输入 | `skill_ids: string[]` |
| 限制 | 单次最多 3 个，必须属于当前用户可见 catalog |
| 输出 | `loaded_skills[]`，包含 `skill_id/effective_version/content/truncated` |
| 错误 | `not_found / not_visible / disabled / load_failed / over_limit` |
| 幂等 | 已加载的 `skill_id + version` 不重复加载 |

### 4.3 目录注入格式
- 每条 descriptor 只包含最小必要字段：
  - `skill_id`
  - `display_name`
  - `description`
  - `effective_version`
  - `when_to_use`（由 description/元数据归一得到）
- 明确禁止把完整 `trigger_phrases/conflicts_with/content` 全量塞进初始 prompt。

### 4.4 贴近 CC 的 metadata 契约
- 设计原则:
  - `description` 负责回答“什么时候该用这个 Skill”，而不是承载长篇正文。
  - Skill 正文负责回答“具体怎么做”。
  - 如果现有 `description` 过长或偏摘要化，应在导入/同步时额外生成 `catalog_description`（或同等派生字段）用于首轮目录注入。
- 对现有模块的最小侵入改造:
  - 保留 `content` 作为完整正文，不改库表主含义。
  - 优先复用当前 `description`；仅当其超过首轮预算或语义不适合“when to use”时，再引入派生 catalog 字段。
  - `trigger_phrases` 不再用于聊天主链路自动命中，可保留给后台调试或运营分析。

### 4.5 向量化在新方案中的位置
- 聊天主路径:
  - 不需要 embedding；catalog 可见集由用户绑定/版本/启停/作用域决定。
- 保留场景:
  - 管理后台搜索
  - 离线评估“某类问题通常会触发哪些 Skill”
  - 当单用户可见 Skill 数量极大时，作为 catalog 预筛的候选技术储备
- 默认判断阈值（工程建议）:
  - 当前已知业务输入：单用户可见 Skill 数量 `< 20`，因此本期冻结为 **聊天主链路完全 zero-embedding**
  - 单用户可见 Skill `<= 100`：不使用向量化预筛
  - 单用户可见 Skill `100~300`：优先做 catalog 压缩/分组，不急于上 embedding
  - 单用户可见 Skill `> 300`：允许评估 embedding 作为目录预筛，但仍不得直接替模型命中正文

### 4.6 细粒度 Skill 与目录层能力支持
- 结论:
  - **支持更细粒度 Skill 是可行的，而且在你当前 DB 结构上可以先做 70% 的能力。**
  - 当前结构已支持“把一个大能力拆成多个小 Skill 记录”；当前不支持得最完整的是“像目录包一样的层级组织、附属资源文件、脚本资产与依赖关系”。
  - 用户已确认本轮目标是：**选择 Phase A，即把一个大能力拆成多层级的独立小 Skill，而不是先做多资源 Skill 包。**
- 当前结构已支持的部分:
  - `skill_id` 已是稳定标识，可直接把一个能力拆成多个原子 Skill，例如：
    - `sql.query-author`
    - `sql.index-review`
    - `sql.schema-design`
  - `definition/version/binding` 已能分别治理这些原子 Skill 的版本与用户可见性。
  - 对于“一个能力拆细后按需加载”，固定 `load_skills` 工具天然兼容。
- 当前结构欠缺的部分:
  - 缺少显式层级字段：无法直接表达“父 skill / 子 skill / 技能包”
  - 缺少资源表：无法像 CC 技能目录那样给某个 Skill 绑定多个 reference 文件、脚本或 assets
  - 缺少依赖图：无法表达“先加载 A，再按需读取 A 的 REFERENCE/BEST_PRACTICES/SCRIPT”
- 贴近 CC 的两阶段支持方案:
  - **Phase A（最小侵入，推荐先做）**
    - 继续使用现有三层表
    - 通过命名规范 + 轻量层级字段实现细粒度 Skill：`domain.capability.variant`
    - catalog 首轮按“逻辑分组 / 逻辑层级”展示，但底层仍是平铺 skill 记录
    - 适用目标：先把大 Skill 拆小，让 LLM 更容易精确命中
  - **Phase B（更像目录包）**
    - 为 Skill 定义/版本增加层级与资源能力，例如：
      - `parent_skill_id` 或 `group_key`
      - `t_agent_skill_resources`
      - `t_agent_skill_resource_versions`
    - 让一个 Skill 既有 metadata，也能挂多个 reference/script/resource 子对象
    - 适用目标：真正模拟 CC 中“一个 skill 目录 + 多个附属文件/脚本”的组织形式
- 冻结建议:
  - 当前先做 **Phase A**，不要第一期就扩表做复杂目录树。
  - 原因是：你现在单用户可见 Skill `< 20`，先把原子 Skill 粒度与 metadata 语义打磨对，收益远高于先上层级树。

### 4.7 Phase A 的 DB 层级化最小实现
- 结论:
  - **不需要新增新表，也能支持“多层级独立小 Skill”的第一期实现。**
  - 推荐做法是：在现有 `definition/version` 结构上补少量层级元数据字段，而不是一上来设计完整资源树。
- 推荐字段归属:
  - `t_agent_skill_definitions`（稳定层级信息）
    - `catalog_path`: 例如 `sql/query/author`
    - `group_key`: 例如 `sql`
    - `parent_skill_id`: 可空；用于逻辑父节点
    - `catalog_order`: 用于目录展示排序
    - `is_leaf`: 是否叶子 Skill
  - `t_agent_skill_versions`（版本化提示信息）
    - `catalog_description`: 首轮目录展示文案，强调 when-to-use
    - `when_to_use`: 可选短句，便于模型判断是否调用 loader
- 设计原则:
  - 层级信息放 definition：因为它应该跨版本稳定。
  - 目录描述放 version：因为它是 prompt-facing 文案，可能需要版本迭代。
  - `skill_id` 继续作为唯一业务主键，不用把 path 当主键。
- 示例:
  - `skill_id=sql.query.author`
  - `catalog_path=sql/query/author`
  - `group_key=sql`
  - `parent_skill_id=sql.query`
  - `is_leaf=true`
- 运行时展示语义:
  - 首轮 catalog 可按 path/group 渲染成：
    - SQL
      - Query
        - Author
        - Review
      - Schema
        - Design
  - 但底层 loader 仍只接受叶子 `skill_id` 列表，不加载组节点。

## 5. 决策权衡（仅放弃原因）
- 放弃路径: 继续以 `search_skills()` 的向量/关键词召回结果直接替模型决定命中 Skill
- 放弃原因:
  - 与“类似 CC 的固定工具 + 模型自主加载”目标相冲突
  - 后端静默命中会削弱模型可解释性，且会话行为难与 Claude 风格对齐
- 放弃路径: 为每个 Skill 动态注册一个独立 tool
- 放弃原因:
  - tool 数量与 skill 数量耦合，prompt/tool schema 膨胀快
  - 版本切换、用户隔离、禁用控制都会直接影响 tool surface，治理复杂度显著升高
- 放弃路径: 运行时直接从 `app/ai/skills` 文件读取 Skill 正文
- 放弃原因:
  - 破坏你项目现有的版本/绑定/模板治理闭环
  - 无法正确支持多租户用户绑定与发布回滚

## 6. requirement_seeds
- D-01 `FR-SKILL-CATALOG-PRELOAD`
  - trigger: 聊天会话进入首轮 LLM 调用前
  - input_contract:
    - required_fields: [`user_id`, `messages`]
    - optional_fields: [`thread_id`, `trace_id`]
    - defaults:
      - `thread_id`: ""
      - `trace_id`: ""
  - output_contract:
    - required_fields: [`skill_catalog_context`, `skill_catalog_manifest`]
    - optional_fields: [`catalog_version`, `visible_skill_count`]
  - failure_semantics: 目录不可用时允许本轮无 catalog 运行，但必须记录结构化告警，不得偷偷切回 hybrid 注入
  - observability_fields: [`user_id`, `trace_id`, `visible_skill_count`, `catalog_build_source`]
  - rollback_anchor: `SKILL_RUNTIME_MODE=hybrid_rag`
  - acceptance_cmd_ref: `venv/bin/python -m pytest app/tests/test_skill_catalog_manifest.py -q`
- D-02 `FR-SKILL-TOOL-LOAD`
  - trigger: LLM 在对话中显式调用 `load_skills`
  - input_contract:
    - required_fields: [`skill_ids[]`]
    - optional_fields: [`reason`]
    - defaults: {}
  - output_contract:
    - required_fields: [`loaded_skills[]`]
    - optional_fields: [`errors[]`, `truncated_count`]
  - failure_semantics: 非法 skill_id 返回结构化错误；不得用其他 skill 替代
  - observability_fields: [`user_id`, `trace_id`, `requested_skill_ids`, `loaded_skill_ids`, `effective_versions`]
  - rollback_anchor: `ENABLE_PROGRESSIVE_SKILL_LOADING=false`
  - acceptance_cmd_ref: `venv/bin/python -m pytest app/tests/test_skill_loader_tool.py -q`
- D-03 `FR-SKILL-SESSION-CANONICAL`
  - trigger: Skill 被成功加载并进入当前会话
  - input_contract:
    - required_fields: [`loaded_skill_ids`, `effective_versions`]
    - optional_fields: [`loaded_from_cache`, `truncated_flags`]
    - defaults: {}
  - output_contract:
    - required_fields: [`additional_kwargs.skill_runtime`]
    - optional_fields: [`loaded_skill_context`] 
  - failure_semantics: 缺少 canonical 字段视为实现失败，禁止宣称回放一致
  - observability_fields: [`thread_id`, `trace_id`, `loaded_skill_ids`, `catalog_version`]
  - rollback_anchor: `ENABLE_SKILL_RUNTIME_TRACE=false`
  - acceptance_cmd_ref: `venv/bin/python -m pytest app/tests/test_skill_runtime_replay.py -q`
- D-04 `FR-ADMIN-SEARCH-DECOUPLE`
  - trigger: 管理后台搜索 / 调试 Skill 命中效果
  - input_contract:
    - required_fields: [`query`]
    - optional_fields: [`user_id`, `mode`]
    - defaults:
      - `mode`: `hybrid`
  - output_contract:
    - required_fields: [`debug_candidates[]`]
    - optional_fields: [`score_breakdown`, `retrieval_log`]
  - failure_semantics: 仅影响后台调试，不影响聊天主路径
  - observability_fields: [`query_hash`, `mode`, `candidate_count`]
  - rollback_anchor: `ENABLE_SKILL_ADMIN_SEARCH=true`
  - acceptance_cmd_ref: `venv/bin/python -m pytest app/tests/test_skill_retrieval_smoke.py -q`
- D-05 `FR-SKILL-METADATA-PROGRESSIVE`
  - trigger: Skill 导入/同步到数据库，或 catalog 构建前
  - input_contract:
    - required_fields: [`name`, `description`, `content`]
    - optional_fields: [`trigger_phrases`, `scope`]
    - defaults: {}
  - output_contract:
    - required_fields: [`catalog_description`]
    - optional_fields: [`when_to_use`]
  - failure_semantics: 若无法生成派生目录描述，则回退为原始 `description`，不得阻断 Skill 上线
  - observability_fields: [`skill_id`, `description_source`, `description_length`, `derived_catalog_description`]
  - rollback_anchor: `ENABLE_SKILL_CATALOG_METADATA_NORMALIZATION=false`
  - acceptance_cmd_ref: `venv/bin/python -m pytest app/tests/test_skill_catalog_manifest.py -q`

## 7. implementation_seeds
- task_id: T-01
  feature_id: P1-runtime-catalog
  blocked_by: []
  file_paths:
    - app/services/skill_service.py
    - app/ai/state.py
  symbols:
    - SkillService.build_skill_catalog_manifest
    - SkillService.format_skill_catalog_as_context
    - MultiAgentState.skill_catalog_manifest
    - MultiAgentState.skill_catalog_context
  change_type: modify
- task_id: T-02
  feature_id: P1-skill-loader-tool
  blocked_by: [T-01]
  file_paths:
    - app/ai/workflow/multi_agent_graph.py
    - app/services/skill_service.py
  symbols:
    - _create_load_skills_tool
    - _get_supervisor_tools
    - SkillService.load_skills_for_session
  change_type: modify
- task_id: T-03
  feature_id: P1-session-canonical-trace
  blocked_by: [T-02]
  file_paths:
    - app/ai/workflow/multi_agent_graph.py
    - app/ai/protocol.py
    - app/ai/state.py
  symbols:
    - additional_kwargs.skill_runtime
    - MultiAgentState.loaded_skill_registry
    - MultiAgentState.loaded_skill_context
    - skill_context(deprecated_compat)
  change_type: modify
- task_id: T-04
  feature_id: P1-runtime-mode-switch
  blocked_by: [T-01]
  file_paths:
    - app/core/config_contract.py
    - app/services/skill_service.py
    - docs/API文档/接口文档.md
  symbols:
    - skill.runtime_mode
    - feature.enable_progressive_skill_loading
  change_type: modify
- task_id: T-05
  feature_id: P1-catalog-metadata-contract
  blocked_by: [T-01]
  file_paths:
    - app/models/agent_skill.py
    - alembic/versions/*_add_progressive_skill_catalog_fields.py
    - app/api/v1/endpoints/skill_admin_api.py
    - app/services/skill_service.py
    - docs/内部参考/AI技能库.md
  symbols:
    - AgentSkillDefinition.catalog_path
    - AgentSkillDefinition.catalog_order
    - AgentSkillVersion.catalog_description
    - AgentSkillVersion.when_to_use
    - SkillMetadataUpdateRequest
    - SkillService.build_catalog_descriptor
    - catalog_description
    - when_to_use
  change_type: modify
- task_id: T-06
  feature_id: P1-tests-and-docs
  blocked_by: [T-02, T-03, T-04]
  file_paths:
    - app/tests/test_skill_catalog_manifest.py
    - app/tests/test_skill_loader_tool.py
    - app/tests/test_skill_runtime_replay.py
    - docs/内部参考/AI技能库.md
  symbols:
    - test_catalog_preload
    - test_loader_tool_visibility
    - test_runtime_replay_rehydrate
  change_type: add

## 8. execution_chain_seed
- preferred_mode: core
- task_key: `PP-20260307-db-progressive-skill-loading`
- card_seed:
  - T-01
  - T-02
  - T-03
  - T-04
  - T-05
  - T-06
- execution_contract_hint:
  - delivery_mode: staged
  - execution_unit: all_tasks
  - commit_policy: single_commit
  - stop_boundary: none

## 9. risk_rollback_contract
- 关键风险（含反例）:
  - R-01: Skill 描述目录过大，首轮 system prompt 膨胀
    - 反例: 一个用户可见 200+ skills，全部描述直接注入导致首轮 token 过大
  - R-02: LLM 不调用 `load_skills`，导致原本 hybrid 可命中的 Skill 不再自动生效
    - 反例: 用户问 SQL 问题，模型忽略目录中 `sql-expert`，直接普通回答
  - R-03: Tool 调用了错误 skill_id，出现误加载或权限泄漏风险
    - 反例: 用户 A 试图经模型调用加载用户 B 专属版本
  - R-04: 回放只存了 loaded ids，没有正文，后续版本缺失导致恢复失败
    - 反例: 旧会话引用 `skill_id=v2`，该版本被错误删除或不可见
  - R-05: 现有 `description` 过长或不描述“何时使用”，导致模型看了目录仍不会正确调用 `load_skills`
    - 反例: `description` 更像正文摘要，而不是明确的触发条件说明
- 回退锚点（默认开关 true，回退 false）:
  - `feature.enable_progressive_skill_loading=true`
  - `skill.runtime_mode=catalog_tool`
  - 回退时：`feature.enable_progressive_skill_loading=false` 且 `skill.runtime_mode=hybrid_rag`
- 回退路径:
  - 保留现有 `search_skills/search_skills_debug` 代码与 admin 检索 API
  - 回退后聊天主链重新使用当前 hybrid 注入逻辑，Skill Loader tool 不再注册

## 10. 设计补充说明
### 10.1 模块边界 / 依赖方向 / 状态归属 / 错误处理责任（门禁四段式）
- 模块边界:
  - Skill 治理层负责“什么 Skill 存在、哪个版本有效、用户能看什么”；运行时加载层只负责“目录构建与正文加载”。
- 依赖方向:
  - `SKILL.md -> import/sync -> definition/version/binding -> runtime catalog -> load_skills tool -> session context`，禁止反向从会话层直接读文件。
- 状态归属:
  - 作者态在文件，运行时真理源在 DB runtime view，会话态在 LangGraph state，回放态在 `additional_kwargs.skill_runtime`。
- 错误处理责任:
  - 治理数据错误由 `SkillService` 报告；目录构建错误在 preprocess 降级；tool load 错误以 ToolMessage 返回；聊天主链不得因 Skill 失败而整体中断。

### 10.2 与当前实现的结构性差异
| 维度 | 当前实现 | 冻结后实现 |
|---|---|---|
| 命中决策 | 后端 hybrid 检索决定 | LLM 读描述目录后决定 |
| 首轮注入 | 可能直接注入 skill_context 片段 | 只注入 catalog 描述 |
| 全文加载 | 后端静默裁剪后注入 | 通过固定工具显式加载 |
| runtime 主路径 | `search_skills_debug()` | `build_skill_catalog_manifest() + load_skills()` |
| embedding/FTS | 参与主链路命中 | 退出主链路，只保留后台用途 |
| description 语义 | 兼做检索摘要 | 主要表达“何时使用该 Skill” |

### 10.3 外部对齐依据
- Anthropic 官方 Skills 文档公开说明 progressive disclosure：初始化先加载名称与描述，命中后再加载完整 Skill 指令。
- Claude Code 官方文档公开说明支持文件系统中的 Custom Skills 自动发现；未公开完整内部 prompt 组装细节，因此“CC 内部完全同实现”属于推断，但设计语义可对齐。

### 10.4 Phase A 实现契约补充冻结（补齐 handoff 阻断点）
- 冻结目标:
  - 本节只补齐“schema 真理源 / 会话状态壳 / replay canonical 载荷”三项实现契约，不改动前文高层方案。
  - Phase A 仍以“最小侵入、设计优先”为原则，避免第一期为了目录树能力引入过多持久化字段与兼容层。
- 单一契约源（冻结）:
  - 运行时 catalog metadata 的真理源固定为 `t_agent_skill_definitions + t_agent_skill_versions`。
  - `t_agent_skills` 仅保留导入兼容、检索调试、历史过渡用途；**不得**继续承载新的 catalog/runtime metadata 写入责任。
  - 管理面若需要编辑 catalog metadata，必须经 definition/version 视图或其 service 封装，不得绕回兼容表单独写值。
- Phase A 持久化字段最小集（冻结）:
  - `t_agent_skill_definitions`：
    - `catalog_path`：目录层级路径，作为唯一稳定层级表达
    - `catalog_order`：同层展示顺序
  - `t_agent_skill_versions`：
    - `catalog_description`：首轮目录展示文案
    - `when_to_use`：可选短句；为空时由 `catalog_description/description` 派生
  - Phase A 默认不新增 `group_key / parent_skill_id / is_leaf` 持久化字段；其值统一由 `catalog_path` 在运行时派生。
  - 若后续确认存在“派生无法满足排序/权限/运营配置”的真实阻断，再升级到 Phase B 扩展字段或资源表，不在本期预埋。
- 迁移与管理面约束（冻结）:
  - 第一批实现必须同时覆盖 `SQLAlchemy model + Alembic migration + skill_admin API/schema`，禁止只在 service 内用临时字典或 JSON patch 伪装字段存在。
  - 文档/API 若仍保留兼容表返回结构，必须标记 catalog 字段来源为 definition/version 运行时视图，不得形成双真理源。

### 10.5 会话状态归属与刷新语义冻结
- 会话态唯一状态壳:
  - `skill_catalog_manifest`：当前轮对当前用户可见的 descriptor 列表
  - `skill_catalog_context`：由 manifest 渲染后的首轮 prompt 文本
  - `loaded_skill_registry`：本会话已加载 Skill 的唯一状态源，键为 `skill_id`，值至少包含 `version / truncated / source_turn_id`
  - `loaded_skill_context`：由 `loaded_skill_registry` 派生的拼接上下文，用于后续轮次推理
- 兼容字段口径:
  - 现有 `skill_context` 在 Phase A 仅允许作为兼容派生字段读取，不再作为新链路状态真理源。
  - `selected_skill_ids / skill_injection_meta` 可在灰度期保留观测，但 progressive loader 开启后不得再承担 replay/恢复语义。
- 刷新语义（冻结）:
  - `skill_catalog_manifest` 按轮构建，触发点固定在 `preprocess`。
  - `loaded_skill_registry` 按会话累积；同一 `skill_id + version` 幂等去重，不重复写入。
  - 用户绑定/发布版本变更默认只影响**新会话**；当前会话一旦已加载某版本，不在会话中途自动热切换。
  - 回放时优先依据 `additional_kwargs.skill_runtime` 恢复 `loaded_skill_registry`，禁止再从历史 `skill_context` 反向猜测版本。

### 10.6 `additional_kwargs.skill_runtime` canonical 载荷冻结
- canonical 字段结构（冻结）:
```yaml
additional_kwargs:
  skill_runtime:
    runtime_mode: progressive_loader|hybrid_rag
    catalog_version: "<manifest_hash_or_version>"
    visible_skill_count: <int>
    loaded_skills:
      - skill_id: "sql.query.author"
        version: "v2026.03.07"
        truncated: false
    replay_source: live|rehydrated
```
- 语义约束:
  - `loaded_skills` 是回放与恢复的唯一 canonical 列表；不得再混用 `selected_skill_ids` 或自由文本 `skill_context` 作为恢复依据。
  - `catalog_version` 可由 manifest 哈希、发布时间戳或等价稳定版本生成，但必须在同轮内可复现。
  - `replay_source=rehydrated` 表示正文来自历史版本回源重建，而非原始实时 ToolMessage。
- 读旧写新（冻结）:
  - Progressive loader 启用后，新消息仅写 `additional_kwargs.skill_runtime`。
  - 历史字段 `selected_skill_ids / skill_injection_meta / skill_context` 在过渡期只读不写；回放逻辑若读到旧字段，必须归一转换到 `skill_runtime` 后再向下游暴露。
  - 若历史版本不存在或回源失败，统一写入 `replay_source=rehydrated` 与 `replay_skill_version_missing` 观测事件，不得伪造正文。

## 11. design_freeze_summary（唯一门禁）
```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 5
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
  topic: "db-backed-progressive-skill-loading"
  design_source: "docs/plans/2026-03-07-db-backed-progressive-skill-loading-design.md"
  handoff_ready: true
  required:
    product_contract_summary:
      target_users:
        - 平台管理员
        - 终端用户
        - Agent 运行时
      core_scenarios:
        - 首轮预装 Skill 描述目录
        - LLM 显式调用 Skill Loader tool
        - 用户绑定版本驱动可见 Skill 集
      business_goal_metrics:
        - 聊天主链路 100% 统一到 Skill Loader 机制
        - 90% 以上命中会话可追溯 loaded_skill_ids/effective_versions
        - 用户隔离正确率 100%
      non_goals:
        - 不把每个 Skill 变成独立 tool
        - 不做 Skill 自动发布
        - 不保留 hybrid 作为聊天主路径
      acceptance_gates:
        - 首轮仅注入描述目录
        - 命中必须经 `load_skills` 工具
        - 非法 skill_id 不得 silent fallback
        - 回放能重建加载版本
    requirement_seeds:
      - design_item: D-01
        fr_id: FR-SKILL-CATALOG-PRELOAD
        trigger: 聊天会话进入首轮 LLM 调用前
        input_contract:
          required_fields: [user_id, messages]
          optional_fields: [thread_id, trace_id]
          defaults:
            thread_id: ""
            trace_id: ""
        output_contract:
          required_fields: [skill_catalog_context, skill_catalog_manifest]
          optional_fields: [catalog_version, visible_skill_count]
        failure_semantics: 目录不可用时可无 catalog 继续，但必须记录结构化告警，不得偷偷切回 hybrid 注入
        observability_fields: [user_id, trace_id, visible_skill_count, catalog_build_source]
        rollback_anchor: SKILL_RUNTIME_MODE=hybrid_rag
        acceptance_cmd_ref: venv/bin/python -m pytest app/tests/test_skill_catalog_manifest.py -q
      - design_item: D-02
        fr_id: FR-SKILL-TOOL-LOAD
        trigger: LLM 在对话中显式调用 load_skills
        input_contract:
          required_fields: [skill_ids]
          optional_fields: [reason]
          defaults: {}
        output_contract:
          required_fields: [loaded_skills]
          optional_fields: [errors, truncated_count]
        failure_semantics: 非法 skill_id 返回结构化错误，不得用其他 skill 替代
        observability_fields: [user_id, trace_id, requested_skill_ids, loaded_skill_ids, effective_versions]
        rollback_anchor: ENABLE_PROGRESSIVE_SKILL_LOADING=false
        acceptance_cmd_ref: venv/bin/python -m pytest app/tests/test_skill_loader_tool.py -q
      - design_item: D-03
        fr_id: FR-SKILL-SESSION-CANONICAL
        trigger: Skill 被成功加载并进入当前会话
        input_contract:
          required_fields: [loaded_skill_ids, effective_versions]
          optional_fields: [loaded_from_cache, truncated_flags]
          defaults: {}
        output_contract:
          required_fields: [additional_kwargs.skill_runtime]
          optional_fields: [loaded_skill_context]
        failure_semantics: 缺少 canonical 字段视为实现失败，禁止宣称回放一致
        observability_fields: [thread_id, trace_id, loaded_skill_ids, catalog_version]
        rollback_anchor: ENABLE_SKILL_RUNTIME_TRACE=false
        acceptance_cmd_ref: venv/bin/python -m pytest app/tests/test_skill_runtime_replay.py -q
      - design_item: D-04
        fr_id: FR-ADMIN-SEARCH-DECOUPLE
        trigger: 管理后台搜索 / 调试 Skill 命中效果
        input_contract:
          required_fields: [query]
          optional_fields: [user_id, mode]
          defaults:
            mode: hybrid
        output_contract:
          required_fields: [debug_candidates]
          optional_fields: [score_breakdown, retrieval_log]
        failure_semantics: 仅影响后台调试，不影响聊天主路径
        observability_fields: [query_hash, mode, candidate_count]
        rollback_anchor: ENABLE_SKILL_ADMIN_SEARCH=true
        acceptance_cmd_ref: venv/bin/python -m pytest app/tests/test_skill_retrieval_smoke.py -q
      - design_item: D-05
        fr_id: FR-SKILL-METADATA-PROGRESSIVE
        trigger: Skill 导入/同步到数据库，或 catalog 构建前
        input_contract:
          required_fields: [name, description, content]
          optional_fields: [trigger_phrases, scope]
          defaults: {}
        output_contract:
          required_fields: [catalog_description]
          optional_fields: [when_to_use]
        failure_semantics: 若无法生成派生目录描述，则回退为原始 description，不得阻断 Skill 上线
        observability_fields: [skill_id, description_source, description_length, derived_catalog_description]
        rollback_anchor: ENABLE_SKILL_CATALOG_METADATA_NORMALIZATION=false
        acceptance_cmd_ref: venv/bin/python -m pytest app/tests/test_skill_catalog_manifest.py -q
    implementation_seeds:
      - task_id: T-01
        feature_id: P1-runtime-catalog
        blocked_by: []
        file_paths:
          - app/services/skill_service.py
          - app/ai/state.py
        symbols:
          - SkillService.build_skill_catalog_manifest
          - SkillService.format_skill_catalog_as_context
          - MultiAgentState.skill_catalog_manifest
          - MultiAgentState.skill_catalog_context
        change_type: modify
      - task_id: T-02
        feature_id: P1-skill-loader-tool
        blocked_by: [T-01]
        file_paths:
          - app/ai/workflow/multi_agent_graph.py
          - app/services/skill_service.py
        symbols:
          - _create_load_skills_tool
          - _get_supervisor_tools
          - SkillService.load_skills_for_session
        change_type: modify
      - task_id: T-03
        feature_id: P1-session-canonical-trace
        blocked_by: [T-02]
        file_paths:
          - app/ai/workflow/multi_agent_graph.py
          - app/ai/protocol.py
          - app/ai/state.py
        symbols:
          - additional_kwargs.skill_runtime
          - MultiAgentState.loaded_skill_registry
          - MultiAgentState.loaded_skill_context
          - skill_context(deprecated_compat)
        change_type: modify
      - task_id: T-04
        feature_id: P1-runtime-mode-switch
        blocked_by: [T-01]
        file_paths:
          - app/core/config_contract.py
          - app/services/skill_service.py
          - docs/API文档/接口文档.md
        symbols:
          - skill.runtime_mode
          - feature.enable_progressive_skill_loading
        change_type: modify
      - task_id: T-05
        feature_id: P1-catalog-metadata-contract
        blocked_by: [T-01]
        file_paths:
          - app/models/agent_skill.py
          - alembic/versions/*_add_progressive_skill_catalog_fields.py
          - app/api/v1/endpoints/skill_admin_api.py
          - app/services/skill_service.py
          - docs/内部参考/AI技能库.md
        symbols:
          - AgentSkillDefinition.catalog_path
          - AgentSkillDefinition.catalog_order
          - AgentSkillVersion.catalog_description
          - AgentSkillVersion.when_to_use
          - SkillMetadataUpdateRequest
          - SkillService.build_catalog_descriptor
          - catalog_description
          - when_to_use
        change_type: modify
      - task_id: T-06
        feature_id: P1-tests-and-docs
        blocked_by: [T-02, T-03, T-04, T-05]
        file_paths:
          - app/tests/test_skill_catalog_manifest.py
          - app/tests/test_skill_loader_tool.py
          - app/tests/test_skill_runtime_replay.py
          - docs/内部参考/AI技能库.md
        symbols:
          - test_catalog_preload
          - test_loader_tool_visibility
          - test_runtime_replay_rehydrate
        change_type: add
    execution_chain_seed:
      preferred_mode: core
      task_key: PP-20260307-db-progressive-skill-loading
      card_seed: [T-01, T-02, T-03, T-04, T-05, T-06]
      execution_contract_hint:
        delivery_mode: staged
        execution_unit: all_tasks
        commit_policy: single_commit
        stop_boundary: none
    alignment_contract:
      strict_match: true
      requirement_seed_ids: [D-01, D-02, D-03, D-04, D-05]
      implementation_task_ids: [T-01, T-02, T-03, T-04, T-05, T-06]
      card_seed_ids: [T-01, T-02, T-03, T-04, T-05, T-06]
  extended:
    observability_hints:
      - 为 catalog 构建记录 visible_skill_count / catalog_version / build_source
      - 为 loader tool 记录 requested_skill_ids / loaded_skill_ids / effective_versions / truncated_count
      - 为回放恢复记录 replay_skill_version_missing / replay_rehydrate_source
    risk_counterexample_map:
      - risk_id: R-01
        counterexample: 200+ skills 全量描述注入导致首轮 token 失控
        verify_cmd: venv/bin/python -m pytest app/tests/test_skill_catalog_manifest.py -q
      - risk_id: R-02
        counterexample: 模型忽略 sql-expert 描述目录，未调用 load_skills
        verify_cmd: venv/bin/python -m pytest app/tests/test_skill_loader_tool.py -q
      - risk_id: R-03
        counterexample: 用户 A 会话请求到用户 B 不可见 skill 版本
        verify_cmd: venv/bin/python -m pytest app/tests/test_skill_loader_tool.py -q
      - risk_id: R-04
        counterexample: 回放时引用历史版本但 DB 中缺失该版本
        verify_cmd: venv/bin/python -m pytest app/tests/test_skill_runtime_replay.py -q
      - risk_id: R-05
        counterexample: description 更像正文摘要，模型读完目录后仍不会调用 load_skills
        verify_cmd: venv/bin/python -m pytest app/tests/test_skill_catalog_manifest.py -q
    assumptions:
      - 聊天主 LLM 支持 tool calling 或兼容 json-object 工具调用语义
      - 运行时允许在 preprocess 阶段为当前用户构建 descriptor catalog
      - 当前 admin/version/binding 表结构足以支撑该方案，无需新增表
  requirement_seeds: [D-01, D-02, D-03, D-04, D-05]
  implementation_seeds: [T-01, T-02, T-03, T-04, T-05, T-06]
  execution_chain_seed:
    preferred_mode: core
    task_key: PP-20260307-db-progressive-skill-loading
    card_seed: [T-01, T-02, T-03, T-04, T-05, T-06]
```

## 13. 审批记录
- design_approved: true
- approved_at: "2026-03-07T00:00:00+08:00"
- approved_round: "round-3"
- approval_evidence: "用户回复“接受”“好的”，确认第一期继续采用 progressive loader 单方案，并补齐 schema 真理源、会话状态壳、additional_kwargs.skill_runtime 三项实现契约；Phase A 持久化字段最小集冻结为 catalog_path/catalog_order/catalog_description/when_to_use。"
- approval_mode: approved
- go_no_go: GO
- blocking_issues: []

## 14. clarify_consistency_check（机读）
```yaml
clarify_consistency_check:
  clarify_phase: approval
  current_round: 3
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
