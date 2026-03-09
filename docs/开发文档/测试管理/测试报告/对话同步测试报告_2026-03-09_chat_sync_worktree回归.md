# 对话同步测试报告_2026-03-09_chat_sync_worktree回归

## Executive Summary
- 结论：PASS（本轮仅针对 `web/e2e/chat_sync.spec.cjs` 做定向回归）
- 范围：`/Users/jijingkun/.codex/worktrees/dc2d/fastapi/web/e2e/chat_sync.spec.cjs`
- 环境：worktree=`/Users/jijingkun/.codex/worktrees/dc2d/fastapi`，branch=`codex/skill`
- 端口：`VK_BACKEND_BASE_URL=http://127.0.0.1:8155`，`VK_FRONTEND_BASE_URL=http://127.0.0.1:3748`
- 结果：`5 passed (2.9m)`
- 说明：本轮回归使用 `--no-deps`，因为全局 `auth.setup` 仍走旧 UI 登录 + `storageState` 路径，不适配当前 `sessionStorage(auth:token)` 认证模型

## Root Cause
- 本轮收口的问题不是业务断言，而是测试自身过度依赖固定等待：`waitForTimeout(...)` 太多，导致时序靠碰运气。
- 收敛方式：
  - 复用现有 `sendMessageAndWait(...)` / `waitForChatReady(...)`
  - 用 `locator` 可见性与 `expect.poll(...)` 替代裸 sleep
  - 不新增新 helper，不扩散修改范围，只瘦 `chat_sync.spec.cjs`
- 独立运行态风险：`web/e2e/auth.setup.cjs` 仍假设认证可由 `storageState` 复用，但当前前端 token 真正存放在 `sessionStorage`，所以带依赖的全链路 setup 仍不可靠

## Lean Evidence
- 文件：`/Users/jijingkun/.codex/worktrees/dc2d/fastapi/web/e2e/chat_sync.spec.cjs`
- 变更量：`+49 / -115`，净减 `66` 行
- 结构变化：
  - 删除 8 处裸 `waitForTimeout(...)`
  - 删除重复的“填输入框 + 回车 + 等待 AI”样板代码
  - 统一收口到现有 helper 与状态断言

## Required Evidence
- 上下文比对通过（worktree / branch）
- 最小静态校验通过（`node -c` / `eslint`）
- 后端在线健康检查通过
- `chat_sync.spec.cjs` 顺序回归通过

## Actual Evidence
- 上下文比对：通过
- Python 解释器：`/Users/jijingkun/.codex/worktrees/dc2d/fastapi/.vibe/venv/bin/python`
- 后端健康检查：`GET /api/v1/health -> 200 OK`
- 回归命令：
  - `cd web && CI=1 PLAYWRIGHT_REUSE_EXISTING_SERVER=true E2E_API_BASE="$VK_BACKEND_BASE_URL" PLAYWRIGHT_BASE_URL="$VK_FRONTEND_BASE_URL" npx playwright test e2e/chat_sync.spec.cjs --project=chromium --workers=1 --reporter=line --no-deps`
- 结果：`5 passed (2.9m)`
- Playwright 报告：`/Users/jijingkun/.codex/worktrees/dc2d/fastapi/web/playwright-report/index.html`

## Trace Matrix
| 用例 | 结果 | 证据 |
|---|---|---|
| TC-SYNC-001 简单对话 | PASS | 前端拿到 AI 回复，后端登录链路可用 |
| TC-SYNC-002 刷新后历史一致性 | PASS | 刷新前后相似度 = 1 |
| TC-SYNC-003 快速连续发送 | PASS | 用户消息数量 = 3，达到预期 |
| TC-SYNC-004 长文本响应处理 | PASS | 响应长度 = 2925 |
| TC-SYNC-005 特殊字符处理 | PASS | 特殊字符按文本显示，未触发脚本执行 |

## Scripted Flow Status
- `pwd` / `git branch --show-current` / `git worktree list`：已执行
- `VERIFY_CONTEXT_MISMATCH` 检查：通过
- `bash scripts/repo_python.sh`：已执行
- `node -c web/e2e/chat_sync.spec.cjs`：通过
- `cd web && npx eslint e2e/chat_sync.spec.cjs`：通过
- `curl "$VK_BACKEND_BASE_URL/api/v1/health"`：通过
- Playwright 定向回归：通过
- 报告回填：已执行

## Residual Risk
- `web/e2e/auth.setup.cjs` 仍是旧认证模型：UI 登录 + `storageState`。
- 当前前端实际认证模型是 `sessionStorage(auth:token)`；因此带 `dependencies: ['setup']` 的全链路 Playwright 运行，仍可能卡在 setup，而不是卡在业务用例本身。
- 这不影响本轮 `chat_sync.spec.cjs` 的定向通过结论，但影响更大范围 E2E 的统一稳定性。

## Commands
```bash
pwd
git branch --show-current
git worktree list
eval "$(bash scripts/vk_ports.sh --export)"
git rev-parse --show-toplevel
git rev-parse HEAD
bash scripts/repo_python.sh
node -c web/e2e/chat_sync.spec.cjs
cd web && npx eslint e2e/chat_sync.spec.cjs
curl -i "${VK_BACKEND_BASE_URL}/api/v1/health"
cd web && CI=1 PLAYWRIGHT_REUSE_EXISTING_SERVER=true E2E_API_BASE="$VK_BACKEND_BASE_URL" PLAYWRIGHT_BASE_URL="$VK_FRONTEND_BASE_URL" npx playwright test e2e/chat_sync.spec.cjs --project=chromium --workers=1 --reporter=line --no-deps
```
