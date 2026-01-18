"""文件读取工具（中文注释）。

提供从 MinIO 读取已上传文件的能力，供 Agent 在分析文档时使用。
"""
import io
import json
import logging
from typing import Optional

from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables.config import RunnableConfig

from app.core import config as ai_config
from app.services.asset_service import get_asset_service

logger = logging.getLogger(__name__)

# 可选依赖导入
try:
    import pandas as pd
except ImportError:
    pd = None


class ReadFileInput(BaseModel):
    """读取文件工具的输入参数。"""
    file_path: str = Field(
        description="文件的 URL 路径，通常是用户上传文件时返回的 URL，如 /api/v1/assets/xxx/yyy/file.xlsx"
    )


@tool(args_schema=ReadFileInput)
def read_uploaded_file(file_path: str, config: RunnableConfig) -> str:
    """
    读取用户上传的文件内容。

    支持的文件类型：
    - Excel (.xlsx, .xls): 返回数据预览和统计信息
    - CSV (.csv): 返回数据预览和统计信息
    - 文本文件 (.txt, .json): 返回文件内容
    - PDF: 返回提取的文本内容

    Args:
        file_path: 文件的 URL 路径，如 /api/v1/assets/user/thread/file.xlsx

    Returns:
        文件内容或数据预览的 JSON 格式字符串
    """
    try:
        # 从 URL 提取 object_key
        # URL 格式: /api/v1/assets/{object_key}
        if file_path.startswith("/api/v1/assets/"):
            object_key = file_path[len("/api/v1/assets/"):]
        elif file_path.startswith("http"):
            # 完整 URL，提取路径部分
            from urllib.parse import urlparse
            parsed = urlparse(file_path)
            path = parsed.path
            if "/api/v1/assets/" in path:
                object_key = path.split("/api/v1/assets/")[1]
            else:
                return json.dumps({"error": f"无法解析 URL: {file_path}"}, ensure_ascii=False)
        else:
            object_key = file_path
        
        logger.info("读取文件: object_key=%s", object_key)
        
        # 从 MinIO 获取文件
        asset_service = get_asset_service()
        response = asset_service.client.get_object(
            bucket_name=ai_config.MINIO_BUCKET_ASSETS,
            object_name=object_key
        )
        
        file_content = response.read()
        response.close()
        response.release_conn()
        
        # 获取文件信息
        stat = asset_service.client.stat_object(
            bucket_name=ai_config.MINIO_BUCKET_ASSETS,
            object_name=object_key
        )
        content_type = stat.content_type or ""
        file_size = stat.size
        
        # 根据文件类型处理
        file_ext = object_key.lower().split(".")[-1] if "." in object_key else ""
        
        # Excel 文件
        if file_ext in ["xlsx", "xls"] or "spreadsheet" in content_type or "excel" in content_type:
            return _read_excel(file_content, object_key)
        
        # CSV 文件
        elif file_ext == "csv" or "csv" in content_type:
            return _read_csv(file_content, object_key)
        
        # JSON 文件
        elif file_ext == "json" or "json" in content_type:
            return _read_json(file_content, object_key)
        
        # 文本文件
        elif file_ext == "txt" or "text/plain" in content_type:
            return _read_text(file_content, object_key)
        
        # PDF 文件
        elif file_ext == "pdf" or "pdf" in content_type:
            return _read_pdf(file_content, object_key)
        
        else:
            return json.dumps({
                "status": "unsupported",
                "message": f"暂不支持直接读取此文件类型: {file_ext} ({content_type})",
                "file_size": file_size,
                "object_key": object_key
            }, ensure_ascii=False)
            
    except Exception as e:
        logger.exception("读取文件失败: %s", e)
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _read_excel(content: bytes, object_key: str) -> str:
    """读取 Excel 文件。"""
    if pd is None:
        return json.dumps({"error": "pandas 未安装，无法读取 Excel 文件"}, ensure_ascii=False)
    
    try:
        # 读取 Excel
        df = pd.read_excel(io.BytesIO(content))
        
        # 构建响应
        result = {
            "status": "success",
            "file_type": "excel",
            "file_name": object_key.split("/")[-1],
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "preview": df.head(20).to_dict(orient="records"),  # 前20行预览
            "statistics": {}
        }
        
        # 添加数值列的统计信息
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            result["statistics"] = df[numeric_cols].describe().to_dict()
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({"error": f"读取 Excel 失败: {str(e)}"}, ensure_ascii=False)


def _read_csv(content: bytes, object_key: str) -> str:
    """读取 CSV 文件。"""
    if pd is None:
        return json.dumps({"error": "pandas 未安装，无法读取 CSV 文件"}, ensure_ascii=False)
    
    try:
        # 尝试不同编码
        for encoding in ["utf-8", "gbk", "gb2312", "latin1"]:
            try:
                df = pd.read_csv(io.BytesIO(content), encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            return json.dumps({"error": "无法解析 CSV 文件编码"}, ensure_ascii=False)
        
        result = {
            "status": "success",
            "file_type": "csv",
            "file_name": object_key.split("/")[-1],
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "preview": df.head(20).to_dict(orient="records"),
            "statistics": {}
        }
        
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            result["statistics"] = df[numeric_cols].describe().to_dict()
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({"error": f"读取 CSV 失败: {str(e)}"}, ensure_ascii=False)


def _read_json(content: bytes, object_key: str) -> str:
    """读取 JSON 文件。"""
    try:
        data = json.loads(content.decode("utf-8"))
        
        result = {
            "status": "success",
            "file_type": "json",
            "file_name": object_key.split("/")[-1],
            "content": data
        }
        
        # 如果是列表，添加长度信息
        if isinstance(data, list):
            result["length"] = len(data)
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({"error": f"读取 JSON 失败: {str(e)}"}, ensure_ascii=False)


def _read_text(content: bytes, object_key: str) -> str:
    """读取文本文件。"""
    try:
        # 尝试不同编码
        for encoding in ["utf-8", "gbk", "gb2312", "latin1"]:
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = content.decode("utf-8", errors="ignore")
        
        # 限制返回长度
        max_length = 10000
        if len(text) > max_length:
            text = text[:max_length] + f"\n\n... (截断，原文件共 {len(content)} 字节)"
        
        return json.dumps({
            "status": "success",
            "file_type": "text",
            "file_name": object_key.split("/")[-1],
            "content": text,
            "length": len(content)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"读取文本文件失败: {str(e)}"}, ensure_ascii=False)


def _read_pdf(content: bytes, object_key: str) -> str:
    """读取 PDF 文件。"""
    try:
        # 尝试使用 PyPDF2
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            text_parts = []
            for page in reader.pages[:20]:  # 最多读取前20页
                text_parts.append(page.extract_text() or "")
            text = "\n\n".join(text_parts)
            
            return json.dumps({
                "status": "success",
                "file_type": "pdf",
                "file_name": object_key.split("/")[-1],
                "total_pages": len(reader.pages),
                "extracted_pages": min(20, len(reader.pages)),
                "content": text[:10000] if len(text) > 10000 else text
            }, ensure_ascii=False)
            
        except ImportError:
            return json.dumps({
                "status": "error",
                "message": "PyPDF2 未安装，无法读取 PDF 文件。请使用 pip install PyPDF2 安装。",
                "file_name": object_key.split("/")[-1]
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({"error": f"读取 PDF 失败: {str(e)}"}, ensure_ascii=False)


# 导出工具列表
file_tools = [read_uploaded_file]
