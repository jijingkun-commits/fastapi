# Cardrun WTIMP Dispatch Bridge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 `cardrun` 在 `dispatch` 阶段真实调用 `wtimp` 执行桥，并把结构化回执写入 canonical `execution_evidence`，消除“只消费人工回填证据、不真正执行子代理”的断层。

**Architecture:** 维持 `cardrun/kernel` 只负责编排与收口，不直接承载大段实现逻辑；新增一个轻量 `wtimp` 执行桥适配器，专门负责解析当前卡片的 `ws_file`、解析当前会话 worktree、调用本机 `codex exec` 执行 `$jjk-wtimp`、校验 JSON 回执并映射为统一错误码。`wt-flow` 仍是唯一 `verify -> merge` 主路径，`wtimp(cardrun_dispatch)` 只负责“实现 + commit + 回执”，不得重复 create/merge。

**Tech Stack:** Python 3.11+, `subprocess`, `json`, `pytest`, Bash `wt-flow.sh`, Codex CLI `codex exec`

---

## 四段式架构结论（实施前门禁）

### 模块边界

- `scripts/coder4/coder4_bootstrap_kernel.py`：只做选卡、门禁、状态推进、错误码收敛、证据落盘。
- `scripts/coder4/wtimp_dispatch_bridge.py`：只做 `wtimp` 调用、回执解析、结构化错误映射。
- `scripts/coder4/wt-flow.sh`：只做 worktree/create/verify/merge 生命周期。
- `jjk-wtimp`：只做单卡实现与提交，在 `executor_mode=cardrun_dispatch` 下禁止 create/merge。

### 依赖方向

- 允许：`kernel -> wtimp_dispatch_bridge -> codex exec -> jjk-wtimp -> wt-flow`
- 禁止：`wtimp` 反向写 `task-runner-state.json`、`verify/create-pr` 反向推导 dispatch 证据。

### 状态归属

- 任务真理源：`workdocs/任务拆解/<task_split_dir>/contracts/_active_task.json`
- 运行态真理源：`.artifacts/states/task_splits/<task_split_dir>/<task_key>/task-runner-state.json`
- 会话真理源：`.artifacts/states/task_splits/<task_split_dir>/<task_key>/active-session-<session_id>.json`
- 证据真理源：`.artifacts/states/task_splits/<task_split_dir>/<task_key>/task-ledger.jsonl`

### 错误处理责任

- `wtimp_dispatch_bridge`：输出 `CARDRUN_SUBAGENT_FAILED`、`CARDRUN_EXECUTION_RESULT_INVALID`、`CARDRUN_WS_MAPPING_BROKEN`
- `kernel`：输出 `CARDRUN_EXECUTOR_UNSUPPORTED`、`CARDRUN_NO_COMMIT_EVIDENCE`
- `wt-flow.sh`：输出 `MERGE_NO_COMMITS`、verify/merge 原子失败

---

## 范围与非范围

### 本次范围（必须完成）

- `dispatch` 从“只检查外部传入 `commit_sha`”升级为“真实调用 `wtimp` 并消费回执”。
- `execution_evidence` 必须由桥接回执生成，不再依赖人工补传 `--commit-sha`。
- `task-ledger.jsonl`、顶层 result JSON、dispatch tests 三处证据口径统一。
- `worktree_path` 必须从当前 session 真路径解析，不再写旧 `.worktrees/<card_id>` 假路径。

### 本次非范围（单列 follow-up，不在本 patch 混做）

- `verified` 状态机收敛与 `next` 对 `verified` 的阻断。
- `acceptance_checks` 前缀白名单兼容 `rg/pnpm/PYTHONPATH=...`。
- 多 `_active_task.json` 场景下的默认上下文选择改造。

---

## 实施策略选择

### 方案 A：`kernel` 直接 `subprocess.run(["codex", ...])` 调起 `wtimp`（推荐）

- 优点：依赖最短，不引入自调用 HTTP；运行链清晰，最接近“执行桥”本义。
- 缺点：要求本机安装 `codex` CLI；需要自己处理超时、stdout JSON 提取、错误码映射。

### 方案 B：`kernel` 调 `/api/v1/dev-tools/codex/exec` 间接桥接

- 优点：已有开发工具接口，外层已有 workdir 和超时校验。
- 缺点：`kernel -> HTTP -> 本机 codex` 形成自调用，职责更绕；运行态更依赖服务已启动。

### 决策

- 采用 **方案 A**。
- 理由：当前项目未上线，设计合理性优先；应优先保持依赖方向短而清晰，避免为了复用现成接口把主链路变成“脚本依赖服务自身”的环路。

---

## 任务拆分

### Task 1: 先补桥接契约测试

**Files:**
- Create: `tests/unit/test_coder4_wtimp_dispatch_bridge.py`
- Modify: `tests/unit/test_coder4_dispatch_executor.py`
- Modify: `tests/unit/test_coder4_commit_evidence_gate.py`

**Step 1: 写失败测试，锁定桥接输入输出契约**

新增用例至少覆盖：

```python
def test_dispatch_bridge_builds_codex_exec_command_for_cardrun_dispatch():
    ...

def test_dispatch_bridge_parses_json_result_and_requires_commit_sha():
    ...

def test_dispatch_bridge_maps_nonzero_exit_to_subagent_failed():
    ...

def test_dispatch_apply_action_uses_bridge_result_not_manual_commit_arg():
    ...
```

**Step 2: 运行失败测试，确认当前实现确实没有桥接能力**

Run:

```bash
pytest tests/unit/test_coder4_wtimp_dispatch_bridge.py -q
pytest tests/unit/test_coder4_dispatch_executor.py -q
pytest tests/unit/test_coder4_commit_evidence_gate.py -q
```

Expected:

- 至少出现一个失败，指向“缺少 bridge 模块 / apply_action 仍依赖外部 `commit_sha`”。

**Step 3: 提交测试骨架前，不实现业务逻辑**

- 先只把测试写完整，确保根因被测试命中，而不是先改实现。

**Step 4: 再次运行，确认失败稳定可复现**

Run:

```bash
pytest tests/unit/test_coder4_wtimp_dispatch_bridge.py -q --maxfail=1
```

Expected:

- 稳定 FAIL，失败原因清晰且可指向 bridge 缺失。

---

### Task 2: 新增 `wtimp` 执行桥适配器

**Files:**
- Create: `scripts/coder4/wtimp_dispatch_bridge.py`
- Test: `tests/unit/test_coder4_wtimp_dispatch_bridge.py`

**Step 1: 定义 bridge 输入/输出 dataclass 与错误码映射**

最小对象：

```python
@dataclass
class WtimpDispatchRequest:
    task_key: str
    card_id: str
    ws_file: str
    worktree_path: str
    executor_mode: str
    timeout_seconds: int = 1800


@dataclass
class WtimpDispatchResult:
    ok: bool
    executor: str
    executor_mode: str
    card_id: str
    ws_file: str
    subagent_id: str | None
    commit_sha: str | None
    merge_sha: str | None
    changed_files: list[str]
    acceptance_results: list[dict[str, object]]
    error_code: str | None = None
    error_message: str | None = None
```

**Step 2: 实现命令构建函数，固定使用 `codex exec` 主路径**

要求：

- 使用 `subprocess.run()`
- `cwd` 必须是当前卡片真实 `worktree_path`
- prompt 必须显式要求：调用 `$jjk-wtimp`、`executor_mode=cardrun_dispatch`、最终只输出一段 JSON
- 禁止通过 HTTP 自调 `/dev-tools/codex/exec`

**Step 3: 实现 stdout JSON 提取与字段校验**

必须校验：

- `ok`
- `executor == "wtimp"`
- `executor_mode == "cardrun_dispatch"`
- `card_id` 与请求一致
- `ws_file` 与请求一致
- `commit_sha` 非空

不满足时统一抛出结构化错误：

- `CARDRUN_EXECUTION_RESULT_INVALID`
- `CARDRUN_NO_COMMIT_EVIDENCE`

**Step 4: 运行桥接模块测试**

Run:

```bash
pytest tests/unit/test_coder4_wtimp_dispatch_bridge.py -q
```

Expected:

- PASS

---

### Task 3: 把 bridge 接入 `kernel dispatch` 主路径

**Files:**
- Modify: `scripts/coder4/coder4_bootstrap_kernel.py`
- Test: `tests/unit/test_coder4_dispatch_executor.py`
- Test: `tests/unit/test_coder4_commit_evidence_gate.py`

**Step 1: 写失败测试，锁定 `apply_action(dispatch)` 必须主动调用 bridge**

新增/改造断言：

```python
def test_apply_dispatch_action_invokes_bridge_and_returns_bridge_evidence(monkeypatch):
    ...

def test_apply_dispatch_action_maps_bridge_error_to_cardrun_subagent_failed(monkeypatch):
    ...
```

**Step 2: 在 `apply_action()` 中替换当前“手工 commit 门禁”逻辑**

实现要求：

- 通过当前卡 `cards_by_id[target_card_id]["source_ws_file"]` 获取 `ws_file`
- 通过当前 session state 真正解析 `worktree_path`
- 调用 `wtimp_dispatch_bridge.run_dispatch(...)`
- 成功时返回：

```python
{
    "performed": True,
    "action": "dispatch",
    "card_id": target_card_id,
    "task_id": target_task_id,
    "executor_mode": "wtimp",
    "executor_dispatch_mode": "cardrun_dispatch",
    "subagent_id": result.subagent_id,
    "ws_file": result.ws_file,
    "commit_sha": result.commit_sha,
    "merge_sha": result.merge_sha,
    "merge_owner": "wt_flow",
}
```

失败时：

- `wtimp` 非 0 退出 / 返回非法 JSON / 缺关键字段，一律收敛为 `CardrunContractError(code="CARDRUN_SUBAGENT_FAILED" | "CARDRUN_EXECUTION_RESULT_INVALID")`

**Step 3: 保留 CLI `--commit-sha` 仅作为回放/测试注入，不作为正常 dispatch 主路径**

- 正常 dispatch 成功后，`commit_sha` 来自 bridge result。
- 若 bridge 未执行，不允许靠手工 `--commit-sha` 冒充“自动执行成功”。

**Step 4: 运行回归测试**

Run:

```bash
pytest tests/unit/test_coder4_dispatch_executor.py -q
pytest tests/unit/test_coder4_commit_evidence_gate.py -q
pytest tests/unit/test_coder4_single_merge_path.py -q
```

Expected:

- PASS

---

### Task 4: 修正 worktree 真实路径与 evidence 一致性

**Files:**
- Modify: `scripts/coder4/coder4_bootstrap_kernel.py`
- Modify: `scripts/coder4/wt-flow.sh`
- Test: `tests/unit/test_coder4_execution_evidence_migration.py`
- Create: `tests/unit/test_coder4_worktree_session_resolution.py`

**Step 1: 写失败测试，锁定 `worktree_path` 必须来自 session 真路径**

新增断言：

```python
def test_dispatch_attempt_evidence_uses_real_session_worktree_path():
    ...
```

**Step 2: 在 `kernel` 中新增解析当前 session worktree 的 helper**

要求：

- 优先使用 `WT_FLOW_SESSION_ID`
- 否则从任务级 `.state/<task_key>/active-session-*.json` 单文件解析
- 多会话且未指定时 fail-fast，禁止猜测

**Step 3: 用真实 `worktree_path` 回填 attempt/ledger/result**

- 替换当前旧逻辑：`.worktrees/<card_id>`
- 保证 bridge 调用路径、attempt 证据路径、ledger 路径三者一致

**Step 4: 运行路径与 evidence 回归测试**

Run:

```bash
pytest tests/unit/test_coder4_execution_evidence_migration.py -q
pytest tests/unit/test_coder4_worktree_session_resolution.py -q
```

Expected:

- PASS

---

### Task 5: 文档同步与机读口径收口

**Files:**
- Modify: `.cursor/commands/jjk-cardrun.md`
- Modify: `.cursor/commands/jjk-wtimp.md`
- Modify: `docs/开发文档/流程与工具/AI协作速查表.md`
- Modify: `docs/开发文档/流程与工具/指令用法_实现方式_工程流全景手册.md`

**Step 1: 先写文档，再收尾代码**

必须同步写清：

- `dispatch` 会真实调用 `wtimp`
- `wtimp(cardrun_dispatch)` 只返回 JSON 回执，不做 merge
- `commit_sha` 不再依赖人工 CLI 注入
- 失败码新增：`CARDRUN_SUBAGENT_FAILED`、`CARDRUN_EXECUTION_RESULT_INVALID`、`CARDRUN_WS_MAPPING_BROKEN`

**Step 2: 运行文档一致性检查（最小替代证据）**

Run:

```bash
rg -n "/jjk-imp-ws|/jjk-wtimp" .cursor/commands docs/开发文档
```

Expected:

- `cardrun` 主链不再残留“自动调用 `imp-ws`”旧口径

**Step 3: 做一次 focused 回归**

Run:

```bash
pytest \
  tests/unit/test_coder4_wtimp_dispatch_bridge.py \
  tests/unit/test_coder4_dispatch_executor.py \
  tests/unit/test_coder4_commit_evidence_gate.py \
  tests/unit/test_coder4_single_merge_path.py \
  tests/unit/test_coder4_execution_evidence_migration.py \
  -q
```

Expected:

- 全部 PASS

---

## 交付清单

- `scripts/coder4/wtimp_dispatch_bridge.py`
- `tests/unit/test_coder4_wtimp_dispatch_bridge.py`
- `tests/unit/test_coder4_worktree_session_resolution.py`
- 更新后的 `scripts/coder4/coder4_bootstrap_kernel.py`
- 更新后的 `jjk-cardrun/jjk-wtimp` 文档

---

## 风险与回退

| 风险 | 触发条件 | 影响 | 回退策略 |
|---|---|---|---|
| 本机无 `codex` CLI | bridge 启动时 `FileNotFoundError` | dispatch 无法自动执行 | 直接阻断并输出 `CARDRUN_SUBAGENT_FAILED`，不允许伪造 `commit_sha` |
| `wtimp` 输出非 JSON | 模型输出漂移 | bridge 无法解析 | fail-fast `CARDRUN_EXECUTION_RESULT_INVALID`，补强 prompt 与测试 |
| `ws_file` 映射失败 | 卡片契约不完整 | dispatch 无法定位 WS | fail-fast `CARDRUN_WS_MAPPING_BROKEN` |
| 多会话未指明 session | session 状态文件 >1 | 可能跑错 worktree | fail-fast，不做猜测 |

---

## 执行完成判定（DoD）

- `cardrun` 的 `dispatch` 不再依赖人工传入 `--commit-sha`
- `apply_action(dispatch)` 会真实调用 bridge
- bridge 会真实调用 `codex exec` 执行 `$jjk-wtimp`
- `execution_evidence.commit_sha/subagent_id/ws_file` 来自 bridge result
- `task-ledger.jsonl`、top-level result、tests 三者口径一致
- `wtimp(cardrun_dispatch)` 仍不做 merge，`wt-flow` 保持唯一收口

---

## Follow-up（不在本计划混做）

1. `verified` 状态机与 `next` 阻断收敛
2. `acceptance_checks` 命令前缀兼容扩展
3. 多 `_active_task.json` 下显式上下文选择机制

---

Plan complete and saved to `workdocs/归档/正文/设计/2026-03-06-cardrun-wtimp-dispatch-bridge-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
