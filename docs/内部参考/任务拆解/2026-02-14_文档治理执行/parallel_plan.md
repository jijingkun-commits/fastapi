# 并行计划书：文档治理执行

> 计划 ID: PP-20260214-DOCS-GOVERNANCE
> 主题: 基于已拍板决策推进 docs 全量治理执行（准确性修正 + 结构收敛 + 门禁收口）
> 输入来源: `docs/内部参考/迭代需求/docs_governance_requirements.md` / `docs/内部参考/迭代需求/docs_governance_implementation_plan.md`

---

## 0. G0 协议冻结

### 0.1 冻结目标

在并行执行前冻结本轮文档治理的“权威源规则、命名规则、模板占位规则”，避免各 WS 发生策略漂移。

### 0.2 冻结范围

1. 权威源规则：命令细节以 `.cursor/commands/*.md` 为权威；`架构设计/` 为设计权威，`代码解读/` 为实现辅助。
2. 命名规则：`内部参考/迭代需求` 维持当前目录结构，不引入双层归档；采用“通用入口 + 专项前缀”命名。
3. 模板规则：`开发工作流.md` 模板代码保留，但必须显式标注“示例占位”。

### 0.3 required/optional 与兼容约束

#### `authority_rule`

- required：`scope`、`authority_source`、`consumer_scope`
- optional：`notes`
- 兼容策略：允许追加新 scope，不允许改写既有 scope 的 authority_source 语义。

#### `naming_rule`

- required：`directory`、`pattern`、`keep_structure`
- optional：`examples`
- 兼容策略：保持 `keep_structure=true`，仅允许补充命名示例，不允许新增归档层级要求。

#### `placeholder_rule`

- required：`marker`、`applies_to`
- optional：`replacement_hint`
- 兼容策略：允许扩展 marker 文案，不允许删除“示例占位”强制提示。

### 0.4 协议机读文件

- `docs/内部参考/任务拆解/2026-02-14_文档治理执行/contracts/doc_governance_contract_v1.json`

### 0.5 owner 与消费方

- 契约 owner：`WS-00_G0_治理协议冻结`
- 消费只读方：`WS-01`、`WS-02`、`WS-03`、`WS-04`、`WS-G1`、`WS-G2`

---

## 1. seed 来源判定

1. `task_key`：`PP-20260214-DOCS-GOVERNANCE`
2. `task_key` 来源：`vkplan 推导`（本轮 `/jjk-plan core` 未产出 parallel seed）
3. `card_seed` 来源：`vkplan 推导`
4. 推导依据：
   - `docs_governance_requirements.md` 中的 P0/P1/P2 与验收标准
   - `docs_governance_implementation_plan.md` 的 Phase 1/2/3 与批次 A/B 清单
5. 风险提醒：
   - 文档去重阶段可能触发跨 WS 文件冲突；若冲突无法隔离，按本计划第 8 节回退串行。

---

## 2. 前置可并行判定（四问）

1. 子任务可独立开始并独立交付：**是**（P0 修正、边界收敛、命名规范可分治）。
2. 文件白名单可做到互斥：**是**（按 WS 分配核心文件 owner）。
3. 关键状态字段可保证单写入权：**是**（Gate 状态仅 G1/G2 回填）。
4. 各子任务可执行局部验证：**是**（以 docs_guard + 文本抽检命令为主）。

结论：**并行通过（受限并行）**。  
并行层以 `WS-01/WS-02/WS-03/WS-04` 分治，Gate 层串行。

---

## 3. 自动拆分依据（冲突图）

### 3.1 冲突与依赖

1. 准确性修正冲突：`README/数据库设计/测试指南/待办Agent设计` 由 `WS-01` 单 owner。
2. 命令百科冲突：`vibe-coding开发技巧.md` 与速查策略由 `WS-02` 单 owner。
3. 边界收敛冲突：`代码解读/*` 与 `架构设计` 边界文案由 `WS-03` 单 owner。
4. 索引与命名冲突：`内部参考/迭代需求` 命名说明与 `SUMMARY` 索引由 `WS-04` 单 owner。
5. Gate 收口冲突：门禁状态回填仅 `WS-G1/WS-G2` 可写。

### 3.2 分组结果

- Foundation：`WS-00`
- 并行交付层：`WS-01`、`WS-02`、`WS-03`、`WS-04`
- 串行门禁层：`WS-G1 -> WS-G2`

---

## 4. 工作包总览

| WS | 名称 | 类型 | 可并行 | hard 依赖 |
|---|---|---|---|---|
| WS-00 | G0 治理协议冻结 | Foundation | 否 | 无 |
| WS-01 | P0 准确性修正 | Parallel | 是 | WS-00 |
| WS-02 | 命令权威源与百科校准 | Parallel | 是 | WS-00 |
| WS-03 | 架构设计与代码解读边界收敛 | Parallel | 是 | WS-00 |
| WS-04 | 迭代需求命名规范与索引治理 | Parallel | 是 | WS-00 |
| WS-G1 | 集成回归门禁 | Gate | 否 | WS-01, WS-02, WS-03, WS-04 |
| WS-G2 | 文档终稿门禁 | Gate | 否 | WS-G1 |

---

## 5. 冲突矩阵（互不干涉硬约束）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|---|---|---|---|
| `docs/README.md` | WS-01 | 否 | 准确性文案单 owner |
| `docs/开发文档/架构设计/数据库设计.md` | WS-01 | 否 | 模型映射单 owner |
| `docs/开发文档/测试管理/测试指南与环境配置.md` | WS-01 | 否 | 测试命令单 owner |
| `docs/开发文档/技巧与速查/vibe-coding开发技巧.md` | WS-02 | 否 | 命令百科单 owner |
| `docs/开发文档/代码解读/多智能体工作流.md` | WS-03 | 否 | 边界收敛单 owner |
| `docs/开发文档/代码解读/多智能体系统详解.md` | WS-03 | 否 | 边界收敛单 owner |
| `docs/内部参考/迭代需求/*` | WS-04 | 否 | 命名规范单 owner |
| `docs/SUMMARY.md` | WS-04 | 否 | 索引收敛单 owner |
| `docs/内部参考/任务拆解/2026-02-14_文档治理执行/parallel_plan.md` | WS-G1/WS-G2 | 否 | Gate 回填单 owner |

---

## 6. 依赖图与里程碑

### 6.1 依赖图

`WS-00 -> {WS-01, WS-02, WS-03, WS-04} -> WS-G1 -> WS-G2`

### 6.2 里程碑

1. M0：治理协议冻结可机读。
2. M1：P0 失准项修复完成。
3. M2：命令百科与权威源口径对齐完成。
4. M3：架构设计/代码解读边界收敛完成。
5. M4：迭代需求命名规范与索引说明完成。
6. M5：集成门禁通过。
7. M6：文档终稿门禁通过并可落卡执行。

---

## 7. 合并策略

1. 合并顺序固定：`WS-00 -> WS-01/02/03/04 -> WS-G1 -> WS-G2`。
2. 并行层若发生白名单冲突，以 owner WS 为准，冲突变更回退。
3. 禁止跳过 `WS-G1` 直接进入 `WS-G2`。

---

## 8. 串行回退说明

- 是否触发：否（当前判定可并行）
- 触发条件：
  1. `vibe-coding开发技巧.md` 与边界文档出现不可分离冲突。
  2. `SUMMARY` 索引改动与并行层文档调整发生高频冲突。
  3. G1 无法完成责任 WS 归因。
- 回退路线：`WS-01 -> WS-02 -> WS-03 -> WS-04 -> WS-G1 -> WS-G2`

---

## 9. 看板导出索引

- `task_key`: `PP-20260214-DOCS-GOVERNANCE`
- 拆解目录 ID: `2026-02-14_文档治理执行`
- WS 总数: `7`（含 `WS-00`）
- 可落卡数: `6`（`WS-01...WS-G2`）
- Gate 总数: `2`
- 默认列流转：`Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则：`<task_key>::<WS-ID>`
- 卡片标题规则：`<WS-ID> <标题> [<task_key>]`

---

## 10. Gate 执行状态

### 10.1 WS-G1 结果

- `docs_guard`：通过（2026-02-14，`python3 scripts/docs_guard.py --strict` -> `errors=0`，`warnings=0`，`summary_coverage=104/104`）
- 路径抽检：通过（`app/ai/workflow/data_graph.py` 命中 2 处；`示例占位` 命中 2 处）
- 责任归因：完成（DOC-GATE-001/003/004 -> WS-04；DOC-GATE-002 -> WS-03）

### 10.2 WS-G2 结果

- 文档终稿一致性复核：通过（`docs/文档梳理与重构方案_2026-02-13.md` 已回填 Gate 收口结果与发布摘要）。
- 索引与命名规则复核：通过（`docs/SUMMARY.md` 与 `2026-02-14_文档治理执行` 拆解目录入口一致，迭代需求入口可追溯）。
- 终稿门禁命令：通过（2026-02-14，`python3 scripts/docs_guard.py --strict` -> `errors=0`，`warnings=0`，`summary_coverage=104/104`）。

---

## 11. Gate 收口结果

1. `WS-G1` 已执行：是（2026-02-14）
2. `WS-G2` 已执行：是（2026-02-14）
3. Gate 结论：`WS-G1`、`WS-G2` 均通过，文档治理任务可按 `Gate -> Done` 收口。
