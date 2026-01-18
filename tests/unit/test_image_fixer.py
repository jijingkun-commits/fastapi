
import unittest
import json
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.ai.utils.image_fixer import fix_missing_image_links

class TestImageFixer(unittest.TestCase):
    
    def test_no_messages(self):
        self.assertEqual(fix_missing_image_links([]), [])

    def test_no_tool_messages(self):
        msgs = [
            HumanMessage(content="hi"),
            AIMessage(content="hello")
        ]
        self.assertEqual(fix_missing_image_links(msgs), msgs)

    def test_tool_message_without_image(self):
        msgs = [
            HumanMessage(content="calc"),
            AIMessage(content="", tool_calls=[{"name": "calc", "args": {}, "id": "1"}]),
            ToolMessage(content="42", tool_call_id="1"),
            AIMessage(content="result is 42")
        ]
        self.assertEqual(fix_missing_image_links(msgs), msgs)

    def test_fix_missing_image(self):
        img_url = "http://example.com/img.png"
        tool_output = json.dumps({
            "status": "success",
            "image_url": img_url,
            "message": "ok"
        })
        
        msgs = [
            HumanMessage(content="draw"),
            AIMessage(content="", tool_calls=[{"name": "fig_inter", "args": {}, "id": "1"}]),
            ToolMessage(content=tool_output, tool_call_id="1"),
            AIMessage(content="Here is the chart.")
        ]
        
        fixed = fix_missing_image_links(msgs)
        last_msg = fixed[-1]
        
        self.assertIn(img_url, last_msg.content)
        self.assertIn("![Generated Image]", last_msg.content)
        self.assertTrue(last_msg.content.endswith(f"\n\n![Generated Image]({img_url})"))

    def test_image_already_present(self):
        img_url = "http://example.com/img.png"
        tool_output = json.dumps({
            "status": "success",
            "image_url": img_url,
            "message": "ok"
        })
        
        content = f"Here is the chart.\n![chart]({img_url})"
        msgs = [
            HumanMessage(content="draw"),
            AIMessage(content="", tool_calls=[{"name": "fig_inter", "args": {}, "id": "1"}]),
            ToolMessage(content=tool_output, tool_call_id="1"),
            AIMessage(content=content)
        ]
        
        fixed = fix_missing_image_links(msgs)
        self.assertEqual(fixed[-1].content, content)

    def test_multiple_images(self):
        url1 = "http://example.com/1.png"
        url2 = "http://example.com/2.png"
        
        tool_output1 = json.dumps({"status": "success", "image_url": url1})
        tool_output2 = json.dumps({"status": "success", "image_url": url2})
        
        msgs = [
            HumanMessage(content="draw 2"),
            AIMessage(content="", tool_calls=[{"name": "fig", "args": {}, "id": "1"}, {"name": "fig", "args": {}, "id": "2"}]),
            ToolMessage(content=tool_output1, tool_call_id="1"),
            ToolMessage(content=tool_output2, tool_call_id="2"),
            AIMessage(content="Here are charts.")
        ]
        
        fixed = fix_missing_image_links(msgs)
        content = fixed[-1].content
        self.assertIn(url1, content)
        self.assertIn(url2, content)

    def test_ignore_previous_turn_images(self):
        # 模拟上一轮对话（已经包含图片）
        # Human -> AI -> Tool -> AI
        url_old = "http://example.com/old.png"
        tool_output_old = json.dumps({"status": "success", "image_url": url_old})
        
        msgs = [
            HumanMessage(content="draw old"),
            AIMessage(content="use tool"),
            ToolMessage(content=tool_output_old, tool_call_id="1"),
            AIMessage(content=f"Old chart: ![img]({url_old})"),
            
            # 新一轮
            HumanMessage(content="say hi"),
            AIMessage(content="hi")
        ]
        
        fixed = fix_missing_image_links(msgs)
        # 最后一句话不应该包含 old.png，因为那是上一轮的
        self.assertEqual(fixed[-1].content, "hi")

if __name__ == '__main__':
    unittest.main()
