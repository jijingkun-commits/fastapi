#!/usr/bin/env python3

from pathlib import Path
import runpy


def main() -> int:
    target = (Path(__file__).resolve().parent / "coder4" / "check_integration_gate.py").resolve()
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
