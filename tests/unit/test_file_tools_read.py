"""本地 read 工具单元测试。"""

import json
from pathlib import Path

from app.ai.tools import file_tools


def _build_config(user_id: int = 1) -> dict:
    """构造工具调用配置。"""
    return {"configurable": {"user_id": user_id}}


def test_read_admin_can_read_local_file(monkeypatch, tmp_path: Path):
    """admin 用户可通过 file_path 别名成功读取文件。"""
    target = tmp_path / "sample.txt"
    target.write_text("alpha\nbeta\n", encoding="utf-8")

    monkeypatch.setattr(file_tools, "PROJECT_ROOT", tmp_path.resolve())

    captured: dict[str, int] = {}

    def fake_get_user_role(user_id: int):
        captured["user_id"] = user_id
        return "admin", None

    monkeypatch.setattr(file_tools, "_get_user_role", fake_get_user_role)

    result = file_tools.read.func(
        file_path="sample.txt",
        config=_build_config(1001),
    )
    payload = json.loads(result)

    assert payload["status"] == "success"
    assert payload["tool"] == "read"
    assert payload["path"] == "sample.txt"
    assert payload["content"] == "alpha\nbeta\n"
    assert payload["line_start"] == 1
    assert payload["line_end"] == 2
    assert captured["user_id"] == 1001


def test_read_non_admin_should_be_denied(monkeypatch):
    """非 admin 角色应返回权限拒绝错误。"""
    monkeypatch.setattr(file_tools, "_get_user_role", lambda user_id: ("user", None))

    result = file_tools.read.func(
        path="README.md",
        config=_build_config(2002),
    )
    payload = json.loads(result)

    assert payload["status"] == "error"
    assert payload["error"] == "permission_denied"
    assert "仅支持 admin" in payload["message"]


def test_read_should_reject_path_traversal(monkeypatch, tmp_path: Path):
    """路径越界访问应被拒绝。"""
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True, exist_ok=True)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside", encoding="utf-8")

    monkeypatch.setattr(file_tools, "PROJECT_ROOT", project_root.resolve())
    monkeypatch.setattr(file_tools, "_get_user_role", lambda user_id: ("admin", None))

    result = file_tools.read.func(
        path="../outside.txt",
        config=_build_config(3003),
    )
    payload = json.loads(result)

    assert payload["status"] == "error"
    assert payload["error"] == "path_not_allowed"
    assert "路径越界" in payload["message"]


def test_read_offset_and_limit_should_take_effect(monkeypatch, tmp_path: Path):
    """offset/limit 应按行分页返回结果。"""
    target = tmp_path / "paged.txt"
    target.write_text("".join(f"line{i}\n" for i in range(1, 8)), encoding="utf-8")

    monkeypatch.setattr(file_tools, "PROJECT_ROOT", tmp_path.resolve())
    monkeypatch.setattr(file_tools, "_get_user_role", lambda user_id: ("admin", None))

    result = file_tools.read.func(
        path="paged.txt",
        offset=3,
        limit=2,
        config=_build_config(4004),
    )
    payload = json.loads(result)

    assert payload["status"] == "success"
    assert payload["line_start"] == 3
    assert payload["line_end"] == 4
    assert payload["line_count"] == 2
    assert payload["content"] == "line3\nline4\n"
    assert payload["truncated"] is True
    assert payload["next_offset"] == 5
