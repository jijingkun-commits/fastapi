"""对话资产服务层（中文注释）。

核心功能：
- 上传文件到 MinIO 并保存元数据
- 生成预签名 URL
- 将 minio:// 协议替换为有效的预签名 URL
"""
import io
import logging
import mimetypes
import os
import re
from datetime import timedelta
from typing import Optional
from uuid import uuid4

from minio import Minio, S3Error
from sqlalchemy.orm import Session

from app.models.chat_asset import ChatAsset, AssetType
from app.schemas.chat_asset import ChatAssetCreate
from app.repositories import chat_assets_repository
from app.core import config as ai_config

logger = logging.getLogger(__name__)

# MinIO 协议前缀
MINIO_PROTOCOL = "minio://"
# 预签名 URL 有效期（小时）
PRESIGNED_URL_EXPIRES_HOURS = 1


class AssetService:
    """对话资产服务类。"""
    
    def __init__(self):
        self.client = self._build_client()
    
    @staticmethod
    def _build_client() -> Minio:
        """初始化 MinIO 客户端。"""
        # 检查必要配置
        if not all([ai_config.MINIO_ENDPOINT, ai_config.MINIO_ACCESS_KEY, ai_config.MINIO_SECRET_KEY]):
            logger.warning("MinIO 环境变量未完全配置，资产服务可能无法正常工作")
        
        return Minio(
            endpoint=ai_config.MINIO_ENDPOINT,
            access_key=ai_config.MINIO_ACCESS_KEY,
            secret_key=ai_config.MINIO_SECRET_KEY,
            secure=ai_config.MINIO_SECURE
        )
    
    def ensure_bucket(self, bucket_name: str = None) -> None:
        """确保 bucket 存在。"""
        target_bucket = bucket_name or ai_config.MINIO_BUCKET_ASSETS
        try:
            if not self.client.bucket_exists(target_bucket):
                self.client.make_bucket(target_bucket)
                logger.info(f"Bucket '{target_bucket}' 已创建")
        except S3Error as e:
            logger.error(f"创建 bucket 失败: {e}")
            raise
    
    def check_connection(self) -> dict:
        """检查 MinIO 连接健康状态。
        
        Returns:
            包含连接状态信息的字典：
            - healthy: 是否健康
            - endpoint: MinIO 端点地址
            - bucket: bucket 名称
            - bucket_exists: bucket 是否存在
            - error: 错误信息（如果有）
        """
        result = {
            "healthy": False,
            "endpoint": ai_config.MINIO_ENDPOINT,
            "bucket": ai_config.MINIO_BUCKET_ASSETS,
            "bucket_exists": False,
            "error": None
        }
        
        try:
            # 尝试检查 bucket 是否存在
            bucket_exists = self.client.bucket_exists(ai_config.MINIO_BUCKET_ASSETS)
            result["bucket_exists"] = bucket_exists
            result["healthy"] = True
            
            if bucket_exists:
                logger.info("✅ MinIO 连接正常: endpoint=%s, bucket=%s", 
                           ai_config.MINIO_ENDPOINT, ai_config.MINIO_BUCKET_ASSETS)
            else:
                logger.warning("⚠️ MinIO 连接正常但 bucket 不存在: %s", ai_config.MINIO_BUCKET_ASSETS)
                
        except Exception as e:
            result["error"] = str(e)
            logger.error("❌ MinIO 连接失败: endpoint=%s, error=%s", 
                        ai_config.MINIO_ENDPOINT, e, exc_info=True)
        
        return result

    
    def upload_and_save(
        self,
        db: Session,
        file_content: bytes,
        username: str,
        chat_id: str,
        qa_record_id: int,
        user_id: Optional[int] = None,
        asset_type: AssetType = AssetType.IMAGE,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> ChatAsset:
        """上传文件到 MinIO 并保存元数据到数据库。
        
        目录结构: {username}/{chat_id}/{asset_type}/{uuid}.ext
        
        Args:
            db: 数据库会话
            file_content: 文件内容（bytes）
            username: 用户名
            chat_id: 对话ID
            qa_record_id: 关联的问答记录ID
            user_id: 用户ID
            asset_type: 资产类型
            file_name: 原始文件名
            content_type: MIME 类型
            
        Returns:
            保存的 ChatAsset 对象
        """
        self.ensure_bucket()
        
        # 生成唯一文件名
        file_ext = ""
        if file_name:
            _, file_ext = os.path.splitext(file_name)
        elif content_type:
            file_ext = mimetypes.guess_extension(content_type) or ""
        
        uuid_name = f"{uuid4()}{file_ext}"
        
        # 构建 object_key: {username}/{chat_id}/{asset_type}/{uuid}.ext
        object_key = f"{username}/{chat_id}/{asset_type.value}s/{uuid_name}"
        
        # 上传到 MinIO
        file_stream = io.BytesIO(file_content)
        file_size = len(file_content)
        
        if not content_type:
            content_type = mimetypes.guess_type(file_name or uuid_name)[0] or "application/octet-stream"
        
        try:
            self.client.put_object(
                bucket_name=ai_config.MINIO_BUCKET_ASSETS,
                object_name=object_key,
                data=file_stream,
                length=file_size,
                content_type=content_type
            )
            logger.info(f"文件上传成功: {object_key}")
        except S3Error as e:
            logger.error(f"文件上传失败: {e}")
            raise
        
        # 保存元数据到数据库
        asset_data = ChatAssetCreate(
            qa_record_id=qa_record_id,
            chat_id=chat_id,
            user_id=user_id,
            asset_type=asset_type,
            object_key=object_key,
            file_name=file_name,
            file_size=file_size,
            content_type=content_type,
        )
        
        return chat_assets_repository.create_asset(db, asset_data)

    def register_existing_asset(
        self,
        db,
        object_key: str,
        chat_id: str,
        qa_record_id: int = 0,
        user_id: Optional[int] = None,
        asset_type: AssetType = AssetType.IMAGE,
        file_name: Optional[str] = None,
    ):
        """注册已存在的 MinIO 资产（补录元数据）。
        
        用于工具直接上传文件到 MinIO 后，补充记录到数据库。
        尝试获取文件大小和类型。
        """
        try:
            # 获取文件信息
            stat = self.client.stat_object(ai_config.MINIO_BUCKET_ASSETS, object_key)
            file_size = stat.size
            content_type = stat.content_type
        except Exception as e:
            logger.warning(f"获取 MinIO 文件信息失败 ({object_key}): {e}")
            file_size = 0
            content_type = "application/octet-stream"
        
        # 提取文件名
        if not file_name:
            file_name = os.path.basename(object_key)
            
        asset_data = ChatAssetCreate(
            qa_record_id=qa_record_id,
            chat_id=chat_id,
            user_id=user_id,
            asset_type=asset_type,
            object_key=object_key,
            file_name=file_name,
            file_size=file_size,
            content_type=content_type,
        )
        
        return chat_assets_repository.create_asset(db, asset_data)
    
    def generate_presigned_url(
        self,
        object_key: str,
        bucket_name: str = None,
        expires_hours: int = PRESIGNED_URL_EXPIRES_HOURS,
    ) -> str:
        """生成预签名 URL。
        
        Args:
            object_key: MinIO 对象路径
            bucket_name: bucket 名称
            expires_hours: 过期时间（小时）
            
        Returns:
            预签名 URL
        """
        if bucket_name is None:
            bucket_name = ai_config.MINIO_BUCKET_ASSETS
        """生成预签名 URL。
        
        Args:
            object_key: MinIO 对象路径
            bucket_name: bucket 名称
            expires_hours: 过期时间（小时）
            
        Returns:
            预签名 URL
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_key,
                expires=timedelta(hours=expires_hours)
            )
            return url
        except S3Error as e:
            logger.error(f"生成预签名 URL 失败: {e}")
            raise
    

    
    def get_proxy_url(self, object_key: str) -> str:
        """生成代理访问 URL（推荐使用）。
        
        通过后端 API 代理访问 MinIO，优点：
        - 权限校验：只有资产所有者可以访问
        - 永不过期：相比 presigned URL 更稳定
        - 可缓存：支持浏览器缓存
        
        Args:
            object_key: MinIO 对象路径，格式为 {user_id}/{thread_id}/{type}/{filename}
            
        Returns:
            代理 URL，如 /api/v1/assets/2/abc123/charts/xxx.png
        """
        return f"/api/v1/assets/{object_key}"
    



# 全局单例
_asset_service: Optional[AssetService] = None


def get_asset_service() -> AssetService:
    """获取 AssetService 单例。"""
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetService()
    return _asset_service
