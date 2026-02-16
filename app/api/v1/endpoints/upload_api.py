"""图片上传 API（中文注释）。

提供用户图片上传接口，上传到 MinIO 后返回代理 URL。
用于聊天时发送图片给 AI 分析。
"""
import logging
import uuid
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from minio.error import S3Error

from app.api.deps import get_current_user_optional
from app.models.user import User
from app.models.chat_asset import AssetType
from app.db.session import get_db_context
from app.services.asset_service import get_asset_service
from app.core import config as ai_config

router = APIRouter(prefix="/upload", tags=["upload"])
logger = logging.getLogger("api.upload")

# 允许的文件类型（图片 + 文档）
ALLOWED_CONTENT_TYPES = {
    # 图片类型
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    # Excel 类型
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    # CSV
    "text/csv": ".csv",
    "application/csv": ".csv",
    # PDF
    "application/pdf": ".pdf",
    # Word 类型
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    # 文本类型
    "text/plain": ".txt",
    # JSON
    "application/json": ".json",
}

# 最大文件大小（50MB）
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("")
async def upload_image(
    file: UploadFile = File(...),
    thread_id: Optional[str] = None,
    current_user: User = Depends(get_current_user_optional),
):
    """上传图片到 MinIO。
    
    前端上传图片后，返回代理 URL 供聊天时使用。
    
    Args:
        file: 上传的图片文件
        thread_id: 可选，对话 ID（用于组织存储路径）
        current_user: 当前用户
        
    Returns:
        {
            "url": "/api/v1/assets/...",  # 代理 URL
            "object_key": "...",           # MinIO 对象路径
            "file_name": "...",            # 原始文件名
            "content_type": "image/jpeg"   # 内容类型
        }
        
    Raises:
        400: 文件类型不支持或文件过大
        500: 上传失败
    """
    # 验证文件类型
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件类型: {content_type}。支持: 图片(JPEG/PNG/GIF/WEBP)、文档(Excel/CSV/PDF/Word/TXT/JSON)"
        )
    
    # 读取文件内容
    content = await file.read()
    
    # 验证文件大小
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持 {MAX_FILE_SIZE // 1024 // 1024}MB"
        )
    
    # 生成唯一文件名
    ext = ALLOWED_CONTENT_TYPES[content_type]
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    
    # 构建存储路径
    user_id = str(current_user.id) if current_user else "anonymous"
    thread_prefix = thread_id or "uploads"
    object_key = f"{user_id}/{thread_prefix}/images/{unique_name}"
    
    try:
        asset_service = get_asset_service()
        
        # 上传到 MinIO
        asset_service.client.put_object(
            bucket_name=ai_config.MINIO_BUCKET_ASSETS,
            object_name=object_key,
            data=BytesIO(content),
            length=len(content),
            content_type=content_type,
        )

        # 补录资产元数据，保持上传文件与工具生成文件一致的管理方式
        try:
            asset_type = AssetType.IMAGE if content_type.startswith("image/") else AssetType.ATTACHMENT
            with get_db_context() as db:
                asset_service.register_existing_asset(
                    db=db,
                    object_key=object_key,
                    chat_id=thread_prefix,
                    user_id=current_user.id if current_user else None,
                    asset_type=asset_type,
                    file_name=file.filename,
                )
        except Exception as db_error:
            logger.warning("上传成功但资产元数据补录失败: %s", db_error)
        
        logger.info("图片上传成功: %s (%d bytes)", object_key, len(content))
        
        # 返回代理 URL
        proxy_url = f"/api/v1/assets/{object_key}"
        
        return {
            "url": proxy_url,
            "object_key": object_key,
            "file_name": file.filename,
            "content_type": content_type,
            "size": len(content),
        }
        
    except S3Error as e:
        logger.error("MinIO 上传失败: %s", e)
        raise HTTPException(status_code=500, detail="图片上传失败")
    except Exception as e:
        logger.exception("上传图片时发生错误: %s", e)
        raise HTTPException(status_code=500, detail="服务器内部错误")
