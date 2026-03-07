#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from workflow_contract_clarify_plan_impl import AlignmentCheckError, _build_parser, _write_output, run_alignment_check


def wrapper_notice() -> str:
    return "[DEPRECATED] check_clarify_plan_alignment.py 已降级为 wrapper，请改用 python3 scripts/check_workflow_contract.py --mode clarify_plan"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    print(wrapper_notice(), file=sys.stderr)
    command = [
        sys.executable,
        str((Path(__file__).resolve().parent / "check_workflow_contract.py").resolve()),
        "--mode",
        "clarify_plan",
        *args,
    ]
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
