<!-- AUTO-GENERATED FROM AGENTS.md via scripts/sync_rules_to_cc.py. DO NOT EDIT. -->

# 项目代理工作指南（Claude 镜像）

本文件是`/Users/jijingkun/bojxAI/fastapi` 下的主规则。
作用域覆盖当前目录及所有子目录；若子目录存在更深层 `AGENTS.md`，以更深层文件为准。

## 层级与优先级（强制）
1. 系统/开发者硬约束 > 当次用户目标 > Layer1（本文件）> Layer2（`.cursor/rules/*.mdc`）> `PLANS.md` > Layer4（`memory-bank.md`）> 代理默认习惯。
2. 同层规则冲突时，优先“更具体路径、更强约束、更可验证”的规则。
3. 出现规则冲突时，先说明冲突点、取舍理由与风险，再执行。
4. Layer1 只保留治理口径与交付门禁；技术细则统一落在 Layer2，执行长流程统一落在 `PLANS.md`，避免根文件继续长胖。

## Layer1 执行治理（强制）
1. **未上线项目优先架构正确**：设计合理和简洁优先于兼容性与改动量；结构问题默认 `refactor`，禁止用 `patch`、fallback、兼容层、重复分支或硬编码开关掩盖。
2. **架构门禁先行**：任何改动前必须先给出“模块边界、依赖方向、状态归属、错误处理责任”四段式结论；说不清则禁止开工。
3. **瘦身合同先行**：`bugfix/refactor` 或新实现替代旧职责时，必须先声明 `obsolete_paths`、`retained_paths`、`single_entry_owner`、`line_budget`；说不清则禁止开工。
4. **默认做减法**：默认 `line_budget=added<=deleted`；若净增长，必须先说明架构必要性与不可拆分原因。
5. **文档先行且原位修改**：涉及架构/API/表结构/配置/功能变动时，先更新真理源文档再改代码；同主题默认原位修改，禁止平行追加。
6. **外部事实先核验**：涉及最佳实践、第三方库/API、官方实现或最新信息时，优先核验官方或权威来源，再下结论。
7. **语义判定边界固定**：禁止在编排层（如 `app/services/**`、`app/api/**`、router/controller）新增关键词词表、正则词表或 substring 语义判定；语义识别必须收敛到 `intent/policy/resolver` 层并输出结构化 contract。
8. **Lean 交付要有证据**：热点目录/热点文件必须过 `lean-guard`；未给出删除清单、重复收敛、复杂度变化、验证结果，不得宣称 `lean/refactor` 完成。

## 执行流程入口（强制）
1. 改代码、跑测试、做验收前，先读 `PLANS.md` 对应章节。
2. `PLANS.md` 是以下流程的唯一入口：`patch` 门槛、执行上下文校验、文件编辑工具契约、测试解释器契约、测试语义分层、运行态校验。
3. 命中 API / Schema / Route / DTO / 接口语义变更时，除本文件外还必须遵守 `.cursor/rules/doc_sync.mdc` 与对应的 `jjk-api-doc-sync` 门禁。

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
  - 测试质量与坏测试治理：`.cursor/rules/test_quality.mdc`

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
