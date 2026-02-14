---
description: 正式规划：默认产出 requirements.md 与技术方案，可选生成并行 card_seed
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

> **与 `/clarify` 的区别**: `/plan` 会产出 `requirements.md` 与 `implementation_plan.md`；`/clarify` 只做问答确认。

---

## 输入模式（新增）

### 1) core 模式（默认）

`/plan` 或 `/plan core`

- 产出：`requirements.md` + `implementation_plan.md`
- 不强制产出 `card_seed`
- 适用于单人/单 AI、小范围改动、无需并行落卡

### 2) parallel 模式（并行规划）

`/plan parallel`

- 产出：`requirements.md` + `implementation_plan.md` + 最小 `card_seed`
- 要求给出 `task_key`（后续卡片前缀）
- 适用于多人/多 AI/多 worktree 并行
- 并行拆解与落卡前准备由后续 `/vkplan` 承接

---

## 1. 需求分析 (Requirement Analysis)

**产出**:
1. 迭代级概览：`docs/内部参考/迭代需求/requirements.md`
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

**产出**: `docs/内部参考/迭代需求/implementation_plan.md` (Artifact)

> **唯一产出路径**: `implementation_plan.md` 统一放在 `docs/内部参考/迭代需求/`，不再使用仓库根目录路径。

**内容**:
1. **架构变更**: 涉及哪些模块？数据库要改吗？
2. **API 设计**: 接口定义
3. **风险评估**: 哪里容易出 Bug？

### 架构评审必查项

在输出 `docs/内部参考/迭代需求/implementation_plan.md` 前，必须补充“架构影响与约束”，至少包含：

1. **模块边界**：策略属于哪个层（Prompt / Workflow / Node / Frontend），是否越层；避免同一决策分散在多个节点重复实现。
2. **状态契约**：关键字段 canonical 定义、来源优先级、生命周期（创建/合并/清理），是否存在别名漂移风险。
3. **路由闭环**：从意图分析到澄清/消歧/确认/执行的收敛路径，是否存在“回到同一追问”的循环风险。
4. **端到端链路**：前端上下文（如 `current_todo_id`）到后端状态注入的时序一致性，是否会在发送前被提前清理。
5. **可测试性**：以上四项是否有对应单测/联测覆盖，缺口需在计划中显式列出。

### 2.1 主从文档机制

当某个子域存在“专项架构重构”且复杂度明显高于主计划时，采用“主计划 + 专项附录”模式：

1. 主计划固定为：`docs/内部参考/迭代需求/implementation_plan.md`
2. 专项附录命名：`docs/内部参考/迭代需求/implementation_plan_<主题>.md`
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

仅当命令为 `/plan parallel` 时，`implementation_plan.md` 必须追加“可拆解种子信息”。

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
3. 当走 `core` 模式时，可直接 `/imp`；当走 `parallel` 模式时，推荐 `/vkplan -> /vktodo（或 /vkkb） -> /imp-ws`。

## 4. 衔接下游

规划完成后：
- 并行场景：执行 `/vkplan` 进行并行拆解（继承主从关系、契约冻结与 `task_key/card_seed`）
- 看板场景：执行 `/vktodo`（或 `/vkkb`）直接落卡；其前置会自动完成 G0 基线校验
- 单任务实现：执行 `/imp`
- 测试设计：执行 `/test` 基于模块需求文档生成测试用例

---
*使用 `/plan` 触发。是开发周期的正式起点。*
---
