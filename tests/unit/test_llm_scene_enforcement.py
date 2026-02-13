"""LLM 场景化调用治理测试。"""

import ast
from pathlib import Path


ALLOWED_NO_MODEL_ID_CALLERS = {
    "app/ai/config/todo_config.py",  # 统一依赖注入包装器，透传 kwargs
    "app/ai/test_tool_calls.py",     # 本地测试脚本
}


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

            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name != "get_llm":
                continue

            has_model_kw = any(kw.arg == "model_id" for kw in node.keywords)
            if not has_model_kw:
                violations.append(f"{rel_path}:{node.lineno}")

    assert not violations, (
        "发现未场景化的 get_llm 调用，请改为 get_scene_llm(scene=...) "
        "或显式传递 model_id:\n" + "\n".join(violations)
    )
