"""wt-flow wrapper 入口回归测试。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


SOURCE_WRAPPER = Path("scripts/wt-flow.sh")


def test_wt_flow_wrapper_reports_entity_script_when_detached(tmp_path: Path):
    detached_wrapper = tmp_path / "wt-flow.sh"
    shutil.copy2(SOURCE_WRAPPER, detached_wrapper)
    detached_wrapper.chmod(0o755)

    result = subprocess.run(
        ["bash", str(detached_wrapper), "status"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "wrapper" in result.stderr
    assert "scripts/coder4/wt-flow.sh" in result.stderr
    assert "单一真理源" in result.stderr or "实体脚本" in result.stderr


def test_wt_flow_wrapper_delegates_to_entity_script_when_layout_is_complete(tmp_path: Path):
    scripts_dir = tmp_path / "scripts"
    entity_dir = scripts_dir / "coder4"
    entity_dir.mkdir(parents=True, exist_ok=True)

    wrapper_path = scripts_dir / "wt-flow.sh"
    shutil.copy2(SOURCE_WRAPPER, wrapper_path)
    wrapper_path.chmod(0o755)

    entity_path = entity_dir / "wt-flow.sh"
    entity_path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'entity:%s\\n' \"${1:-missing}\"\n",
        encoding="utf-8",
    )
    entity_path.chmod(0o755)

    result = subprocess.run(
        ["bash", str(wrapper_path), "status"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "entity:status"
    assert result.stderr.strip() == ""
