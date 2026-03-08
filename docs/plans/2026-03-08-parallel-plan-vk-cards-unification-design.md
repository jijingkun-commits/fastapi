# parallel_plan 降级为自动生成总览设计

## 背景

- 当前拆卡链同时维护 `parallel_plan.md` 与 `vk_cards.json` 两份并行计划信息。
- `jjk-cardrun`、`wt-flow`、`wtimp` 的机器消费主入口实际已经收敛到 `vk_cards.json`。
- `parallel_plan.md` 仍承担 Gate 回填与人工总览职责，导致“执行真理源”和“展示视图”混杂，存在双写漂移风险。

## 决策

- `vk_cards.json` 升级为拆卡阶段唯一机器真理源。
- `parallel_plan.md` 降级为自动生成的人类可读总览，不再承担唯一状态归属。
- Gate 结果、Gate 契约、工作流总览优先写入 `vk_cards.json`；`parallel_plan.md` 由 `vk_cards.json` 渲染生成。

## 边界与取舍

- 保留 `implementation_plan.md` 作为上游设计真理源，不回写运行态 Gate 结果。
- 保留 `parallel_plan.md` 文件路径，避免现有文档引用、人工阅读与历史目录结构一次性断裂。
- 对消费侧采用兼容迁移：
  - `gate_contract` 校验不再强依赖 `parallel_plan.md` 存在；
  - `backfill_gate_status.py` 改为优先回写 `vk_cards.json`，并同步生成 `parallel_plan.md`；
  - 规则文档改口径：`parallel_plan.md` 为可选生成视图，不再是机器真理源。

## 数据归属

### 继续归 `implementation_plan.md`

- `planning_contract`
- `execution_contract`
- `implementation_tasks`
- `task_to_pr_mapping`

### 统一归 `vk_cards.json`

- `execution_mode`
- `single_active_card`
- `auto_done_policy`
- `card_order`
- `gate_contract`
- `preflight`
- `source_files`
- `cards[*]`
- `mapping_checks`
- `gate_results`（新增，作为 Gate 运行态真理源）

### 降级为生成视图的 `parallel_plan.md`

- 执行策略摘要
- 卡片/WS 总览
- 来源文件索引
- 预检摘要
- Gate 结果展示

## 实施步骤

1. 更新工作流文档与模板，声明 `vk_cards.json` 为唯一机器真理源。
2. 为 `parallel_plan.md` 增加渲染器，支持从 `vk_cards.json` 自动生成 Markdown 总览。
3. 重构 `backfill_gate_status.py`：先回写 `vk_cards.json.gate_results`，再生成 `parallel_plan.md`。
4. 重构 `gate_contract` 校验：`parallel_plan.md` 改为可选兼容输入。
5. 为新行为补最小单元测试，覆盖 Gate 回填与无 `parallel_plan.md` 场景。

## 验证策略

- `backfill_gate_status.py` 在 dry-run / 非 dry-run 下都能产出一致 Gate 摘要。
- `workflow_contract_gate_contract_impl.run_check` 在缺少 `parallel_plan.md` 时仍可用 `vk_cards + implementation_plan` 通过校验。
- 生成的 `parallel_plan.md` 包含执行策略、卡片总览、Gate 结果三块核心信息。

## 风险

- 历史文档中仍会出现“手写 `parallel_plan.md`”口径，需要规则同步迁移。
- 部分历史任务拆解目录未包含新 `gate_results` 字段，需兼容旧结构。
- 若未来需要更强的人类可编辑编排文档，应新建独立说明文档，而不是恢复 `parallel_plan.md` 的真理源角色。
