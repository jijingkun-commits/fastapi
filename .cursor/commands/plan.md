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
| 只需要需求与技术方案（不拆卡） | `/plan` ✅ |
| 需要后续并行拆解与看板落卡 | `/plan`（建议 `parallel`）后接 `/vkplan` ✅ |
| 只想快速澄清理解 | `/clarify` |
| 一站式从需求到交付 | `/feature` |

> **与 `/clarify` 的区别**: `/plan` 会产出 `<topic>_requirements.md` 与 `<topic>_implementation_plan.md`；`/clarify` 只做问答确认。

---

## 输入模式（新增）

### 命名对齐要求（新增）

`<topic>` 默认与任务拆解目录 `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/` 的 `<主题>` 对齐，优先使用中文主题短语。

1. 新增规划文档默认使用中文主题前缀：`<主题>_requirements.md`、`<主题>_implementation_plan.md`。
2. 若已存在同主题任务拆解目录，命名必须复用同一 `<主题>` 语义，不允许漂移。
3. `task_key` 的英文机读标识独立维护，不强制写入文件名前缀。

### 1) core 模式（默认）

`/plan` 或 `/plan core`

- 产出：`<topic>_requirements.md` + `<topic>_implementation_plan.md`
- 不强制产出 `card_seed`
- 适用于单人/单 AI 主导规划，改动范围可小可大（含跨模块/全局架构）
- 默认无需并行落卡；若后续需要多人并行再切换 `/plan parallel` + `/vkplan`
- 若属于全局改造，`<topic>_implementation_plan.md` 必须显式包含：分阶段路线图、跨模块依赖矩阵、回滚与观测方案

### 2) parallel 模式（并行规划）

`/plan parallel`

- 产出：`<topic>_requirements.md` + `<topic>_implementation_plan.md` + 最小 `card_seed`
- 要求给出 `task_key`（后续卡片前缀）
- 适用于多人/多 AI/多 worktree 并行
- 并行拆解与落卡前准备由后续 `/vkplan` 承接

### 3) hydrate 模式（旧文档沉淀注入）

`/plan hydrate` 或 `/plan parallel hydrate`

- 适用：已有大量历史方案、`output/**` 分析、专题计划，但执行链已跑偏或信息分散。
- 目标：把现有沉淀“压缩进”新的 `requirements + implementation_plan`，避免后续 `/vkplan` 丢信息。
- 约束：`hydrate` 只允许重组与对齐，不新增“第四类主文档”。

`hydrate` 时必须显式列出输入来源（建议写入 implementation plan 的“输入来源清单”）：

1. 总控/波次：`openclaw全量迁移_implementation_plan.md`、`迁移执行波次_implementation_plan.md`
2. 专题计划：P1~P6 对应 implementation 文档
3. 分析沉淀：`output/openclaw源码解析/**`（仅抽取与当前功能点直接相关的证据）
4. 历史并行拆解：`docs/内部参考/任务拆解/**`（仅复用可验证的结构与门禁，不继承失效口径）

---

## 1. 需求分析 (Requirement Analysis)

**产出**:
1. 迭代级概览：`docs/内部参考/迭代需求/<topic>_requirements.md`
2. 模块级需求：`docs/产品文档/<模块>需求.md`

**必须包含**:
1. **用户故事**: 谁？在什么场景？想要做什么？为什么？
2. **验收标准**:
   - 功能性: Happy Path
   - 异常/边界: 断网、非法输入、超长文本
   - 性能/稳定性: 关键路径耗时、重试/超时
3. **非功能需求**: 性能、安全、数据一致性
4. **关联测试**: 预留 TC 编号（便于追溯矩阵）
5. **业务场景**: 结合银行工作场景（如贷款/存款/分行/合规约束）

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
3. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/...`（由 `/vkplan` 产出）
4. 其余仅允许作为“输入来源”被引用，不得升级为新的主计划文档类别。

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

### 2.B 与 `/vkplan` 的机读契约（必填）

`<topic>_implementation_plan.md` 必须在末尾给出一个 YAML 代码块，供 `/vkplan` 直接消费：

```yaml
planning_contract:
  execution_mode: serial  # serial | parallel
  card_order: [C01, C02, C03, C04, C05, C06]
  strict_single_active_card: true
  cards:
    - card_id: C01
      wave: P1
      feature_ids: [P1-01, P1-02, P1-03, P1-04, P1-05]
      depends_on: []
      done_gate:
        - P1-01~P1-05 tests green
        - cancel_after_token_count=0
```

说明：

1. 若你要串行执行（自动执行场景），`execution_mode` 必须是 `serial`。
2. `card_id`/`feature_id` 一旦发布，不得在 `/vkplan` 阶段重命名。
3. `/vkplan` 只能细化，不能改写 `depends_on` 的硬依赖。

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

并要求 `/vkplan` 在 WS 文档中同步“契约 owner + 消费只读方”关系。

### 2.3 并行拆解种子（仅 parallel 模式必填）

仅当命令为 `/plan parallel` 时，`<topic>_implementation_plan.md` 必须追加“可拆解种子信息”。

最小字段：

1. `task_key`（全局唯一，建议 `PP-YYYYMMDD-主题`）
2. `card_seed`（YAML 或表格）
   - `cap_id`
   - `title`
   - `hard_depends_on`
   - `soft_depends_on`
   - `file_scope`
   - `owner_fields`
   - `check_cmd`
   - `dod`

补充规则：

1. `hard_depends_on` 仅用于阻塞依赖；非阻塞引用写入 `soft_depends_on`。
2. `file_scope` 必须可映射到后续 WS 白名单。
3. 未提供 seed 时，`/vkplan` 可临时补齐，但必须在 `parallel_plan.md` 标注“seed 来源为 vkplan 推导”。

## 3. 与 `/vkplan` 的关系（澄清）

`/plan` 与 `/vkplan` **不是二选一的替代关系**，而是分工关系：

1. `/plan` 负责“需求与架构正确性”。
2. `/vkplan` 负责“并行拆包与可执行边界”。
3. 当走 `core` 模式时，可直接 `/imp`；当走 `parallel` 模式时，推荐 `/vkplan -> /vktodo -> /imp-ws`。

## 4. 信息不丢失要求（新增）

为避免“计划正确但执行跑偏”，`/plan` 输出时必须满足：

1. `implementation_plan` 的每个功能点都能映射到唯一 `feature_id`。
2. 每个 `feature_id` 都有：机制描述 + 代码锚点 + 验证命令 + 回滚锚点。
3. 每个卡片（`card_id`）都绑定明确 `feature_id` 列表，禁止“统一模型基线迁移”这类泛化标题替代。
4. 引用 `output/**` 时只允许“证据引用”，不允许把长篇分析原文直接复制到卡片描述。
5. 若存在历史执行偏差，需在计划中新增“偏差修复清单”，明确哪些旧卡作废、哪些卡重建。

## 5. 衔接下游

规划完成后：
- 并行场景：执行 `/vkplan` 进行并行拆解（继承主从关系、契约冻结与 `task_key/card_seed`）
- 看板场景：执行 `/vktodo` 直接落卡；其前置会自动完成 G0 基线校验
- 单任务实现：执行 `/imp`
- 测试设计：执行 `/test` 基于模块需求文档生成测试用例

---
*使用 `/plan` 触发。是开发周期的正式起点。*
---
