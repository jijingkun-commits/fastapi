---
description: Worktree 隔离实现：自动建分支 -> 隔离编码 -> 合并回主分支
---

> 参考规则: @dual-database

# Worktree 隔离实现工作流 (Worktree-Isolated Implementation)

在独立 worktree 中执行代码修改，完成后自动合并回主分支，保证每次改动可追溯、可回滚。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 任何需要隔离的代码修改 | `/jjk-wtimp` |
| 已有计划，只需编码（不隔离） | `/jjk-imp` |
| 已拆分为 WS 子任务 | `/jjk-imp-ws` |
| 一站式从需求到交付 | `/jjk-feature` |

> **等效于**: worktree 创建 + `/jjk-imp` + 测试验证 + 自动合并 + 清理

---

## 阶段 0: 环境校验与 Worktree 创建

### 0.1 执行上下文校验

```bash
pwd
git rev-parse --show-toplevel
git branch --show-current
git worktree list
```

- 确认当前在主仓库的 master/main 分支上
- 确认工作区干净（无未提交变更）

### 0.2 生成分支名

从用户输入中提取关键词，生成分支 slug：

- 格式: `<日期>-<关键词>`，如 `20260226-add-export-api`
- 日期使用 YYYYMMDD
- 关键词用英文短横线连接，不超过 40 字符

### 0.3 创建 Worktree

```bash
bash scripts/wt-flow.sh create <slug>
```

脚本会自动：
1. 从 master 创建 `feature/<slug>` 分支
2. 在 `.worktrees/<slug>/` 创建 worktree
3. 保存会话状态到 `.omc/state/wt-flow-state.json`

### 0.4 切换工作目录

创建成功后，**所有后续操作必须在 worktree 路径下执行**：

```bash
cd <worktree-path>
```

验证切换成功：

```bash
git branch --show-current  # 应显示 feature/<slug>
```

---

## 阶段 1: 复杂度评估与执行模式选择

进入编码前，先评估任务复杂度，决定单人执行还是 team 并行。

### 1.1 复杂度判定

根据 implementation_plan 或 requirements 文档，统计预期改动范围：

| 指标 | 单人模式 | Team 并行模式 |
|------|---------|--------------|
| 预期改动文件数 | <= 5 | > 5 |
| 涉及独立模块数 | 1 | >= 2 |
| 前后端同时改动 | 否 | 是 |
| 有 implementation_plan 且含多个 phase | 否 | 是 |

满足 Team 并行模式任一条件时，**建议用户切换到 team 模式**：

```
检测到本次任务涉及 N 个文件 / M 个独立模块，建议使用 team 并行执行。
是否切换？(Y/n)
```

- 用户确认后，进入阶段 1B（Team 并行）
- 用户拒绝或任务简单，进入阶段 1A（单人编码）

### 1A: 单人编码

完全复用 `/jjk-imp` 的编码规范，在 worktree 内执行：

**输入**:
- `docs/内部参考/迭代需求/<topic>_requirements.md`（迭代级概览）
- `docs/产品文档/<模块>需求.md`（模块级用户故事/验收标准）
- `docs/内部参考/迭代需求/<topic>_implementation_plan.md`（如有）

**规范**:
- 遵循 `.cursor/rules/core.mdc`、`.cursor/rules/doc_sync.mdc` 与场景规则
- 若涉及架构/API/表结构/配置变更，先更新对应文档草案，再进入代码修改
- **禁止**: 自作聪明地修改需求
- 关键行为变化需回填到测试案例文档与追溯矩阵

### 1B: Team 并行编码

在当前 worktree 内启动 team，**teammates 不得使用 `isolation: "worktree"`**（避免 worktree 嵌套）。

**启动方式**:

```
/team N:executor "在 <worktree-path> 内完成以下任务：..."
```

**约束**:
1. 所有 teammates 的工作目录必须是当前 worktree 路径
2. teammates 之间按文件/模块划分职责，避免同文件冲突
3. 每个 teammate 完成后提交各自的改动
4. team 完成后，由主流程统一进入阶段 2（文档同步）和阶段 3（验证）

---

## 阶段 2: 文档同步闭环 (Doc Sync Loop)

完全复用 `/jjk-imp` 的文档同步规则：

- API 变更 -> `docs/API文档/接口文档.md`
- 数据库变更 -> `docs/开发文档/架构设计/数据库设计.md`
- 配置变更 -> `docs/开发文档/快速入门/配置说明.md` + `.env.example`
- 架构变更 -> 对应架构文档

---

## 阶段 3: 提交与验证

### 3.1 在 worktree 内提交

```bash
cd <worktree-path>
git add <files>
git commit -m "<type>(<scope>): <描述>"
```

遵循 `/jjk-git-commit` 的提交规范。

### 3.2 快速自测

```bash
# 在 worktree 内运行相关测试
cd <worktree-path>
python -m pytest tests/path/to/test.py -v
```

- 测试通过后才进入合并阶段
- 测试失败则修复后重新提交

---

## 阶段 4: 合并回主分支

### 4.1 执行合并

```bash
bash scripts/wt-flow.sh merge
```

脚本会自动：
1. 检查 worktree 内无未提交变更
2. 检查 master 是否前进，如有则先 rebase
3. rebase 冲突时自动 abort 并提示手动解决
4. `git merge --no-ff` 合并回 master（保留合并提交）
5. 清理 worktree 和分支

### 4.2 异常处理

| 场景 | 脚本行为 | 用户操作 |
|------|---------|---------|
| worktree 有未提交变更 | 拒绝合并 | 先 commit |
| rebase 冲突 | 自动 abort，保留 worktree | 手动进入 worktree 解决冲突 |
| merge 冲突 | 自动 abort | 手动解决后重新 merge |
| 无新提交 | 跳过合并，直接清理 | 无需操作 |

### 4.3 保留 worktree（可选）

如果想合并但保留 worktree 供后续使用：

```bash
bash scripts/wt-flow.sh merge --no-cleanup
```

---

## 完整执行示例

```
/jjk-wtimp 添加导出 API 功能

# 自动执行:
# 1. bash scripts/wt-flow.sh create 20260226-add-export-api
# 2. cd .worktrees/20260226-add-export-api
# 3. 编码 + 文档同步（同 /jjk-imp）
# 4. git add + git commit
# 5. pytest 验证
# 6. bash scripts/wt-flow.sh merge
# 7. 回到 master，合并完成
```

---
*使用 `/jjk-wtimp` 触发。等效于 worktree 隔离版的 `/jjk-imp`，每次改动独立分支、可追溯、可原子回滚。*
