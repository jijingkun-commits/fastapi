"""Vanna 客户端 submit_prompt 兼容性测试。"""

from types import SimpleNamespace
from unittest.mock import patch

from app.ai.semantic.vanna_client import VannaPGVector


def test_submit_prompt_normalizes_list_content_blocks():
    """当 LLM 返回 list content 时，submit_prompt 应返回可解析文本。"""

    class _FakeLLM:
        def invoke(self, _messages):
            return SimpleNamespace(
                content=[
                    {"type": "text", "text": "```sql\nSELECT 1;\n```"},
                    {
                        "type": "function_call",
                        "name": "assign_to_data_expert",
                        "arguments": "{}",
                    },
                ]
            )

    with patch("app.ai.llm_util.get_llm", return_value=_FakeLLM()):
        client = VannaPGVector()
        result = client.submit_prompt([{"role": "user", "content": "测试"}])

    assert isinstance(result, str)
    assert "SELECT 1" in result
