# 自动化大型任务开发（主机方案）— 实施方案

> 日期：2026-02-28
> 对应需求：`docs/内部参考/迭代需求/自动化大型任务开发_主机方案_requirements.md`
> 主设计输入：`docs/内部参考/迭代需求/自动化大型任务开发设计方案.md`
> 执行清单输入：`docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md`
> 规划模式：`parallel`（用于后续 `/jjk-vkplan` 拆卡与执行）

---

## 0. 规划元信息与输入对齐

### 0.1 输入来源清单

| source_id | 来源文件 | 抽取原子 |
|-----------|---------|---------|
| SRC-01 | `docs/内部参考/迭代需求/自动化大型任务开发设计方案.md` | hooks-first、三层状态、P0~P3 路线、Ch15~17 门禁 |
| SRC-02 | `docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md` | Phase 勾选项、Exit Gate、会话交接字段 |
| SRC-03 | `docs/内部参考/迭代需求/vibe_kanban依赖分析报告.md` | VK 依赖范围与清理边界 |
| SRC-04 | `docs/内部参考/迭代需求/heartbeat替代cron_交叉验证研究报告.md` | wake/agent/cron 触发能力拆分 |
| SRC-05 | `docs/内部参考/迭代需求/vibe_kanban方案评审报告.md` | 风险缓解建议与校验项 |

### 0.2 对齐与审批标记

- `DESIGN_APPROVAL_FALLBACK_ACK`：本轮按用户在 2026-02-28 当前会话明确指令执行；
- `SUPERPOWERS_ARTIFACT_UNALIGNED`：未发现 `docs/plans/` 下同主题 `design_approved: true` 文档，需在实施前补齐归档；
- 计划产出继续有效，但在 G01 Gate 增加“审批归档补齐”检查项。

---

## 1. 架构影响与约束

### 1.1 模块边界

| 层级 | 归属模块 | 本轮变更 | 禁止越层 |
|------|---------|---------|---------|
| 触发层 | OpenClaw hooks/cron | 调整触发策略与鉴权基线 | 禁止在业务代码中散落触发策略 |
| 编排层 | `scripts/coder4/coder4_bootstrap_kernel.py` | 本地模式、状态迁移、推进触发 | 禁止在 shell 脚本中复制决策逻辑 |
| 执行层 | `scripts/coder4/wt-flow.sh` | worktree 生命周期与 gate 校验 | 禁止回写业务状态到 VK 作为真理源 |
| 状态层 | `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/*` | state/attempt/ledger 收敛 | 禁止引入第四套主状态源 |
| 展示层 | VK 同步 | 只读异步推送 | 禁止让 VK 推送结果反向驱动执行 |

### 1.2 状态契约

| 字段/文件 | canonical 定义 | 来源优先级 | 生命周期 |
|----------|----------------|-----------|---------|
| `task_key` | 当前任务唯一标识 | `_active_task.json` > `task-runner-state.json` | 任务启动写入，任务结束归档 |
| `card_order` | 卡片顺序与硬依赖范围 | `vk_cards.json` > `task-runner-state.json` | 计划冻结后只允许增量扩展 |
| `card_status_map/card_status` | 卡片运行态 | `task-runner-state.json` | 每轮执行读写，任务完成归档 |
| `attempt_*` | 单轮执行证据 | `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json::gate_results/merge_results/<task_key>/` | 每轮新增，按保留策略清理 |
| `ledger` | 阶段性可审计台账 | `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-ledger.jsonl` | 全流程追加，禁止覆盖 |

### 1.3 路由闭环

执行路径固定为：
`触发事件(wake/agent/cron)` -> `scope_guard` -> `bootstrap_kernel` -> `wt-flow` -> `done_gate` -> `state+ledger` -> `wake 下一轮`。

约束：
1. 严禁卡片完成后跳过 `done_gate` 直接进入下卡；
2. 严禁在执行中回写并依赖外部看板状态做主决策；
3. 同一触发窗口必须命中互斥锁与幂等键。

### 1.4 端到端链路

| 链路节点 | 输入 | 输出 | 失效保护 |
|---------|------|------|---------|
| hooks 入口 | token + payload | agent turn/wake 事件 | token 校验失败立即 401 |
| kernel | active_task + cards + state | action + target_card | 读取失败进入 BLOCKED |
| wt-flow | card_id + repo 状态 | 验证结果 + merge 结果 | dirty fail-fast + 冲突阻塞 |
| ledger/attempt | 执行证据 | 可审计记录 | 原子写 + 锁保护 |
| VK 同步 | 卡片状态快照 | 可视化状态 | 失败不阻断主链路 |

### 1.5 可测试性

1. 单元：kernel 状态迁移、幂等判定、状态文件写锁；
2. 集成：wake/agent/cron 并发触发、串行推进闭环；
3. 演练：备份恢复、BLOCKED 恢复、VK 断连降级；
4. 文档门禁：`python3 scripts/docs_guard.py --strict` 必须通过。

---

## 2. 轻文档边界（3+1）

本主题仅维护以下主产物：

1. `docs/内部参考/迭代需求/自动化大型任务开发_主机方案_requirements.md`
2. `docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md`
3. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/...`（由 `/jjk-vkplan` 产出）
4. 其余文档仅作为输入引用，不新增第四类主计划文档。

---

## 3. 测试策略（test_strategy）

```yaml
test_strategy:
  - feature_id: P0-01
    test_cases:
      - TC-HOST-01: hooks wake/agent 返回码符合预期
      - TC-HOST-02: 无 token 请求被拒绝
    test_first: true
  - feature_id: P0-02
    test_cases:
      - TC-HOST-03: 并发触发只执行一次
    test_first: true
  - feature_id: P1-01
    test_cases:
      - TC-HOST-04: 中断场景下状态文件仍可恢复
    test_first: true
  - feature_id: P1-03
    test_cases:
      - TC-HOST-05: wt-flow 命令与 fail-fast 生效
    test_first: false
  - feature_id: G-2
    test_cases:
      - TC-HOST-06: seed->done 闭环通过
    test_first: false
  - feature_id: P3-01
    test_cases:
      - TC-HOST-07: VK 不可用不影响主链路
    test_first: false
  - feature_id: G-4
    test_cases:
      - TC-HOST-08: 备份恢复与回滚演练通过
    test_first: false
```

---

## 4. 功能机制包总表（Feature Packet）

### 4.1 总表

| feature_id | 目标与边界 | 代码锚点 | 回滚锚点 |
|-----------|-----------|---------|---------|
| P0-01 | hooks 本地安全基线（监听、token、权限） | `~/.openclaw-dev/openclaw.json`, `scripts/coder4_watchdog.py` | 恢复上一个 openclaw 配置快照 |
| P0-02 | 触发互斥锁 + 幂等键防重复执行 | `scripts/coder4/coder4_bootstrap_kernel.py` | 关闭幂等扩展分支并恢复旧执行路径 |
| P1-01 | `task-runner-state.json` 原子写 + 锁 | `scripts/coder4/coder4_bootstrap_kernel.py` | 使用 `.bak` 恢复 state |
| P1-02 | kernel 本地模式收口（读本地状态、完成后 wake） | `scripts/coder4/coder4_bootstrap_kernel.py` | 切回旧参数并暂停自动推进 |
| P1-03 | wt-flow 扩展 + done_gate 命令白名单 | `scripts/coder4/wt-flow.sh` | 回退到仅 create/merge/cleanup 版本 |
| P1-04 | attempt/ledger 本地化与清理策略 | `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json::gate_results/merge_results/`, `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-ledger.jsonl` | 停止清理并恢复归档快照 |
| P2-01 | 3000 payload 迁移与仓外规则重写 | `WORKFLOW_AUTO.md`, `VK_AGENT_PROMPTS.md` | 恢复仓外备份 |
| P3-01 | VK 只读同步与定时全量对账 | `scripts/coder4/coder4_vk_sync.py` | 禁用同步任务，仅保留本地运行 |
| G-1 | 安全门禁闭环 | Ch15/Ch17 + hooks 验证脚本 | 失败即 No-Go |
| G-2 | 执行链路闭环门禁 | kernel + wt-flow + done_gate | 失败即冻结推进 |
| G-3 | 迁移一致性门禁 | payload 31 项迁移清单 | 失败即回退到 `/jjk-plan` |
| G-4 | 回滚演练门禁 | backup/restore + 故障SOP | 失败即 No-Go |

### 4.2 逐项机制包（含最小代码样例）

#### P0-01 hooks 本地安全基线

- 目标与边界：仅允许本地回环访问 hooks；token 必填；禁止 root 进程。
- 触发条件与状态流转：启动前检查 -> hooks 请求验签 -> 通过后执行。
- 代码锚点：`~/.openclaw-dev/openclaw.json`，`scripts/coder4_watchdog.py`。
- 关键契约字段：`OPENCLAW_HOOKS_TOKEN`、`gateway.port`。
- 回滚锚点：恢复 `openclaw.json` 备份。
- 验证命令：见 `T-01`。
- 来源证据：SRC-01 Ch15，SRC-04 hooks 能力审计。

```bash
# 样例：本地回环验证
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $OPENCLAW_HOOKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"health-check","mode":"now"}' \
  http://127.0.0.1:19002/hooks/wake
```

#### P0-02 触发互斥锁与幂等键

- 目标与边界：并发触发场景下最多一次有效执行。
- 触发条件与状态流转：收到触发 -> 获取 run lock -> 校验幂等键 -> 执行或跳过。
- 代码锚点：`scripts/coder4/coder4_bootstrap_kernel.py`。
- 关键契约字段：`coder4-run.lock`、`idempotency_key`、`SKIP_DUPLICATE_EVENT`。
- 回滚锚点：关闭幂等判定逻辑并恢复旧触发节奏。
- 验证命令：见 `T-02`。
- 来源证据：SRC-01 Ch11.5。

```python
def should_execute(event_key: str, lock_path: Path) -> bool:
    with lock_path.open("w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        return not is_duplicate(event_key)
```

#### P1-01 状态文件原子写与锁保护

- 目标与边界：状态文件在中断与并发下仍保持可恢复。
- 触发条件与状态流转：状态更新 -> 写临时文件 -> `os.replace` -> 更新完成。
- 代码锚点：`scripts/coder4/coder4_bootstrap_kernel.py`。
- 关键契约字段：`schema_version`、`task_key`、`card_status_map`。
- 回滚锚点：恢复 `.json.bak`。
- 验证命令：见 `T-03`。
- 来源证据：SRC-01 Ch4.6。

```python
def atomic_write(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
```

#### P1-02 kernel 本地模式收口

- 目标与边界：去除执行路径对 VK 读取依赖，推进后自动触发下一轮。
- 触发条件与状态流转：`load_context(local)` -> `decide_action` -> `apply_action` -> `trigger_next_round`。
- 代码锚点：`scripts/coder4/coder4_bootstrap_kernel.py`。
- 关键契约字段：`--local-mode`、`state_file`、`last_action_result`。
- 回滚锚点：禁用自动 wake，恢复手动触发。
- 验证命令：见 `T-04`。
- 来源证据：SRC-01 Ch5。

```bash
python3 scripts/coder4/coder4_bootstrap_kernel.py \
  --local-mode --apply-bootstrap \
  --active-task docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
```

#### P1-03 wt-flow 扩展与 done_gate 白名单

- 目标与边界：新增 `next/verify/list` 并确保验证命令可控。
- 触发条件与状态流转：next 选卡 -> verify 验收 -> merge/cleanup。
- 代码锚点：`scripts/coder4/wt-flow.sh`。
- 关键契约字段：`ALLOWED_PREFIXES`、`execution_mode`。
- 回滚锚点：回退到旧脚本版本。
- 验证命令：见 `T-05`。
- 来源证据：SRC-01 Ch6。

```bash
bash scripts/coder4/wt-flow.sh next
bash scripts/coder4/wt-flow.sh verify C01
bash scripts/coder4/wt-flow.sh list
```

#### P1-04 attempt/ledger 本地化

- 目标与边界：每次执行都有结构化证据与可追溯台账。
- 触发条件与状态流转：dispatch 开始创建 attempt -> gate 后写结果 -> ledger 追加。
- 代码锚点：`docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json::gate_results/merge_results/`、`docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-ledger.jsonl`。
- 关键契约字段：`attempt_id`、`worktree_path`、`commit_sha`。
- 回滚锚点：恢复最近归档目录。
- 验证命令：见 `T-06`。
- 来源证据：SRC-01 Ch7。

```json
{
  "attempt_id": "attempt_001",
  "card_id": "C03",
  "result": "done_gate_passed",
  "worktree_path": "/Users/jijingkun/bojxAI/fastapi/.worktrees/C03"
}
```

#### P2-01 payload 迁移与规则重写

- 目标与边界：将 3000 字符约束迁移到文档化契约，cron 简化为 watchdog。
- 触发条件与状态流转：规则迁移 -> 31 项对照验证 -> A/B 对比。
- 代码锚点：`WORKFLOW_AUTO.md`、`VK_AGENT_PROMPTS.md`、`AGENTS.md`。
- 关键契约字段：`P-01~P-05`、`E-01~E-06`、`D-01~D-07`、`C-01~C-10`、`O-01~O-03`。
- 回滚锚点：执行 `coder4_external_restore.sh`。
- 验证命令：见 `T-07`。
- 来源证据：SRC-01 附录 B。

```bash
python3 scripts/docs_guard.py --strict
# 并执行 31 项 checklist 全量复核
```

#### P3-01 VK 只读同步与全量对账

- 目标与边界：VK 仅做展示层，推送失败不阻断执行。
- 触发条件与状态流转：状态变更 -> 异步同步 -> 定时全量校验。
- 代码锚点：`scripts/coder4/coder4_vk_sync.py`。
- 关键契约字段：`sync_result`、`last_sync_at`。
- 回滚锚点：禁用同步脚本与定时任务。
- 验证命令：见 `T-08`。
- 来源证据：SRC-01 Ch10/P3。

```python
try:
    sync_to_vk(card_id, status)
except Exception:
    logger.warning("vk sync failed, continue main flow")
```

#### G-1 安全门禁闭环

- 目标与边界：上线前所有安全门禁必须全绿。
- 触发条件与状态流转：执行门禁脚本 -> 汇总结果 -> Go/No-Go。
- 代码锚点：`docs/.../自动化大型任务开发设计方案.md` Ch15/17。
- 关键契约字段：`G-01`、`G-02`。
- 回滚锚点：No-Go 即冻结上线。
- 验证命令：见 `T-09`。
- 来源证据：SRC-01 Ch17。

```bash
python3 scripts/docs_guard.py --strict && echo "G-1 PASS"
```

#### G-2 执行链路闭环门禁

- 目标与边界：至少一张卡片完成全流程闭环。
- 触发条件与状态流转：seed -> activate -> dispatch -> verify -> done。
- 代码锚点：kernel + wt-flow + attempts。
- 关键契约字段：`current_card`、`last_action_result`。
- 回滚锚点：失败即进入 BLOCKED 并冻结推进。
- 验证命令：见 `T-10`。
- 来源证据：SRC-02 Phase Exit Gate。

```bash
bash scripts/coder4/wt-flow.sh list
python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode
```

#### G-3 迁移一致性门禁

- 目标与边界：31 项迁移与规划契约一致。
- 触发条件与状态流转：迁移完成 -> checklist 验证 -> A/B 对比。
- 代码锚点：实施方案附录与规则文档。
- 关键契约字段：`source_atoms`、`feature_id`、`card_id` 映射。
- 回滚锚点：迁移失败回退并重新规划。
- 验证命令：见 `T-11`。
- 来源证据：SRC-01 附录 B.4。

```bash
grep -n "待迁移" docs/内部参考/迭代需求/自动化大型任务开发设计方案.md
```

#### G-4 回滚演练门禁

- 目标与边界：验证备份恢复脚本在主机环境可闭环。
- 触发条件与状态流转：备份 -> 注入故障 -> 恢复 -> 复验。
- 代码锚点：`scripts/coder4_external_backup.sh`、`scripts/coder4_external_restore.sh`。
- 关键契约字段：`manifest.tsv`、`checksums.sha256`。
- 回滚锚点：恢复失败即 No-Go。
- 验证命令：见 `T-12`。
- 来源证据：SRC-01 ADR-009。

```bash
bash scripts/coder4_external_backup.sh
bash scripts/coder4_external_restore.sh <backup_dir>
```

---

## 5. 工单级任务包（implementation_tasks）

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: P0-01
    phase: P0
    file_paths:
      - ~/.openclaw-dev/openclaw.json
      - scripts/coder4_watchdog.py
    symbols:
      - verify_hooks_token
      - resolve_gateway_url
    change_type: modify
    acceptance_cmds:
      - python3 scripts/coder4_watchdog.py --dry-run
      - python3 - <<'PY'\nimport os;assert len(os.getenv('OPENCLAW_HOOKS_TOKEN',''))>=32\nprint('token-ok')\nPY
    rollback_point: 恢复 openclaw.json 备份并重启 OpenClaw

  - task_id: T-02
    feature_id: P0-02
    phase: P0
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
    symbols:
      - with_run_lock
      - should_skip_duplicate
    change_type: modify
    acceptance_cmds:
      - python3 scripts/coder4/coder4_bootstrap_kernel.py --help
    rollback_point: 暂时关闭互斥幂等逻辑并回退到单触发入口

  - task_id: T-03
    feature_id: P1-01
    phase: P1
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
    symbols:
      - atomic_write_json
      - load_local_state
    change_type: modify
    acceptance_cmds:
      - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --active-task docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
    rollback_point: 使用 task-runner-state.json.bak 回滚

  - task_id: T-04
    feature_id: P1-02
    phase: P1
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
    symbols:
      - build_kernel_context
      - apply_action
    change_type: modify
    acceptance_cmds:
      - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --apply-bootstrap --active-task docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
    rollback_point: 停用自动 wake，仅保留手工触发

  - task_id: T-05
    feature_id: P1-03
    phase: P1
    file_paths:
      - scripts/coder4/wt-flow.sh
    symbols:
      - cmd_next
      - cmd_verify
      - cmd_list
    change_type: modify
    acceptance_cmds:
      - bash scripts/coder4/wt-flow.sh status
      - bash scripts/coder4/wt-flow.sh guard
    rollback_point: 回退到仅 create/merge/cleanup 版本

  - task_id: T-06
    feature_id: P1-04
    phase: P1
    file_paths:
      - docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json::gate_results/merge_results/
      - docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-ledger.jsonl
    symbols:
      - create_attempt
      - record_attempt_evidence
    change_type: add
    acceptance_cmds:
      - test -f docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json || true
      - test -f docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-ledger.jsonl || true
    rollback_point: 从最近 archive 恢复 attempts 与 ledger

  - task_id: T-07
    feature_id: P2-01
    phase: P2
    file_paths:
      - ~/.openclaw/workspace-dev/WORKFLOW_AUTO.md
      - ~/.openclaw/workspace-dev/VK_AGENT_PROMPTS.md
      - AGENTS.md
    symbols:
      - payload_migration_checklist
      - hard_constraints
    change_type: modify
    acceptance_cmds:
      - python3 scripts/docs_guard.py --strict
    rollback_point: 执行 scripts/coder4_external_restore.sh 回滚仓外规则

  - task_id: T-08
    feature_id: P3-01
    phase: P3
    file_paths:
      - scripts/coder4/coder4_vk_sync.py
    symbols:
      - sync_to_vk
      - sync_all_cards
    change_type: add
    acceptance_cmds:
      - python3 scripts/coder4/coder4_vk_sync.py --dry-run
    rollback_point: 禁用 VK 同步定时任务与 hooks 后置同步

  - task_id: T-09
    feature_id: G-1
    phase: Gate
    file_paths:
      - docs/内部参考/迭代需求/自动化大型任务开发设计方案.md
      - docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md
    symbols:
      - Ch15
      - Ch17
    change_type: modify
    acceptance_cmds:
      - python3 scripts/docs_guard.py --strict
    rollback_point: 任何安全门禁失败立即 No-Go

  - task_id: T-10
    feature_id: G-2
    phase: Gate
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
      - scripts/coder4/wt-flow.sh
    symbols:
      - decide_action
      - verify_done_gate
    change_type: verify
    acceptance_cmds:
      - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --active-task docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
    rollback_point: 失败后冻结推进并保留当前 worktree

  - task_id: T-11
    feature_id: G-3
    phase: Gate
    file_paths:
      - docs/内部参考/迭代需求/自动化大型任务开发设计方案.md
    symbols:
      - payload_checklist
      - planning_contract
    change_type: verify
    acceptance_cmds:
      - grep -n "待迁移" docs/内部参考/迭代需求/自动化大型任务开发设计方案.md || true
    rollback_point: 未闭环则回退到 /jjk-plan 重新收敛

  - task_id: T-12
    feature_id: G-4
    phase: Gate
    file_paths:
      - scripts/coder4_external_backup.sh
      - scripts/coder4_external_restore.sh
    symbols:
      - backup_manifest
      - restore_manifest
    change_type: verify
    acceptance_cmds:
      - bash scripts/coder4_external_backup.sh
    rollback_point: 恢复失败立即 No-Go
```

---

## 6. 并行拆解种子（parallel 模式）

```yaml
task_key: PP-20260228-AUTO-LARGE-TASK-HOST
card_seed:
  - card_id: C00
    title: 主机基线预检与备份冻结
    feature_ids: [P0-01]
    hard_depends_on: []
    soft_depends_on: []
    file_scope:
      - scripts/coder4_external_backup.sh
      - ~/.openclaw-dev/openclaw.json
    owner_fields: [platform, ops]
    check_cmd:
      - bash scripts/coder4_external_backup.sh
    done_gate:
      - backup manifest 和 checksum 生成成功

  - card_id: C01
    title: hooks 互斥与幂等治理
    feature_ids: [P0-02]
    hard_depends_on: [C00]
    soft_depends_on: []
    file_scope:
      - scripts/coder4/coder4_bootstrap_kernel.py
    owner_fields: [backend]
    check_cmd:
      - python3 scripts/coder4/coder4_bootstrap_kernel.py --help
    done_gate:
      - 并发触发场景仅一次有效执行

  - card_id: C02
    title: 状态文件原子写与锁保护
    feature_ids: [P1-01]
    hard_depends_on: [C01]
    soft_depends_on: []
    file_scope:
      - scripts/coder4/coder4_bootstrap_kernel.py
    owner_fields: [backend]
    check_cmd:
      - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --active-task docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
    done_gate:
      - state 写入中断可恢复

  - card_id: C03
    title: kernel 本地模式收口
    feature_ids: [P1-02]
    hard_depends_on: [C02]
    soft_depends_on: []
    file_scope:
      - scripts/coder4/coder4_bootstrap_kernel.py
    owner_fields: [backend]
    check_cmd:
      - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --apply-bootstrap --active-task docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
    done_gate:
      - 本地模式闭环可运行

  - card_id: C04
    title: wt-flow 扩展与 done_gate 白名单
    feature_ids: [P1-03]
    hard_depends_on: [C03]
    soft_depends_on: []
    file_scope:
      - scripts/coder4/wt-flow.sh
    owner_fields: [backend]
    check_cmd:
      - bash scripts/coder4/wt-flow.sh status
    done_gate:
      - next/verify/list 命令可用

  - card_id: C05
    title: attempt/ledger 本地化
    feature_ids: [P1-04]
    hard_depends_on: [C04]
    soft_depends_on: []
    file_scope:
      - docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/
    owner_fields: [backend]
    check_cmd:
      - test -f docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json || true
    done_gate:
      - attempt 与 ledger 均可写入

  - card_id: C06
    title: payload 迁移与仓外规则重写
    feature_ids: [P2-01]
    hard_depends_on: [C05]
    soft_depends_on: []
    file_scope:
      - ~/.openclaw/workspace-dev/WORKFLOW_AUTO.md
      - ~/.openclaw/workspace-dev/VK_AGENT_PROMPTS.md
      - AGENTS.md
    owner_fields: [platform]
    check_cmd:
      - python3 scripts/docs_guard.py --strict
    done_gate:
      - 31 项迁移清单全部闭环

  - card_id: C07
    title: VK 只读同步与对账
    feature_ids: [P3-01]
    hard_depends_on: [C06]
    soft_depends_on: []
    file_scope:
      - scripts/coder4/coder4_vk_sync.py
    owner_fields: [backend]
    check_cmd:
      - python3 scripts/coder4/coder4_vk_sync.py --dry-run
    done_gate:
      - VK 断连不阻断主链路

  - card_id: G01
    title: G-1 安全门禁闭环
    feature_ids: [G-1]
    hard_depends_on: [C07]
    soft_depends_on: []
    file_scope:
      - docs/内部参考/迭代需求/自动化大型任务开发设计方案.md
    owner_fields: [ops]
    check_cmd:
      - python3 scripts/docs_guard.py --strict
    done_gate:
      - hooks/token/权限门禁全绿

  - card_id: G02
    title: G-2 执行链路闭环
    feature_ids: [G-2]
    hard_depends_on: [G01]
    soft_depends_on: []
    file_scope:
      - scripts/coder4/coder4_bootstrap_kernel.py
      - scripts/coder4/wt-flow.sh
    owner_fields: [backend]
    check_cmd:
      - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --active-task docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
    done_gate:
      - seed->done 闭环验证通过

  - card_id: G03
    title: G-3 迁移一致性闭环
    feature_ids: [G-3]
    hard_depends_on: [G02]
    soft_depends_on: []
    file_scope:
      - docs/内部参考/迭代需求/自动化大型任务开发设计方案.md
    owner_fields: [platform]
    check_cmd:
      - grep -n "待迁移" docs/内部参考/迭代需求/自动化大型任务开发设计方案.md || true
    done_gate:
      - 迁移映射与契约一致

  - card_id: G04
    title: G-4 回滚演练闭环
    feature_ids: [G-4]
    hard_depends_on: [G03]
    soft_depends_on: []
    file_scope:
      - scripts/coder4_external_backup.sh
      - scripts/coder4_external_restore.sh
    owner_fields: [ops]
    check_cmd:
      - bash scripts/coder4_external_backup.sh
    done_gate:
      - 备份恢复演练通过
```

---

## 7. planning_contract（供 /jjk-vkplan 消费）

```yaml
planning_contract:
  execution_mode: serial
  card_order: [C00, C01, C02, C03, C04, C05, C06, C07, G01, G02, G03, G04]
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
    inspection/question-card: policy_gate
  gate_contract:
    mode: as_cards
    gate_ids: [G01, G02, G03, G04]
    depends_on:
      G01: [C07]
      G02: [G01]
      G03: [G02]
      G04: [G03]

  cards:
    - card_id: C00
      wave: P0
      title: 主机基线预检与备份冻结
      feature_ids: [P0-01]
      depends_on: []
      task_mode: implementation-card
      merge_required: false
      done_gate:
        - hooks token 已配置且本地监听基线通过
        - backup manifest/checksum 生成完成
      acceptance_checks:
        - bash scripts/coder4_external_backup.sh
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md

    - card_id: C01
      wave: P0
      title: hooks 互斥与幂等治理
      feature_ids: [P0-02]
      depends_on: [C00]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 并发触发仅一次有效执行
        - 重复事件命中 SKIP_DUPLICATE_EVENT
      acceptance_checks:
        - python3 scripts/coder4/coder4_bootstrap_kernel.py --help
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md

    - card_id: C02
      wave: P1
      title: 状态文件原子写与锁保护
      feature_ids: [P1-01]
      depends_on: [C01]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - state 原子写通过中断测试
        - schema 与锁机制校验通过
      acceptance_checks:
        - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --active-task docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md

    - card_id: C03
      wave: P1
      title: kernel 本地模式收口
      feature_ids: [P1-02]
      depends_on: [C02]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - load_context 不依赖 VK 读取
        - 触发下一轮 wake 生效
      acceptance_checks:
        - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --apply-bootstrap --active-task docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md

    - card_id: C04
      wave: P1
      title: wt-flow 扩展与 done_gate 白名单
      feature_ids: [P1-03]
      depends_on: [C03]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - next/verify/list 可用
        - 主仓 dirty fail-fast 生效
      acceptance_checks:
        - bash scripts/coder4/wt-flow.sh status
        - bash scripts/coder4/wt-flow.sh guard
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md

    - card_id: C05
      wave: P1
      title: attempt/ledger 本地化
      feature_ids: [P1-04]
      depends_on: [C04]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - attempts 与 ledger 均可写入并可追溯
      acceptance_checks:
        - test -f docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json || true
        - test -f docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-ledger.jsonl || true
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md

    - card_id: C06
      wave: P2
      title: payload 迁移与仓外规则重写
      feature_ids: [P2-01]
      depends_on: [C05]
      task_mode: implementation-card
      merge_required: false
      done_gate:
        - 31 项迁移清单全部闭环
        - docs_guard 严格校验通过
      acceptance_checks:
        - python3 scripts/docs_guard.py --strict
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发设计方案.md

    - card_id: C07
      wave: P3
      title: VK 只读同步与对账
      feature_ids: [P3-01]
      depends_on: [C06]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - VK 不可用不阻断主链路
      acceptance_checks:
        - python3 scripts/coder4/coder4_vk_sync.py --dry-run
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md

    - card_id: G01
      wave: Gate
      title: G-1 安全门禁闭环
      feature_ids: [G-1]
      depends_on: [C07]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - hooks/token/监听/权限门禁全绿
      acceptance_checks:
        - python3 scripts/docs_guard.py --strict
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md

    - card_id: G02
      wave: Gate
      title: G-2 执行链路闭环
      feature_ids: [G-2]
      depends_on: [G01]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - seed->done 闭环通过
      acceptance_checks:
        - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --active-task docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md

    - card_id: G03
      wave: Gate
      title: G-3 迁移一致性闭环
      feature_ids: [G-3]
      depends_on: [G02]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - 迁移映射与契约一致
      acceptance_checks:
        - grep -n "待迁移" docs/内部参考/迭代需求/自动化大型任务开发设计方案.md || true
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发设计方案.md

    - card_id: G04
      wave: Gate
      title: G-4 回滚演练闭环
      feature_ids: [G-4]
      depends_on: [G03]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - backup/restore 演练通过
      acceptance_checks:
        - bash scripts/coder4_external_backup.sh
      evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md
```

---

## 8. 风险评估

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| token 配置错误导致 hooks 全失败 | 高 | 直接阻断主链路 | G01 强制校验 + 401 告警 |
| 并发触发重复推进 | 高 | 重复 merge/状态错写 | 互斥锁 + 幂等键 + 并发压测 |
| state 文件损坏 | 高 | 执行上下文不可读 | 原子写 + `.bak` + 恢复演练 |
| 仓外规则迁移遗漏 | 中 | 行为偏移或漏约束 | 31 项 checklist + G03 门禁 |
| VK 只读同步误当真理源 | 中 | 反向污染执行状态 | 明确单向同步，失败不阻断 |

---

## 9. 衔接下游

1. 先执行 `/jjk-vkplan`，将 `planning_contract` 落地为任务拆解目录；
2. 再执行 `/jjk-vktodo` 进行落卡与状态推进；
3. 实施阶段按 `card_id` 串行推进，遵守 Ch17 Exit Gate；
4. 每会话结束必须更新打钩板与交接字段。

---

## 10. 机读结论块

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-vkplan
  notes:
    - DESIGN_APPROVAL_FALLBACK_ACK 已记录，后续需补齐 docs/plans 审批归档
    - SUPERPOWERS_ARTIFACT_UNALIGNED 已记录，不阻断当前规划落地
```
