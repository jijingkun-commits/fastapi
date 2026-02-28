---
description: 组合验证：审查 + 测试 + UAT 一站式验收
---

> 参考规则: @dual-database

# 组合验证工作流 (Verify Workflow)

将代码审查、自动测试和 UAT 验收合为一体，一次完成验证闭环。
默认采用“自动判定优先”，仅在自动证据不足时进入交互式确认。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 实现完成，一次性完成全部验证 | `/jjk-verify` ✅ |
| 只需代码审查（不跑测试） | `/jjk-review` |
| 只需完整测试流程（含报告产出） | `/jjk-test` |
| 修复 Bug 后快速验证 | `/jjk-debug`（包含回归测试） |

> **等效于**: `/jjk-review`（精简版）+ `/jjk-test`（精简版）+ 自动 UAT（默认）+ 交互 UAT（可选）

## 执行硬约束（防止无报告返回）

1. 无论成功、失败或中断，本轮最后都必须输出 `## 验证报告`，禁止只停留在提问或中间状态。
2. 若进入交互 UAT，必须先输出“自动证据版报告（AUTO/MIXED）”，再发起 1~3 条最小确认。
3. 任一关键命令失败时，报告中必须记录：`命令原文 + 退出码 + 错误摘要 + 后续处理`。
4. 变更范围获取失败时，必须自动降级为“工作区 + 最近提交”分析，不得因为分支名错误直接终止。
5. 报告必须可复现：至少包含命令、退出码、通过/失败统计、关键断言与新增/历史问题区分。

---

## 阶段 1: 变更分析 (Change Analysis)

1. **获取变更范围**:
```bash
# 1) 优先使用 main/master 与 HEAD 做三点对比
BASE_REF=""
if git show-ref --verify --quiet refs/heads/main || git show-ref --verify --quiet refs/remotes/origin/main; then
  BASE_REF="main"
elif git show-ref --verify --quiet refs/heads/master || git show-ref --verify --quiet refs/remotes/origin/master; then
  BASE_REF="master"
fi

if [ -n "$BASE_REF" ]; then
  # 已提交差异
  git diff "${BASE_REF}...HEAD" --stat
  # 工作区差异（兼容尚未提交的 /jjk-imp 结果）
  git diff --stat
  git diff --cached --stat
else
  # 2) 仓库无 main/master 时自动降级，避免命令直接失败
  echo "⚠️ 未找到 main/master，降级为工作区 + 最近提交变更"
  git diff --stat
  git diff --cached --stat
  git show --stat --oneline -n 1
fi
```

2. **识别影响面**:
   - 变更涉及哪些模块（AI/API/前端/数据库）
   - 是否涉及高风险文件（`agent_prompts.py`、`state.py`、`*_graph.py`）
   - 是否有 API/数据库/配置变更

3. **确定验证策略**:

| 变更类型 | 审查深度 | 测试范围 | UAT 必要性 |
|---------|---------|---------|-----------|
| 纯后端逻辑 | 标准 | 单元测试 | 可选 |
| API 变更 | 深度 | 单元 + API 测试 | 推荐 |
| 前端变更 | 标准 | E2E 测试 | 必须 |
| AI 工作流变更 | 深度 | 单元 + 集成 | 必须 |
| 数据库变更 | 深度 | 迁移验证 | 推荐 |

## 阶段 2: 快速审查 (Quick Review)

> 精简版 `/jjk-review`，聚焦关键问题。

**Checklist**:
- [ ] 功能是否符合需求/计划？
- [ ] 有无明显逻辑错误或遗漏？
- [ ] 安全问题（SQL 注入、XSS、硬编码密钥）？
- [ ] 代码风格是否符合项目规范（中文注释、类型提示）？
- [ ] 文档是否需要同步更新？

发现问题时：
- 简单问题：直接修复，继续验证
- 严重问题：停止验证，报告问题，建议回到实现阶段

## 阶段 3: 自动测试 (Auto Test)

> 精简版 `/jjk-test`，只跑必要的测试。

### 3.1 环境检查

```bash
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
cd "$ROOT_DIR"

if [ -f scripts/vk_ports.sh ]; then
  eval "$(bash scripts/vk_ports.sh --export)"
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  BACKEND_PORT=8000; FRONTEND_PORT=3000
else
  BACKEND_PORT="${VK_BACKEND_PORT:-${TEST_BACKEND_PORT:-8000}}"
  FRONTEND_PORT="${VK_FRONTEND_PORT:-${TEST_FRONTEND_PORT:-3000}}"
fi
export TEST_BACKEND_PORT="$BACKEND_PORT"
export TEST_FRONTEND_PORT="$FRONTEND_PORT"
```

### 3.2 按变更范围选择测试

```bash
# 后端变更：跑相关单元测试
venv/bin/python -m pytest tests/unit/ -v --tb=short -q

# 前端变更：跑 E2E（需要服务启动）
cd web && npx playwright test <相关spec>

# API 变更：跑 API 测试
venv/bin/python -m pytest tests/api/ -v --tb=short -q
```

规则：
1. 只跑与变更相关的测试，不跑全量
2. 测试失败时记录到验证报告，不中断流程
3. 后端未启动时先尝试自动拉起一次

### 3.3 文档同步检查

- [ ] API 变更 -> `docs/API文档/接口文档.md` 已更新？
- [ ] 数据库变更 -> `docs/开发文档/架构设计/数据库设计.md` 已更新？
- [ ] 配置变更 -> `docs/开发文档/快速入门/配置说明.md` 已更新？

## 阶段 4: UAT 验收（默认自动判定，可选交互）

> 默认不要求用户逐项手工点 PASS/FAIL。优先用“可执行命令 + 断言”自动判定。

### 4.0 模式选择规则

1. **默认：自动判定（Auto UAT）**
   - 若存在可执行测试或可脚本化接口校验，则直接运行并判定。
   - 以“测试断言 + 命令退出码 + 关键回包字段”为准，不要求用户看日志。
2. **降级：交互确认（Interactive UAT）**
   - 仅在自动证据不足时启用（例如纯视觉体验、文案体验、主观可用性）。
   - 交互项应最小化为 1~3 条，不做冗长逐项盘问。
3. **直接出报告（强制优先）**
   - 自动证据充分时，直接输出最终验证报告，不得再要求用户逐项手动确认。

### 4.1 自动判定（Auto UAT）执行模板

按变更类型执行对应校验：

```bash
# 1) 能力级回归（优先使用已存在测试）
venv/bin/python -m pytest -q <相关 tests>

# 2) API 契约（字段级断言）
venv/bin/python -m pytest -q tests/api/ -k "<关键词>"

# 3) 数据库与迁移状态（结构级断言）
venv/bin/alembic current

# 4) 文档门禁（如本次涉及文档）
venv/bin/python scripts/docs_guard.py --strict
```

自动判定输出必须包含：
- 命令、退出码、通过/失败用例数
- 关键断言点（文件路径 + 行号）
- 新增问题与历史问题区分（例如 docs 历史断链）

### 4.2 交互确认（仅在必要时）

当且仅当自动证据不足时，向用户发起最小确认：
- 每项给出“你需要观察的对象”和“通过标准”（例如某个 API 回包字段）
- 用户只需回复 `PASS` / `FAIL`，无需手工读大量日志
- 若 `FAIL`，进入自动诊断并给出修复建议

## 阶段 5: 验证报告 (Verification Report)

输出精简的验证报告（不写入文件，直接展示）：

### 5.0 报告模式选择

1. **默认标准报告**：使用完整结构（适合 PR/评审留痕）。
2. **极简报告模式**：当用户明确提到“极简报告 / 简版报告 / 只要结论 / 8-12 行”时启用。
3. 不论哪种模式，都必须包含：`总结 + 测试统计 + UAT结论 + 自动证据 + 文档同步 + 下一步建议`。

极简报告模板（8-12 行）：

```markdown
## 验证报告（极简）
- 总结: PASS / WARN / FAIL
- 审查: 发现 N（已修复 M），遗留: [...]
- 测试: 通过 X / Y，失败: [...]
- UAT: 模式=AUTO/INTERACTIVE/MIXED，通过 A / B，待修复: [...]
- 证据: [命令] <cmd> exit=<code> pass=<p> fail=<f>
- 断言: <文件路径:行号> -> <断言内容>
- 问题归类: 新增=[...]，历史=[...]
- 文档同步: [x]/[ ]
- 阻断与降级: 无 / <说明>
- 建议: <下一步动作>
```

标准报告模板：

```markdown
## 验证报告

### 总结: PASS / FAIL / WARN

### 审查结果
- 发现问题: N 个（已修复 M 个）
- 遗留问题: [列表]

### 测试结果
- 通过: X / Y
- 失败: [失败用例列表]

### UAT 结果
- 模式: AUTO / INTERACTIVE / MIXED
- 通过: A / B
- 待修复: [问题列表]

### 自动判定证据
- [命令] <原文> | exit=<code> | 通过=<pass> | 失败=<fail>
- [断言] <文件路径:行号> -> <断言内容>
- [问题归类] 新增问题: [...] / 历史问题: [...]

### 阻断与降级记录
- [记录] <若无则写“无”>

### 文档同步
- [x] 已同步 / [ ] 需要补充: [具体文档]

### 建议
- [下一步行动建议]
```

最低要求：
1. 就算执行中出现错误，也必须输出报告（标准或极简其一，可将总结标记为 `FAIL` 或 `WARN`）。
2. 禁止只输出“继续中/待确认”而不附报告。
3. 若用户要求“简短”，优先使用极简模板；若用户要求“详细”，优先使用标准模板。

### 判定规则

| 条件 | 判定 |
|------|------|
| 审查无严重问题 + 测试全通过 + UAT 全通过 | PASS |
| 有非阻塞问题但核心功能正常 | WARN |
| 有阻塞问题或核心测试失败 | FAIL |

PASS/WARN -> 建议提交或创建 PR
FAIL -> 建议回到实现阶段修复

---
*使用 `/jjk-verify` 触发。适合在 `/jjk-imp` 之后一次性完成全部验证。*
