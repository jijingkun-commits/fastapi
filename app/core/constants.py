import re

# 分页相关
MAX_PAGE_SIZE = 100       # 分页最大数量
DEFAULT_LANGUAGE = "zh-CN" # 默认语言

# 图片处理相关
IMG_BUFFER_MAX_SIZE = 2000      # 图片缓冲区最大长度（预签名 URL 可能很长）
TOOL_OUTPUT_PREVIEW_LEN = 500   # 工具输出预览长度
TOOL_OUTPUT_STORAGE_LEN = 1000  # 工具输出存储长度
MESSAGE_TITLE_MAX_LEN = 50      # 消息标题最大长度

# MinIO 相关
MINIO_URL_SCHEME = "minio://"

# 编译后的正则表达式（只编译一次，处处使用）
# 匹配 Markdown 图片语法: ![alt](url)，捕获 URL
MARKDOWN_IMAGE_PATTERN = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')

# 匹配完整的 Markdown 图片标签
MARKDOWN_IMAGE_FULL_PATTERN = re.compile(r'!\[[^\]]*\]\([^)]+\)')


from typing import Optional

def extract_url_from_image_tag(image_tag: str) -> Optional[str]:
    """从 Markdown 图片标签中提取 URL。
    
    Args:
        image_tag: Markdown 图片标签，如 '![desc](http://...)'
        
    Returns:
        URL 字符串，如果提取失败则返回 None
    """
    match = MARKDOWN_IMAGE_PATTERN.search(image_tag)
    return match.group(1) if match else None
