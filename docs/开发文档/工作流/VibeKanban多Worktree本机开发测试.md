# Vibe Kanban 多 Worktree 本机开发与测试

## 背景

2026-02 在尝试使用 Vibe Kanban 进行子任务并行时，项目采用了 Git worktree 机制：

- 主仓库与子任务目录共享同一份 Git 历史。
- 子任务目录会创建独立 worktree，适合并行开发。

本项目选择“本机命令启动”方式（不通过容器启动 `web`/`backend`），因此在多 worktree 并行场景下出现两个典型问题：

1. 多个 worktree 同时启动服务容易端口冲突。
2. 测试流程原本按固定端口 `3000/8000` 设计，与并行开发冲突。

## 目标

1. 为 Vibe Kanban 提供可直接配置的 3 类脚本：`setup`、`dev server`、`cleanup`。
2. 主分支（`main`/`master`）保持固定端口 `3000/8000`，确保全量回归习惯不变。
3. 子任务分支允许自动端口隔离，减少并行开发冲突。

## 端口策略

### 主分支（门禁/全量测试）

- 后端固定：`8000`
- 前端固定：`3000`

### 子任务 worktree（并行开发）

- 根据 `分支名 + worktree 路径` 计算稳定端口。
- 同一 worktree 多次启动保持一致，不同 worktree 自动错开。
- 允许通过环境变量手工覆盖：
  - `VK_BACKEND_PORT`
  - `VK_FRONTEND_PORT`

## 脚本说明

脚本位于 `scripts/`：

- `scripts/vk_setup.sh`
  - 初始化 worktree 本地配置。
  - 优先复用主 worktree 的 `.env.dev` / `web/.env.local`。
  - 默认在本地 `venv` 不可用时，通过 `.vibe/venv` 复用主 worktree 的 `venv`。
  - 生成 `.env.vk.local` 与 `web/.env.vk.local`（记录当前 worktree 端口与 URL）。
- `scripts/vk_dev.sh`
  - 启动本机 `backend + web`（或单独启动其中之一）。
  - 输出当前访问地址，供本地调试和 Vibe Kanban 识别。
- `scripts/vk_cleanup.sh`
  - 停止当前 worktree 启动的服务进程并清理 PID 文件。
- `scripts/vk_ports.sh`
  - 统一计算端口并输出 `BACKEND_PORT/FRONTEND_PORT` 等环境变量。

## 共享 venv 策略

- 默认：`VK_SHARED_VENV_MODE=auto`（本地 `venv` 不可用时启用共享 venv）。
- 强制共享：`VK_SHARED_VENV_MODE=always`（共享 venv 不可用时失败）。
- 关闭共享：`VK_SHARED_VENV_MODE=off`（每个 worktree 使用独立环境）。
- 可指定共享路径：`VK_SHARED_VENV_PATH=/绝对路径/venv`。
- 若检测到本地 `venv` 不可用（例如只有 `Scripts/`），脚本会通过 `.vibe/venv` 自动指向共享 venv。

## 推荐流程

### 1) 子任务 worktree（开发自测）

```bash
bash scripts/vk_setup.sh
bash scripts/vk_dev.sh up

# 最小验证（示例）
.vibe/venv/bin/python -m pytest -q tests/unit
```

### 2) 门禁 worktree（全量回归）

- 在 `main`/`master` 上执行 `/review` 与 `/test`。
- 默认走固定端口 `3000/8000`。

## Vibe Kanban 项目配置建议

在 Project 的脚本配置中可直接填写：

- Setup Script: `bash scripts/vk_setup.sh`
- Dev Server Script: `bash scripts/vk_dev.sh up`
- Cleanup Script: `bash scripts/vk_cleanup.sh`

## 与测试规则的关系

本次变更遵循以下原则：

1. 子任务阶段（`/imp-ws`）执行最小验证，避免把所有 worktree 都拉到全量测试。
2. 全量 `review/test` 在门禁层统一执行，保持基线稳定。
3. 若在主分支执行测试，仍优先使用 `3000/8000`。


## 命令侧端到端流程（并行开发）

为避免“拆了解但不能并行执行”，建议命令链路固定为：

```text
/clarify -> /plan -> /vkplan(= /rwfj) -> /vkkb(或 /vktodo)
        -> /imp-ws(WS-01...WS-N 并行)
        -> /imp-ws(WS-G1) -> /imp-ws(WS-G2)
        -> /review -> /test
```

`/vktodo` 推荐优先使用路径直传，减少手写 `cards=` 长参数：

```text
/vktodo 2026-02-12_skill检索对齐_cursor_mvp
```

推进状态示例：

```text
/vktodo 2026-02-12_skill检索对齐_cursor_mvp move Doing
```

关键要求：

1. 先执行 `/plan`，产出需求与技术方案（含 `task_key/card_seed`）。
2. `/vkplan` 语义等价 `/rwfj`，固定产出 `WS-00_G0_协议冻结`，并为每个 WS 生成 `card_export`。
3. `WS-00` 在 `/vkplan`（`/rwfj`）阶段生成并冻结；需先将含 `WS-00` 的基线提交合并，再从该基线拆分并行 worktree。
4. `/vkkb` 或 `/vktodo` 负责默认落卡；其前置会自动执行 G0 基线校验，`/vk` 降级为可选导出审阅命令。
5. `WS-00` 为 master 前置里程碑，不进入 VK 落卡与推进列表。
6. `/vktodo` 路径模式会自动读取 `vk_cards.json`，建卡时使用卡片 `column`，推进时默认按 `task_key` 前缀筛选。
7. 卡片唯一键必须为 `<task_key>::<WS-ID>`，标题采用 `WS-ID` 前置并保留 `task_key`。
8. Gate 层按 `WS-G1 -> WS-G2` 串行执行，结果由回填脚本写入 `parallel_plan.md`。
