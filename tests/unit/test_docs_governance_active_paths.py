"""活跃文档治理路径回归测试。"""

from __future__ import annotations

import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


DOCS_GUARD_PATH = Path("scripts/docs_guard.py")
WORKFLOW_PATH = Path(".github/workflows/contract-gate.yml")
GITIGNORE_PATH = Path(".gitignore")
LEGACY_STATE_MANIFEST = Path(".state/cardrun_wtimp/pr_ready_manifest_cardrun内置wtimp执行器.json")


def _load_docs_guard_module():
    module_name = f"docs_guard_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, DOCS_GUARD_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_legacy_entry_pages_only_are_treated_as_process_docs():
    module = _load_docs_guard_module()

    iteration_readme = (Path("docs/内部参考/迭代需求/README.md")).resolve()
    task_split_readme = (Path("docs/内部参考/任务拆解/README.md")).resolve()
    hypothetical_legacy_body = (Path("docs/内部参考/迭代需求/example.md")).resolve()

    assert module.resolve_doc_role(iteration_readme) == "process"
    assert module.resolve_doc_role(task_split_readme) == "process"
    assert module.resolve_doc_role(hypothetical_legacy_body) == "support"


def test_contract_gate_uploads_current_machine_readable_artifacts():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "workdocs/归档/报告/机读校验/composite-query-multimodal-response-contract_clarify_plan_alignment.json" in text
    assert "workdocs/归档/报告/机读校验/composite-query-multimodal-response-contract_planning_temporal_gate.json" in text
    assert "docs/内部参考/迭代需求/composite-query-multimodal-response-contract_clarify_plan_alignment.json" not in text
    assert "docs/内部参考/迭代需求/composite-query-multimodal-response-contract_planning_temporal_gate.json" not in text


def test_gitignore_blocks_root_state_and_legacy_manifest_is_gone():
    text = GITIGNORE_PATH.read_text(encoding="utf-8")

    assert "/.state/" in text
    assert "/docs/内部参考/迭代需求/requirements.md" not in text
    assert "/docs/内部参考/迭代需求/implementation_plan.md" not in text
    assert not LEGACY_STATE_MANIFEST.exists()


def test_runtime_state_pollution_only_flags_existing_tracked_files(tmp_path):
    module = _load_docs_guard_module()
    tracked_deleted = Path(".state/deleted.json")
    tracked_existing = Path(".state/existing.json")
    existing_file = tmp_path / tracked_existing
    existing_file.parent.mkdir(parents=True, exist_ok=True)
    existing_file.write_text("{}", encoding="utf-8")

    original_root = module.ROOT
    original_iter = module.iter_git_tracked_paths
    try:
        module.ROOT = tmp_path
        module.iter_git_tracked_paths = lambda pathspec: [tracked_deleted, tracked_existing]
        findings = []

        count = module.check_tracked_runtime_state_pollution(findings)

        assert count == 1
        assert len(findings) == 1
        assert findings[0].file == str(tracked_existing)
    finally:
        module.ROOT = original_root
        module.iter_git_tracked_paths = original_iter
