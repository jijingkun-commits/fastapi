# JJK Governance Skills Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 新增 `jjk-arch-gate` 与 `jjk-api-doc-sync` 两个治理型项目技能，并完成工作流文档与记忆同步。

**Architecture:** 以 `.cursor/commands/jjk-*.md` 作为单一真理源，新增两条治理命令；再通过 `scripts/sync_rules_to_cc.py --only commands` 自动镜像到 `.agents/skills/`。文档层只补入口、链路与使用边界，不重复命令正文。

**Tech Stack:** Markdown、仓库同步脚本 `scripts/sync_rules_to_cc.py`、命令镜像机制、工作流文档。

---

### Task 1: 写入设计与实施文档

**Files:**
- Create: `workdocs/归档/正文/设计/2026-03-08-jjk-governance-skills-design.md`
- Create: `workdocs/归档/正文/设计/2026-03-08-jjk-governance-skills-implementation.md`

**Step 1: 固化设计结论**

把已获用户批准的设计写入 design 文档，记录四段式架构结论、方案对比、风险与审批证据。

**Step 2: 固化实施计划**

把本轮改动拆成“命令真理源、文档入口、镜像同步、最小验证”四类任务，避免边做边漂移。

**Step 3: 验证文档可追溯**

检查 design / implementation 文件名、日期与主题一致，便于后续记忆与检索。

### Task 2: 同步工作流与速查文档

**Files:**
- Modify: `docs/开发文档/流程与工具/开发工作流.md`
- Modify: `docs/开发文档/流程与工具/指令用法_实现方式_工程流全景手册.md`
- Modify: `docs/开发文档/流程与工具/AI协作速查表.md`
- Modify: `docs/开发文档/流程与工具/vibe-coding开发技巧.md`
- Modify: `memory-bank.md`

**Step 1: 补命令入口**

在工作流总览、命令选型、快捷命令中补入 `jjk-arch-gate` 与 `jjk-api-doc-sync`。

**Step 2: 明确边界**

把两个命令定位为“治理前置门禁”，不替代 `jjk-plan/jjk-imp/jjk-review/jjk-verify`。

**Step 3: 写长期决策**

在 `memory-bank.md` 中记录“治理前置命令显式化”的长期决策与失效条件。

### Task 3: 新增命令真理源

**Files:**
- Create: `.cursor/commands/jjk-arch-gate.md`
- Create: `.cursor/commands/jjk-api-doc-sync.md`

**Step 1: 定义 `jjk-arch-gate`**

写清输入前置、四段式结论、阻断码、默认 `refactor` 判定与输出契约。

**Step 2: 定义 `jjk-api-doc-sync`**

写清 API/Schema/Route 文档映射、Must Update / Should Review / Not In Scope 三栏、阻断码与链路位置。

**Step 3: 保持风格一致**

对齐现有 `jjk-*` 命令的结构：说明、输入前置、执行流程、禁止项、推荐链路、示例。

### Task 4: 生成 Skill 镜像

**Files:**
- Create: `.agents/skills/jjk-arch-gate/SKILL.md`
- Create: `.agents/skills/jjk-api-doc-sync/SKILL.md`

**Step 1: 执行同步脚本**

运行 `scripts/sync_rules_to_cc.py --only commands`，让命令镜像自动生成 Skill。

**Step 2: 检查镜像结果**

确认新 Skill 带有 `AUTO-GENERATED: jjk-skill-mirror` 标记，且 source 指回对应 `.cursor/commands` 文件。

### Task 5: 做最小可用性验证

**Files:**
- Verify only: `.cursor/commands/jjk-arch-gate.md`
- Verify only: `.cursor/commands/jjk-api-doc-sync.md`
- Verify only: `.agents/skills/jjk-arch-gate/SKILL.md`
- Verify only: `.agents/skills/jjk-api-doc-sync/SKILL.md`

**Step 1: 校验关键引用**

用 `rg` 确认工作流文档、速查表与技巧文档都能检索到新命令名。

**Step 2: 校验镜像链路**

确认 `.agents/skills` 中存在两个新 Skill，且内容由命令文件自动镜像而来。

**Step 3: 校验文本质量**

运行 `git diff --check` 作为最小静态检查，确保无明显空白或冲突标记。

**Validation Note:** 这次改动是命令/文档/Skill 镜像层面的治理能力补齐，没有合适的运行时单元测试入口；因此采用“同步脚本 + 检索断言 + diff 静态检查”作为最小可复核验证。
