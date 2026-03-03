# 多任务并行开发 Worktree 冲突问题分析报告

> **文档类型**: 问题分析与解决方案
> **创建日期**: 2026-03-03
> **问题优先级**: P1（阻塞多任务并行开发）
> **涉及组件**: `jjk-cardrun`, `wt-flow.sh`, `jjk-vkplan`

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

### 1.2 技术架构

项目采用 `jjk-*` 工作流体系进行任务管理：

```
/jjk-plan (生成需求与技术方案)
  ↓
/jjk-vkplan (拆解为卡片 + 生成 vk_cards.json)
  ↓
/jjk-cardrun (串行执行卡片)
  ├─ wt-flow.sh next (创建 worktree + 激活卡片)
  ├─ /jjk-imp-ws (执行单卡实现)
  ├─ wt-flow.sh verify (done_gate 验证)
  └─ wt-flow.sh merge (合并回主分支) ← 需要手动调用
```

**Worktree 隔离机制**：
- 每个卡片在独立的 worktree 中开发
- 分支命名：`feature/<card_id>`（如 `feature/C03`）
- 工作目录：`.worktrees/<card_id>`

---

## 2. 问题分析

### 2.1 问题1：分支命名冲突

**问题描述**：

当前分支命名格式为 `feature/<card_id>`，缺少任务上下文前缀。当多个任务并行时，如果卡片编号相同（如任务A的C01和任务B的C01），会导致分支名冲突。

**根因分析**：

`wt-flow.sh` 的 `cmd_create` 函数（第336行）：
```bash
local branch="feature/${slug}"
```

`cmd_next` 函数调用 `cmd_create "$next_card"`（第446行），其中 `next_card` 就是卡片ID（如 `C03`），没有任务前缀。

**实际案例**：

```bash
# 任务A：移除 Planner
git branch
  feature/C01  # 图结构调整
  feature/C02  # State 合同调整
  feature/C03  # Supervisor 重构

# 任务B：待办优化（并行开发）
git worktree add .worktrees/C01 feature/C01  # ❌ 冲突！分支已存在
```

**影响范围**：
- ❌ 无法同时开发多个任务
- ❌ 分支名冲突导致 `git worktree add` 失败
- ❌ 即使手动改名，也无法追溯卡片与任务的对应关系

### 2.2 问题2：缺少自动合并机制

**问题描述**：

`jjk-cardrun` 只负责"拆解 + 执行 + 验证"，不包括"合并回主分支"。所有卡片执行完成后，需要手动调用 `wt-flow.sh merge` 才能合并。

**根因分析**：

查看 `jjk-cardrun` 的 SKILL.md（第73-151行），执行流程为：
```
1. 读取并校验串行契约
2. 选卡与激活（wt-flow.sh next）
3. 主控调度子代理执行（/jjk-imp-ws）
4. done_gate 验证（wt-flow.sh verify）
5. 循环推进策略（mode=loop）
```

**缺失环节**：
- ❌ 没有第6步：合并回主分支
- ❌ 所有卡片 done 后，worktree 和分支仍然存在
- ❌ 需要手动执行 `bash scripts/wt-flow.sh merge`

**影响范围**：
- ⚠️ 容易遗忘合并步骤，导致代码未同步到主分支
- ⚠️ 多个任务完成后，不清楚合并顺序
- ⚠️ 手动合并容易出错（忘记切换分支、忘记 cleanup 等）

### 2.3 问题3：冲突检测与解决机制不完善

**问题描述**：

当多个任务修改同一文件时，合并时可能产生冲突。当前 `wt-flow.sh merge` 有冲突检测，但缺少以下能力：
1. **冲突预警**：合并前无法预知哪些文件会冲突
2. **自动解决**：简单冲突（如导入语句顺序）需要手动解决
3. **合并顺序**：多个任务完成后，不知道先合并哪个

**根因分析**：

`wt-flow.sh` 的 `cmd_merge` 函数（第492-530行）：
```bash
# 1. 如果 base_branch 有新提交，先 rebase
if ! git -C "$wt_path" rebase "${base_branch}" 2>/dev/null; then
    _err "rebase 冲突，自动中止 rebase，保留 worktree 供手动解决"
    git -C "$wt_path" rebase --abort 2>/dev/null || true
    exit 1
fi

# 2. 执行 merge
if ! git merge --no-ff "${branch}" -m "merge: ${branch} into ${base_branch}"; then
    _err "merge 冲突，自动中止"
    git merge --abort 2>/dev/null || true
    exit 1
fi
```

**冲突处理策略**：
- ✅ 有冲突检测（rebase 和 merge 阶段）
- ✅ 冲突时自动中止，保留现场
- ❌ 没有冲突预警（合并前不知道会不会冲突）
- ❌ 没有自动冲突解决
- ❌ 没有合并顺序建议

**实际案例**：

```bash
# 任务A：移除 Planner（修改 multi_agent_graph.py 第3811-3900行）
# 任务B：待办优化（修改 multi_agent_graph.py 第1016-1087行）

# 任务A先合并 → 成功
bash scripts/wt-flow.sh merge

# 任务B后合并 → 可能冲突
bash scripts/wt-flow.sh merge
# ❌ rebase 冲突：multi_agent_graph.py
# 需要手动进入 .worktrees/C01 解决冲突
```

**影响范围**：
- ⚠️ 合并时才发现冲突，浪费时间
- ⚠️ 手动解决冲突容易出错
- ⚠️ 不知道先合并哪个任务，可能选择错误的合并顺序

---

## 3. 解决方案

### 3.1 方案1：分支命名增加任务前缀（短期，必做）

**目标**：解决分支名冲突问题，支持多任务并行开发。

**实施方案**：

修改 `wt-flow.sh` 的 `cmd_create` 和 `cmd_next` 函数，从 `_active_task.json` 读取 `task_key`，拼接到分支名中。

**修改位置**：`scripts/wt-flow.sh:336`

**修改前**：
```bash
local branch="feature/${slug}"
```

**修改后**：
```bash
local task_key=""
if [[ -f "$ACTIVE_TASK_FILE" ]]; then
  task_key="$(jq -r '.task_key // ""' "$ACTIVE_TASK_FILE" 2>/dev/null || echo "")"
fi

if [[ -n "$task_key" ]]; then
  local branch="feature/${task_key}/${slug}"
else
  local branch="feature/${slug}"
fi
```

**效果对比**：

| 场景 | 修改前 | 修改后 |
|------|--------|--------|
| 任务A的C01 | `feature/C01` | `feature/planner-refactor/C01` |
| 任务B的C01 | `feature/C01` ❌ 冲突 | `feature/todo-enhance/C01` ✅ 不冲突 |
| 任务C的C01 | `feature/C01` ❌ 冲突 | `feature/delivery-optimize/C01` ✅ 不冲突 |

**验收标准**：
1. 多个任务并行时，分支名不冲突
2. 分支名能清晰反映任务上下文
3. 向后兼容（没有 `task_key` 时仍使用原命名）

**实施成本**：低（1-2 小时）

---

### 3.2 方案2：增加自动合并机制（中期，推荐）

**目标**：`jjk-cardrun` 在所有卡片完成后，自动合并回主分支。

**实施方案**：

在 `jjk-cardrun` 的 SKILL.md 中增加第6步：合并回主分支。

**修改位置**：`.agents/skills/jjk-cardrun/SKILL.md:73-151`

**新增流程**：
```
5. 循环推进策略（mode=loop）
6. 自动合并（新增）
   - 检测所有卡片是否 done
   - 调用 wt-flow.sh merge
   - 清理 worktree 和分支
```

**实现逻辑**（伪代码）：
```python
# 在 jjk-cardrun 的最后阶段
if mode == "loop" and all_cards_done():
    # 检查是否有未合并的 worktree
    if has_active_worktree():
        # 自动合并
        run("bash scripts/wt-flow.sh merge")
        log("所有卡片已完成并合并到主分支")
    else:
        log("所有卡片已完成，无需合并")
```

**配置选项**（可选）：
```bash
# 环境变量控制是否自动合并
export CARDRUN_AUTO_MERGE=true  # 默认 true
export CARDRUN_AUTO_CLEANUP=true  # 默认 true
```

**验收标准**：
1. 所有卡片 done 后，自动调用 `wt-flow.sh merge`
2. 合并成功后，自动清理 worktree 和分支
3. 合并失败时，保留现场并提示用户

**实施成本**：中（4-6 小时）

---

### 3.3 方案3：增加冲突预警与合并顺序建议（长期，可选）

**目标**：在合并前预警潜在冲突，并建议合并顺序。

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

**实现逻辑**：
```bash
#!/usr/bin/env bash
# wt-flow-conflict-check.sh

# 1. 列出所有 worktree
git worktree list

# 2. 对比每个 worktree 与 master 的差异
for wt in $(git worktree list | awk '{print $1}'); do
  git -C "$wt" diff master --name-only
done

# 3. 找出被多个 worktree 修改的文件
# 4. 分析修改的行号范围
# 5. 判断是否有重叠（潜在冲突）
# 6. 输出冲突报告和合并顺序建议
```

**验收标准**：
1. 能检测出被多个任务修改的文件
2. 能分析修改的行号范围
3. 能判断冲突风险（高/中/低）
4. 能给出合并顺序建议

**实施成本**：高（1-2 天）

---

### 3.4 方案4：引入合并队列与自动化冲突解决（长期，可选）

**目标**：多个任务完成后，自动按顺序合并，并尝试自动解决简单冲突。

**实施方案**：

1. **合并队列**：
   - 多个任务完成后，加入合并队列
   - 按依赖关系和冲突风险排序
   - 依次合并，失败时暂停并通知用户

2. **自动冲突解决**：
   - 导入语句冲突：自动排序并合并
   - 空行冲突：自动选择保留
   - 注释冲突：自动合并（保留两边）
   - 复杂冲突：标记为需要人工解决

**实现逻辑**（伪代码）：
```python
# 合并队列管理器
class MergeQueue:
    def add_task(self, task_key, worktree_path):
        # 加入队列
        pass

    def sort_by_priority(self):
        # 按依赖关系和冲突风险排序
        pass

    def merge_next(self):
        # 合并下一个任务
        task = self.queue.pop(0)
        try:
            # 尝试自动合并
            auto_merge(task)
        except ConflictError as e:
            # 尝试自动解决
            if can_auto_resolve(e):
                auto_resolve(e)
                auto_merge(task)
            else:
                # 需要人工解决
                notify_user(task, e)
                self.queue.insert(0, task)  # 放回队列
```

**验收标准**：
1. 多个任务完成后，自动加入合并队列
2. 按合理顺序依次合并
3. 简单冲突能自动解决
4. 复杂冲突能暂停并通知用户

**实施成本**：高（3-5 天）

---

## 4. 方案对比与推荐

### 4.1 方案对比

| 方案 | 解决问题 | 实施成本 | 风险 | 推荐度 |
|------|----------|----------|------|--------|
| **方案1：分支命名前缀** | 分支冲突 | 低（1-2h） | 低 | ⭐⭐⭐⭐⭐ 必做 |
| **方案2：自动合并** | 手动合并遗忘 | 中（4-6h） | 中 | ⭐⭐⭐⭐ 推荐 |
| **方案3：冲突预警** | 合并前不知道冲突 | 高（1-2天） | 低 | ⭐⭐⭐ 可选 |
| **方案4：合并队列** | 多任务合并顺序 | 高（3-5天） | 高 | ⭐⭐ 长期优化 |

### 4.2 推荐实施路径

**阶段1：立即实施（本周）**
- ✅ 方案1：分支命名增加任务前缀
- ✅ 验证多任务并行开发流程

**阶段2：短期优化（下周）**
- ✅ 方案2：增加自动合并机制
- ✅ 完善 `jjk-cardrun` 的完整闭环

**阶段3：中期优化（下月）**
- 🔄 方案3：增加冲突预警
- 🔄 建立多任务并行开发规范

**阶段4：长期优化（下季度）**
- 🔄 方案4：引入合并队列
- 🔄 自动化冲突解决

---

## 5. 实施计划

### 5.1 方案1：分支命名前缀（立即实施）

**负责人**：待定
**预计工时**：1-2 小时
**实施步骤**：

1. **修改 `wt-flow.sh`**（30分钟）
   - 修改 `cmd_create` 函数
   - 从 `_active_task.json` 读取 `task_key`
   - 拼接到分支名中

2. **测试验证**（30分钟）
   - 创建两个测试任务
   - 验证分支名不冲突
   - 验证向后兼容性

3. **文档更新**（30分钟）
   - 更新 `wt-flow.sh` 的使用说明
   - 更新 `jjk-cardrun` 的 SKILL.md

**验收标准**：
- [ ] 多个任务并行时，分支名不冲突
- [ ] 分支名格式：`feature/<task_key>/<card_id>`
- [ ] 向后兼容（没有 `task_key` 时仍使用原命名）

---

### 5.2 方案2：自动合并机制（下周实施）

**负责人**：待定
**预计工时**：4-6 小时
**实施步骤**：

1. **修改 `jjk-cardrun` SKILL.md**（1小时）
   - 增加第6步：自动合并
   - 定义合并触发条件
   - 定义失败处理策略

2. **实现自动合并逻辑**（2-3小时）
   - 检测所有卡片是否 done
   - 调用 `wt-flow.sh merge`
   - 处理合并失败场景

3. **测试验证**（1-2小时）
   - 测试正常合并流程
   - 测试合并冲突场景
   - 测试失败回滚

**验收标准**：
- [ ] 所有卡片 done 后，自动调用 `wt-flow.sh merge`
- [ ] 合并成功后，自动清理 worktree 和分支
- [ ] 合并失败时，保留现场并提示用户

---

## 6. 风险评估

### 6.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 分支命名修改破坏现有流程 | 高 | 低 | 向后兼容设计 + 充分测试 |
| 自动合并失败导致代码丢失 | 高 | 中 | 合并前备份 + 失败时保留现场 |
| 冲突解决不当导致逻辑错误 | 高 | 中 | 只自动解决简单冲突 + 人工审查 |

### 6.2 流程风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 多任务并行导致合并顺序混乱 | 中 | 高 | 建立合并顺序规范 + 冲突预警 |
| 自动合并掩盖潜在问题 | 中 | 中 | 合并后强制运行测试 + 人工审查 |
| 团队成员不熟悉新流程 | 低 | 高 | 文档培训 + 示例演示 |

---

## 7. 成功指标

### 7.1 功能指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|----------|
| 分支命名冲突率 | 100%（多任务时） | 0% | 实际测试 |
| 自动合并成功率 | 0%（需手动） | ≥ 80% | 统计数据 |
| 冲突预警准确率 | 0%（无预警） | ≥ 90% | 人工验证 |

### 7.2 效率指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|----------|
| 多任务并行开发周期 | 串行（3-6周） | 并行（1-2周） | 项目周期统计 |
| 合并操作耗时 | 30-60分钟/任务 | ≤ 10分钟/任务 | 时间记录 |
| 冲突解决耗时 | 1-2小时/冲突 | ≤ 30分钟/冲突 | 时间记录 |

---

## 8. 附录

### 8.1 相关文件清单

| 文件 | 说明 |
|------|------|
| `scripts/wt-flow.sh` | Worktree 生命周期管理脚本 |
| `.agents/skills/jjk-cardrun/SKILL.md` | 串行卡片执行入口 |
| `.agents/skills/jjk-vkplan/SKILL.md` | 并行拆解入口 |
| `docs/内部参考/任务拆解/_active_task.json` | 当前活跃任务配置 |
| `docs/内部参考/任务拆解/<task_key>/vk_cards.json` | 卡片契约 |

### 8.2 参考文档

- [Git Worktree 官方文档](https://git-scm.com/docs/git-worktree)
- [多任务并行开发最佳实践](https://docs.github.com/en/get-started/using-git/about-git-worktree)
- [Supervisor 架构重构方案](./2026-03-02-supervisor-refactor-remove-planner.md)

### 8.3 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-03-03 | v1.0 | 初始版本 | Claude |

---

**报告结论**：

当前 `jjk-cardrun` + `wt-flow.sh` 的架构支持单任务的 worktree 隔离开发，但在多任务并行场景下存在**分支命名冲突**和**缺少自动合并**两个关键问题。

**推荐立即实施方案1（分支命名前缀）**，解决分支冲突问题，支持多任务并行开发。短期内实施方案2（自动合并机制），完善 `jjk-cardrun` 的完整闭环。中长期可考虑方案3和方案4，进一步提升多任务并行开发的效率和安全性。
