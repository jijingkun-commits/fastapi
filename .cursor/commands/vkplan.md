---
description: 并行拆解入口（前提：已完成 /plan，并继承同主题命名）
---

> 参考规则: @dual-database

# VKPlan 工作流 (Split to Executable Cards)

用于在 `/plan` 完成后执行任务拆解，产出可直接供 `/vktodo` 落卡与自动执行器消费的结果。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 定位

- 前置要求：必须先完成 `/plan`
- 核心目标：完成“可执行拆解 + G0 冻结”，生成 `vk_cards.json` 供 `/vktodo` 直接使用
- 关键要求：机读信息不能丢失（机制、代码锚点、验证门禁、回滚锚点都必须落到卡片字段）

---

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 已完成 `/plan`，准备并行拆解 | `/vkplan` ✅ |
| 已完成 `/plan hydrate`，需要把历史沉淀转成可执行卡 | `/vkplan` ✅ |
| 尚未完成需求与技术方案 | 先 `/plan` |
| 已有完整拆解产物，仅需重落卡 | `/vktodo` |

---

## 命名衔接（与 `/plan` 强一致）

1. `/vkplan` 必须读取同一主题的 `/plan` 产物：
   - `docs/内部参考/迭代需求/<主题>_requirements.md`
   - `docs/内部参考/迭代需求/<主题>_implementation_plan.md`
2. 并行拆解目录必须与同一 `<主题>` 对齐：
   - `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/`
3. 拆解产物中的来源引用必须保持一致：
   - `parallel_plan.md` 的“输入来源”
   - `workstreams/WS-*.md` 的“来源主计划”
   - `vk_cards.json` 中涉及主计划的 `file_scope`
4. 若 `/plan` 命名规则更新，`/vkplan` 需同步继承，不得回退到旧通用名。

---

## 机读契约继承（强制）

`/vkplan` 必须优先读取 implementation plan 末尾 `planning_contract`：

1. `execution_mode`（`serial|parallel`）
2. `card_order`（例如 `C01..C06`）
3. `cards[].feature_ids`
4. `cards[].depends_on`
5. `cards[].done_gate`

规则：

1. 若 `execution_mode=serial`，必须产出“单活串行”卡片编排（同一时刻仅 1 张卡可进入 Doing）。
2. 不得在 `/vkplan` 阶段重命名 `card_id` / `feature_id`。
3. 不得弱化 `depends_on` 的硬依赖。
4. `feature_id` 必须一一映射到 `WS`（或 `Card WS`）文档中的功能机制段。

---

## 执行阶段

1. 读取 `/plan` 产物（`<主题>_requirements.md`、`<主题>_implementation_plan.md`）。
2. 读取 `implementation_plan` 中的“功能机制包（Feature Packet）”与 `planning_contract`。
3. 生成拆解产物（`parallel_plan.md` + `workstreams/WS-*.md`），并在 WS 中保留机制细节与代码样例锚点。
4. 在拆解阶段完成 G0（`WS-00`）冻结与机读契约。
5. 生成 `vk_cards.json`（默认落卡范围不含 `WS-00`）；仅在需要批量导入提示时生成 `vk_import_prompt.txt`。

若任一阶段失败，立即停止并给出系统性修复建议（含架构归因与维护性影响）。

---

## 信息不丢失映射（新增）

`vk_cards.json.cards[*]` 至少包含以下字段（可扩展，不可省略）：

1. `feature_ids`
2. `mechanism_summary`
3. `code_anchor_refs`
4. `example_refs`
5. `acceptance_checks`
6. `rollback_anchors`
7. `evidence_entry`
8. `task_mode`（`implementation-card|inspection-card|question-card`）
9. `merge_required`

约束：

1. `mechanism_summary` 必须来自 implementation plan 的功能机制包，不允许自由改写语义。
2. `example_refs` 只放“最小样例路径/片段锚点”，不塞大段正文。
3. `acceptance_checks` 必须可直接执行（命令级）。
4. `evidence_entry` 必须指向权威回填位置（例如 `迁移执行波次_implementation_plan.md` 具体节）。

---

## 字段完整性硬拦截（新增）

`/vkplan` 在写入 `vk_cards.json` 前必须做完整性校验。以下任一字段缺失时，直接 `FAIL_FAST` 并停止产出：

1. `feature_ids`
2. `mechanism_summary`
3. `code_anchor_refs`
4. `acceptance_checks`
5. `rollback_anchors`
6. `evidence_entry`
7. `task_mode`
8. `merge_required`

补充：

1. 不允许“留空后执行期补齐”。
2. 不允许把缺失字段降级到自然语言备注。
3. 校验失败时必须输出“缺失字段清单 + 影响 card_id + 修复建议”。

---

## Feature/Card 双向覆盖校验（新增）

为防止 feature 漏卡或重复漂移，`/vkplan` 必须输出双向校验结果：

1. **forward check**：每个 `card_id` 至少绑定 1 个 `feature_id`。
2. **reverse check**：implementation plan 的每个 `feature_id` 必须且仅能映射到 1 张实现卡。
3. **orphan check**：不允许存在未被任何卡片承载的 `feature_id`。
4. **duplicate check**：除明确声明“共享检查卡”外，同一 `feature_id` 不得重复落在多张实现卡。

任一校验失败时：

1. `vk_cards.json` 标记为不可执行；
2. 不得进入 `/vktodo`；
3. 必须先回填 `implementation_plan` 或重排卡片映射。

---

## 串行执行编排（新增）

当 `execution_mode=serial` 时，`/vkplan` 必须满足：

1. `parallel_plan.md` 写明 `single_active_card=true`。
2. `vk_cards.json` 的 `hard_depends_on` 串成单链（如 `C01 -> C02 -> ...`）。
3. 仅在前置卡满足 `done_gate` 后，后置卡才允许推进。
4. Gate 类卡（如 `G1/G2`）默认串行，不可并行推进。
5. 默认禁止自动 `inreview -> done`（实现卡需人工/门禁确认）。

---

## 与 output 分析的融合规则（新增）

1. `output/**` 只作为“证据来源”，必须先落入 implementation plan 的功能机制包。
2. `/vkplan` 禁止直接把 `output` 长文塞入卡片描述。
3. 每个 WS 仅引用与本功能点直接相关的 1~3 条分析证据。
4. 若分析证据与实现计划冲突，以 implementation plan 为准并记录冲突裁决。

---

## 必做产出

1. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/parallel_plan.md`
2. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-*.md`
3. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/vk_cards.json`
4. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/vk_import_prompt.txt`（可选）

---

## 下游链路

推荐极简链路：`/plan -> /vkplan -> /vktodo -> /imp-ws`

- `/vktodo`：直接落卡/推进（多 worktree 场景默认执行 `/vksync` 硬拦截）
- `/imp-ws`：从并行层 WS 开始执行（`WS-00` 已由前置阶段完成）
- 自动执行器场景：必须以 `vk_cards.json` 为唯一执行输入，不允许自由重写卡标题与 DoD

手工分步链路（调试用）：`/plan -> /vkplan -> /vksync -> /vktodo`

---
*使用 `/vkplan` 触发。用于“完成拆解后直接进入 `/vktodo`”。*
---
