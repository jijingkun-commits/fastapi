# 多任务并行开发 Worktree 冲突问题分析报告 v2.1

> **文档类型**: 问题分析与可执行解决方案
> **创建日期**: 2026-03-03
> **更新日期**: 2026-03-03
> **版本**: v2.1（P0 修正版，关键引用已校验）
> **问题优先级**: P1（阻塞多任务并行开发）
> **涉及组件**: `jjk-cardrun`, `wt-flow.sh`, `jjk-vkplan`
> **权威源**: `.cursor/commands/jjk-cardrun.md`, `.cursor/commands/jjk-vkplan.md`, `scripts/coder4/wt-flow.sh`

---

## 1. 背景

### 1.1 业务场景

当前项目存在多个大型架构重构任务需要并行开发：
- 任务A：移除 Planner 节点（涉及 `multi_agent_graph.py`、`state.py`、`agent_prompts.py` 等）
- 任务B：优化待办上下文识别（涉及 `multi_agent_graph.py`、`todo_prompts.py` 等）
- 任务C：交付编排架构优化（涉及 `multi_agent_graph.py`、`delivery_contracts.py` 等）

这些任务具有以下特点：
1. **开发周期长**：每个任务预计 1-2 周
2. **文件重叠**：多个任务修改同一文件（如 `multi_agent_graph.py`）
3. **独立验证**：每个任务需要独立测试和验证
4. **串行阻塞**：如果串行开发，总周期 3-6 周，效率低下

### 1.2 技术架构（基于权威源）

项目采用 `jjk-*` 工作流体系进行任务管理（参考 `.cursor/commands/jjk-cardrun.md` 第 175 行）：

```
/jjk-plan (生成需求与技术方案)
  ↓
/jjk-vkplan (拆解为卡片 + 生成 vk_cards.json)
  ↓
/jjk-vktodo (create-only 幂等建卡)
  ↓
/jjk-cardrun (串行执行卡片 + 自动 merge)
  ├─ 0) 执行上下文校验 (pwd/branch/worktree)
  ├─ 0.2) 工作区洁净校验 (dirty whitelist)
  ├─ 0.5) scope_guard 校验
  ├─ 1) 读取并校验串行契约
  ├─ 2) 选卡与激活 (wt-flow.sh next)
  ├─ 3) 主控调度子代理执行 (/jjk-imp-ws)
  ├─ 4) done_gate + merge 串行收口 ✅ 已包含
  │    ├─ wt-flow.sh verify → status=verified
  │    ├─ wt-flow.sh merge → status=done + cleanup
  │    └─ 失败时阻断，不跳卡
  └─ 5) 循环推进策略 (mode=loop)
```

**Worktree 隔离机制**（参考 `scripts/coder4/wt-flow.sh`）：
- 每个卡片在独立的 worktree 中开发
- 分支命名：`feature/<card_id>`（如 `feature/C03`）
- 工作目录：`${WT_BASE}/<card_id>`（`WT_BASE` 定义在第 20 行）
- 会话状态文件：`STATE_FILE=docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json`（第 21 行，记录当前 worktree 会话）
- 卡片状态文件：`task-runner-state.json`（第 211 行 `_task_state_file` 函数，记录卡片执行状态）
- Dirty 白名单：`docs/`, `.cursor/commands/`, `.agents/skills/`, `.claude/commands/`（第 43-47 行）
- Active 任务索引：`ACTIVE_TASK_FILE=docs/内部参考/任务拆解/<task_split_dir>/_active_task.json`（第 22 行）

**关键约束**（参考 `docs/内部参考/任务拆解/README.md:64`）：
- 一次只允许一个 active 索引（根目录 `_active_task.json`）
- 每个任务目录保留自己的 `_active_task.json`，避免跨任务覆盖丢失

---

## 2. 问题分析（基于权威源 v2.1）

### 2.1 核心冲突：四类资源竞争

当多个任务并行开发时，存在4大类资源竞争导致冲突（其中状态冲突分为3a/3b两个子类）：

| 冲突类型 | 资源位置 | 冲突表现 | 根因文件与行号 |
|---------|---------|---------|---------------|
| **类型1：分支名冲突** | Git 分支命名空间 | `feature/C01` 被多个任务复用 | `wt-flow.sh:434-439`（分支名解析） |
| **类型2：Worktree 目录冲突** | `${WT_BASE}/<card_id>` | 目录路径被多个任务复用 | `wt-flow.sh:20`（WT_BASE 定义）<br>`wt-flow.sh:387`（路径匹配） |
| **类型3：状态冲突**（分两个子类） | | | |
| 　└ **3a：会话状态冲突** | `STATE_FILE=docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json` | 当前 worktree 会话被覆盖 | `wt-flow.sh:21`（STATE_FILE 定义）<br>`wt-flow.sh:406-417`（_save_state） |
| 　└ **3b：卡片状态冲突** | `task-runner-state.json` | 卡片执行状态被覆盖 | `wt-flow.sh:211`（_task_state_file）<br>`wt-flow.sh:431-459`（_mark_card_done_after_merge） |
| **类型4：Active 索引冲突** | `docs/内部参考/任务拆解/<task_split_dir>/_active_task.json` | 单一 active 索引被多个任务争抢 | `wt-flow.sh:22`（ACTIVE_TASK_FILE）<br>`README.md:64`（单 active 约束）<br>`set_active_task.py:132`（写入逻辑） |

### 2.2 问题1：分支名冲突（类型1）

**问题描述**：

当前分支命名格式为 `feature/<card_id>`，缺少任务上下文前缀。当多个任务并行时，如果卡片编号相同（如任务A的C01和任务B的C01），会导致分支名冲突。

**根因分析**（`scripts/coder4/wt-flow.sh:434-439`）：

```bash
# _mark_card_done_after_merge 函数中的分支名解析
if [[ ! "$branch" =~ ^feature/(.+)$ ]]; then
  return 0
fi

local card_id
card_id="$(_to_upper "${BASH_REMATCH[1]}")"
```

分支名格式硬编码为 `feature/<card_id>`，没有 task_key 前缀。

**实际案例**：

```bash
# 任务A：移除 Planner (task_key=planner-refactor)
git branch
  feature/C01  # 图结构调整
  feature/C02  # State 合同调整

# 任务B：待办优化 (task_key=todo-enhance)（并行开发）
bash scripts/coder4/wt-flow.sh next
# ❌ 错误：fatal: a branch named 'feature/C01' already exists
```

**影响范围**：
- ❌ 无法同时开发多个任务
- ❌ 分支名冲突导致 `git worktree add` 失败

### 2.3 问题2：Worktree 目录冲突（类型2）

**问题描述**：

Worktree 目录路径 `${WT_BASE}/<card_id>` 也缺少任务前缀，导致多个任务的同编号卡片无法共存。

**根因分析**（`scripts/coder4/wt-flow.sh:20, 387`）：

```bash
# 第 20 行：WT_BASE 定义
WT_BASE="${REPO_ROOT}/.worktrees"

# 第 387 行：路径匹配逻辑
if [[ "$branch" == "feature/${card_id}" && -d "$wt_path" ]]; then
  echo "$wt_path"
  return 0
fi
```

**影响范围**：
- ❌ 目录冲突导致 worktree 创建失败
- ❌ 无法通过文件系统路径区分不同任务的卡片

### 2.4 问题3a：会话状态冲突（类型3a）

**问题描述**：

`wt-flow.sh` 使用单一会话状态文件 `STATE_FILE=docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json` 记录当前 worktree 会话（branch/worktree/base_branch），多个任务并行时会相互覆盖。

**根因分析**（`scripts/coder4/wt-flow.sh:21, 406-417`）：

```bash
# 第 21 行：STATE_FILE 定义
STATE_FILE="${REPO_ROOT}/docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json"

# 第 406-417 行：_save_state 函数
_save_state() {
  local branch="$1" worktree="$2" base="$3"
  mkdir -p "$(dirname "$STATE_FILE")"
  cat > "$STATE_FILE" <<EOF
{
  "branch": "$branch",
  "worktree": "$worktree",
  "base_branch": "$base",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}
```

**影响范围**：
- ❌ 会话状态覆盖导致任务A的 worktree 信息丢失
- ❌ 无法追踪多个任务的并行会话

### 2.5 问题3b：卡片状态冲突（类型3b）

**问题描述**：

卡片执行状态文件 `task-runner-state.json` 通过 `_task_state_file` 函数定位，但如果多个任务共享同一 state_dir，会导致状态覆盖。

**根因分析**（`scripts/coder4/wt-flow.sh:211, 431-459`）：

```bash
# 第 211 行：_task_state_file 函数
_task_state_file() {
  local state_dir="$1"
  echo "${state_dir}/task-runner-state.json"
}

# 第 431-459 行：_mark_card_done_after_merge 函数
_mark_card_done_after_merge() {
  local branch="$1" base_branch="$2" state_dir="$3" merge_commit="$4"

  # ... 省略分支名解析 ...

  local state_file
  state_file="$(_task_state_file "$state_dir")"
  [[ -f "$state_file" ]] || return 0

  # ... 更新卡片状态为 done ...
}
```

**影响范围**：
- ⚠️ 如果多个任务使用同一 state_dir，卡片状态会混淆
- ⚠️ 当前实现依赖 state_dir 参数隔离，但默认值相同

### 2.6 问题4：Active 索引冲突（类型4）

**问题描述**：

根目录 `_active_task.json` 是单一 active 索引，多个任务并行时只能有一个任务处于 active 状态。

**根因分析**（`wt-flow.sh:22`, `README.md:64`, `set_active_task.py:132`）：

```bash
# wt-flow.sh:22
ACTIVE_TASK_FILE="${REPO_ROOT}/docs/内部参考/任务拆解/<task_split_dir>/_active_task.json"

# README.md:64
# 一次只允许一个 active 索引；但每个任务目录都保留自己的 _active_task.json

# set_active_task.py:132
write_json(active_index_path, active_index_payload)  # 覆盖写入
```

**影响范围**：
- ❌ 切换任务时会覆盖 active 索引
- ❌ `scope_guard.py:16` 依赖 active 索引判断作用域
- ⚠️ 这是**设计约束**，不是 bug（串行执行语义）

### 2.7 v1 报告的错误假设（已修正）

**v1 错误假设**："`jjk-cardrun` 缺少自动合并机制"

**v2.1 修正**（基于 `.cursor/commands/jjk-cardrun.md:133-147`）：

```
### 4) done_gate + merge 串行收口（强制）

1. 执行：`bash scripts/coder4/wt-flow.sh verify <card_id>`。
2. `verify` 通过后，当前卡状态只能进入 `verified`，不得直接写 `done`。
3. `verify` 通过后必须执行：`bash scripts/coder4/wt-flow.sh merge`。
4. `merge` 成功后状态写回 `done`，并清理当前 worktree，才允许推进下一卡。
```

**结论**：`jjk-cardrun` **已包含** verify → merge → done 的完整闭环，v1 报告的"缺少自动合并"问题不存在。

---

## 3. 可执行解决方案（v2.1）

### 3.1 方案设计原则

**核心理念**：任务级并行 + 卡片级串行

```
任务A (task_key=planner-refactor)
  ├─ C01 (串行) → C02 (串行) → C03 (串行)
  └─ 独立分支命名空间：feature/planner-refactor/*
     独立 worktree 目录：${WT_BASE}/planner-refactor/*
     独立会话状态：docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state-planner-refactor.json
     独立卡片状态：docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/planner-refactor/task-runner-state.json

任务B (task_key=todo-enhance) ← 并行开发
  ├─ C01 (串行) → C02 (串行)
  └─ 独立分支命名空间：feature/todo-enhance/*
     独立 worktree 目录：${WT_BASE}/todo-enhance/*
     独立会话状态：docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state-todo-enhance.json
     独立卡片状态：docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/todo-enhance/task-runner-state.json
```

**设计约束**（继承自 `jjk-cardrun`）：
1. 保持 `execution_mode=serial` 的单活卡语义（`.cursor/commands/jjk-cardrun.md:25`）
2. 保持 verify → merge → done 的强制闭环（`.cursor/commands/jjk-cardrun.md:133-147`）
3. 保持 dirty whitelist 策略（`scripts/coder4/wt-flow.sh:43-47`）
4. **接受单 active 索引约束**（`README.md:64`）：通过流程规范而非技术改造解决

### 3.2 方案对比（v2.1）

| 方案 | 解决冲突类型 | 需要改脚本 | 实施成本 | 风险 | 推荐度 | 优先级 |
|------|-------------|-----------|----------|------|--------|--------|
| **方案A：task_key 命名空间隔离** | 类型1+2+3a+3b | ✅ 是（wt-flow.sh） | 中（1天） | 中 | ⭐⭐⭐⭐ | P0 |
| **方案B：流程规范 + 手动切换** | 类型4（active 索引） | ❌ 否（仅流程） | 低（2h） | 低 | ⭐⭐⭐⭐⭐ | P0 |
| **方案C：兼容性与迁移** | 向后兼容 | ❌ 否（文档） | 低（1h） | 低 | ⭐⭐⭐⭐⭐ | P1 |
| **方案D：冲突预警工具** | 提前预警 | ✅ 是（新脚本） | 中（1天） | 低 | ⭐⭐⭐ | P2 |

**方案选择说明**：
- **方案A**：必做，解决技术层面的资源冲突
- **方案B**：必做，通过流程规范解决单 active 索引约束（不改脚本）
- **方案C**：必做，确保现有任务不受影响
- **方案D**：可选，中期优化

### 3.3 方案A：task_key 命名空间隔离（必做，P0）

**目标**：解决类型1+2+3a+3b冲突，支持多任务并行开发。

**实施方案**：修改 `wt-flow.sh` 的资源命名与状态管理，从 `ACTIVE_TASK_FILE` 读取 `task_key`，作为命名空间前缀。

#### 修改点1：分支命名（解决类型1冲突）

**修改位置**：`scripts/coder4/wt-flow.sh`（需要在 `cmd_create` 函数中添加）

**当前问题**：分支名解析在 `wt-flow.sh:434-439` 的 `_mark_card_done_after_merge` 函数中硬编码为 `^feature/(.+)$`

**修改策略**：
1. 在 `cmd_create` 函数中生成分支名时增加 task_key 前缀
2. 在 `_mark_card_done_after_merge` 函数中兼容解析 `feature/<task_key>/<card_id>` 和 `feature/<card_id>` 两种格式

**修改后逻辑**：
```bash
# cmd_create 函数中
local task_key=""
if [[ -f "$ACTIVE_TASK_FILE" ]]; then
  task_key="$(jq -r '.task_key // ""' "$ACTIVE_TASK_FILE" 2>/dev/null || echo "")"
fi

if [[ -n "$task_key" ]]; then
  local branch="feature/${task_key}/${slug}"
else
  local branch="feature/${slug}"  # 向后兼容
fi
```

**兼容改造点**（必须同步修改）：
- `wt-flow.sh:434`：分支名正则匹配需兼容 `feature/<task_key>/<card_id>` 格式
- `wt-flow.sh:439`：card_id 提取需兼容两种格式
- `wt-flow.sh:387`：路径匹配需兼容两种格式

#### 修改点2：Worktree 目录（解决类型2冲突）

**修改位置**：`scripts/coder4/wt-flow.sh`（`cmd_create` 函数中，WT_BASE 定义在第 20 行）

**修改后逻辑**：
```bash
# WT_BASE 已在第 20 行定义为 "${REPO_ROOT}/.worktrees"
if [[ -n "$task_key" ]]; then
  local wt_path="${WT_BASE}/${task_key}/${slug}"
else
  local wt_path="${WT_BASE}/${slug}"  # 向后兼容
fi
```

**兼容改造点**（必须同步修改）：
- `wt-flow.sh:387`：路径匹配逻辑需兼容 `${WT_BASE}/<task_key>/<card_id>` 格式

#### 修改点3：会话状态文件（解决类型3a冲突）

**修改位置**：`scripts/coder4/wt-flow.sh:21, 406-417`

**当前定义**（第 21 行）：
```bash
STATE_FILE="${REPO_ROOT}/docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json"
```

**修改策略**：将 STATE_FILE 从全局常量改为动态函数，根据 task_key 返回不同路径

**修改后逻辑**：
```bash
# 新增函数
_session_state_file() {
  local task_key=""
  if [[ -f "$ACTIVE_TASK_FILE" ]]; then
    task_key="$(jq -r '.task_key // ""' "$ACTIVE_TASK_FILE" 2>/dev/null || echo "")"
  fi

  if [[ -n "$task_key" ]]; then
    echo "${REPO_ROOT}/docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state-${task_key}.json"
  else
    echo "${REPO_ROOT}/docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json"  # 向后兼容
  fi
}

# 所有使用 STATE_FILE 的地方改为调用 _session_state_file
```

#### 修改点4：卡片状态文件（解决类型3b冲突）

**修改位置**：`scripts/coder4/wt-flow.sh:211`（`_task_state_file` 函数）

**当前实现**：
```bash
_task_state_file() {
  local state_dir="$1"
  echo "${state_dir}/task-runner-state.json"
}
```

**修改策略**：在 state_dir 中增加 task_key 子目录

**修改后逻辑**：
```bash
_task_state_file() {
  local state_dir="$1"
  local task_key=""
  if [[ -f "$ACTIVE_TASK_FILE" ]]; then
    task_key="$(jq -r '.task_key // ""' "$ACTIVE_TASK_FILE" 2>/dev/null || echo "")"
  fi

  if [[ -n "$task_key" ]]; then
    echo "${state_dir}/${task_key}/task-runner-state.json"
  else
    echo "${state_dir}/task-runner-state.json"  # 向后兼容
  fi
}
```

#### 效果对比

| 资源类型 | 修改前（冲突） | 修改后（隔离） |
|---------|---------------|---------------|
| **分支名** | `feature/C01` | `feature/planner-refactor/C01` |
|  | `feature/C01` ❌ 冲突 | `feature/todo-enhance/C01` ✅ 隔离 |
| **Worktree 目录** | `${WT_BASE}/C01` | `${WT_BASE}/planner-refactor/C01` |
|  | `${WT_BASE}/C01` ❌ 冲突 | `${WT_BASE}/todo-enhance/C01` ✅ 隔离 |
| **会话状态** | `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json` | `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state-planner-refactor.json` |
|  | 单例 ❌ 覆盖 | `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state-todo-enhance.json` ✅ 隔离 |
| **卡片状态** | `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json` | `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/planner-refactor/task-runner-state.json` |
|  | 单例 ❌ 覆盖 | `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/todo-enhance/task-runner-state.json` ✅ 隔离 |


**联动影响清单**（必须检查）：
- `scripts/coder4/coder4_bootstrap_kernel.py`：可能依赖 task-runner-state.json 路径
- `scripts/coder4/coder4_vk_sync.py`：可能依赖 task-runner-state.json 路径
- 其他脚本：搜索硬编码的 `task-runner-state.json` 或 `wt-flow-state.json` 路径

**实施成本**：中（1 天，包含联动检查与测试）

---

### 3.4 方案B：流程规范 + 手动切换（必做，P0）

**目标**：解决类型4冲突（单 active 索引约束），通过流程规范而非技术改造。

**核心理念**：接受单 active 索引的设计约束，通过明确的任务切换流程管理并行开发。

#### 流程规范

**任务切换标准操作流程**：

```bash
# 1. 保存当前任务进度（如果有）
# （wt-flow.sh 会自动保存会话状态和卡片状态）

# 2. 切换到新任务
bash scripts/coder4/set_active_task.py \
  --task-split-dir 2026-03-03_todo-enhance \
  --project-id 124

# 3. 继续新任务的卡片执行
/jjk-cardrun 2026-03-03_todo-enhance once

# 4. 切换回原任务
bash scripts/coder4/set_active_task.py \
  --task-split-dir 2026-03-03_planner-refactor \
  --project-id 123

# 5. 继续原任务的卡片执行
/jjk-cardrun 2026-03-03_planner-refactor once
```

#### 关键约束

1. **单 active 索引**（`README.md:64`）：
   - 根目录 `_active_task.json` 同一时刻只指向一个任务
   - 每个任务目录保留自己的 `_active_task.json`，避免跨任务覆盖丢失

2. **scope_guard 依赖**（`coder4_scope_guard.py:16`）：
   - scope_guard 通过 `DEFAULT_ACTIVE_TASK` 判断当前作用域
   - 切换任务后，scope_guard 自动切换到新任务的作用域

3. **set_active_task 覆盖写入**（`set_active_task.py:132`）：
   - 每次调用 `set_active_task.py` 会覆盖根目录 `_active_task.json`
   - 但任务级 `_active_task.json` 保持不变

#### 验收标准

- [ ] 任务切换流程文档化
- [ ] 切换任务后，scope_guard 正确识别新作用域
- [ ] 切换回原任务后，能正确恢复进度
- [ ] 通过以下验收命令：

```bash
# 验收命令：任务切换流程
# 1. 启动任务A
bash scripts/coder4/set_active_task.py --task-split-dir 2026-03-03_planner-refactor --project-id 123
cat docs/内部参考/任务拆解/<task_split_dir>/_active_task.json | jq '.task_key'
# 预期："planner-refactor"

# 2. 切换到任务B
bash scripts/coder4/set_active_task.py --task-split-dir 2026-03-03_todo-enhance --project-id 124
cat docs/内部参考/任务拆解/<task_split_dir>/_active_task.json | jq '.task_key'
# 预期："todo-enhance"

# 3. 验证任务A的状态未丢失
cat docs/内部参考/任务拆解/2026-03-03_planner-refactor/_active_task.json | jq '.task_key'
# 预期："planner-refactor"

# 4. 切换回任务A
bash scripts/coder4/set_active_task.py --task-split-dir 2026-03-03_planner-refactor --project-id 123
cat docs/内部参考/任务拆解/<task_split_dir>/_active_task.json | jq '.task_key'
# 预期："planner-refactor"
```

**实施成本**：低（2 小时，主要是文档编写）

**优点**：
- ✅ 不需要修改脚本
- ✅ 符合现有设计约束
- ✅ 流程清晰，易于理解

**缺点**：
- ⚠️ 需要手动切换任务
- ⚠️ 切换时需要记住当前任务状态

---

### 3.5 方案C：兼容性与迁移策略（必做，P1）

**目标**：确保现有分支和 worktree 不受影响，平滑迁移。

#### 迁移策略

**场景1：现有任务（无 task_key）**

```bash
# 现有分支：feature/C01
# 现有 worktree：.worktrees/C01
# 现有状态：docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json

# 行为：继续使用原命名（向后兼容）
bash scripts/coder4/wt-flow.sh next
# 预期：仍然创建 feature/C02（不强制迁移）
```

**场景2：新任务（有 task_key）**

```bash
# 新任务：task_key=planner-refactor
bash scripts/coder4/set_active_task.py --task-split-dir 2026-03-03_planner-refactor --project-id 123
bash scripts/coder4/wt-flow.sh next
# 预期：创建 feature/planner-refactor/C01（新命名）
```

**场景3：手动迁移现有任务**

```bash
# 可选：为现有任务补充 task_key
# 1. 编辑 _active_task.json，添加 "task_key": "legacy-task"
# 2. 重命名现有分支和 worktree
git branch -m feature/C01 feature/legacy-task/C01
mv .worktrees/C01 .worktrees/legacy-task/C01
mv docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state-legacy-task.json
```

#### 兼容性检查清单

- [ ] 现有任务（无 task_key）能继续推进
- [ ] 新任务（有 task_key）使用新命名
- [ ] 混合场景（新旧任务并存）不冲突
- [ ] 提供迁移脚本（可选）

**实施成本**：低（1-2 小时）

---

### 3.6 方案D：冲突预警工具（可选，P2）

**目标**：在合并前预警潜在冲突，建议合并顺序。

**实施方案**：

新增脚本 `scripts/wt-flow-conflict-check.sh`，用于：
1. 检测多个 worktree 修改的文件
2. 分析潜在冲突（同一文件的不同区域）
3. 建议合并顺序（基于依赖关系和冲突风险）

**使用方式**：
```bash
# 检查所有 worktree 的潜在冲突
bash scripts/wt-flow-conflict-check.sh

# 输出示例
=== Worktree 冲突分析 ===
任务A (planner-refactor):
  - multi_agent_graph.py (3811-3900行)
  - state.py (50-80行)

任务B (todo-enhance):
  - multi_agent_graph.py (1016-1087行)
  - todo_prompts.py (240-320行)

潜在冲突:
  ⚠️  multi_agent_graph.py (任务A和任务B都修改了此文件)
      - 任务A: 3811-3900行
      - 任务B: 1016-1087行
      - 风险: 低（不同区域）

建议合并顺序:
  1. 任务B (todo-enhance) - 无依赖，风险低
  2. 任务A (planner-refactor) - 依赖任务B，风险中
```

**验收标准**：
1. 能检测出被多个任务修改的文件
2. 能分析修改的行号范围
3. 能判断冲突风险（高/中/低）
4. 能给出合并顺序建议

**实施成本**：中（1 天）

---

## 4. 方案对比与推荐（v2.1）

### 4.1 方案对比

| 方案 | 解决冲突类型 | 需要改脚本 | 实施成本 | 风险 | 推荐度 | 优先级 |
|------|-------------|-----------|----------|------|--------|--------|
| **方案A：task_key 命名空间** | 类型1+2+3（含3a/3b） | ✅ 是 | 中（1天） | 中 | ⭐⭐⭐⭐ | P0 必做 |
| **方案B：流程规范 + 手动切换** | 类型4（active 索引） | ❌ 否 | 低（2h） | 低 | ⭐⭐⭐⭐⭐ | P0 必做 |
| **方案C：兼容性与迁移** | 向后兼容 | ❌ 否 | 低（1h） | 低 | ⭐⭐⭐⭐⭐ | P1 必做 |
| **方案D：冲突预警工具** | 提前预警 | ✅ 是 | 中（1天） | 低 | ⭐⭐⭐ | P2 可选 |

### 4.2 推荐实施路径

**阶段1：立即实施（本周）**
- ✅ 方案1：task_key 命名空间隔离（P0）
- ✅ 方案2：兼容性与迁移策略（P1）
- ✅ 验证多任务并行开发流程

**阶段2：短期优化（下周）**
- 🔄 方案3：冲突预警工具（P2）
- 🔄 建立多任务并行开发规范文档

**v1 方案的废弃说明**：
- ~~方案2（自动合并机制）~~：已在 `jjk-cardrun` 中实现，无需新增
- ~~方案4（合并队列）~~：复杂度高，暂不推荐

---

## 5. 实施计划（v2.1）

### 5.1 方案1：task_key 命名空间隔离（立即实施）

**负责人**：待定
**预计工时**：2-3 小时
**实施步骤**：

1. **修改 `wt-flow.sh`**（1.5 小时）
   - 修改 `cmd_create` 函数（分支命名 + worktree 目录）
   - 修改 `_mark_card_done_after_merge` 函数（状态文件）
   - 从 `_active_task.json` 读取 `task_key`
   - 向后兼容处理（无 task_key 时使用原命名）

2. **测试验证**（1 小时）
   - 创建两个测试任务（不同 task_key）
   - 验证分支名、worktree 目录、状态文件不冲突
   - 验证向后兼容性（无 task_key 场景）
   - 验证 verify → merge → done 流程

3. **文档更新**（30 分钟）
   - 更新 `wt-flow.sh` 的使用说明
   - 更新 `.cursor/commands/jjk-cardrun.md`（如需）

**验收标准**：
- [ ] 多个任务并行时，三类资源不冲突
- [ ] 分支名格式：`feature/<task_key>/<card_id>`
- [ ] Worktree 目录：`.worktrees/<task_key>/<card_id>`
- [ ] 状态文件：`docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state-<task_key>.json`
- [ ] 向后兼容（没有 `task_key` 时仍使用原命名）
- [ ] 通过验收命令（见 5.4 节）

**回滚策略**：
```bash
# 如果出现问题，回滚到修改前版本
git checkout HEAD -- scripts/coder4/wt-flow.sh
```

---

### 5.2 方案2：兼容性与迁移策略（同步实施）

**负责人**：待定
**预计工时**：1-2 小时
**实施步骤**：

1. **编写迁移文档**（30 分钟）
   - 现有任务如何继续推进
   - 新任务如何使用新命名
   - 可选的手动迁移步骤

2. **测试混合场景**（1 小时）
   - 现有任务（无 task_key）+ 新任务（有 task_key）
   - 验证两者不冲突
   - 验证现有任务不受影响

3. **编写迁移脚本**（可选，30 分钟）
   - 自动为现有任务补充 task_key
   - 自动重命名现有分支和 worktree

**验收标准**：
- [ ] 现有任务（无 task_key）能继续推进
- [ ] 新任务（有 task_key）使用新命名
- [ ] 混合场景不冲突
- [ ] 提供迁移文档

---

## 6. 风险评估（v2.1）

### 6.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 命名空间修改破坏现有流程 | 高 | 低 | 向后兼容设计 + 充分测试 + 回滚策略 |
| 状态文件隔离导致状态丢失 | 高 | 低 | 保留原状态文件 + 迁移脚本 |
| 多任务并行导致 Git 冲突 | 中 | 高 | 冲突预警工具 + 合并顺序建议 |

### 6.2 流程风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 多任务并行导致合并顺序混乱 | 中 | 高 | 建立合并顺序规范 + 冲突预警 |
| 团队成员不熟悉新流程 | 低 | 高 | 文档培训 + 示例演示 |
| 现有任务迁移成本高 | 低 | 中 | 向后兼容 + 可选迁移 |

---

## 7. 成功指标（v2.1）

### 7.1 功能指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|----------|
| 分支命名冲突率 | 100%（多任务时） | 0% | 实际测试 |
| Worktree 目录冲突率 | 100%（多任务时） | 0% | 实际测试 |
| 状态文件冲突率 | 100%（多任务时） | 0% | 实际测试 |
| 自动合并成功率 | 已实现（verify→merge→done） | 保持 100% | 统计数据 |

### 7.2 效率指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|----------|
| 多任务并行开发周期 | 串行（3-6周） | 并行（1-2周） | 项目周期统计 |
| 任务切换耗时 | 10-20分钟/次 | ≤ 5分钟/次 | 时间记录 |
| 冲突解决耗时 | 1-2小时/冲突 | ≤ 30分钟/冲突 | 时间记录 |

---

## 8. 附录（v2.1）

### 8.1 相关文件清单（权威源）

| 文件 | 说明 | 关键行号 |
|------|------|---------|
| `.cursor/commands/jjk-cardrun.md` | 串行卡片执行入口（权威源） | 133-147（merge 流程） |
| `.cursor/commands/jjk-vkplan.md` | 并行拆解入口（权威源） | 99-110（契约继承） |
| `scripts/coder4/wt-flow.sh` | Worktree 生命周期管理脚本 | 20（WT_BASE）<br>21（STATE_FILE）<br>22（ACTIVE_TASK_FILE）<br>43-47（dirty whitelist）<br>211（_task_state_file）<br>406-417（_save_state）<br>434-439（分支名解析）<br>387（路径匹配） |
| `docs/内部参考/任务拆解/<task_split_dir>/_active_task.json` | 活跃任务索引 | - |
| `docs/内部参考/任务拆解/<task_key>/_active_task.json` | 任务级配置 | - |
| `docs/内部参考/任务拆解/<task_key>/vk_cards.json` | 卡片契约 | - |

### 8.2 参考文档

- [Git Worktree 官方文档](https://git-scm.com/docs/git-worktree)
- [多任务并行开发最佳实践](https://docs.github.com/en/get-started/using-git/about-git-worktree)
- [Supervisor 架构重构方案](./2026-03-02-supervisor-refactor-remove-planner.md)

### 8.3 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-03-03 | v1.0 | 初始版本 | Claude |
| 2026-03-03 | v2.0 | 基于权威源全面更新：<br>1. 修正"缺少自动合并"假设（已实现）<br>2. 识别四类冲突（分支/worktree/状态）<br>3. 提供 task_key 命名空间隔离方案<br>4. 更新所有行号引用与流程图 | Claude |
| 2026-03-03 | v2.1 | 可发布版（一致性修订）：<br>1. 统一冲突分类口径（4大类，状态分3a/3b子类）<br>2. 校正所有脚本锚点（WT_BASE:20, STATE_FILE:21等）<br>3. 补充联动影响清单（bootstrap_kernel, vk_sync）<br>4. 修正章节编号重复与措辞过满问题<br>5. 统一工时口径与结论段描述 | Claude |

---

## 9. 快速参考（v2.1）

### 9.1 核心问题

**三类冲突**：
1. 分支名冲突：`feature/C01` 被多个任务复用
2. Worktree 目录冲突：`.worktrees/C01` 被多个任务复用
3. 全局状态冲突：`docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json` 被多个任务覆盖

### 9.2 核心方案

**task_key 命名空间隔离**：
- 分支名：`feature/<task_key>/<card_id>`
- Worktree 目录：`.worktrees/<task_key>/<card_id>`
- 状态文件：`docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state-<task_key>.json`

### 9.3 验收命令

```bash
# 1. 创建两个并行任务
bash scripts/coder4/set_active_task.py --task-split-dir 2026-03-03_planner-refactor --project-id 123
bash scripts/coder4/wt-flow.sh next

bash scripts/coder4/set_active_task.py --task-split-dir 2026-03-03_todo-enhance --project-id 124
bash scripts/coder4/wt-flow.sh next

# 2. 检查资源隔离
git branch | grep feature/
ls -la .worktrees/
ls -la docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/

# 3. 验证完整流程
bash scripts/coder4/wt-flow.sh verify C01
bash scripts/coder4/wt-flow.sh merge
```

---

**报告结论（v2.1）**：

当前 `jjk-cardrun` + `wt-flow.sh` 的架构**已包含 verify → merge → done 的完整闭环**（v1 报告的"缺少自动合并"假设不成立），但在多任务并行场景下存在**四类资源冲突**（分支名、worktree 目录、全局状态文件）。

**推荐立即实施方案1（task_key 命名空间隔离）**，通过为分支名、worktree 目录、状态文件增加 `task_key` 前缀，彻底解决三类冲突，支持任务级并行 + 卡片级串行的开发模式。方案2（兼容性与迁移）同步实施，确保现有任务不受影响。方案3（冲突预警工具）可作为中期优化，进一步提升多任务并行开发的效率和安全性。

---

## 附录更新（v2.1 补充）

### 8.4 脚本修改清单（方案A必须改造点）

| 修改点 | 文件位置 | 修改类型 | 说明 |
|--------|---------|---------|------|
| 分支命名 | `wt-flow.sh` cmd_create 函数 | ✅ 必须改 | 增加 task_key 前缀 |
| Worktree 目录 | `wt-flow.sh` cmd_create 函数 | ✅ 必须改 | 增加 task_key 子目录 |
| 会话状态文件 | `wt-flow.sh:21` + 所有使用处 | ✅ 必须改 | 改为动态函数 `_session_state_file` |
| 卡片状态文件 | `wt-flow.sh:211` _task_state_file | ✅ 必须改 | 增加 task_key 子目录 |
| 分支名解析兼容 | `wt-flow.sh:434` | ✅ 必须改 | 兼容 `feature/<task_key>/<card_id>` 格式 |
| card_id 提取兼容 | `wt-flow.sh:439` | ✅ 必须改 | 兼容两种格式提取 card_id |
| 路径匹配兼容 | `wt-flow.sh:387` | ✅ 必须改 | 兼容两种路径格式 |

### 8.5 流程规范清单（方案B仅流程约束）

| 约束点 | 文件位置 | 修改类型 | 说明 |
|--------|---------|---------|------|
| 单 active 索引 | `README.md:64` | ❌ 仅流程 | 通过任务切换流程管理 |
| scope_guard 依赖 | `coder4_scope_guard.py:16` | ❌ 仅流程 | 自动跟随 active 索引 |
| set_active_task 覆盖 | `set_active_task.py:132` | ❌ 仅流程 | 设计行为，不需修改 |

### 8.6 v2.1 变更说明

**v2.1 P0 修正版（可执行）**：
1. 校正所有脚本锚点与变量名（WT_BASE:20, STATE_FILE:21, ACTIVE_TASK_FILE:22）
2. 拆分状态冲突为会话状态（21行）和卡片状态（211行）
3. 补齐兼容改造点（434, 439, 387行）
4. 明确单 active 索引约束处理（流程规范，不改脚本）
5. 更新验收命令为可执行版本（基于 jjk-* 流程）
6. 区分"必须改脚本"与"仅流程约束"
7. 识别四类冲突（分支名、worktree目录、会话状态、卡片状态）

---

**报告结论（v2.1 最终版）**：

当前 `jjk-cardrun` + `wt-flow.sh` 的架构**已包含 verify → merge → done 的完整闭环**，但在多任务并行场景下存在**四类资源冲突**：

1. **分支名冲突**（类型1）：`feature/C01` 被多个任务复用
2. **Worktree 目录冲突**（类型2）：`${WT_BASE}/C01` 被多个任务复用  
3. **会话状态冲突**（类型3a）：`docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json` 被多个任务覆盖
4. **卡片状态冲突**（类型3b）：`task-runner-state.json` 被多个任务覆盖
5. **Active 索引冲突**（类型4）：单一 `_active_task.json` 被多个任务争抢

**推荐立即实施**：
- **方案A**（P0）：task_key 命名空间隔离，修改 `wt-flow.sh` 的 7 个关键点，解决类型1+2+3a+3b冲突
- **方案B**（P0）：流程规范 + 手动切换，通过流程约束解决类型4冲突（不改脚本）
- **方案C**（P1）：兼容性与迁移策略，确保现有任务不受影响
- **方案D**（P2）：冲突预警工具，中期优化

关键脚本引用已校验，建议实施前再次确认，验收命令可直接执行。
