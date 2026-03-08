# 项目代理工作指南（Codex 版）

本文件是`/Users/jijingkun/bojxAI/fastapi` 下的主规则。
作用域覆盖当前目录及所有子目录；若子目录存在更深层 `AGENTS.md`，以更深层文件为准。

## 层级与优先级（强制）
1. 系统/开发者硬约束 > 当次用户目标 > Layer1（本文件）> Layer2（`.cursor/rules/*.mdc`）> Layer3（Skills / tools）> Layer4（`memory-bank.md`）> 代理默认习惯。
2. 同层规则冲突时，优先“更具体路径、更强约束、更可验证”的规则。
3. 出现规则冲突时，先说明冲突点、取舍理由与风险，再执行。
4. Layer1 只保留治理口径与交付门禁；技术细则与场景化规范统一落在 Layer2，避免重复维护。

## Layer1 执行治理（强制）
1. **工作模式默认 `lean`（激进瘦身模式）**：核心是**主动消灭浪费**——优先删除冗余代码、收敛重复逻辑、缩短调用链、消除不必要抽象；**本项目未上线，架构设计质量绝对优先于兼容性与改动量**，根因在结构/依赖/状态归属层面必须 `refactor`，禁止用 `patch` 或兼容层掩盖。
2. **架构评审门禁**：任何改动前必须提交“模块边界、依赖方向、状态归属、错误处理责任”四段式结论；原则解释统一引用 `.cursor/rules/core.mdc` 第 6 条。
3. 3. **根因修复门禁**：禁止以多层 fallback、重复分支、硬编码开关或兼容层掩盖问题；未上线阶段涉及模块边界、依赖方向、状态归属、错误处理责任时优先 `refactor`；修复说明必须包含根因定位与修复层级，技术细则统一引用 `.cursor/rules/core.mdc` 第 7 条。
4. **变更量约束**：在 `bugfix/refactor` 中若 `新增行数 > 删除行数`，必须说明架构必要性；新功能可豁免但必须说明原因。
5. **文档变更门禁**：涉及架构/API/表结构/配置变更/功能变动时，先更新文档再改代码；同步细则统一引用 `.cursor/rules/doc_sync.mdc` 与 `.cursor/rules/core.mdc` 第 8 条。
6. **证据化交付**：未给出瘦身证据（删除清单、重复收敛、复杂度变化、验证结果）不得宣称 `lean/refactor` 完成。
7. **去重约束**：Layer1 只保留治理口径与交付门禁，不复述 Layer2 技术细则；同主题仅保留“门禁 + 引用”。

## `patch` 模式附加门槛（强制）
- 必须包含：影响范围、临时性说明、回退路径、后续治理任务。

## 执行上下文校验（强制）
### A. 基础观测（每次执行前）
修改代码或运行测试前必须先输出：
1. `pwd`
2. `git branch --show-current`
3. `git worktree list`

### B. 期望上下文比对（`jjk-verify` / 测试前强制）
仅做基础观测不足以保证“测对分支/测对 worktree”，必须做“期望值比对”：
1. 从输入证据中提取期望上下文（至少其一）：`task_id/pr_id`、目标分支、目标 worktree 路径、目标提交 SHA。
2. 采集实际上下文：`pwd`、`git rev-parse --show-toplevel`、`git branch --show-current`、`git rev-parse HEAD`。
3. 比对“期望 vs 实际”；任一关键项不一致，`FAIL_FAST` 输出 `VERIFY_CONTEXT_MISMATCH` 并停止测试执行。
4. `jjk-verify` 报告必须包含：目标上下文、实际上下文、比对结论、阻断/放行原因。
5. 若输入证据无法提供可比对的期望上下文，`FAIL_FAST` 输出 `VERIFY_INPUT_INCOMPLETE`，禁止进入测试阶段。

## 文件编辑工具契约（强制）
1. 文件编辑必须以当前会话**实际暴露**的工具集为准；若没有独立 `apply_patch` 入口，禁止通过 `exec_command` 包装 `apply_patch`。
2. 命中该场景时，必须显式记录 `APPLY_PATCH_TOOL_UNAVAILABLE_FALLBACK`，并改用当前可用的直接写回方式（如 Python/Perl/安全 shell 重写），禁止因工具冲突反复空转。
3. 若后续环境真实暴露独立 `apply_patch` 工具，应优先使用真实工具；仓内规则不为不存在的工具制造兼容壳。

## 测试解释器契约（强制）
1. 任何测试/验证命令在执行前，必须先通过 `bash scripts/repo_python.sh` 解析仓库测试解释器，禁止默认裸用 `python3 -m pytest`。
2. 解析优先级固定为：`VK_RUNTIME_VENV` -> `venv` -> `.venv` -> `.vibe/venv` -> 系统 `python3/python`；只有仓内解释器不存在时，才允许回落到系统解释器。
3. `jjk-verify` / 测试证据中必须回显本次命中的解释器路径，避免再次出现“测错环境”。

## 测试语义分层（强制）
1. TDD/调试阶段的定向回归，统一使用 `bash scripts/pytest_targeted.sh <tests...>`，默认附带 `--no-cov`，只验证当前根因是否命中。
2. 最终收口/门禁验证继续使用常规 pytest/coverage 命令；coverage 只属于最终收口语义，不得混入开发期红绿循环。
3. 两类命令禁止混用；若定向入口收到 `--cov` 类参数，应立即 `FAIL_FAST`，避免再次把 coverage 噪音带回 RED 阶段。

## 运行态校验（按需强制）
以下场景必须补充运行态校验，不得只做静态命令验证：
1. 端口/服务启动相关问题；
2. API 联调、E2E/UAT、回归关键链路；
3. 用户明确要求“确认服务是否启动/端口是否可用”。

推荐最小校验集（按需选择）：
1. 先基于当前分支/工作树计算端口：`eval "$(bash scripts/vk_ports.sh --export)"`
2. 端口监听：`lsof -nP -iTCP:${VK_BACKEND_PORT} -sTCP:LISTEN`、`lsof -nP -iTCP:${VK_FRONTEND_PORT} -sTCP:LISTEN`
3. 后端健康：`curl -sf "http://127.0.0.1:${VK_BACKEND_PORT}/health"`
4. 前端可达：`curl -I "http://127.0.0.1:${VK_FRONTEND_PORT}"`
5. 浏览器/E2E 验证必须使用 `VK_FRONTEND_BASE_URL`（或 `PLAYWRIGHT_BASE_URL`）与 `VK_BACKEND_BASE_URL`，禁止硬编码 `3000/8000`。

未执行运行态校验时，必须在交付中写明：未触发原因、替代证据、残余风险。

## Layer2 规则入口（唯一源）
- 规则唯一源：`.cursor/rules/*.mdc`
- 命令唯一源：`.cursor/commands/*.md`
- 详细技术约束以 Layer2 为准（不在本文件重复）：
  - 核心原则与技术栈：`.cursor/rules/core.mdc`
  - MCP 路由与联网/GitHub 检索：`.cursor/rules/mcp-routing.mdc`
  - 双数据库约束：`.cursor/rules/dual-database.mdc`
  - 文档同步与映射：`.cursor/rules/doc_sync.mdc`
  - LangGraph 约束：`.cursor/rules/langgraph.mdc`
  - 语言风格：`.cursor/rules/python_style.mdc`、`.cursor/rules/typescript_style.mdc`

## Layer3 技能入口（功能级）
- Skills / tools 用于功能级执行策略。
- 命中技能触发条件时必须使用；缺失或不可用时说明原因并降级，不得阻塞任务。

## Layer4 项目记忆（历史决策）
- 决策记录文件：`memory-bank.md`（本仓库根目录）。
- 机器扫描快照（如 `.omc/project-memory.json`）不替代人工决策记录。
- 任何会影响后续实现的长期决策，都应更新 `memory-bank.md`。
- 仅记录“长期有效决策”，不记录一次性执行日志。
- 单条记录建议控制在 8~12 行，必须包含：日期、主题、最终决策、取舍理由、影响范围、失效条件、关联链接。
- 记录状态必须显式标注：`ACTIVE` / `SUPERSEDED` / `DEPRECATED`。
- 文件顶部维护“生效决策索引”（建议最多 20 条）；超出部分按月归档到 `docs/内部参考/决策归档/`。

## 规则维护与同步
- 指南唯一源：`AGENTS.md`（`CLAUDE.md` 由同步脚本镜像生成，禁止手改）。
- 生成产物（禁止手改）：`.claude/rules/*.md`、`.claude/commands/*.md`。
- 同步命令：`python3 scripts/sync_rules_to_cc.py`。

## 脚本目录约定
- 个人工作流脚本实体在 `.cursor/scripts/`，`scripts/` 下为 symlink。
- 项目脚本直接放 `scripts/` 及其子目录（`db/`、`data/`）。
