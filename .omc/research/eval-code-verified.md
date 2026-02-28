# 代码实证评估报告：自动化大型任务开发设计方案

> 评估日期：2026-02-27
> 评估方法：深入分析 fastapi 仓库代码、openclaw 源码、coder4 运行时状态
> 评估对象：`docs/内部参考/迭代需求/自动化大型任务开发设计方案.md`（2168 行）

---

## 总体评分：7.2 / 10

**与前三份报告的对比**：前三份报告（critique 7.5、completeness 8.0、architecture 7.8）基于文档交叉审查，本报告基于实际代码验证。代码实证发现了前三份报告未能捕获的关键事实错误，因此评分下调。

---

## 一、CRITICAL 级发现（代码实证）

### C1. Gateway 默认端口错误：设计方案写 42800，实际为 18789

**代码证据**：
- `openclaw/src/config/types.gateway.ts` L280：`port?: number` 注释 "default: 18789"
- 全仓搜索 `42800`：零匹配
- `42873` 是 media host 默认端口，非 gateway

**设计方案引用**：
- Ch 4.1 L318：`hooks_gateway_url: "http://localhost:42800"` ← **错误**
- Ch 5.4 L544：`heartbeat_turn()` 函数签名默认值 `"http://localhost:42800"` ← **错误**
- Ch 9.2 L1219：`os.getenv("OPENCLAW_GATEWAY", "http://localhost:42800")` ← **错误**
- Ch 14.2 前置验证脚本：验证目标 `localhost:42800` ← **错误**

**影响**：所有 hooks 调用将连接到错误端口，静默失败。前置验证脚本本身也会失败。

**修复**：全文替换 `42800` → `18789`，或从 `~/.openclaw/openclaw.json` 的 `gateway.port` 字段动态读取。

**前三份报告状态**：eval-critique C1 指出"端口来源不明"但未给出正确值。本报告首次确认正确端口。

### C2. 认证方式已确认：Bearer Token 必填，设计方案完全未处理

**代码证据**：
- `openclaw/src/gateway/hooks.ts` L158-175：`extractHookToken(req)` 从 `Authorization: Bearer <token>` 或 `X-OpenClaw-Token` header 提取
- `openclaw/src/gateway/server-http.ts` L253-291：`safeEqualSecret(token, hooksConfig.token)` timing-safe 比较
- `hooks.token` 为必填字段：`hooks.enabled=true` 时无 token 直接抛异常
- 速率限制：每 IP 60s 内 20 次认证失败 → 429

**设计方案引用**：
- Ch 9.2 `trigger_next_round()` 代码：`httpx.post(url, json=payload)` ← **无认证 header**
- Ch 14.2 前置验证脚本：`httpx.post(url, json=...)` ← **无认证 header**
- 全文搜索 `Bearer`/`token`/`X-OpenClaw-Token`：零匹配

**影响**：所有 hooks 调用将收到 401 Unauthorized，整个 hooks-first 架构无法工作。

**修复**：
1. `task-runner-state.json` Schema 新增 `hooks_token` 字段（或从环境变量 `OPENCLAW_HOOKS_TOKEN` 读取）
2. 所有 `httpx.post()` 调用增加 `headers={"Authorization": f"Bearer {token}"}`
3. 前置验证脚本增加 token 获取和验证步骤

**前三份报告状态**：eval-critique C1 指出"认证方式完全未知"，本报告首次确认具体机制。

### C3. /hooks/wake 的 mode 参数语义已确认，设计方案描述不完整

**代码证据**：
- `openclaw/src/gateway/hooks.ts` L209-220：mode 仅支持 `"now"` | `"next-heartbeat"`，默认 `"now"`
- `"now"` → 调用 `requestHeartbeatNow()`，250ms coalesce 窗口后立即执行
- `"next-heartbeat"` → 仅注入系统事件，等待下一次定时 heartbeat 自然触发

**设计方案引用**：
- Ch 3.2 触发器能力拆分表：仅提到 `mode: "now"`，未提及 `"next-heartbeat"`
- Ch 9.2 代码示例：`json={"text": prompt, "mode": "now"}` ← 正确但不完整

**影响**：中等。`"next-heartbeat"` 模式可用于低优先级通知场景（如 VK 只读同步），设计方案未利用此能力。

---

## 二、HIGH 级发现（代码实证）

### H1. coder4_task_ledger.jsonl 为空文件（0 字节），证据链断裂

**代码证据**：
- `~/.openclaw/workspace-dev/state/coder4_task_ledger.jsonl`：文件存在但 0 字节
- git log 显示 C01-C06 均已 commit 到 master（最新 bd903a4）
- `coder4_cron_state.json`：`round=54, last_result=ALL_DONE, last_bootstrap_card_id=C05`

**设计方案引用**：
- Ch 7 attempt 系统设计假设 ledger 有历史数据可迁移
- Ch 7.3 能力对比表声称"本地 attempt 替代 VK attempt"

**影响**：
1. C01-C06 的完成缺乏标准化证据记录，可能是手动/非标准路径完成
2. G01（实测证据闭环）Gate 验收将因缺乏证据而无法通过
3. attempt 系统迁移无历史数据可参考

### H2. coder4 主执行 cron job 不在当前 jobs.json 中

**代码证据**：
- `~/.openclaw/cron/jobs.json` 仅含 2 个 job：
  - `ragflow_kb`（每 10 分钟，enabled=true）
  - `coder4 进度提醒`（每 8 分钟，enabled=false）
- 总控手册引用的主执行 job（id `3889e1fe-...`，`*/3 * * * *`）不在此文件中
- 可能在 `~/.openclaw-dev/cron/jobs.json`（手册引用路径）

**设计方案引用**：
- Ch 9.4 cron watchdog 设计基于修改现有 cron expr 从 `*/3` 改为 `0 * * * *`
- 如果主执行 job 路径不确定，P0 阶段的 cron 修改目标文件也不确定

**影响**：P0 阶段回滚方案（"改回 cron expr"）的目标文件路径需要先确认。

### H3. heartbeat.prompt 是配置字段而非文件，注入机制与设计方案描述有偏差

**代码证据**：
- `openclaw/src/config/types.agent-defaults.ts`：`heartbeat.prompt` 是 agent 配置中的字符串字段
- `openclaw/src/infra/heartbeat-runner.ts` L593-604：
  - 默认读取 `HEARTBEAT.md` 文件
  - `heartbeat.prompt` 配置可覆盖默认 prompt
  - Exec 完成事件使用 `EXEC_EVENT_PROMPT` 替代
  - Cron 事件使用 `buildCronEventPrompt(cronEvents)` 替代

**设计方案引用**：
- 附录 B.2 迁移策略：将 3000 字符约束注入 `heartbeat.prompt`
- Ch 0 术语表：`heartbeat.prompt` 描述为"OpenClaw 配置字段"← 正确
- 但 Ch 8.4 jobs.json 改造方案未区分 `heartbeat.prompt`（配置字段）和 `HEARTBEAT.md`（文件）

**影响**：3000 字符约束的注入路径需要明确：是写入 `heartbeat.prompt` 配置字段，还是写入 `HEARTBEAT.md` 文件？两者的生效机制不同。

### H4. /hooks/agent 返回 202 异步执行，设计方案未处理异步结果获取

**代码证据**：
- `openclaw/src/gateway/server-http.ts` L335-361：`/hooks/agent` 立即返回 `202 { ok: true, runId }`
- 实际 agent turn 异步执行，结果通过系统事件注入主会话
- 无同步等待 API，无 webhook 回调机制

**设计方案引用**：
- Ch 9.3 使用 `/hooks/agent` 进行"精准控制"，但代码示例 `httpx.post()` 后直接处理响应
- 未设计如何获取异步执行结果（轮询？等待系统事件？）

**影响**：`dispatch_coder4` 通过 `/hooks/agent` 触发执行后，无法同步获知执行结果。需要设计结果回收机制。

### H5. Transcript pruning 条件已确认，设计方案 R5 缓解措施不够具体

**代码证据**：
- `openclaw/src/infra/heartbeat-runner.ts` L386-403：
  - `captureTranscriptState()` 记录执行前 transcript 文件大小
  - 仅当 LLM 回复为 `HEARTBEAT_OK`（无实质内容）时才 truncate
  - coder4 的实质性输出（dispatch/seed/activate）**不会触发 pruning**
- `isDuplicateMain` L737-742：24 小时内相同文本视为重复，跳过发送

**设计方案引用**：
- Ch 12.1 R5 缓解措施："使用隔离会话 + 定期重置"
- 未给出具体重置频率和上下文保留策略

**影响**：6 张卡片串行执行（每张可能多轮 dispatch），transcript 持续增长。按每轮 ~2000 token 估算，54 轮后约 108K token，可能接近或超过上下文窗口。

### H6. wt-flow.sh 当前仅 5 个子命令，设计方案新增 5 个子命令的工作量被低估

**代码证据**：
- `scripts/wt-flow.sh`：231 行，实现 create/merge/cleanup/status/guard
- 设计方案 Ch 6 要求新增 next/verify/list + 串行/并行执行模式
- 当前 wt-flow.sh 无任何状态文件读写逻辑（状态由 `.omc/state/wt-flow-state.json` 管理，仅记录会话信息）
- 新增的 next/verify 需要读写 `task-runner-state.json`，这是全新的能力

**影响**：P1 阶段 wt-flow.sh 扩展从"小改"变为"中等改造"，需要引入 jq 依赖和原子写入逻辑。

---

## 三、MEDIUM 级发现（代码实证）

### M1. bootstrap_kernel.py 的 VK API 调用比设计方案统计更多

**代码证据**：
- `scripts/coder4_bootstrap_kernel.py` 中的 VK HTTP 调用：
  - L231：`list_tasks()` → `GET /api/tasks?project_id=...`
  - L382：`http_json("PATCH", f"/api/tasks/{task_id}", ...)` → 更新状态
  - L396：`http_json("POST", "/api/tasks", ...)` → 创建任务（seed）
  - L410+：`http_json("PATCH", ...)` → 激活任务（activate）
- 设计方案附录 A.1 统计 HTTP REST 3 处，实际至少 4 处（含 activate）

### M2. _active_task.json 当前指向已完成任务，scope 切换机制需验证

**代码证据**：
- `docs/内部参考/任务拆解/_active_task.json`：指向 `PP-20260221-OPENCLAW-REBUILD-BASELINE`
- `coder4_cron_state.json`：`last_result=ALL_DONE`
- 但 G01-G04 Gate 卡尚未在看板创建

**影响**：设计方案 Ch 5.2 的 `scope_guard` 模块假设 `_active_task.json` 始终指向活跃任务。当前状态（ALL_DONE 但 Gate 未创建）是一个未定义的边界条件。

### M3. OpenClaw 配置使用 YAML/JSON 双格式，设计方案仅提及 JSON

**代码证据**：
- `openclaw/src/config/` 支持 `config.yaml` 和 `.json` 双格式
- `~/.openclaw/openclaw.json` 当前为 JSON 格式
- hooks 配置在 `gateway.hooks` 下，非独立顶层字段

**影响**：设计方案中引用 OpenClaw 配置时应明确路径和格式。

### M4. cron 存储路径与设计方案假设不一致

**代码证据**：
- OpenClaw cron 存储由 `cron.store` 配置字段决定
- 实际路径可能是 `~/.openclaw/cron-store.json` 或 `~/.openclaw/cron/jobs.json`
- 设计方案 Ch 8.4 假设修改 `~/.openclaw-dev/cron/jobs.json`

**影响**：P0 阶段修改 cron 配置时需要先确认实际存储路径。

---

## 四、设计方案假设验证结果

| # | 设计方案假设 | 代码验证结果 | 状态 |
|---|------------|------------|------|
| A1 | Gateway 在 `localhost:42800` 监听 | **错误**，默认端口 18789 | ❌ 不成立 |
| A2 | `/hooks/wake` 和 `/hooks/agent` 无需认证 | **错误**，需要 Bearer Token | ❌ 不成立 |
| A3 | `heartbeat.prompt` 支持 3000 字符注入 | **部分成立**，是配置字段可覆盖，但需区分与 HEARTBEAT.md 的关系 | ⚠️ 需澄清 |
| A4 | OpenClaw Codex 执行超时后状态可恢复 | `/hooks/agent` 支持 `timeoutSeconds` 参数，超时后 job 标记失败 | ✅ 成立 |
| A5 | `os.rename()` 在 macOS APFS 上是原子操作 | POSIX 标准保证 | ✅ 成立 |
| A6 | `jq` 在所有目标环境中可用 | macOS 默认不含 jq，需 brew install | ⚠️ 需确认 |
| A7 | 单一开发者使用，无并发写入 | heartbeat 串行执行确认（250ms coalesce） | ✅ 成立 |

---

## 五、与前三份评估报告的交叉验证

| 前报告发现 | 代码验证结果 | 评价 |
|-----------|------------|------|
| eval-critique C1：端口来源不明 | **确认错误**，正确端口 18789 | 前报告发现正确但未给出答案 |
| eval-critique C2：payload 迁移缺逐条对照 | 设计方案附录 B.4 已补充 31 项 checklist | 前报告发现已被修复 |
| eval-critique H3：verify 命令注入风险 | `eval "$check"` 确实存在，但 acceptance_checks 来源可控 | 风险真实但概率低 |
| eval-critique H5：单点故障转移到 OpenClaw | **确认**，cron watchdog 也依赖 OpenClaw 进程 | 前报告发现正确 |
| eval-architecture 维度 2：hooks-first 评分 9/10 | **需下调**，端口和认证两个核心前提错误 | 实际可行性低于文档评估 |
| eval-architecture 维度 4：Schema 评分 8/10 | 维持，Schema 设计本身合理 | 前报告评价准确 |
| eval-completeness：87% 覆盖率 | 维持，但 3 项未覆盖中 2 项（端口/认证）严重程度上升 | 覆盖率数字不变但质量权重需调整 |

---

## 六、coder4 当前运行状态评估

### 已完成
- C01-C06 全部 commit 到 master（bd903a4 为最新）
- C00 预检通过（preflight_status.json passed=true）
- _active_task.json 正确指向当前任务

### 阻塞项
1. **G01-G04 Gate 卡未落看板**：cron_state 报告 ALL_DONE（scoped done=5），但 card_order 有 10 张卡
2. **证据台账为空**：coder4_task_ledger.jsonl 0 字节，G01 验收无据可依
3. **主执行 cron 路径不确定**：jobs.json 中无主执行 job
4. **cron 当前未运行**：coder4 进度提醒 job enabled=false

### 与设计方案的关系
设计方案是对"下一代"自动化架构的规划。当前 coder4 系统处于"C01-C06 已完成、G01-G04 待推进"的过渡状态。设计方案的实施应在当前任务完全收口后启动。

---

## 七、修复优先级建议

### P0 阻塞项（实施前必须修复）

| # | 问题 | 修复内容 | 工作量 |
|---|------|---------|--------|
| 1 | Gateway 端口错误 | 全文替换 42800 → 18789，改为从配置动态读取 | 0.5h |
| 2 | 认证缺失 | 新增 token 获取逻辑，所有 httpx.post 增加 Bearer header | 1h |
| 3 | 前置验证脚本修复 | 更新端口 + 增加认证 + 增加 token 验证步骤 | 0.5h |

### P1 高优先级（P1 阶段开始前修复）

| # | 问题 | 修复内容 | 工作量 |
|---|------|---------|--------|
| 4 | /hooks/agent 异步结果获取 | 设计结果回收机制（轮询 cron state 或等待系统事件） | 2h |
| 5 | heartbeat.prompt vs HEARTBEAT.md 澄清 | 明确 3000 字符注入的具体路径和优先级 | 1h |
| 6 | Transcript pruning 会话重置策略 | 补充具体重置频率和上下文保留方式 | 1h |
| 7 | cron 存储路径确认 | 确认实际 jobs.json 路径，更新 Ch 8.4 | 0.5h |

### P2 中优先级（实施过程中修复）

| # | 问题 | 修复内容 | 工作量 |
|---|------|---------|--------|
| 8 | VK API 调用统计修正 | 附录 A.1 从 3 处更新为 4 处 | 0.5h |
| 9 | /hooks/wake mode 参数补全 | Ch 3.2 补充 "next-heartbeat" 模式说明 | 0.5h |
| 10 | _active_task ALL_DONE 边界条件 | Ch 5.2 补充 scope_guard 对 ALL_DONE 状态的处理 | 1h |

---

## 八、总结

本报告通过实际代码审查验证了设计方案的核心假设。**两个 CRITICAL 级发现（端口错误 + 认证缺失）是前三份文档审查报告未能确认的事实错误**，直接影响 hooks-first 架构的可行性。

好消息是：这两个问题都是"已知未知"变为"已知已知"，修复成本低（合计 2 小时），不影响整体架构方向。hooks-first + cron-watchdog 的混合方案在修正端口和认证后仍然是正确的架构选择。

设计方案的核心价值——三层真理源、VK 只读降级、分阶段实施——经代码验证后依然成立。

---

*代码实证评估完成。基于 fastapi 仓库 463 行 bootstrap_kernel + 231 行 wt-flow.sh + openclaw 仓库 1123 行 heartbeat-runner + 436 行 server-http 的源码审查。*
