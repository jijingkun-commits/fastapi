
import os
import sys
from unittest.mock import MagicMock

# 模拟环境变量
os.environ["MINIO_ENDPOINT"] = "localhost:19000"
os.environ["MINIO_ACCESS_KEY"] = "admin"
os.environ["MINIO_SECRET_KEY"] = "12345678"
os.environ["MINIO_BUCKET_ASSETS"] = "chat-assets"

# 添加路径
sys.path.append(os.getcwd())

from app.core.middlewares.message_processor import process_message_for_response

# 模拟输入：包含 minio:// 的 Markdown
test_content = "这里有一张图片：\n\n![图表](minio://chat-assets/3/mock-thread/charts/fig_123.png)"

print(f"原始内容: {test_content}")

# 调用处理函数
try:
    processed = process_message_for_response(test_content)
    print("\n处理后内容:")
    print(processed)
    
    # 检查 URL
    import re
    url_match = re.search(r'\((http[^\)]+)\)', processed)
    if url_match:
        url = url_match.group(1)
        print(f"\n提取的 URL: {url}")
        if "%3F" in url:
            print("❌ 错误：URL 中包含 %3F (被重复编码了)")
        elif "?" in url:
            print("✅ 正常：URL 中包含 ? (未被编码)")
        else:
            print("❓ 警告：URL 中没有查询参数")
            
except Exception as e:
    print(f"❌ 执行出错: {e}")
