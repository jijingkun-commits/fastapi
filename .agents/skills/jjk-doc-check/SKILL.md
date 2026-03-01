---
name: jjk-doc-check
description: "Use when you need `jjk-doc-check` in this repository. Source intent: 文档同步检查入口（消费 diff/manifest）：映射规则核验与遗漏分级，支持大范围自动 Team"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-doc-check.md -->

> 参考规则: @dual-database

# 文档同步检查 (Doc Sync Check)

`$jjk-doc-check` 是 `jjk-*` 体系里的文档一致性入口，负责核验“代码变更 -> 文档更新”是否完成闭环。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `$jjk-review`：提供已识别的改动边界与风险项。
2. `verification-before-completion`：提供证据优先原则，避免主观“已同步”判断。
3. `team`（OMX）：大规模变更并行映射与报告汇总。
4. `$jjk-doc-check`：负责输入映射校验、文档规则匹配、遗漏分级与同步建议输出。

约束：

1. 禁止在 `$jjk-doc-check` 复制上游 skill 正文；只保留调用契约与本地增强。
2. 禁止在检查阶段顺手改业务代码；修复应回退 `$jjk-imp(-ws)` 或 `$jjk-quick`。
3. `$jjk-team-doc-check` 不再作为主入口，统一由 `$jjk-doc-check` 按规模自动升级 Team。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`$jjk-doc-check`
2. Codex：`$jjk-doc-check`

> 说明：Codex 推荐显式调用 `$jjk-doc-check`。

## 模板来源优先级（跨项目，强制）

`$jjk-doc-check` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_doc_check_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_doc_check_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。
`GLOBAL_TEMPLATE_MISSING` 属于全局预检失败标记，可与命令级 `FAIL_FAST` 标记并存。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 提交前检查文档是否同步 | `$jjk-doc-check` ✅ |
| 代码审查时补充文档一致性证据 | `$jjk-review` |
| 快速改动后做最小闭环检查 | `$jjk-quick` |

---

## 输入前置（强制）

至少提供以下输入之一：

1. 当前分支相对 `main/master` 的 diff；
2. `pr_ready_manifest` / `pr_ready_manifest_ws`；
3. `review_report_<topic>.md`（含改动范围）。

硬约束：

1. 若无法确定对比基线（`main/master`），`FAIL_FAST` 输出 `DOC_CHECK_BASELINE_MISSING`。
2. 若无可追溯输入（`task_id/pr_id` 或清晰 diff），`FAIL_FAST` 输出 `DOC_CHECK_INPUT_INCOMPLETE`。
3. 若文档映射规则不可读（如 `.cursor/rules/doc_sync.mdc` 缺失），`FAIL_FAST` 输出 `DOC_CHECK_MAPPING_RULE_MISSING`。
4. 检查结束无报告产物，`FAIL_FAST` 输出 `DOC_CHECK_REPORT_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. 变更文件范围与模块分类（后端/API/前端/AI/配置/脚本）。
2. 变更类型（功能、修复、重构、配置、测试、文档）。
3. 特殊处理痕迹（兜底逻辑/兼容分支/临时绕过）是否存在。

### 0.5) 大范围检查自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 变更文件 `>= 40`；
2. 涉及模块 `>= 5`；
3. 同时覆盖后端+前端+AI+配置四类；
4. 存在多个并行 worktree 或多卡片合并前检查。

执行策略：

1. **有 Team 能力时**：按模块并行映射文档，Leader 汇总统一报告。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束（新增，轻量）

1. Team 模式下必须启用抽检互审：至少抽检 `20%` 工作项（向上取整，最少 `1` 项）。
2. 每个抽检项必须包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
3. 抽检未通过的工作项不得推进到下一阶段，必须先复核并补齐证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。

### 1) 获取变更文件列表

```bash
# 优先使用基线差异
git diff --name-only main...HEAD
```

规则：

1. 必须在报告中记录使用的 diff 命令与基线分支。
2. 变更为空时输出 `DOC_CHECK_NO_CHANGES` 并结束。

### 2) 分类变更文件

至少按以下类别分组：

| 文件路径匹配 | 类别 |
|-------------|------|
| `app/ai/workflow/` `app/ai/tools/` | AI 模块 |
| `app/api/` | API 接口 |
| `app/models/` | 数据库模型 |
| `web/src/components/` | 前端组件 |
| `.env*` | 环境配置 |
| 命中兜底逻辑/兼容补丁/临时绕过的代码变更 | 特殊处理（防屎山） |
| `docs/` | 文档 |

### 3) 检查文档映射

根据 `.cursor/rules/doc_sync.mdc` 映射规则，检查：

| 代码变更 | 应更新文档 |
|---------|-----------|
| `app/ai/workflow/` | `docs/开发文档/架构设计/AI模块设计.md` |
| `app/ai/tools/` | `docs/开发文档/架构设计/AI模块设计.md` |
| `app/api/` | `docs/API文档/接口文档.md` |
| `app/models/` | `docs/开发文档/架构设计/数据库设计.md` |
| `web/src/components/` | `docs/开发文档/架构设计/前端架构.md` |
| 环境变量 | `docs/开发文档/快速入门/配置说明.md` |
| 特殊处理（兜底逻辑/兼容补丁/临时绕过） | `docs/开发文档/架构设计/防屎山记录手册.md` |

特殊处理变更还需检查：

| 场景 | 应更新文档 |
|------|-----------|
| 新增特殊处理 | `docs/开发文档/架构设计/防屎山记录手册.md` 新增 SP 条目 |
| 修改已登记特殊处理 | 更新对应 SP 的状态、最后更新、涉及文件 |

当变更命中具体业务模块时，额外检查以下需求文档与测试文档：

| 模块 | 需求文档 | 测试文档 |
|------|---------|---------|
| 待办助手 | `docs/产品文档/待办助手需求.md` | `docs/开发文档/测试管理/待办助手测试案例.md` |
| 聊天系统 | `docs/产品文档/聊天系统需求.md` | `docs/开发文档/测试管理/聊天系统测试案例.md` |
| 管理后台 | `docs/产品文档/管理后台需求.md` | `docs/开发文档/测试管理/管理后台测试案例.md` |
| 问数助手 | `docs/产品文档/问数助手需求.md` | `docs/开发文档/测试管理/问数引擎测试案例.md` |

### 4) 输出同步报告与等级结论

必须输出：

1. 已同步文档清单；
2. 疑似遗漏清单（含理由与证据）；
3. 可豁免项（含依据）；
4. 结论等级（`PASS/WARN/FAIL`）。

结论建议：

1. `PASS`：关键映射均已同步，无阻断遗漏。
2. `WARN`：存在非阻断遗漏，需补充文档。
3. `FAIL`：存在阻断级遗漏（如 API/模型变更无同步文档）。

---

## 输出模板（推荐）

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_doc_check_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_doc_check_templates.md`。

## 禁止项（强制）

1. 禁止无基线 diff 就直接给“已同步”结论。
2. 禁止忽略特殊处理（防屎山）文档同步。
3. 禁止用“纯小改动”掩盖关键文档遗漏。
4. 禁止无报告结束流程。

## 推荐链路

`$jjk-imp(-ws)` 或 `$jjk-quick` -> `$jjk-doc-check` -> `$jjk-review`

## 使用示例

```text
$jjk-doc-check
```

```text
$jjk-doc-check @docs/内部参考/迭代需求/review_report_<topic>.md
```

---
*使用 `$jjk-doc-check` 触发。目标是“代码与文档同源一致”，不是形式化勾选。*
