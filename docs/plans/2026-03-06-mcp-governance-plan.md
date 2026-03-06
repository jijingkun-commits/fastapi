# MCP 配置治理与健康检查 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 收敛 MCP 权威配置，修复当前两个异常 MCP，并交付可重复执行的体检入口。

**Architecture:** 以 `/Users/jijingkun/.codex/config.toml` 作为当前会话权威配置源，项目内 `.mcp.json` 作为协作镜像；先更新文档，再做最小配置修复，最后用最小调用链复测每个启用的 MCP。

**Tech Stack:** Codex MCP、TOML、JSON、shell、Docker、Node.js `npx`

---

### Task 1: 写设计与计划文档

**Files:**
- Create: `docs/plans/2026-03-06-mcp-governance-design.md`
- Create: `docs/plans/2026-03-06-mcp-governance-plan.md`

**Step 1: 写设计文档**
- 记录模块边界、依赖方向、状态归属、错误处理责任。

**Step 2: 写实施计划**
- 明确要修改的配置文件、文档文件、验证命令与回退方式。

**Step 3: 自检文档完整性**
Run: `rg -n '权威配置|Token|vibe_kanban|体检' docs/plans/2026-03-06-mcp-governance-*.md`
Expected: 命中设计与计划关键字。

### Task 2: 更新文档口径

**Files:**
- Modify: `docs/开发文档/工作流/开发工作流.md`
- Modify: `memory-bank.md`

**Step 1: 更新工作流文档**
- 新增 MCP 配置治理章节，说明权威配置源、项目镜像、敏感信息约束与体检命令。

**Step 2: 更新项目记忆**
- 记录“MCP 权威配置收敛”长期决策、影响范围、失效条件。

**Step 3: 自检文档同步**
Run: `rg -n 'MCP 配置治理|权威配置|体检' docs/开发文档/工作流/开发工作流.md memory-bank.md`
Expected: 新增条目可检索。

### Task 3: 修复权威配置与项目镜像

**Files:**
- Modify: `/Users/jijingkun/.codex/config.toml`
- Modify: `.mcp.json`

**Step 1: 备份全局配置**
Run: `cp /Users/jijingkun/.codex/config.toml /Users/jijingkun/.codex/config.toml.bak-20260306-mcp`
Expected: 生成备份文件。

**Step 2: 修 GitHub MCP 配置**
- 在全局配置中为 `github-mcp-server` 显式注入环境变量占位；移除项目镜像中的明文 PAT。

**Step 3: 修 vibe_kanban MCP 配置**
- 将全局配置改为固定本地二进制与代理环境，和项目镜像保持一致。

**Step 4: 做静态一致性校验**
Run: `rg -n 'github-mcp-server|vibe_kanban|GITHUB_PERSONAL_ACCESS_TOKEN' /Users/jijingkun/.codex/config.toml .mcp.json`
Expected: 全局与项目镜像命令一致，项目镜像不再含明文 Token。

### Task 4: 新增体检脚本

**Files:**
- Create: `scripts/check_mcp_health.sh`

**Step 1: 写脚本**
- 输出基础上下文、配置源、启用 MCP 名单、每个 MCP 的健康状态。

**Step 2: 覆盖关键检查**
- 检查 GitHub Token 是否存在、`vibe_kanban` 二进制是否存在、数据库命令是否可用。

**Step 3: 运行脚本**
Run: `bash scripts/check_mcp_health.sh`
Expected: 输出结构化表格/摘要，区分 `OK / FAIL / BLOCKED`。

### Task 5: 复测 MCP

**Files:**
- Modify: 无（验证）

**Step 1: 复测资源型 MCP**
Run: 使用 MCP 工具复测 `postgres`、`postgres-data-db`、`playwright`、`minio`、`context7`
Expected: 均成功。

**Step 2: 复测异常项启动链路**
Run: 通过最小启动命令复测 `github-mcp-server`、`vibe_kanban`
Expected: `github-mcp-server` 不再报缺 Token；`vibe_kanban` 至少到达稳定可诊断状态。

**Step 3: 汇总结论**
- 给出删除清单、重复收敛、复杂度变化、验证结果。
