# OpenClaw 吃透度补强：B1/B2 扩展验证手册

> 文档类型：扩展验证手册（高保真复刻）  
> 创建日期：2026-02-18  
> 目标：在 B0 完成后，补齐 Sandbox 生命周期与 Cron 边界验证，并给出 B2 延后项的可执行验收框架。

---

## 0. 使用边界

本手册用于：

- **B1（建议补）**：提升“高保真复刻”可信度；
- **B2（可延后）**：建立后续扩展模块的验收模板。

前置条件：

- B0-1/B0-2/B0-3 已完成或至少具备基础证据链；
- 已有统一事件日志与验证产物目录。

建议目录：

- `output/openclaw源码解析/验证记录/B1-B2/`

---

## 1. B1-1：Sandbox 生命周期实测

## 1.1 验证目标

验证 `workspaceAccess = ro/rw/none` 三种模式下：

1. 工具可见性是否符合策略；
2. 实际执行权限是否与宣称一致；
3. 生命周期事件是否完整（创建、运行、销毁）。

## 1.2 场景矩阵

| 场景 | access | 预期 | 必须证据 |
|---|---|---|---|
| S1 只读访问 | `ro` | 读类工具可用，写类拒绝 | allow/deny 事件 + 错误码 |
| S2 可写访问 | `rw` | 读写按策略允许，危险操作仍需审批/拦截 | policy_applied + approval 证据 |
| S3 无工作区 | `none` | 文件类工具整体不可用或降级 | 工具可见性与执行结果一致 |
| S4 生命周期回收 | 任一模式 | run 结束后沙箱正确回收 | sandbox_created/sandbox_closed |

## 1.3 执行步骤（模板）

1. 为同一测试任务分别设置 `ro/rw/none`；
2. 在每种模式执行同一组工具动作：`read -> write -> exec`；
3. 记录工具可见集合与实际执行结果；
4. 结束 run 后验证沙箱回收与残留资源。

## 1.4 证据 Schema

```json
{
  "scenario": "B1-1_S1_ro",
  "workspace_access": "ro",
  "tool_attempts": [
    {"tool": "read", "expected": "allow", "actual": "allow"},
    {"tool": "write", "expected": "deny", "actual": "deny", "reason": "workspace_ro"}
  ],
  "lifecycle": [
    {"event": "sandbox.created", "ts": "..."},
    {"event": "sandbox.closed", "ts": "..."}
  ],
  "result": "pass"
}
```

## 1.5 通过门槛

- ro/rw/none 三模式均完成；
- 工具策略无“可见可调但实际越权成功”矛盾；
- 生命周期事件闭合（created 与 closed 成对）。

---

## 2. B1-2：Cron isolated-agent 与主会话边界

## 2.1 验证目标

验证 cron 触发的 isolated-agent 是否与主会话正确隔离，并在回传时遵守统一语义。

关键关注：

1. 状态隔离：cron run 不污染主会话运行态；
2. 回传语义：回传事件与普通 subagent 是否一致；
3. 错误边界：cron 失败不会卡死主流程。

## 2.2 场景矩阵

| 场景 | 输入 | 预期 | 必须证据 |
|---|---|---|---|
| S1 定时触发成功 | cron 正常触发任务 | isolated run 完成并可追踪 | cron_run_id + session 关联 |
| S2 定时触发失败 | 模拟任务错误 | 错误被隔离记录，不污染主会话 | isolated error 事件 |
| S3 并发重叠 | cron 与主会话同时运行 | 互不抢占状态，回传有序 | run registry 快照 |
| S4 回传一致性 | cron 结果回传主会话 | 事件语义与 subagent 对齐 | announce/reconcile 证据 |

## 2.3 执行步骤（模板）

1. 建立可重复 cron 触发任务；
2. 在主会话进行并行交互；
3. 分别记录主会话与 cron run 的 registry 快照；
4. 核对回传事件字段是否对齐。

## 2.4 证据 Schema

```json
{
  "scenario": "B1-2_S3_overlap",
  "main_session_id": "sess_main",
  "cron_run_id": "cron_001",
  "main_run_id": "run_101",
  "timeline": [
    {"ts": "...", "event": "cron.triggered", "run_id": "cron_001"},
    {"ts": "...", "event": "main.run.started", "run_id": "run_101"},
    {"ts": "...", "event": "cron.completed", "run_id": "cron_001"},
    {"ts": "...", "event": "main.run.completed", "run_id": "run_101"}
  ],
  "isolation_check": {
    "state_leak": false,
    "queue_pollution": false
  },
  "result": "pass"
}
```

## 2.5 通过门槛

- cron 成功/失败/并发重叠均验证；
- 主会话状态未受污染；
- 回传事件语义可统一归档。

---

## 3. B2：延后项验证框架（先建模板）

> B2 不要求立即实测，但要提前定义验收标准，避免后期返工。

## 3.1 Channel 插件生态（延后）

建议最小验收维度：

- 插件加载成功率；
- 路由字段完整率（channel/to/account/thread）；
- 权限隔离与失败降级路径。

建议产物：

- `B2-channel-plugin-matrix.md`
- 每个 channel 1 份 smoke 证据 JSON。

## 3.2 TUI/CLI 辅助路径（延后）

建议最小验收维度：

- 命令语义与后端事件一致性；
- 中断/重试/恢复指令可追踪；
- 多会话切换下上下文不串。

建议产物：

- `B2-tui-cli-checklist.md`
- 指令回放日志 + 事件对照表。

---

## 4. 统一证据规范（B1/B2 共用）

每份证据 JSON 至少包含：

- `scenario`
- `input_profile`
- `timeline[]`
- `expected`
- `actual`
- `result`
- `risk_level`
- `next_action`

建议新增汇总索引：

- `output/openclaw源码解析/验证记录/B1-B2/summary.md`

---

## 5. 执行节奏建议

1. 第 1 周：完成 B1-1（sandbox）
2. 第 2 周：完成 B1-2（cron 边界）
3. 第 3 周：只建 B2 模板，不强行全测

这样可以保证：

- 不阻塞你当前核心重构；
- 又为未来多渠道扩展提前铺好验证跑道。

---

## 6. B1/B2 通过定义（阶段性）

- **B1 通过**：B1-1 + B1-2 场景全过，且有结构化证据可复核；
- **B2 就绪**：每个延后模块都有“可执行 checklist + 可收集证据模板”。

---

## 7. 与你当前迁移蓝图的关系

- B1 对应“高保真复刻能力兜底”，避免只复刻 happy path；
- B2 对应“长期演进治理”，避免后续插件化与多入口改造失控。

**一句话：B1/B2 不是锦上添花，而是防止系统在扩展阶段失真。**
