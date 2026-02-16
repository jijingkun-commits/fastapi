"""LLM 场景化调用治理测试。"""

import ast
from typing import Optional
from pathlib import Path


ALLOWED_NO_MODEL_ID_CALLERS = {
    "app/ai/config/todo_config.py",  # 统一依赖注入包装器，透传 kwargs
    "app/ai/test_tool_calls.py",     # 本地测试脚本
}

ALLOWED_LEGACY_SCENE_CALLERS = {
    "app/ai/llm_util.py",  # 兼容层自身
}


def _get_call_name(node: ast.Call) -> Optional[str]:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def test_no_naked_get_llm_calls_outside_allowlist():
    """除白名单外，生产代码禁止出现未显式 model_id 的 get_llm 调用。"""

    project_root = Path(__file__).resolve().parents[2]
    app_root = project_root / "app"
    violations: list[str] = []

    for file_path in sorted(app_root.rglob("*.py")):
        rel_path = file_path.relative_to(project_root).as_posix()

        if rel_path in ALLOWED_NO_MODEL_ID_CALLERS:
            continue
        if "/examples/" in rel_path or "/tests/" in rel_path:
            continue

        source = file_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if _get_call_name(node) != "get_llm":
                continue

            has_model_kw = any(kw.arg == "model_id" for kw in node.keywords)
            if not has_model_kw:
                violations.append(f"{rel_path}:{node.lineno}")

    assert not violations, (
        "发现未场景化的 get_llm 调用，请改为 get_scene_llm(scene_key=...) "
        "或显式传递 model_id:\n" + "\n".join(violations)
    )


def test_get_scene_llm_must_use_scene_key_kwarg():
    """业务代码调用 get_scene_llm 时必须显式传 scene_key。"""

    project_root = Path(__file__).resolve().parents[2]
    app_root = project_root / "app"
    violations: list[str] = []

    for file_path in sorted(app_root.rglob("*.py")):
        rel_path = file_path.relative_to(project_root).as_posix()

        if rel_path in ALLOWED_LEGACY_SCENE_CALLERS:
            continue
        if "/examples/" in rel_path or "/tests/" in rel_path:
            continue

        source = file_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if _get_call_name(node) != "get_scene_llm":
                continue

            has_scene_key_kw = any(kw.arg == "scene_key" for kw in node.keywords)
            if not has_scene_key_kw:
                violations.append(f"{rel_path}:{node.lineno}")

    assert not violations, (
        "发现未使用 scene_key 的 get_scene_llm 调用，"
        "请改为 get_scene_llm(scene_key='模块.函数名', ...):\n"
        + "\n".join(violations)
    )
