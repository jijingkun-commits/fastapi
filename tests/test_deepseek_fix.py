
import sys
import os
import unittest
import logging
from langchain_core.messages import AIMessage, HumanMessage

# Ensure app can be imported
sys.path.append(os.getcwd())

# Configure logging to see output from llm_util
logging.basicConfig(level=logging.INFO)

from app.ai.llm_util import CustomChatDeepSeek

class TestDeepSeekFix(unittest.TestCase):
    def test_reasoning_injection(self):
        # 1. Setup the patched LLM
        # We don't need a real key since we only test payload generation
        llm = CustomChatDeepSeek(api_key="fake-key", model="deepseek-reasoner")

        # 2. Create invalid history (Assistant message with tool calls but NO reasoning_content)
        # This simulates the state that causes the API error
        msgs = [
            HumanMessage(content="Calculate 1+1"),
            AIMessage(
                content="", 
                tool_calls=[{"name": "calculator", "args": {"expr": "1+1"}, "id": "call_1"}],
                additional_kwargs={} # Missing reasoning_content
            ),
        ]

        # 3. Generate payload
        # Note: _convert_input is used internally, we mimic internal call
        # But _get_request_payload takes the 'input_' which is the list of messages
        payload = llm._get_request_payload(msgs)

        # 4. Verify payload structure
        messages_payload = payload["messages"]
        self.assertEqual(len(messages_payload), 2)
        
        assistant_msg = messages_payload[1]
        self.assertEqual(assistant_msg["role"], "assistant")
        
        # This is the CRITICAL assertion
        # It must have "reasoning_content" injected, even if empty
        self.assertIn("reasoning_content", assistant_msg)
        self.assertEqual(assistant_msg["reasoning_content"], "")
        
        print("\n✅ Verification SUCCESS: 'reasoning_content' was injected into payload!")

if __name__ == "__main__":
    unittest.main()
