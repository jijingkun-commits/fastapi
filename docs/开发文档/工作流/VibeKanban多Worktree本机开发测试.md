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
  - 启动 `web` 前会检查 `web/node_modules` 与 `next` CLI；依赖缺失时自动安装（`pnpm install --frozen-lockfile`/`npm ci`，失败回退常规 install）。
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

- 在 `main`/`master` 上执行 `/jjk-review` 与 `/jjk-test`。
- 默认走固定端口 `3000/8000`。

## Vibe Kanban 项目配置建议

在 Project 的脚本配置中可直接填写：

- Setup Script: `bash scripts/vk_setup.sh`
- Dev Server Script: `bash scripts/vk_dev.sh up`
- Cleanup Script: `bash scripts/vk_cleanup.sh`

## 与测试规则的关系

本次变更遵循以下原则：

1. 子任务阶段（`/jjk-imp-ws`）执行最小验证，避免把所有 worktree 都拉到全量测试。
2. 全量 `review/test` 在门禁层统一执行，保持基线稳定。
3. 若在主分支执行测试，仍优先使用 `3000/8000`。


## 命令侧端到端流程（并行开发）

为避免“拆了解但不能并行执行”，建议命令链路固定为：

> 命令权威源：`.cursor/commands/*.md`。本文用于流程落地与本机脚本约定，命令细节冲突时以权威源为准。

```text
/jjk-clarify -> /jjk-plan parallel（或 /jjk-plan core） -> /jjk-vkplan
        -> /jjk-vktodo <任务拆解目录> create（create-only）
        -> /jjk-cardrun <任务拆解目录> loop
        -> python3 scripts/check_gate_contract_consistency.py --task-split-dir <任务拆解目录>
        -> python3 scripts/check_integration_gate.py --task-split-dir <任务拆解目录> --baseline master
        -> /jjk-review -> /jjk-test（或 /jjk-verify）
```

`/jjk-vktodo` 推荐优先使用路径直传，减少手写 `cards=` 长参数：

```text
/jjk-vktodo 2026-02-12_skill检索对齐_cursor_mvp
```

显式 create 示例：

```text
/jjk-vktodo 2026-02-12_skill检索对齐_cursor_mvp create
```

关键要求：

1. 先执行 `/jjk-plan` 产出需求与技术方案；并行推荐 `/jjk-plan parallel` 直接给出 `task_key/card_seed`，若使用 `/jjk-plan core` 则由 `/jjk-vkplan` 推导并在 `parallel_plan.md` 标注来源。
2. `/jjk-vkplan` 固定产出 `WS-00_G0_协议冻结`，并为每个 WS 生成 `card_export`。
3. `WS-00` 在 `/jjk-vkplan` 阶段生成并冻结；需先将含 `WS-00` 的基线提交合并，再从该基线拆分并行 worktree。
4. `/jjk-vktodo` 仅负责 create-only 幂等建卡；状态推进与执行调度由 `/jjk-cardrun` 负责。
5. `WS-00` 为 master 前置里程碑，不进入 VK 落卡与推进列表。
6. `/jjk-vktodo` 路径模式会自动读取 `vk_cards.json`，建卡时使用卡片 `column`，不再支持 `move` 推进。
7. 卡片唯一键必须为 `<task_key>::<WS-ID>`，标题采用 `WS-ID` 前置并保留 `task_key`。
8. `/jjk-cardrun` 对实现卡必须执行 `verify -> merge -> done`，并在 merge 后生成证据。
9. Gate 层至少包含 `G01`（契约一致性）与 `IG01`（主干可见性）双门禁。
10. 自动执行器运行前，必须将当前任务写入 `docs/内部参考/任务拆解/_active_task.json`，并确保其中 `task_key` 与目标 `vk_cards.json` 一致。
11. coder4 自动执行总控细节与排障请看：`docs/开发文档/工作流/Coder4自动执行总控手册.md`。

推荐命令：

```bash
python3 scripts/set_active_task.py \
  --task-split-dir <YYYY-MM-DD_主题> \
  --project-id <VK_PROJECT_ID>
```
