import os
import sys
import logging
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv(".env.dev")

# 模拟配置
class Config:
    RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY")
    RAGFLOW_API_URL = os.getenv("RAGFLOW_API_URL")
    RAGFLOW_DATASET_IDS = os.getenv("RAGFLOW_DATASET_IDS", "").split(",")
    RAGFLOW_TOP_K = int(os.getenv("RAGFLOW_TOP_K", "5"))
    RAGFLOW_SIMILARITY_THRESHOLD = float(os.getenv("RAGFLOW_SIMILARITY_THRESHOLD", "0.6"))
    RAGFLOW_VECTOR_WEIGHT = float(os.getenv("RAGFLOW_VECTOR_WEIGHT", "0.3"))

import app.core.config as app_config
# 强制覆盖 app.core.config 的值以确保与 .env.dev 一致
app_config.RAGFLOW_API_KEY = Config.RAGFLOW_API_KEY
app_config.RAGFLOW_API_URL = Config.RAGFLOW_API_URL
app_config.RAGFLOW_DATASET_IDS = Config.RAGFLOW_DATASET_IDS
app_config.RAGFLOW_TOP_K = Config.RAGFLOW_TOP_K
app_config.RAGFLOW_SIMILARITY_THRESHOLD = Config.RAGFLOW_SIMILARITY_THRESHOLD
app_config.RAGFLOW_VECTOR_WEIGHT = Config.RAGFLOW_VECTOR_WEIGHT

from app.ai.tools.ragflow_tool import knowledge_search, _format_retrieval_results

def test_ragflow_search():
    query = "新电子渠道有哪些功能？"
    logger.info(f"Testing knowledge_search with query: {query}")
    logger.info(f"Config: IDS={Config.RAGFLOW_DATASET_IDS}, TOP_K={Config.RAGFLOW_TOP_K}")

    try:
        # 直接调用工具
        # 注意：knowledge_search 是一个 LangChain 工具对象，我们需要调用它的 func 或者直接 invoke
        # 但在 ragflow_tool.py 中它被 @tool 装饰，所以 result 是 invoke 的结果
        # 为了直接调试内部逻辑，我们可以 import _call_ragflow_retrieval 如果它是公开的，但它不是。
        # 我们可以直接调用 knowledge_search.invoke ? No, knowledge_search is the function decorated by @tool.
        # Check how it's defined. It's decorated with @tool.
        
        # Let's try calling it as a function first (FastAPI/LangChain tools usually preserve the function)
        # However, the @tool decorator might wrap it. 
        # In ragflow_tool.py:
        # @tool(args_schema=KnowledgeSearchInput)
        # def knowledge_search(query: str, dataset_id: str = None) -> str:
        
        result = knowledge_search(query) 
        
        print("\n" + "="*50)
        print(f"Result Length: {len(result)}")
        print("="*50)
        print(result[:2000] + "..." if len(result) > 2000 else result)
        print("="*50)

        # Count images in result
        image_count = result.count("![" )
        print(f"Image Markdown Count: {image_count}")
        
    except Exception as e:
        logger.error(f"Error testing ragflow search: {e}", exc_info=True)

if __name__ == "__main__":
    test_ragflow_search()
