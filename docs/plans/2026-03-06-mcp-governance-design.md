# MCP 配置治理与健康检查 Design

**目标**：收敛当前 Codex MCP 的权威配置来源，修复 `github-mcp-server` 与 `vibe_kanban` 的启动异常，并形成可重复执行的体检口径。

**架构结论**
- 模块边界：将 MCP 相关能力拆分为“运行时权威配置”“项目参考配置”“健康检查入口”三层；不触碰业务代码。
- 依赖方向：`Codex 运行时配置 -> MCP Server 启动命令/环境 -> 外部依赖（Docker、GitHub Token、本地端口文件/本地二进制、数据库、HTTP 服务）`。
- 状态归属：MCP 的命令、参数、环境变量由运行时权威配置管理；项目内 `.mcp.json` 仅作为项目参考与协作镜像；运行态文件如 `vibe-kanban.port` 归本地服务自身。
- 错误处理责任：健康检查脚本负责在握手前暴露“缺 Token / 缺端口文件 / 启动命令漂移”等根因，不把错误下沉到业务使用阶段。

**根因定位**
1. `github-mcp-server`：当前会话真实生效的是 `/Users/jijingkun/.codex/config.toml`，但该配置只透传 `-e GITHUB_PERSONAL_ACCESS_TOKEN`，未在同一权威配置中稳定注入值，导致容器启动时报缺 Token。
2. `vibe_kanban`：全局配置仍使用 `npx -y vibe-kanban@latest --mcp`，而当前环境实际更接近“本机已安装的 MCP 二进制 + 特定代理环境”；`@latest` 方案依赖本地运行态端口文件，启动前置条件未被建模。
3. 配置双源漂移：`/Users/jijingkun/.codex/config.toml` 与项目内 `.mcp.json` 并存且不一致，导致“项目看到的配置”和“本会话实际使用的配置”不一致。

**候选方案**

## 方案 A：继续维持双配置，只修单点异常
- 做法：分别补 Token 注入、修 `vibe_kanban` 命令。
- 优点：改动小。
- 缺点：双源漂移继续存在，后续继续复发。

## 方案 B：收敛权威源为 `/Users/jijingkun/.codex/config.toml`，`.mcp.json` 退化为参考镜像
- 做法：先以当前 Codex 真实生效的全局配置为准修复启动链路，再把项目内 `.mcp.json` 同步成无敏感信息的参考配置。
- 优点：符合当前会话真实行为，根因修复层级正确；便于后续体检。
- 缺点：会引入一次全局用户级配置变更。

## 方案 C：直接移除 `vibe_kanban`
- 做法：从两套配置中删除 `vibe_kanban`。
- 优点：减法彻底。
- 缺点：与当前 `.cursor/commands/jjk-vktodo.md`、`.agents/skills/jjk-vktodo/SKILL.md`、`.cursor/rules/mcp-routing.mdc` 的现役依赖冲突，属于跨流程语义变更，超出本次体检修复范围。

**推荐方案**
- 采用 **方案 B**。
- 原因：它以当前真实运行时为权威源，能在不改业务链路的前提下解决两个异常 MCP 的根因，同时保留后续退役 `vibe_kanban` 的空间。

**设计细节**
1. GitHub MCP
   - 全局配置改为显式从本机环境读取 Token；项目 `.mcp.json` 去掉明文 PAT，避免继续携带敏感信息。
   - 本次只验证“可成功启动并完成 MCP 握手前置条件”，不扩展 GitHub tool 路由。
2. vibe_kanban MCP
   - 全局配置不再使用 `@latest` 启动，而改用项目内已记录的固定本机二进制及代理环境，保持可重复性。
   - 若该二进制可启动但需要外部服务，体检结果明确标注为“受运行态依赖约束”。
3. 体检入口
   - 增加项目内脚本，输出每个 MCP 的 `OK / FAIL / BLOCKED`、根因和建议动作，避免再次手工排障。
4. 文档同步
   - 先写 design + implementation plan。
   - 再更新工作流/配置文档，明确“权威配置源”“项目参考镜像”“MCP 体检命令”。

**验证策略**
- 配置静态校验：检查权威配置和项目镜像是否一致、是否仍含明文 Token。
- 启动链路校验：对 `github-mcp-server`、`vibe_kanban` 执行最小握手/启动验证。
- 功能校验：复测 `context7`、`minio`、`playwright`、`postgres`、`postgres-data-db` 不回归。

**风险与回退**
- 风险 1：Codex 会话可能缓存 MCP 配置，修改后需要新会话才能完全生效。
- 风险 2：`vibe_kanban` 的本地二进制可能依赖独立后台进程，若运行态不存在，仍只能得到 `BLOCKED` 而非 `OK`。
- 回退路径：保留修改前的全局配置备份；若新配置引发更大范围失效，恢复备份并保留项目镜像与体检脚本。
