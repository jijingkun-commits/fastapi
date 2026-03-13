"""测试资产治理合同回归测试。"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_testpaths_only_collect_tests_root() -> None:
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'testpaths = ["tests"]' in pyproject_text


def test_app_tests_no_longer_hosts_collected_test_modules() -> None:
    app_tests = ROOT / "app/tests"
    remaining = sorted(path.name for path in app_tests.glob("test_*.py"))
    assert remaining == [], f"app/tests 仍存在 test_*.py: {remaining}"


def test_compatibility_shell_for_todo_semantic_guard_is_removed() -> None:
    assert not (ROOT / "tests/unit/test_todo_graph_semantic_guard.py").exists()


def test_scripted_flows_live_under_scripts_verify() -> None:
    expected = {
        "ask_data_flow.py",
        "chat_stream_smoke.py",
        "minio_connection.py",
        "skill_visibility.py",
        "todo_complex_flow.py",
        "todo_complex_scenario.py",
        "todo_comprehensive_suite.py",
        "todo_e2e_real.py",
        "todo_multiround.py",
        "todo_shortcuts.py",
        "vanna_retrieval.py",
    }
    actual = {path.name for path in (ROOT / "scripts/verify").glob("*.py")}
    missing = sorted(expected - actual)
    assert not missing, f"scripts/verify 缺少脚本型验证资产: {missing}"


def test_master_todo_runner_no_longer_references_retired_test_paths() -> None:
    runner = ROOT / "tests/run_master_test_suite.py"
    if not runner.exists():
        return

    text = runner.read_text(encoding="utf-8")
    retired_paths = {
        "tests/test_todo_comprehensive_suite.py",
        "tests/test_shortcuts.py",
        "tests/test_todo_complex_flow.py",
    }
    for path in retired_paths:
        assert path not in text, f"Master runner 仍引用已退役路径: {path}"

    canonical_paths = {
        "scripts/verify/todo_comprehensive_suite.py",
        "scripts/verify/todo_shortcuts.py",
        "scripts/verify/todo_complex_flow.py",
    }
    for path in canonical_paths:
        assert path in text, f"Master runner 未对齐 canonical 脚本路径: {path}"
