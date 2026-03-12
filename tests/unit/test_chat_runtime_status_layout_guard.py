"""聊天运行态状态条布局回归门禁。"""

from pathlib import Path
import re


THREAD_FILE = Path("web/src/components/chat/index.tsx")
GLOBAL_CSS_FILE = Path("web/src/app/globals.css")


def _assert_runtime_status_is_rendered_before_footer_and_not_inside_footer() -> None:
    source = THREAD_FILE.read_text(encoding="utf-8")

    runtime_idx = source.index('data-testid="runtime-status"')
    footer_idx = source.index("<footer")

    assert runtime_idx < footer_idx
    assert re.search(
        r'\{currentStatus\?\.message && \(\s*<div[^>]*className="chat-content-shell[^"]*"\s*>\s*<div[^>]*data-testid="runtime-status"',
        source,
        re.S,
    )
    assert not re.search(
        r"<footer[\s\S]*data-testid=\"runtime-status\"",
        source,
        re.S,
    )


def _assert_runtime_status_uses_accessible_inline_bubble_style() -> None:
    source = THREAD_FILE.read_text(encoding="utf-8")
    css = GLOBAL_CSS_FILE.read_text(encoding="utf-8")

    assert 'role="status"' in source
    assert 'aria-live="polite"' in source

    match = re.search(r"\.chat-runtime-status\s*\{(?P<body>.*?)\n  \}", css, re.S)
    assert match is not None
    body = match.group("body")

    assert "max-width: 100%;" in body
    assert (
        "width: fit-content;" in body
        or "display: inline-flex;" in body
    )


def _assert_sticky_to_bottom_content_does_not_keep_dead_footer_slot() -> None:
    source = THREAD_FILE.read_text(encoding="utf-8")

    assert "footer?: ReactNode;" not in source
    assert "{props.footer}" not in source


def test_runtime_status_is_rendered_before_footer_and_not_inside_footer() -> None:
    """运行态状态条应挂在消息流，而不是 footer 输入区。"""

    _assert_runtime_status_is_rendered_before_footer_and_not_inside_footer()


def test_runtime_status_uses_accessible_inline_bubble_style() -> None:
    """运行态状态条应是可访问的内容列内气泡，而不是整行块。"""

    _assert_runtime_status_uses_accessible_inline_bubble_style()


def test_sticky_to_bottom_content_does_not_keep_dead_footer_slot() -> None:
    """消息滚动容器不应保留无人消费的 footer 插槽。"""

    _assert_sticky_to_bottom_content_does_not_keep_dead_footer_slot()


if __name__ == "__main__":
    _assert_runtime_status_is_rendered_before_footer_and_not_inside_footer()
    _assert_runtime_status_uses_accessible_inline_bubble_style()
    _assert_sticky_to_bottom_content_does_not_keep_dead_footer_slot()
