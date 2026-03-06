#!/usr/bin/env python3

from pathlib import Path


_TARGET = (Path(__file__).resolve().parent / "coder4" / "coder4_bootstrap_kernel.py").resolve()
_globals = globals()
_globals["__file__"] = str(_TARGET)
exec(compile(_TARGET.read_text(encoding="utf-8"), str(_TARGET), "exec"), _globals, _globals)
