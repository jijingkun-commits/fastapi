#!/usr/bin/env python3
"""校验 /jjk-clarify 命令、模板与镜像是否一致。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CODEX_PROMPTS_DIR = Path.home() / ".codex" / "prompts"
COMMAND_PATH = Path(".cursor/commands/jjk-clarify.md")
TEMPLATE_PATH = Path("workdocs/_templates/jjk_clarify_templates.md")
SKILL_PATH = Path(".agents/skills/jjk-clarify/SKILL.md")
PROMPT_FILENAME = "jjk-clarify.md"

REQUIRED_COMMAND_SNIPPETS = (
    "默认问题包提问",
    "clarify_phase=approval",
    "clarify_consistency_check",
    "open_questions_count",
    'question_mode: "package|single"',
)
REQUIRED_TEMPLATE_SNIPPETS = (
    "默认提问模板（问题包）",
    "降级模板（单题追问）",
    "question_mode: package",
    "question_mode: single",
    "clarify_phase: approval",
    "open_questions_count: 0",
    "clarify_consistency_check:",
)
REQUIRED_SKILL_SNIPPETS = (
    "默认问题包提问",
    "clarify_phase=approval",
    "clarify_consistency_check",
)
FORBIDDEN_TEMPLATE_SNIPPETS = (
    "默认提问模板（一问一答）",
    "回答后我将继续下一题",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _missing_snippets(text: str, snippets: tuple[str, ...]) -> list[str]:
    return [snippet for snippet in snippets if snippet not in text]


def run_consistency_check(repo_root: Path, codex_prompts_dir: Path | None = None) -> dict[str, Any]:
    prompt_root = codex_prompts_dir or DEFAULT_CODEX_PROMPTS_DIR
    files = {
        "command": str((repo_root / COMMAND_PATH).resolve()),
        "template": str((repo_root / TEMPLATE_PATH).resolve()),
        "skill": str((repo_root / SKILL_PATH).resolve()),
        "prompt": str((prompt_root / PROMPT_FILENAME).resolve()),
    }

    errors: list[dict[str, Any]] = []

    def add_error(code: str, message: str, details: Any) -> None:
        errors.append({"code": code, "message": message, "details": details})

    command_path = repo_root / COMMAND_PATH
    template_path = repo_root / TEMPLATE_PATH
    skill_path = repo_root / SKILL_PATH
    prompt_path = prompt_root / PROMPT_FILENAME

    for label, path in (("command", command_path), ("template", template_path), ("skill", skill_path), ("prompt", prompt_path)):
        if not path.exists():
            add_error("CLARIFY_FILE_MISSING", f"{label} 文件缺失", {"file": str(path)})

    if errors:
        return {"ok": False, "files": files, "errors": errors}

    command_text = _read_text(command_path)
    template_text = _read_text(template_path)
    skill_text = _read_text(skill_path)
    prompt_text = _read_text(prompt_path)

    missing_command = _missing_snippets(command_text, REQUIRED_COMMAND_SNIPPETS)
    if missing_command:
        add_error(
            "CLARIFY_COMMAND_CONTRACT_BROKEN",
            "jjk-clarify 主命令缺少关键契约片段",
            {"missing_snippets": missing_command},
        )

    missing_template = _missing_snippets(template_text, REQUIRED_TEMPLATE_SNIPPETS)
    if missing_template:
        add_error(
            "CLARIFY_TEMPLATE_CONTRACT_BROKEN",
            "jjk-clarify 模板缺少关键契约片段",
            {"missing_snippets": missing_template},
        )

    forbidden_template_hits = [snippet for snippet in FORBIDDEN_TEMPLATE_SNIPPETS if snippet in template_text]
    if forbidden_template_hits:
        add_error(
            "CLARIFY_TEMPLATE_LEGACY_PATTERN",
            "jjk-clarify 模板仍包含旧提问模式片段",
            {"forbidden_snippets": forbidden_template_hits},
        )

    missing_skill = _missing_snippets(skill_text, REQUIRED_SKILL_SNIPPETS)
    if missing_skill:
        add_error(
            "CLARIFY_SKILL_MIRROR_BROKEN",
            "jjk-clarify Skill 镜像缺少关键契约片段",
            {"missing_snippets": missing_skill},
        )

    if prompt_text != command_text:
        add_error(
            "CLARIFY_PROMPT_DRIFT",
            "Codex prompt 与 .cursor/commands/jjk-clarify.md 不一致",
            {
                "command": str(command_path),
                "prompt": str(prompt_path),
            },
        )

    return {"ok": not errors, "files": files, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 /jjk-clarify 命令、模板与镜像一致性")
    parser.add_argument("--repo-root", default=str(ROOT), help="仓库根目录（默认当前项目）")
    parser.add_argument(
        "--codex-prompts-dir",
        default=str(DEFAULT_CODEX_PROMPTS_DIR),
        help="Codex prompts 目录（默认 ~/.codex/prompts）",
    )
    args = parser.parse_args()

    result = run_consistency_check(
        repo_root=Path(args.repo_root).expanduser().resolve(),
        codex_prompts_dir=Path(args.codex_prompts_dir).expanduser().resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
