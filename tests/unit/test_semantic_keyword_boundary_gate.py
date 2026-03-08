"""编排层语义关键词硬编码门禁测试。"""

from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESTRICTED_GLOBS = (
    "app/services/**/*.py",
    "app/api/**/*.py",
    "app/controllers/**/*.py",
    "app/routers/**/*.py",
)
BANNED_CONSTANT_NAME = re.compile(r"(?:^|_)(?:HINTS|KEYWORDS|TRIGGERS)(?:$|_)")


def _iter_restricted_files() -> list[Path]:
    files: list[Path] = []
    for pattern in RESTRICTED_GLOBS:
        files.extend(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(set(files))


def _iter_module_level_target_names(node: ast.AST) -> list[str]:
    names: list[str] = []
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.append(target.id)
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        names.append(node.target.id)
    return names


def test_orchestration_layers_do_not_define_semantic_keyword_tables() -> None:
    """编排层禁止新增 `*_HINTS/*_KEYWORDS/*_TRIGGERS` 语义词表。"""

    violations: list[str] = []
    for file_path in _iter_restricted_files():
        module = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in module.body:
            for name in _iter_module_level_target_names(node):
                normalized = name.strip("_")
                if normalized.upper() != normalized:
                    continue
                if not BANNED_CONSTANT_NAME.search(normalized):
                    continue
                violations.append(f"{file_path.relative_to(ROOT)}::{name}")

    assert not violations, (
        "编排层禁止新增业务语义关键词词表，请把语义识别迁移到 intent/policy/resolver 层并输出结构化 contract。"
        f"\n违规项: {violations}"
    )
