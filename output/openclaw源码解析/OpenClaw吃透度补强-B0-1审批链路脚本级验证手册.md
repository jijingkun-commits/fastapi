# OpenClaw 吃透度补强：B0-1 审批链路脚本级验证手册

> 文档类型：验证手册（动态链路）  
> 创建日期：2026-02-18  
> 目标：验证 OpenClaw exec 审批链路在四类决策下的真实行为，避免“只看源码不跑链路”

---

## 0. 验证目标

B0-1 要回答一个硬问题：

**审批机制是否在真实运行中按预期决定“可执行 / 不可执行 / 超时兜底”**，并形成完整证据链。

需要覆盖 4 类决策：

1. `allow-once`
2. `allow-always`
3. `deny`
4. `timeout`（无人审批）

---

## 1. 代码锚点（本手册依据）

### 1.1 Node host 审批路径

- `../bot/openclaw/src/agents/bash-tools.exec.ts`（约 `512+` 行）
  - `requiresExecApproval(...)`
  - `exec.approval.request`
  - `node.invoke`

### 1.2 Gateway host 审批路径

- `../bot/openclaw/src/agents/bash-tools.exec.ts`（约 `699+` 行）
  - allowlist 校验
  - `allow-once / allow-always` 分支
  - 超时 fallback 分支

> 这两段是审批行为的主路径，脚本验证需同时覆盖。

---

## 2. 验证前置条件

## 2.1 环境要求

- 可运行 OpenClaw gateway / agent 进程
- 能看到系统事件输出（日志或 event stream）
- 可触发至少一个需要审批的 exec 命令

## 2.2 建议开启的日志字段

验证期建议确保可观测以下字段：

- `approval_id`
- `approval_decision`
- `host`（node/gateway）
- `command`
- `context_key`（如 `exec:<approval_id>`）
- `result`（completed/failed/denied/timeout）

## 2.3 验证产物目录（建议）

在你的项目里统一落：

- `output/openclaw源码解析/验证记录/B0-1/`

每个场景一份 JSON：

- `allow-once.json`
- `allow-always.json`
- `deny.json`
- `timeout.json`

---

## 3. 场景矩阵（必须全过）

| 场景 | 预期 | 必须出现的关键事件 |
|---|---|---|
| S1 allow-once | 当次执行成功，后续同命令仍需审批 | `approval.request` -> `decision=allow-once` -> `invoke` |
| S2 allow-always | 当次成功且 allowlist 持久化，后续可直接执行 | `approval.request` -> `decision=allow-always` -> `allowlist update` |
| S3 deny | 命令不执行，明确拒绝原因 | `approval.request` -> `decision=deny` -> `exec denied` |
| S4 timeout | 命令不执行或按 fallback 策略处理，需有超时证据 | `approval.request` -> no decision -> `approval-timeout` |

---

## 4. 脚本级执行步骤（推荐模板）

> 注意：这里给的是“验证脚本流程模板”，命令可按你的部署环境替换。

## 4.1 通用准备

1. 选一条稳定且无副作用的命令（如只读列目录）。
2. 确保该命令路径会触发审批（security/ask 配置命中）。
3. 记录 `start_ts`，开启日志抓取。

## 4.2 S1：allow-once

1. 触发审批命令（第一次）。
2. 在审批端选择 `allow-once`。
3. 验证本次命令执行成功。
4. 再次触发同命令，验证仍会再次进入审批。

通过标准：

- 第一次：有执行结果；
- 第二次：再次出现审批请求（未被永久放行）。

## 4.3 S2：allow-always

1. 触发审批命令（第一次）。
2. 选择 `allow-always`。
3. 再次触发同命令。
4. 验证第二次可直接执行（或明显减少审批链路）。

通过标准：

- 首次有 `allow-always` 决策；
- 后续相同模式命令可免审批（或命中 allowlist）。

## 4.4 S3：deny

1. 触发审批命令。
2. 选择 `deny`。
3. 验证命令未执行。

通过标准：

- 无命令执行结果；
- 存在 `exec denied` 类日志与审批 ID 对应。

## 4.5 S4：timeout

1. 触发审批命令。
2. 不做审批操作，等待超时。
3. 验证系统按配置 fallback（deny 或其他策略）处理。

通过标准：

- 存在 `approval-timeout` 或等价标识；
- 无“静默成功执行”。

---

## 5. 证据链模板（每场景必须填写）

```json
{
  "scenario": "S1_allow_once",
  "host": "gateway",
  "approval_id": "...",
  "command": "...",
  "decision": "allow-once",
  "timeline": [
    {"ts": "...", "event": "approval.request"},
    {"ts": "...", "event": "approval.decision", "value": "allow-once"},
    {"ts": "...", "event": "exec.invoke"},
    {"ts": "...", "event": "exec.completed", "exit_code": 0}
  ],
  "result": "pass",
  "notes": "..."
}
```

---

## 6. 建议复用的现成测试（若在 OpenClaw 仓库）

可优先查看/运行与审批相关的用例：

- `../bot/openclaw/src/agents/openclaw-tools.camera.e2e.test.ts`

建议命令（按仓库实际命令适配）：

- `pnpm test src/agents/openclaw-tools.camera.e2e.test.ts`

> 目的不是“只跑测试即结束”，而是把测试结果与本手册的动态证据链对齐。

---

## 7. 常见失败与定位

## 7.1 触发不到审批

排查：

- `requiresExecApproval` 前置条件是否命中
- 当前 host（node/gateway）路径是否走对
- ask/security 配置是否过宽

## 7.2 超时后仍执行了命令

排查：

- timeout fallback 配置是否允许自动执行
- 是否存在历史 allowlist 命中
- 场景命令是否与 allow-always 记录重叠

## 7.3 allow-always 后仍持续审批

排查：

- allowlist 持久化是否落盘
- 命令归一化是否一致（路径/参数差异）
- agentId 维度是否切换导致策略隔离

---

## 8. 验证通过门槛（B0-1 DoD）

B0-1 仅在以下条件全部满足时通过：

1. S1~S4 四场景全部执行；
2. 每个场景至少 1 份证据 JSON；
3. 每个场景都能关联唯一 `approval_id`；
4. 无“决策与执行结果矛盾”案例；
5. 产出一份汇总结论（通过/失败/风险）。

---

## 9. 与你当前重构计划的关系

- B0-1 通过前：不建议放大 P2 并发能力；
- B0-1 通过后：可继续 B0-2（registry 恢复）与 B0-3（跨 channel collect）。

也就是说，B0-1 是“能否宣称我们真的吃透执行边界”的第一道门。

