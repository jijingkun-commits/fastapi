import json

# 模拟 ragflow_tool.py 的行为
kb_images = {0: "/api/v1/assets/proxy/ragflow/image0", 1: "/api/v1/assets/proxy/ragflow/image1"}
print("原始 kb_images:", kb_images)
print("类型:", type(list(kb_images.keys())[0]))

# JSON 序列化
json_str = json.dumps(kb_images)
print("\nJSON 序列化:", json_str)

# 模拟嵌入到文本
result_text = "【0】内容... [IMG-0]\n\n【1】内容... [IMG-1]"
full_text = result_text + f"\n\n<!--KB_IMAGES:{json_str}-->"
print("\n完整文本:")
print(full_text)

# 模拟 chat_repo.py 的提取
import re
kb_images_match = re.search(r'<!--KB_IMAGES:(\{.*?\})-->', full_text)
if kb_images_match:
    extracted = json.loads(kb_images_match.group(1))
    print("\n提取的 kb_images:", extracted)
    print("类型:", type(list(extracted.keys())[0]))
    
    # 模拟替换
    ai_content = "账户管理... [IMG-0]\n转账功能... [IMG-1]"
    print("\nAI 回复:", ai_content)
    
    for idx_str, url in extracted.items():
        placeholder = f"[IMG-{idx_str}]"
        print(f"查找占位符: {placeholder}, 在内容中: {placeholder in ai_content}")
        if placeholder in ai_content:
            ai_content = ai_content.replace(placeholder, f"![参考图片]({url})", 1)
    
    print("\n替换后:", ai_content)
else:
    print("未找到 KB_IMAGES")
