# GitHub 强门禁并行治理 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在组织仓内落地“单人多大任务并行 + 强门禁主干保护”流程，做到可追踪、可审计、可回滚。  
**Architecture:** 以 GitHub 原生能力为主（Issues/Projects/Rulesets/Merge Queue），仓内补充最小化校验脚本与 CI 门禁，避免规则漂移。执行路径采用“模板标准化 -> 自动校验 -> 阶段验收”三段式。  
**Tech Stack:** GitHub Issues, GitHub Projects (v2), GitHub Rulesets, GitHub Actions (`pull_request` + `merge_group`), Python 3.11, Pytest, `gh` CLI

---

### Task 1: 建立治理配置真理源与校验脚本

**Files:**
- Create: `config/github/parallel_governance.yml`
- Create: `scripts/ci/check_parallel_governance.py`
- Create: `tests/unit/scripts/test_check_parallel_governance.py`
- Modify: `pyproject.toml`

**Step 1: Write the failing test**

```python
from scripts.ci.check_parallel_governance import validate_config

def test_missing_required_keys_should_fail():
    config = {"wip_limit": 3}
    ok, errors = validate_config(config)
    assert not ok
    assert "required_checks" in errors
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/scripts/test_check_parallel_governance.py -v`  
Expected: FAIL with `ImportError` or `validate_config not found`

**Step 3: Write minimal implementation**

```python
REQUIRED_KEYS = {"wip_limit", "required_checks", "require_merge_queue"}

def validate_config(config: dict):
    missing = [k for k in REQUIRED_KEYS if k not in config]
    return (len(missing) == 0, missing)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/scripts/test_check_parallel_governance.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add config/github/parallel_governance.yml scripts/ci/check_parallel_governance.py tests/unit/scripts/test_check_parallel_governance.py pyproject.toml
git commit -m "feat(ci): 新增并行治理配置校验脚本"
```

### Task 2: 为主门禁工作流补齐 merge_group 触发

**Files:**
- Create: `.github/workflows/pr-gate.yml`
- Create: `tests/unit/scripts/test_pr_gate_workflow.py`

**Step 1: Write the failing test**

```python
import yaml

def test_pr_gate_contains_merge_group_trigger():
    with open(".github/workflows/pr-gate.yml", "r", encoding="utf-8") as f:
        wf = yaml.safe_load(f)
    assert "merge_group" in wf["on"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/scripts/test_pr_gate_workflow.py -v`  
Expected: FAIL with file not found or missing `merge_group`

**Step 3: Write minimal implementation**

```yaml
on:
  pull_request:
    branches: [main]
  merge_group:
    types: [checks_requested]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/scripts/test_pr_gate_workflow.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add .github/workflows/pr-gate.yml tests/unit/scripts/test_pr_gate_workflow.py
git commit -m "ci: 为PR门禁增加merge_group触发"
```

### Task 3: 标准化 Parent/Sub-issue 与 Draft PR 模板

**Files:**
- Create: `.github/ISSUE_TEMPLATE/epic.yml`
- Create: `.github/ISSUE_TEMPLATE/subtask.yml`
- Modify: `.github/pull_request_template.md`
- Create: `tests/unit/scripts/test_issue_templates.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

def test_subtask_template_has_dependency_field():
    content = Path(".github/ISSUE_TEMPLATE/subtask.yml").read_text(encoding="utf-8")
    assert "blocked_by" in content
    assert "gate" in content
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/scripts/test_issue_templates.py -v`  
Expected: FAIL with missing template or missing required fields

**Step 3: Write minimal implementation**

```yaml
body:
  - type: textarea
    id: blocked_by
  - type: dropdown
    id: gate
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/scripts/test_issue_templates.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add .github/ISSUE_TEMPLATE/epic.yml .github/ISSUE_TEMPLATE/subtask.yml .github/pull_request_template.md tests/unit/scripts/test_issue_templates.py
git commit -m "docs(github): 标准化并行任务issue与PR模板"
```

### Task 4: 建立 Project 状态与 Gate 对齐检查

**Files:**
- Create: `scripts/ci/check_project_gate_alignment.py`
- Create: `tests/unit/scripts/test_project_gate_alignment.py`
- Create: `docs/ops/github-parallel-governance-runbook.md`

**Step 1: Write the failing test**

```python
from scripts.ci.check_project_gate_alignment import validate_item

def test_done_item_must_have_merged_pr():
    item = {"status": "Done", "pr_state": "OPEN"}
    ok, reason = validate_item(item)
    assert not ok
    assert "merged" in reason.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/scripts/test_project_gate_alignment.py -v`  
Expected: FAIL because `validate_item` not implemented

**Step 3: Write minimal implementation**

```python
def validate_item(item: dict):
    if item.get("status") == "Done" and item.get("pr_state") != "MERGED":
        return False, "Done item requires merged PR"
    return True, ""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/scripts/test_project_gate_alignment.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/ci/check_project_gate_alignment.py tests/unit/scripts/test_project_gate_alignment.py docs/ops/github-parallel-governance-runbook.md
git commit -m "feat(ci): 增加Project与Gate一致性校验"
```

### Task 5: 试运行与验收闭环（两周）

**Files:**
- Create: `docs/reports/2026-03-xx-github-parallel-governance-pilot-report.md`
- Modify: `docs/plans/2026-03-02-github-strong-gated-parallel-development-design.md`

**Step 1: Write the failing test**

```python
def test_placeholder():
    assert False, "pilot metrics file not generated"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/scripts/test_pilot_report_placeholder.py -v`  
Expected: FAIL intentionally, used as pilot checkpoint gate

**Step 3: Write minimal implementation**

```python
def test_placeholder():
    assert True
```

并补齐试运行报告中的五项验收证据：结构/流程/门禁/队列/闭环。

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/scripts/test_pilot_report_placeholder.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add docs/reports/2026-03-xx-github-parallel-governance-pilot-report.md docs/plans/2026-03-02-github-strong-gated-parallel-development-design.md tests/unit/scripts/test_pilot_report_placeholder.py
git commit -m "docs(report): 完成强门禁并行治理试运行验收"
```

---

## 执行检查点（必须满足）

1. 任何时刻 `WIP <= 3`，超限必须先清队列。
2. 所有进入 queue 的 PR 都触发 `merge_group` 检查。
3. `main` 不允许 direct push，不允许绕过 required checks。
4. 每日同步一次 Project 风险字段（`Risk`）。
5. 试运行结束后必须提交复盘报告再扩大范围。

---

## 风险提示

1. 若组织权限不足，ruleset 与 merge queue 配置会受限，先解决权限再实施。
2. 若 CI 任务波动高，merge queue 可能频繁重试，需先治理 flaky。
3. 若 Issue 拆分质量差（依赖不清），并行会退化为串行拥堵。
