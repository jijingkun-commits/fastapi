# PLANS.md

本文件承接本仓库的**执行型长流程规则**。凡是“只有在实现 / 测试 / 验收阶段才需要”的门禁，统一放这里，不再堆在根 `AGENTS.md`。

## 1. `patch` 模式附加门槛（强制）
- 必须包含：影响范围、临时性说明、回退路径、后续治理任务。
- 若 `patch` 已形成新旧双轨，或无法给出 `retained_paths` 的唯一保留理由，必须升级为 `refactor`。

## 2. 执行上下文校验（强制）
### 2.1 基础观测（每次执行前）
修改代码或运行测试前必须先输出：
1. `pwd`
2. `git branch --show-current`
3. `git worktree list`

### 2.2 期望上下文比对（`jjk-verify` / 测试前强制）
1. 从输入证据中提取期望上下文（至少其一）：`task_id/pr_id`、目标分支、目标 worktree 路径、目标提交 SHA。
2. 采集实际上下文：`pwd`、`git rev-parse --show-toplevel`、`git branch --show-current`、`git rev-parse HEAD`。
3. 比对“期望 vs 实际”；任一关键项不一致，`FAIL_FAST` 输出 `VERIFY_CONTEXT_MISMATCH` 并停止测试执行。
4. `jjk-verify` 报告必须包含：目标上下文、实际上下文、比对结论、阻断/放行原因。
5. 若输入证据无法提供可比对的期望上下文，`FAIL_FAST` 输出 `VERIFY_INPUT_INCOMPLETE`，禁止进入测试阶段。

## 3. 文件编辑工具契约（强制）
1. 文件编辑必须以当前会话**实际暴露**的工具集为准；若没有独立 `apply_patch` 入口，禁止通过 shell 包装 `apply_patch`。
2. 命中该场景时，必须显式记录 `APPLY_PATCH_TOOL_UNAVAILABLE_FALLBACK`，并改用当前可用的直接写回方式（如 Python/Perl/安全 shell 重写）。
3. 若后续环境真实暴露独立 `apply_patch` 工具，应优先使用真实工具；仓内规则不为不存在的工具制造兼容壳。

## 4. 测试解释器契约（强制）
1. 任何测试/验证命令在执行前，必须先通过 `bash scripts/repo_python.sh` 解析仓库测试解释器，禁止默认裸用 `python3 -m pytest`。
2. 解析优先级固定为：`VK_RUNTIME_VENV` -> `venv` -> `.venv` -> `.vibe/venv` -> 系统 `python3/python`；只有仓内解释器不存在时，才允许回落到系统解释器。
3. `jjk-verify` / 测试证据中必须回显本次命中的解释器路径，避免再次出现“测错环境”。

## 5. 测试语义分层（强制）
1. TDD/调试阶段的定向回归，统一使用 `bash scripts/pytest_targeted.sh <tests...>`，默认附带 `--no-cov`，只验证当前根因是否命中。
2. 最终收口/门禁验证继续使用常规 pytest/coverage 命令；coverage 只属于最终收口语义，不得混入开发期红绿循环。
3. 两类命令禁止混用；若定向入口收到 `--cov` 类参数，应立即 `FAIL_FAST`。

## 6. 运行态校验（按需强制）
以下场景必须补充运行态校验，不得只做静态命令验证：
1. 端口/服务启动相关问题；
2. API 联调、E2E/UAT、回归关键链路；
3. 用户明确要求“确认服务是否启动/端口是否可用”。

推荐最小校验集（按需选择）：
1. `eval "$(bash scripts/vk_ports.sh --export)"`
2. `lsof -nP -iTCP:${VK_BACKEND_PORT} -sTCP:LISTEN`、`lsof -nP -iTCP:${VK_FRONTEND_PORT} -sTCP:LISTEN`
3. `curl -sf "http://127.0.0.1:${VK_BACKEND_PORT}/health"`
4. `curl -I "http://127.0.0.1:${VK_FRONTEND_PORT}"`
5. 浏览器/E2E 验证必须使用 `VK_FRONTEND_BASE_URL`（或 `PLAYWRIGHT_BASE_URL`）与 `VK_BACKEND_BASE_URL`，禁止硬编码 `3000/8000`。

未执行运行态校验时，必须在交付中写明：未触发原因、替代证据、残余风险。
