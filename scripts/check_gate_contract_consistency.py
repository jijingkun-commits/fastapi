#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from workflow_contract_gate_contract_impl import ContractParseError, _resolve_task_split_dir, _write_output, run_check


def wrapper_notice() -> str:
    return "[DEPRECATED] check_gate_contract_consistency.py 已降级为 wrapper，请改用 python3 scripts/check_workflow_contract.py --mode gate_contract"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    print(wrapper_notice(), file=sys.stderr)
    command = [
        sys.executable,
        str((Path(__file__).resolve().parent / "check_workflow_contract.py").resolve()),
        "--mode",
        "gate_contract",
        *args,
    ]
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
