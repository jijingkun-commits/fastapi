"""check_clarify_contract_consistency 脚本回归测试。"""

from __future__ import annotations

import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/check_clarify_contract_consistency.py")


def _load_module():
    module_name = f"check_clarify_contract_consistency_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _prepare_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    command_path = repo_root / ".cursor" / "commands" / "jjk-clarify.md"
    template_path = repo_root / "docs" / "内部参考" / "迭代需求" / "_templates" / "jjk_clarify_templates.md"
    skill_path = repo_root / ".agents" / "skills" / "jjk-clarify" / "SKILL.md"
    codex_prompts_dir = tmp_path / "codex-prompts"
    prompt_path = codex_prompts_dir / "jjk-clarify.md"

    command_text = """---
description: 单指令澄清冻结入口：在 /jjk-clarify 内完成探索与设计冻结
---

默认问题包提问
clarify_consistency_check
clarify_phase=approval
open_questions_count
question_mode: "package|single"
"""
    template_text = """## 1) 默认提问模板（问题包）
question_mode: package
## 2) 降级模板（单题追问）
question_mode: single
clarify_consistency_check:
  clarify_phase: approval
  open_questions_count: 0
"""
    skill_text = """默认问题包提问
clarify_consistency_check
clarify_phase=approval
"""

    command_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    codex_prompts_dir.mkdir(parents=True, exist_ok=True)

    command_path.write_text(command_text, encoding="utf-8")
    template_path.write_text(template_text, encoding="utf-8")
    skill_path.write_text(skill_text, encoding="utf-8")
    prompt_path.write_text(command_text, encoding="utf-8")
    return repo_root, codex_prompts_dir


def test_run_consistency_check_passes(tmp_path):
    module = _load_module()
    repo_root, codex_prompts_dir = _prepare_repo(tmp_path)

    result = module.run_consistency_check(repo_root=repo_root, codex_prompts_dir=codex_prompts_dir)

    assert result["ok"] is True
    assert result["errors"] == []


def test_run_consistency_check_detects_prompt_drift(tmp_path):
    module = _load_module()
    repo_root, codex_prompts_dir = _prepare_repo(tmp_path)
    (codex_prompts_dir / "jjk-clarify.md").write_text("drifted", encoding="utf-8")

    result = module.run_consistency_check(repo_root=repo_root, codex_prompts_dir=codex_prompts_dir)

    assert result["ok"] is False
    assert any(error["code"] == "CLARIFY_PROMPT_DRIFT" for error in result["errors"])
