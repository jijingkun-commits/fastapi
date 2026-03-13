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
3. **改功能先顺手复盘与减法**：修改某一功能块时，先顺手看一眼该触达范围的模块边界、依赖方向和状态归属是不是更合理；主动识别可一起收口的旧入口、重复逻辑、过期 fallback、空转 helper 和孤儿测试/文档。优先边改边收口，不把这类局部债务默认留给“以后再说”。
4. **职责替换先收口**：`bugfix/refactor` 或新实现替代旧职责时，先说清新的唯一 owner、旧入口如何处理，以及暂留路径的失效条件；不要把新旧双轨留给“以后再删”。
5. **默认先收口，再扩写**：优先复用、外移和删旧；是否净增长不是第一判断，关键看职责是否更集中、旧路径是否真正退役。热点文件与变更集增长统计遵循 Layer2 规则。
6. **文档先行且原位修改**：涉及架构/API/表结构/配置/功能变动时，先更新真理源文档再改代码；同主题默认原位修改，禁止平行追加。
7. **外部事实先核验**：涉及最佳实践、第三方库/API、官方实现或最新信息时，优先核验官方或权威来源，再下结论。
8. **诊断先报结论**：调试/排障场景中，若日志、报错栈、监控或最小复现证据已足以锁定根因，必须先用“结论 + 证据位置 + 是否继续处理”的形式同步用户；未经用户明确同意，不得默认进入优化、修复、重构、补测或文档回填闭环。
9. **语义判定边界固定**：禁止在编排层（如 `app/services/**`、`app/api/**`、router/controller）新增关键词词表、正则词表或 substring 语义判定；语义识别必须收敛到 `intent/policy/resolver` 层并输出结构化 contract。
10. **Lean 交付要有证据**：热点目录/热点文件必须过 `lean-guard`；未给出删除清单、重复收敛、复杂度变化、验证结果，不得宣称 `lean/refactor` 完成。

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
  - 命令与技能写法：`.cursor/rules/command_authoring.mdc`
  - 双数据库约束：`.cursor/rules/dual-database.mdc`
  - 文档同步与映射：`.cursor/rules/doc_sync.mdc`
  - LangGraph 约束：`.cursor/rules/langgraph.mdc`
  - 语言风格：`.cursor/rules/python_style.mdc`、`.cursor/rules/typescript_style.mdc`
  - 测试质量与坏测试治理：`.cursor/rules/test_quality.mdc`

## Layer4 项目记忆（历史决策）
- 项目记忆索引文件：`memory-bank.md`（本仓库根目录，供 AI/协作者快速读取仓库级活跃决策）。
- 人类可读 ADR 正文：`docs/内部参考/决策记录.md`（记录重大技术/架构决策的完整背景、决策与后果）。
- 机器扫描快照（如 `.omc/project-memory.json`）不替代人工决策记录。
- `memory-bank.md` 默认不写；仅当某项变更形成“长期有效、会影响后续实现默认做法、且需要为跨任务/跨会话保留仓库级活跃决策索引”的决策时，才更新。
- 一次性实现、排障过程、测试/验收记录、临时 workaround、模块内部细节默认不进入 `memory-bank.md`；应写回对应真理源文档、`workdocs/`、review/verify 产物或测试报告。
- 命中同主题已有 `ACTIVE` 决策时，优先原位更新现有条目，不新增平行重复记录。
- 重大技术选型或架构取舍若需要解释“为什么这样设计”，正文优先写入 `docs/内部参考/决策记录.md`；`memory-bank.md` 只保留摘要、影响范围与链接。
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
