# VK 依赖分析报告 — 方案评审报告

> 评审日期：2026-02-27
> 评审对象：`docs/内部参考/迭代需求/vibe_kanban依赖分析报告.md`（947 行）
> 评审方式：team+ralph 三路并行评审（架构评审 / 方案批判 / 完整性审查）
> 评审结论：**方向正确，实施路径存在重大前置风险，需补强后方可执行**

---

## 1. 总体评价

报告的核心决策——将 VK 从执行链路移除、降级为只读展示——**完全正确**。VK 的能力错误归因分析（3.1 节）有充分的代码证据支撑，五方一致性校验确实是脆弱性的根源。

但方案在"用什么替代"这个问题上存在两个关键盲区：
1. **heartbeat 机制是假设性方案**，非已验证能力
2. **工时估算过于乐观**，多项成本被遗漏

---

## 2. 关键发现（按严重程度排序）

### 2.1 [Critical] Heartbeat 机制未经验证

这是本次评审发现的最严重问题。报告第 7 章的核心前提是"OpenClaw heartbeat 替代 cron"，但经实际验证：

| 验证项 | 结果 |
|--------|------|
| `jobs.json` 中是否存在 `"kind": "heartbeat"` | **不存在**，两个 job 均为 `"kind": "cron"` |
| `HEARTBEAT.md` 是否存在 | **不存在**（`~/.openclaw/workspace-dev/HEARTBEAT.md`） |
| `AGENTS.md` 中 heartbeat 描述 | 仅一行可选说明："HEARTBEAT.md can hold a tiny checklist for heartbeat runs; keep it small." |
| OpenClaw cron runner 是否识别 `kind: heartbeat` | **无证据** |

报告将一个"可选的文件约定"包装成了一个"已就绪的调度引擎"。如果 OpenClaw 不支持 `kind: heartbeat`，Phase 1 的核心改造无法实施。

**建议**：实施前必须做 PoC——在 `jobs.json` 中创建测试 job 验证 `kind: heartbeat` 是否被识别。如果不支持，改为 `kind: cron` + `bootstrap_kernel --local-mode` 的状态感知方案（效果等价）。

### 2.2 [Critical] 工时估算从 11-18 降到 7-11 的理由不成立

| 遗漏项 | 估算影响 |
|--------|---------|
| heartbeat 调度能力验证/实现 | +1-3 天 |
| 3000 字符 cron payload 行为约束迁移 | +1-2 天 |
| attempt 系统完整替代（container_ref、merge API） | +1-2 天 |
| 仓外改造（WORKFLOW_AUTO 459 行、VK_AGENT_PROMPTS 627 行） | 未充分计入 |

独立评估：**10-16 人天**（vs 报告的 7-11）。

### 2.3 [Major] `consecutiveErrors: 9` 的归因错误

报告 7.1 节将 `consecutiveErrors` 作为 cron 机制缺陷的证据，但实际上：
- `consecutiveErrors: 9` 出现在 **ragflow_kb** job 上（Telegram 投递失败），与 VK 无关
- **coder4** job 的 `consecutiveErrors: 0`，`lastStatus: "ok"`

用另一个 job 的故障来论证 coder4 的调度机制有问题，削弱了"cron 有结构性缺陷"的论点。

### 2.4 [Major] "五方一致性降级为三方"并未真正降低复杂度

原五方：`_active_task.json` / `vk_cards.json` / VK 看板 / `parallel_plan.md` / coder4 状态

新方案实际需要保持一致的文件：`_active_task.json` / `vk_cards.json` / `task-runner-state.json` / `HEARTBEAT.md` / coder4 状态 —— 仍然是**五方**，只是换了载体。

### 2.5 [Major] cron payload 3000 字符行为约束的迁移目标不明

`jobs.json` 中 coder4 的 `payload.message`（约 3000 字符）包含：
- 固定真理源路径声明（5 个文件路径）
- 硬顺序执行协议（6 个步骤 + 子步骤）
- 分支决策矩阵（7 个 action 分支）
- 硬约束清单（10+ 条禁止规则）
- 输出格式模板

这些是 **LLM 行为约束指令**，不是"任务清单"。报告 7.2.1 节设计的 HEARTBEAT.md 只有约 20 行简单清单，两者**语义完全不等价**。报告没有说明这些约束的迁移目标。

### 2.6 [Major] attempt 系统的本地替代方案不等价

报告 3.2.3 节用 `.omc/state/attempts/<card_id>/` 目录替代 VK attempt。但 VK attempt 的实际用途远超"记录执行历史"：

| attempt 能力 | 本地方案是否覆盖 |
|-------------|----------------|
| 记录执行历史 | 覆盖 |
| `container_ref` + `agent_working_dir`（代码执行环境引用） | **未覆盖** |
| `POST /api/task-attempts/{attempt_id}/merge`（触发合并） | **未覆盖** |
| `DONE_GATE_CHECK` 必须在 `attempt_repo_dir` 中执行 | **未覆盖** |

### 2.7 [Minor] VK 引用数量偏差

报告声称"约 156 处（21 个文件）"，实际 grep 验证为约 203 处。文件数一致但引用数偏低约 30%。

---

## 3. 架构评审（7 维度评级）

| 维度 | 评级 | 关键问题 |
|------|------|---------|
| 架构分层合理性 | CONCERN | `dispatch_coder4` 跨层；`HEARTBEAT.md` 混合状态与编排；`wt-flow.sh` 新增 next/verify 违反单一职责 |
| 状态管理设计 | CONCERN | "唯一真理源"不准确，实为分层真理源；`card_order` 在 `vk_cards.json` 和 `task-runner-state.json` 中冗余 |
| heartbeat vs cron | CONCERN | heartbeat 未验证；cron 的确定性/可观测性/简单性优势被忽略 |
| bootstrap_kernel 本地化 | PASS（附条件） | L231 唯一读取点已验证；`dispatch_coder4` 不属于 kernel 职责应移除 |
| 故障恢复设计 | CONCERN | 不可重试错误清单不完整（遗漏 vk_cards.json 格式错误等 5 项）；`write_json` 非原子写入 |
| VK 只读推送 | PASS（附条件） | fire-and-forget 正确；缺少 `resolve_vk_task_id` 缓存策略和定期全量同步 |
| 与 OpenClaw 耦合度 | CONCERN | 单点故障从 VK 转移到 OpenClaw；无 OpenClaw 不可用时的降级方案 |

---

## 4. 被忽略的替代方案

### 方案 A：保留 cron + 移除 VK API 依赖（最小改动）

报告完全没有考虑这个最简方案：

- `build_kernel_context()` L231 改为从本地 JSON 读取
- `apply_action()` 改为写本地 JSON
- cron payload 保持不变（3000 字符行为约束仍有效）
- 不需要 heartbeat，不需要 HEARTBEAT.md，不需要改 jobs.json 的 kind

**估算工作量：3-6 人天**。可作为 Phase 0，后续再评估是否需要 heartbeat。

### 方案 B：修复 VK 稳定性

coder4 当前 `consecutiveErrors: 0`，`lastStatus: "ok"`。如果 VK 不稳定主要来自 MCP 502，可在 `bootstrap_kernel.py` 中加入 retry + fallback to local。成本：0.5-1 人天。

---

## 5. 关键风险 TOP 3

| 排名 | 风险 | 严重度 | 建议 |
|------|------|--------|------|
| 1 | heartbeat 机制未验证即作为核心调度 | 极高 | 实施前做 PoC；准备 fallback 方案（保留 cron + --local-mode） |
| 2 | 单点故障从 VK 转移到 OpenClaw | 高 | `bootstrap_kernel --local-mode` 应可通过系统 `crontab` 独立调度 |
| 3 | `task-runner-state.json` 非原子写入 | 中 | 改为 write-to-temp + `os.rename`；保留 `.bak` 备份 |

---

## 6. 必须的前置验证（按优先级）

| 优先级 | 验证项 | 方法 |
|--------|--------|------|
| P0 | OpenClaw 是否支持 `kind: heartbeat` | 在 `jobs.json` 中创建测试 job，观察是否被调度 |
| P0 | 3000 字符 cron payload 的迁移目标 | 明确行为约束放在 HEARTBEAT.md / WORKFLOW_AUTO.md / 还是其他位置 |
| P1 | attempt 系统完整替代方案 | 明确 `container_ref`、`agent_working_dir`、merge API 的本地化实现 |
| P1 | 考虑"保留 cron + 去 VK API"作为 Phase 0 | 风险最低的第一步，可立即解除 VK 阻断 |
| P2 | 补充 VK 实际故障频次数据 | 从 OpenClaw 日志中统计 coder4 因 VK 导致的失败次数 |

---

## 7. 改进建议汇总

### 架构层面
- `dispatch_coder4` 从 bootstrap_kernel 模块拆分中移除（不属于 kernel 职责）
- `HEARTBEAT.md` 拆分为任务清单（状态层）和执行协议（编排层）
- `wt-flow.sh` 的 `next/verify/list` 独立为 `task-runner.sh`，与 worktree 管理解耦
- 明确三层真理源层级：`_active_task.json`（作用域）> `vk_cards.json`（卡片定义）> `task-runner-state.json`（运行时状态）

### 可靠性层面
- `write_json` 改为 write-to-temp + atomic rename
- 补充不可重试错误清单（vk_cards.json 格式错误、_active_task.json 字段缺失、文件权限等）
- 设计 OpenClaw 不可用时的降级路径（`bootstrap_kernel --local-mode` 可通过系统 crontab 独立调度）
- VK 只读推送增加定期全量同步机制

### 工时层面
- 修正估算为 10-16 人天（补充 heartbeat 验证、payload 迁移、attempt 替代成本）
- 新增 Phase 0：保留 cron + 去 VK API（3-6 天），作为最低风险起步

---

## 8. 评审结论

| 项目 | 评价 |
|------|------|
| 问题分析质量 | 优秀（VK 能力错误归因分析有充分代码证据） |
| 方案方向 | 正确（VK 从执行链路移除是合理决策） |
| 实施路径 | 需补强（heartbeat 未验证、工时低估、attempt 替代不完整） |
| 风险识别 | 部分遗漏（OpenClaw 耦合风险、非原子写入、payload 迁移） |
| 可执行性评分 | **6/10**（补强前置验证后可提升至 8/10） |

**建议的下一步**：
1. 先做 heartbeat PoC 验证（1 天）
2. 如果 heartbeat 不可用，采用"保留 cron + --local-mode"方案（方案 A）
3. 如果 heartbeat 可用，按修正后的路线图执行（补充 Phase 0）

---

*评审完成。三路评审 agent：架构评审（architect/opus）、方案批判（critic/opus）、完整性审查（quality-reviewer/sonnet）。*
