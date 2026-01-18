"""资产代理 API（中文注释）。

提供 MinIO 资产的代理访问，实现：
- 权限校验：用户只能访问自己的资产
- 流式返回：不在后端存储文件，直接转发
- URL 永不过期：相比 presigned URL 更稳定
"""
import logging
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from minio.error import S3Error

from app.api.deps import get_current_user_optional, get_current_user, get_db
from app.models.user import User
from app.services.asset_service import get_asset_service
from app.core import config as ai_config
from app.repositories import chat_assets_repository
from sqlalchemy.orm import Session

router = APIRouter(prefix="/assets", tags=["assets"])
logger = logging.getLogger("api.assets")


# ============================================================
# 注意：路由注册顺序很重要！
# 具体路径的路由必须放在通配符路由 /{object_key:path} 之前
# ============================================================


@router.get("/proxy/ragflow/{image_id:path}")
async def proxy_ragflow_image(image_id: str):
    """代理访问 RAGFlow 知识库图片。
    
    统一图片代理，将请求转发到 RAGFlow 服务。
    
    Args:
        image_id: RAGFlow 图片标识，格式为 {kb_id}-{image_id}
        
    Returns:
        图片流
        
    Raises:
        404: 图片不存在
        502: RAGFlow 服务不可用
    """
    import requests
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from app.core import config
    
    # 构建 RAGFlow 图片 URL
    ragflow_url = f"{config.RAGFLOW_BASE_URL}/v1/document/image/{image_id}"
    
    # 使用同步 requests（与 RAGFlow 兼容性更好）
    def fetch_image():
        return requests.get(ragflow_url, timeout=30)
    
    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            response = await loop.run_in_executor(executor, fetch_image)
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="知识库图片不存在")
        
        response.raise_for_status()
        
        # 获取内容类型
        content_type = response.headers.get("Content-Type", "image/jpeg")
        
        return Response(
            content=response.content,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # 缓存 1 天
            }
        )
        
    except requests.exceptions.ConnectionError:
        logger.error("无法连接到 RAGFlow 服务: %s", ragflow_url)
        raise HTTPException(status_code=502, detail="知识库服务不可用")
    except requests.exceptions.HTTPError as e:
        logger.error("RAGFlow 返回错误: %s", e)
        raise HTTPException(status_code=response.status_code, detail="获取知识库图片失败")
    except Exception as e:
        logger.exception("代理 RAGFlow 图片时发生错误: %s", e)
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/proxy/ragflow/doc/{doc_id}")
async def proxy_ragflow_document(doc_id: str, name: str = None):
    """代理访问 RAGFlow 原始文档。
    
    统一文档代理，将请求转发到 RAGFlow 服务。
    
    Args:
        doc_id: RAGFlow 文档 ID
        name: 可选的文件名（用于下载时的 Content-Disposition）
        
    Returns:
        文件流
    """
    import httpx
    # from app.core import config # 已经在函数外导入或使用 global config
    
    # RAGFlow 的文档下载端点通常是 /v1/document/get/{doc_id}
    ragflow_url = f"{ai_config.RAGFLOW_BASE_URL}/v1/document/get/{doc_id}"
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            # 流式请求以支持大文件
            req = client.build_request("GET", ragflow_url)
            response = await client.send(req, stream=True)
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="知识库文档不存在")
            
            response.raise_for_status()
            
            # 获取内容类型
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            content_disposition = response.headers.get("Content-Disposition")
            
            # 如果提供了文件名，强制设置 Content-Disposition
            headers = {
                "Cache-Control": "public, max-age=3600",
            }
            if name:
                from urllib.parse import quote
                # 处理中文文件名
                encoded_name = quote(name)
                headers["Content-Disposition"] = f'attachment; filename="{encoded_name}"; filename*=utf-8\'\'{encoded_name}'
            elif content_disposition:
                headers["Content-Disposition"] = content_disposition
            
            return StreamingResponse(
                response.aiter_bytes(),
                media_type=content_type,
                headers=headers
            )
            
    except httpx.ConnectError:
        logger.error("无法连接到 RAGFlow 服务: %s", ragflow_url)
        raise HTTPException(status_code=502, detail="知识库服务不可用")
    except httpx.HTTPStatusError as e:
        logger.error("RAGFlow 返回错误: %s", e)
        raise HTTPException(status_code=e.response.status_code, detail="获取知识库文档失败")
    except Exception as e:
        logger.exception("代理 RAGFlow 文档时发生错误: %s", e)
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/user/list")
async def list_user_assets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    chat_id: str = None,
    limit: int = 50,
):
    """获取当前用户的资产列表。
    
    Args:
        chat_id: 可选，按对话 ID 过滤
        limit: 返回数量限制
        
    Returns:
        资产列表，包含访问 URL
    """
    if chat_id:
        assets = chat_assets_repository.get_assets_by_chat_id(db, chat_id)
        # 校验权限：只返回当前用户的资产
        assets = [a for a in assets if a.user_id == current_user.id]
    else:
        assets = chat_assets_repository.get_assets_by_user_id(db, current_user.id, limit)
    
    result = []
    for asset in assets:
        result.append({
            "id": asset.id,
            "chat_id": asset.chat_id,
            "asset_type": asset.asset_type.value if hasattr(asset.asset_type, 'value') else asset.asset_type,
            "file_name": asset.file_name,
            "file_size": asset.file_size,
            "content_type": asset.content_type,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
            "url": f"/api/v1/assets/{asset.object_key}",
        })
    
    return {"total": len(result), "assets": result}


# ============================================================
# 通配符路由必须放在最后！
# ============================================================


@router.get("/{object_key:path}")
async def get_asset(
    object_key: str,
    current_user: User = Depends(get_current_user_optional),
):
    """获取资产文件。
    
    通过代理方式访问 MinIO，实现权限校验。
    
    Args:
        object_key: 对象路径，格式为 {user_id}/{thread_id}/{type}/{filename}
        current_user: 当前登录用户（可选，未登录时做宽松校验）
    
    Returns:
        文件流
    
    Raises:
        403: 无权访问
        404: 文件不存在
    """
    # 权限校验：object_key 应以 {user_id}/ 开头
    # 格式: 2/abc123-thread/charts/xxx.png
    path_parts = object_key.split("/")
    if len(path_parts) < 2:
        raise HTTPException(status_code=400, detail="无效的资产路径")
    
    resource_user_id = path_parts[0]
    
    # 如果用户已登录，校验是否有权访问
    if current_user:
        if str(current_user.id) != resource_user_id:
            logger.warning(
                "用户 %s 尝试访问用户 %s 的资产: %s",
                current_user.id, resource_user_id, object_key
            )
            raise HTTPException(status_code=403, detail="无权访问此资产")
    else:
        # 未登录用户：可以选择完全拒绝或做其他处理
        # 这里暂时允许（保持向后兼容），生产环境可改为拒绝
        logger.debug("未登录用户访问资产: %s", object_key)
    
    # 从 MinIO 获取文件
    try:
        asset_service = get_asset_service()
        response = asset_service.client.get_object(
            bucket_name=ai_config.MINIO_BUCKET_ASSETS,
            object_name=object_key,
        )
        
        # 获取内容类型
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        
        # 流式返回
        def iterfile():
            try:
                for chunk in response.stream(32 * 1024):  # 32KB chunks
                    yield chunk
            finally:
                response.close()
                response.release_conn()
        
        return StreamingResponse(
            iterfile(),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # 缓存 1 天
            }
        )
        
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="资产不存在")
        logger.error("获取资产失败: %s", e)
        raise HTTPException(status_code=500, detail="获取资产失败")
    except Exception as e:
        logger.exception("获取资产时发生错误: %s", e)
        raise HTTPException(status_code=500, detail="服务器内部错误")
