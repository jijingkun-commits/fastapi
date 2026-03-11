---
name: jjk-refactor
description: "Use when you need `jjk-refactor` in this repository. Source intent: 重构入口（消费 plan/review）：在行为等价前提下完成结构改造并证据化交付，支持大范围自动 Team"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-refactor.md -->

# 代码重构工作流 (Refactor Workflow)

`$jjk-refactor` 是 `jjk-*` 体系里的重构入口，负责在不改变业务语义前提下提升可维护性、可测试性和可扩展性。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）
## 跨 IDE 调用方式
## 模板来源优先级（跨项目，强制）

`$jjk-refactor` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_refactor_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_refactor_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。
`GLOBAL_TEMPLATE_MISSING` 属于全局预检失败标记，可与命令级 `FAIL_FAST` 标记并存。

## 输入前置（强制）

至少提供以下输入之一：

1. `implementation_plan`（含重构任务 `task_id`、目标文件、验收命令）；
2. `review_report_<topic>.md`（含技术债/复杂度问题）；
3. 明确重构目标 + 行为不变约束 + `task_id`（`pr_id` 可选）。

硬约束：

1. 缺少 `task_id`（`pr_id` 可选），`FAIL_FAST` 输出 `REFACTOR_INPUT_INCOMPLETE`。
2. 无法界定重构范围（文件/符号/模块），`FAIL_FAST` 输出 `REFACTOR_SCOPE_UNCLEAR`。
3. 缺少行为基线（现有测试或可执行断言），`FAIL_FAST` 输出 `REFACTOR_BASELINE_MISSING`。
4. 重构后出现行为漂移，`FAIL_FAST` 输出 `REFACTOR_BEHAVIOR_DRIFT`。
5. 未产出重构报告，`FAIL_FAST` 输出 `REFACTOR_REPORT_MISSING`。
6. 未冻结 `obsolete_paths` / `retained_paths` / `single_entry_owner` / `line_budget`，`FAIL_FAST` 输出 `REFACTOR_SHRINK_CONTRACT_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

补充执行约束：执行命令时统一遵循 `.cursor/rules/core.mdc` 的“命令执行拆分”规则：单步单目标、失败只重跑当前步、长任务只轮询不重启、输出截断时优先拆短当前步。

至少检查：

1. 当前实现的复杂度热点（重复逻辑、超长函数、耦合点）。
2. 相关业务契约与边界行为。
3. 现有测试覆盖和薄弱区。

### 0.5) 大范围重构自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 待改文件 `>= 15`；
2. 涉及模块 `>= 3`；
3. 同时涉及后端+前端+数据库/配置两类以上边界；
4. 需要并行处理三类以上代码异味（重复、复杂度、性能）。

执行策略：

1. **有 Team 能力时**：按模块/异味类型并行拆分重构，Leader 汇总统一报告。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束

1. Team 模式下，每个成员提交阶段结果后，必须由另一名成员执行反方审查，至少包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
2. `2` 人任务执行双向互审；`3+` 人任务执行环形互审（A 审 B，B 审 C，...，最后一人审 A）。
3. 未通过交叉审查的子任务不得标记完成；出现审查冲突时，必须创建复核子任务并附证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。
5. 仅在 `pending=0`、`in_progress=0` 且交叉审查冲突清零后，才允许进入收尾或关停。

### 1) 锁定等价性约束

1. 明确“不能改变”的行为清单（接口、返回结构、副作用、性能阈值）。
2. 对每项约束绑定验证证据（测试用例/命令/日志断言）。
3. 无法验证的约束必须先补证据再开工。

### 1.5) 冻结瘦身合同

1. 明确 `obsolete_paths`、`retained_paths`、`single_entry_owner`、`line_budget`。
2. 若引入替代实现，旧路径必须同步删除；确需保留时给出唯一理由与失效条件。
3. 未冻结瘦身合同不得进入实施阶段。

### 2) 设计重构切片

1. 拆分为可独立回滚的最小重构单元。
2. 每个单元必须标注：目标文件、改造意图、风险点、验收命令。
3. 复杂重构优先“小步提交 + 连续验证”。

### 3) 实施重构与守护测试

1. 优先执行 `test-driven-development` 契约（先补失败测试再改代码）。
2. 每完成一个切片即执行对应 `acceptance_cmds`。
3. 失败时回退到 `systematic-debugging` 路径定位，不得堆临时补丁。

### 4) 结果验证与质量对照

1. 对照重构前后的行为、复杂度、可维护性指标。
2. 校验性能是否满足目标（若涉及性能优化）。
3. 证据不足时 `FAIL_FAST` 输出 `REFACTOR_EVIDENCE_MISSING`。
4. 若 `obsolete_paths` 未执行或 `retained_paths` 无唯一理由，`FAIL_FAST` 输出 `REFACTOR_OBSOLETE_PATH_RETAINED`。
5. 若本次重构命中 Lean Guard 热点文件，完成重构前必须执行 `python3 scripts/ci/check_lean_budget.py --cached --strict`；失败则 `FAIL_FAST` 输出 `REFACTOR_LEAN_GUARD_FAILED`。

### 5) 报告产出与交接

必须产出：

- `docs/内部参考/迭代需求/refactor_report_<topic>.md`

最小内容：

1. 输入映射（`task_id/card_id/pr_id|none`）
2. 重构切片与改动清单
3. 瘦身合同执行结果（`obsolete_paths` 命中结果、`retained_paths` 保留理由、`single_entry_owner` 收敛结果）
4. 行为等价验证证据
5. 仍待处理项与风险说明
6. 下一步命令建议（`$jjk-review`、`$jjk-verify`）

---

## 输出模板（推荐）

见全局模板：`${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_refactor_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_refactor_templates.md`。

## 禁止项（强制）

1. 禁止无基线测试直接宣称“行为不变”。
2. 禁止在重构阶段引入未声明的新需求。
3. 禁止用临时条件分支掩盖结构问题。
4. 禁止新增实现落地后仍保留同职责旧路径且不给唯一理由。
5. 禁止无报告结束重构流程。

## 推荐链路

`$jjk-review -> $jjk-refactor -> $jjk-review -> $jjk-verify`

## 使用示例

```text
$jjk-refactor
```

```text
$jjk-refactor @docs/内部参考/迭代需求/review_report_<topic>.md
```

---
*使用 `$jjk-refactor` 触发。目标是“结构升级且行为等价”，不是“换个写法就算完成”。*
