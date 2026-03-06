"""coder4 execution_evidence 读旧写新迁移测试。"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/coder4/coder4_bootstrap_kernel.py")


def _load_kernel_module():
    module_name = f"coder4_evidence_migration_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_record_attempt_evidence_writes_canonical_execution_evidence(tmp_path):
    module = _load_kernel_module()
    ledger_file = tmp_path / "task-ledger.jsonl"
    started_at = datetime(2026, 3, 6, 12, 0, 0, tzinfo=timezone.utc)
    ended_at = started_at + timedelta(seconds=3)

    payload = module.record_attempt_evidence(
        ledger_file=ledger_file,
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="c01",
        action="dispatch",
        result="dispatch_executed",
        trigger_source="manual",
        started_at=started_at,
        ended_at=ended_at,
        applied={
            "performed": True,
            "executor_mode": "wtimp",
            "subagent_id": "agent-1",
            "ws_file": "workstreams/WS-01.md",
            "commit_sha": "abc123",
            "merge_sha": "def456",
        },
    )

    attempt = payload["attempt"]
    assert attempt["card_id"] == "C01"
    assert attempt["commit_sha"] == "abc123"
    assert attempt["merge_sha"] == "def456"
    assert attempt["subagent_id"] == "agent-1"
    assert attempt["ws_file"] == "workstreams/WS-01.md"

    canonical = attempt["execution_evidence"]
    assert canonical["executor_mode"] == "wtimp"
    assert canonical["commit_sha"] == "abc123"
    assert canonical["merge_sha"] == "def456"
    assert canonical["subagent_id"] == "agent-1"
    assert canonical["ws_file"] == "workstreams/WS-01.md"

    ledger_entry = json.loads(ledger_file.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert ledger_entry["commit_sha"] == "abc123"
    assert ledger_entry["merge_sha"] == "def456"
    assert ledger_entry["execution_evidence"]["executor_mode"] == "wtimp"
    assert ledger_entry["execution_evidence"]["commit_sha"] == "abc123"


def test_record_attempt_evidence_explicit_args_override_legacy_applied_fields(tmp_path):
    module = _load_kernel_module()
    ledger_file = tmp_path / "task-ledger.jsonl"
    started_at = datetime(2026, 3, 6, 12, 30, 0, tzinfo=timezone.utc)
    ended_at = started_at + timedelta(seconds=5)

    payload = module.record_attempt_evidence(
        ledger_file=ledger_file,
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        action="dispatch",
        result="dispatch_executed",
        trigger_source="manual",
        started_at=started_at,
        ended_at=ended_at,
        commit_sha="new-commit",
        merge_sha="new-merge",
        subagent_id="agent-new",
        ws_file="workstreams/WS-02.md",
        executor_mode="wtimp",
        applied={
            "performed": True,
            "commit_sha": "old-commit",
            "merge_sha": "old-merge",
            "subagent_id": "agent-old",
            "ws_file": "workstreams/WS-old.md",
            "executor_mode": "legacy",
        },
    )

    attempt = payload["attempt"]
    assert attempt["commit_sha"] == "new-commit"
    assert attempt["merge_sha"] == "new-merge"
    assert attempt["subagent_id"] == "agent-new"
    assert attempt["ws_file"] == "workstreams/WS-02.md"
    assert attempt["execution_evidence"]["executor_mode"] == "wtimp"
    assert attempt["execution_evidence"]["commit_sha"] == "new-commit"
