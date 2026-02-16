"""LLM list content 兼容性回归测试。"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage


def test_invoke_llm_for_intent_accepts_list_content():
    """待办意图解析应兼容 list content 响应。"""
    from app.ai.workflow.todo_graph import _invoke_llm_for_intent

    fake_content = [
        {
            "type": "text",
            "text": '{"intent":"create","extracted_info":{"title":"测试待办"}}',
        }
    ]

    class _FakeLLM:
        def invoke(self, _messages):
            return SimpleNamespace(content=fake_content)

    with patch("app.ai.workflow.todo_graph.get_scene_llm", return_value=_FakeLLM()):
        result = _invoke_llm_for_intent(
            recent_messages=[HumanMessage(content="帮我创建一个测试待办")],
            system_prompt="test",
            heuristic_title=None,
            pre_extracted_info=None,
        )

    assert result["intent"] == "create"
    assert result["extracted_info"].get("title") == "测试待办"


@pytest.mark.asyncio
async def test_intent_classifier_accepts_list_content():
    """意图分类器应兼容 list content 响应。"""
    from app.ai.intent_classifier import classify_intent

    class _FakeLLM:
        async def ainvoke(self, _prompt):
            return SimpleNamespace(
                content=[
                    {
                        "type": "text",
                        "text": '{"intent":"data_query","confidence":0.91,"route_to":"data_expert"}',
                    }
                ]
            )

    with patch("app.ai.llm_util.get_scene_llm", return_value=_FakeLLM()):
        result = await classify_intent("查询本月贷款余额")

    assert result.intent == "data_query"
    assert result.route_to == "data_expert"
