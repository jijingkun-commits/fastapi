from app.ai.tools.chatTools import fig_inter


def test_fig_inter_prompt_uses_result_image_as_single_display_owner() -> None:
    description = getattr(fig_inter, "description", "") or ""

    assert "result(image)" in description
    assert "不要重复输出" in description
    assert "你 **必须** 在最终回复中" not in description
    assert "一定要把图片显示出来" not in description
