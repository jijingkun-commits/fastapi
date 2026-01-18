
class Attachment:
    def __init__(self, name, url, mime_type):
        self.name = name
        self.url = url
        self.mime_type = mime_type

def test_logic():
    attachments = [
        {"name": "test.png", "url": "http://u.com/t.png", "mime_type": "image/png"},
        Attachment("doc.pdf", "http://u.com/d.pdf", "application/pdf")
    ]
    
    prompt = "hello"
    final_prompt = prompt
    if attachments:
        # 分离图片和其他文件
        image_attachments = []
        other_attachments = []
        for att in attachments:
            mime = getattr(att, "mime_type", att.get("mime_type") if isinstance(att, dict) else "unknown")
            if "image" in mime:
                image_attachments.append(att)
            else:
                other_attachments.append(att)
        
        # 图片使用 Markdown 格式，这样前端可以直接渲染
        if image_attachments:
            final_prompt += "\n\n"
            for att in image_attachments:
                name = getattr(att, "name", att.get("name") if isinstance(att, dict) else "image")
                url = getattr(att, "url", att.get("url") if isinstance(att, dict) else "")
                if url:
                    # 使用 Markdown 图片格式
                    final_prompt += f"![{name}]({url})\n"
                    # 添加工具调用提示（Agent 需要知道如何处理）
                    final_prompt += f"(请使用 analyze_image 工具分析此图片: {url})\n\n"
        
        # 非图片文件使用原有格式
        if other_attachments:
            final_prompt += "\n\nUser uploaded files:"
            for att in other_attachments:
                name = getattr(att, "name", att.get("name") if isinstance(att, dict) else "unknown")
                url = getattr(att, "url", att.get("url") if isinstance(att, dict) else "")
                mime = getattr(att, "mime_type", att.get("mime_type") if isinstance(att, dict) else "unknown")
                
                final_prompt += f"\n- [{mime}] {name} (URL: {url})"
                
                if url:
                    if "csv" in mime or "spreadsheet" in mime or "excel" in mime:
                        final_prompt += "\n  (Hint: You can use python code to read this file)"
    
    print("Final Prompt:")
    print(final_prompt)
    print("Test Passed")

if __name__ == "__main__":
    try:
        test_logic()
    except Exception as e:
        print(f"Error: {e}")
