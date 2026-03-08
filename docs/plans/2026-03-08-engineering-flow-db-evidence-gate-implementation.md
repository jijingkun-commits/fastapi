# Engineering Flow DB Evidence Gate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a six-stage database evidence gate across `/jjk-plan -> /jjk-vkplan -> /jjk-cardrun -> /jjk-wtimp -> /jjk-test -> /jjk-verify`, so DB-risk tasks cannot be merged or accepted without structured evidence.

**Architecture:** Add `risk_tags`, `mandatory_evidence`, and typed `acceptance_cmds` at planning time; inherit them into `vk_cards.json`; require `wtimp` to emit typed `acceptance_results`; make `cardrun` done gate, `jjk-test`, and `jjk-verify` consume those results mechanically. Keep the existing engineering-flow skeleton and strengthen contracts instead of adding another orchestrator.

**Tech Stack:** Markdown workflow commands, Python workflow validators, shell wrappers, pytest, existing `wt-flow`/`cardrun`/`wtimp` scripts, project documentation.

---

### Task 1: Freeze the contract schema in source command docs

**Files:**
- Modify: `.cursor/commands/jjk-plan.md`
- Modify: `.cursor/commands/jjk-vkplan.md`
- Modify: `.cursor/commands/jjk-cardrun.md`
- Modify: `.cursor/commands/jjk-wtimp.md`
- Modify: `.cursor/commands/jjk-test.md`
- Modify: `.cursor/commands/jjk-verify.md`
- Reference: `docs/plans/2026-03-08-engineering-flow-db-evidence-gate-design.md`

**Step 1: Add the failing contract examples to docs**
- In each command doc, add examples showing a DB-risk task missing `mandatory_evidence` and mark it as invalid.
- Add the new fields and failure codes exactly as frozen in the design.

**Step 2: Run focused grep-based checks**
Run:
```bash
rg -n "risk_tags|mandatory_evidence|acceptance_results|DB_EVIDENCE|VERIFY_.*UNPROVEN" .cursor/commands/jjk-{plan,vkplan,cardrun,wtimp,test,verify}.md
```
Expected: every command doc contains the new contract terms.

**Step 3: Write the minimal contract wording**
- `jjk-plan`: define `risk_tags`, `mandatory_evidence`, typed `acceptance_cmds`
- `jjk-vkplan`: inherit contract to cards, add `cross_card_closure`
- `jjk-cardrun`: done gate must require `evidence_satisfied`
- `jjk-wtimp`: dispatch JSON must contain typed `acceptance_results`
- `jjk-test`: matrix must compare required vs actual evidence
- `jjk-verify`: PASS requires full mandatory evidence set

**Step 4: Verify docs remain internally consistent**
Run:
```bash
python3 scripts/check_clarify_contract_consistency.py || true
```
Expected: no new inconsistency unrelated to `jjk-clarify`; if there are unrelated failures, record and do not silently fix unrelated areas.

**Step 5: Commit**
```bash
git add .cursor/commands/jjk-plan.md .cursor/commands/jjk-vkplan.md .cursor/commands/jjk-cardrun.md .cursor/commands/jjk-wtimp.md .cursor/commands/jjk-test.md .cursor/commands/jjk-verify.md
git commit -m "docs: freeze db evidence gate contract across workflow commands"
```

### Task 2: Teach workflow validation scripts the new evidence contract

**Files:**
- Modify: `scripts/check_workflow_contract.py`
- Test: `tests/unit/test_workflow_tooling_contract_docs.py`
- Test: `tests/unit/test_check_workflow_contract_temporal_rules.py`
- Test: add new focused test file if needed under `tests/unit/`

**Step 1: Write failing validator tests**
Add tests that assert:
- DB-risk task without `mandatory_evidence` fails
- card without inherited `mandatory_evidence` fails
- `typed acceptance_cmds` mismatch fails
- missing `cross_card_closure` on split DB chain fails

**Step 2: Run the failing tests**
Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_workflow_tooling_contract_docs.py -q
```
Expected: FAIL on the new missing-rule cases.

**Step 3: Implement minimal validator logic**
- Parse `risk_tags`
- Parse `mandatory_evidence`
- Parse `acceptance_cmds[*].kind`
- Add new fail-fast codes:
  - `PLAN_DB_EVIDENCE_MISSING`
  - `VKPLAN_EVIDENCE_MAPPING_BROKEN`
  - `VKPLAN_DB_CHAIN_SPLIT_UNCLOSED`

**Step 4: Re-run focused tests**
Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_workflow_tooling_contract_docs.py tests/unit/test_check_workflow_contract_temporal_rules.py -q
```
Expected: PASS for new validator cases.

**Step 5: Commit**
```bash
git add scripts/check_workflow_contract.py tests/unit/test_workflow_tooling_contract_docs.py tests/unit/test_check_workflow_contract_temporal_rules.py
git commit -m "feat: validate db evidence contract in workflow tooling"
```

### Task 3: Propagate evidence requirements into `vk_cards.json`

**Files:**
- Modify: `.cursor/commands/jjk-vkplan.md`
- Modify: scripts or templates that build `vk_cards.json` if present
- Test: add/update focused `vkplan` contract tests under `tests/unit/`

**Step 1: Write failing tests for card inheritance**
Test that generated card payloads contain:
- `risk_tags`
- `mandatory_evidence`
- `cross_card_closure`

**Step 2: Run the focused failing tests**
Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_workflow_gate_usage_report_contract.py -q
```
Expected: FAIL on missing card evidence fields.

**Step 3: Implement minimal propagation**
- In the `vkplan` generation path, copy task evidence obligations to each card
- If one DB chain is split across cards, require one closure owner card

**Step 4: Re-run tests**
Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_workflow_gate_usage_report_contract.py -q
```
Expected: PASS.

**Step 5: Commit**
```bash
git add .cursor/commands/jjk-vkplan.md
git commit -m "feat: propagate db evidence contract into vk cards"
```

### Task 4: Make `wtimp` emit typed `acceptance_results`

**Files:**
- Modify: `.cursor/commands/jjk-wtimp.md`
- Modify: `scripts/coder4/wtimp_dispatch_bridge.py`
- Modify: `scripts/coder4/wt-flow.sh` if needed for result handoff
- Test: `tests/unit/test_coder4_wtimp_dispatch_bridge.py`
- Test: add/update `tests/unit/test_coder4_dispatch_executor.py`

**Step 1: Write failing dispatch JSON contract tests**
Add tests that require `cardrun_dispatch` JSON to contain:
- `acceptance_results`
- `kind`
- `summary`
- `evidence_satisfied`

**Step 2: Run the focused tests**
Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_coder4_wtimp_dispatch_bridge.py -q
```
Expected: FAIL because typed evidence is missing.

**Step 3: Implement minimal JSON contract upgrade**
- Normalize acceptance command outputs into typed result objects
- Mark `evidence_satisfied=false` if any mandatory DB evidence category is missing
- Preserve existing `commit_sha` / `merge_sha` fields

**Step 4: Re-run tests**
Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_coder4_wtimp_dispatch_bridge.py tests/unit/test_coder4_dispatch_executor.py -q
```
Expected: PASS.

**Step 5: Commit**
```bash
git add .cursor/commands/jjk-wtimp.md scripts/coder4/wtimp_dispatch_bridge.py scripts/coder4/wt-flow.sh tests/unit/test_coder4_wtimp_dispatch_bridge.py tests/unit/test_coder4_dispatch_executor.py
git commit -m "feat: emit typed evidence results from wtimp dispatch"
```

### Task 5: Upgrade `cardrun` done gate to consume evidence satisfaction

**Files:**
- Modify: `.cursor/commands/jjk-cardrun.md`
- Modify: `scripts/coder4/coder4_bootstrap_kernel.py`
- Modify: `scripts/coder4/wt-flow.sh`
- Test: `tests/unit/test_coder4_wt_flow_verified_state.py`
- Test: add/update `tests/unit/test_wt_flow_wrapper_entrypoint.py`

**Step 1: Write failing done-gate tests**
Test that:
- `commit_sha` present but `evidence_satisfied=false` blocks verify/merge
- missing DB evidence produces a specific cardrun failure code

**Step 2: Run focused tests**
Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_coder4_wt_flow_verified_state.py -q
```
Expected: FAIL on the new gate rules.

**Step 3: Implement minimal done-gate logic**
- Extend kernel/wt-flow evidence ingestion
- Block `verify -> merge` when mandatory evidence categories are incomplete
- Keep existing `MERGE_NO_COMMITS` semantics intact

**Step 4: Re-run tests**
Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_coder4_wt_flow_verified_state.py tests/unit/test_wt_flow_wrapper_entrypoint.py -q
```
Expected: PASS.

**Step 5: Commit**
```bash
git add .cursor/commands/jjk-cardrun.md scripts/coder4/coder4_bootstrap_kernel.py scripts/coder4/wt-flow.sh tests/unit/test_coder4_wt_flow_verified_state.py tests/unit/test_wt_flow_wrapper_entrypoint.py
git commit -m "feat: require evidence satisfaction before cardrun merge"
```

### Task 6: Make `jjk-test` report required-vs-actual evidence and register scripted flows

**Files:**
- Modify: `.cursor/commands/jjk-test.md`
- Modify: `docs/开发文档/测试管理/测试用例库.md`
- Modify: `docs/开发文档/测试管理/测试指南与环境配置.md`
- Create or modify: a scripted-flow registry document under `docs/开发文档/测试管理/`
- Test: add/update unit tests if a registry parser/script is introduced

**Step 1: Write the failing matrix expectations in docs/tests**
Define that test reports must include:
- `Required Evidence`
- `Actual Evidence`
- `Scripted Flow Status`
- `Historical Gap vs Current Gap`

**Step 2: Run the minimal relevant checks**
Run:
```bash
rg -n "Scripted Flow|Required Evidence|Actual Evidence|DB 持久化" docs/开发文档/测试管理
```
Expected: before implementation, these report terms are incomplete or inconsistent.

**Step 3: Implement the registry/matrix update**
- Enumerate current scripted-flow files
- Tag them by `chat_db` / `data_db` / `env_gate` / `runtime`
- Add the report output contract to `jjk-test`

**Step 4: Verify consistency**
Run:
```bash
rg -n "Scripted Flow|Required Evidence|Actual Evidence|DB 持久化" docs/开发文档/测试管理 .cursor/commands/jjk-test.md
```
Expected: report terms and matrix guidance are present and aligned.

**Step 5: Commit**
```bash
git add .cursor/commands/jjk-test.md docs/开发文档/测试管理/测试用例库.md docs/开发文档/测试管理/测试指南与环境配置.md
git commit -m "docs: register scripted flow evidence in jjk-test matrix"
```

### Task 7: Make `jjk-verify` enforce mandatory evidence for PASS

**Files:**
- Modify: `.cursor/commands/jjk-verify.md`
- Modify: verify templates under `docs/内部参考/迭代需求/_templates/` if needed
- Test: add/update focused tests for verify report generation if a script exists

**Step 1: Write the failing verification expectations**
Add examples where:
- DB-risk task lacks DB evidence -> `FAIL`
- non-mandatory missing evidence -> `WARN`
- all mandatory evidence present -> `PASS`

**Step 2: Run light checks**
Run:
```bash
rg -n "PASS|WARN|FAIL|mandatory_evidence|UNPROVEN|验证报告" .cursor/commands/jjk-verify.md docs/内部参考/迭代需求/_templates
```
Expected: before implementation, mandatory-evidence rules are absent.

**Step 3: Implement minimal verify contract changes**
- Require mandatory evidence set for PASS
- Emit `VERIFY_CHAT_DB_UNPROVEN` and `VERIFY_DATA_DB_UNPROVEN`
- Keep UAT only as a supplement, not a substitute for missing DB evidence

**Step 4: Verify**
Run:
```bash
rg -n "VERIFY_CHAT_DB_UNPROVEN|VERIFY_DATA_DB_UNPROVEN|mandatory_evidence" .cursor/commands/jjk-verify.md docs/内部参考/迭代需求/_templates
```
Expected: PASS/WARN/FAIL gate wording is aligned.

**Step 5: Commit**
```bash
git add .cursor/commands/jjk-verify.md docs/内部参考/迭代需求/_templates
git commit -m "docs: enforce mandatory db evidence in verify gate"
```

### Task 8: Sync mirrors, update long-term memory, and run focused regression

**Files:**
- Modify: `memory-bank.md`
- Run: `python3 scripts/sync_rules_to_cc.py --only commands`
- Verify: command/skill mirror outputs for touched `jjk-*` docs

**Step 1: Record the long-term engineering decision**
Add one ACTIVE decision entry for the DB evidence gate mainchain.

**Step 2: Sync generated mirrors**
Run:
```bash
python3 scripts/sync_rules_to_cc.py --only commands
```
Expected: touched `.cursor/commands/jjk-*.md` are mirrored to `.agents/skills/jjk-*/SKILL.md`.

**Step 3: Run focused regression**
Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_workflow_tooling_contract_docs.py tests/unit/test_coder4_wtimp_dispatch_bridge.py tests/unit/test_coder4_wt_flow_verified_state.py -q
```
Expected: PASS.

**Step 4: Run final collection/build sanity check**
Run:
```bash
PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" -m pytest -q tests/unit/test_repo_python_script.py tests/unit/test_pytest_targeted_script.py
```
Expected: PASS.

**Step 5: Commit**
```bash
git add memory-bank.md .agents/skills/jjk-*/SKILL.md
git commit -m "chore: sync db evidence gate workflow mirrors"
```

---

Plan complete and saved to `docs/plans/2026-03-08-engineering-flow-db-evidence-gate-implementation.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
