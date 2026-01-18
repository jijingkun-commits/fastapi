#!/usr/bin/env python3
"""
MinIO Bucket 初始化脚本

此脚本用于初始化 MinIO 的 bucket 结构和生命周期规则：

├── chat-assets/           # 对话资产（默认 30 天后自动删除）
│   └── {user_id}/
│       └── {thread_id 或 uploads}/
│           └── images/    # 用户上传的图片、文档、图表等
│               └── {uuid}.{ext}

路径格式: chat-assets/{user_id}/{thread_id 或 uploads}/images/{filename}
文件名格式: {uuid12}.{ext}

使用方法:
    python init_minio_buckets.py

环境变量 (可选):
    MINIO_ENDPOINT          - MinIO 服务地址 (默认: http://localhost:19000)
    MINIO_ACCESS_KEY        - 访问密钥
    MINIO_SECRET_KEY        - 秘密密钥
    MINIO_USE_SSL           - 是否使用 SSL (默认: false)
    MINIO_ASSETS_EXPIRE_DAYS - 资产文件过期天数 (默认: 30，0 表示永不过期)
"""

import os
import sys
from io import BytesIO
from urllib.parse import urlparse

try:
    from minio import Minio
    from minio.error import S3Error
    from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration
except ImportError:
    print("错误: 请先安装 minio 库")
    print("运行: pip install minio")
    sys.exit(1)


# ========== 配置 ==========

# MinIO 连接配置
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:19000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "12345678")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

# 文件过期天数（0 表示不过期）
ASSETS_EXPIRE_DAYS = int(os.getenv("MINIO_ASSETS_EXPIRE_DAYS", "30"))

# Bucket 配置
# 注意：子目录会在运行时根据 user_id/thread_id 动态创建，无需预创建
BUCKETS_CONFIG = {
    "chat-assets": {
        "description": "对话资产（图表、图片、上传文档）",
        "folders": [],  # 目录在运行时动态创建: {user_id}/{thread_id 或 uploads}/images/
        "lifecycle_days": ASSETS_EXPIRE_DAYS,  # 默认 30 天后自动删除
    },
}


def parse_endpoint(endpoint: str) -> tuple[str, bool]:
    """
    解析 MinIO 端点地址
    
    Args:
        endpoint: MinIO 端点 URL (例如: http://localhost:19000)
    
    Returns:
        tuple: (host:port, use_ssl)
    """
    parsed = urlparse(endpoint)
    host = parsed.netloc or parsed.path
    use_ssl = parsed.scheme == "https"
    return host, use_ssl


def create_minio_client() -> Minio:
    """创建 MinIO 客户端"""
    host, ssl_from_url = parse_endpoint(MINIO_ENDPOINT)
    # 优先使用环境变量中的 SSL 配置，如果没有则从 URL 推断
    use_ssl = MINIO_USE_SSL or ssl_from_url
    
    print(f"📡 连接到 MinIO: {host} (SSL: {use_ssl})")
    
    client = Minio(
        endpoint=host,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=use_ssl,
    )
    
    return client


def create_bucket_if_not_exists(client: Minio, bucket_name: str, description: str) -> bool:
    """
    如果 bucket 不存在则创建
    
    Args:
        client: MinIO 客户端
        bucket_name: Bucket 名称
        description: Bucket 描述
    
    Returns:
        bool: True 表示新创建，False 表示已存在
    """
    try:
        if client.bucket_exists(bucket_name):
            print(f"  ✅ Bucket '{bucket_name}' 已存在 - {description}")
            return False
        
        client.make_bucket(bucket_name)
        print(f"  🆕 Bucket '{bucket_name}' 创建成功 - {description}")
        return True
        
    except S3Error as e:
        print(f"  ❌ 创建 bucket '{bucket_name}' 失败: {e}")
        raise


def set_lifecycle_rules(client: Minio, bucket_name: str, expire_days: int) -> bool:
    """
    设置 bucket 的生命周期规则（文件自动过期删除）
    
    Args:
        client: MinIO 客户端
        bucket_name: Bucket 名称
        expire_days: 文件过期天数（0 表示不设置）
    
    Returns:
        bool: True 表示设置成功，False 表示跳过
    """
    if expire_days <= 0:
        print(f"    ⏭️  Bucket '{bucket_name}' 不设置生命周期规则（永不过期）")
        return False
    
    try:
        # 创建生命周期规则：所有对象在指定天数后过期删除
        config = LifecycleConfig(
            [
                Rule(
                    rule_id="auto-expire-rule",
                    status="Enabled",
                    expiration=Expiration(days=expire_days),
                ),
            ],
        )
        
        client.set_bucket_lifecycle(bucket_name, config)
        print(f"    ⏰ Bucket '{bucket_name}' 生命周期规则已设置: {expire_days} 天后自动删除")
        return True
        
    except S3Error as e:
        print(f"    ❌ 设置生命周期规则失败: {e}")
        raise


def create_folder_placeholder(client: Minio, bucket_name: str, folder_path: str) -> bool:
    """
    创建文件夹占位符 (MinIO 中文件夹通过以 / 结尾的空对象表示)
    
    Args:
        client: MinIO 客户端
        bucket_name: Bucket 名称
        folder_path: 文件夹路径 (应以 / 结尾)
    
    Returns:
        bool: True 表示新创建，False 表示已存在
    """
    # 确保路径以 / 结尾
    if not folder_path.endswith("/"):
        folder_path += "/"
    
    try:
        # 检查是否已存在
        # Check if exists
        is_exist = False
        for _ in client.list_objects(bucket_name, prefix=folder_path):
            is_exist = True
            break
        
        if is_exist:
            print(f"    📁 文件夹 '{folder_path}' 已存在")
            return False
        
        # 创建空对象作为文件夹占位符
        # 使用 .gitkeep 文件作为占位符，这是常见做法
        placeholder_path = folder_path + ".gitkeep"
        content = BytesIO(b"# This file ensures the folder exists in MinIO\n")
        client.put_object(
            bucket_name,
            placeholder_path,
            content,
            length=content.getbuffer().nbytes,
            content_type="text/plain",
        )
        print(f"    📁 文件夹 '{folder_path}' 创建成功")
        return True
        
    except S3Error as e:
        print(f"    ❌ 创建文件夹 '{folder_path}' 失败: {e}")
        raise


def init_minio_buckets():
    """初始化 MinIO bucket 结构"""
    print("=" * 50)
    print("🚀 MinIO Bucket 初始化脚本")
    print("=" * 50)
    print()
    
    # 创建客户端
    try:
        client = create_minio_client()
    except Exception as e:
        print(f"❌ 无法连接到 MinIO: {e}")
        sys.exit(1)
    
    print()
    print("📦 开始创建 Buckets...")
    print()
    
    stats = {
        "buckets_created": 0,
        "buckets_existed": 0,
        "folders_created": 0,
        "folders_existed": 0,
        "lifecycle_set": 0,
        "errors": 0,
    }
    
    for bucket_name, config in BUCKETS_CONFIG.items():
        description = config["description"]
        folders = config["folders"]
        lifecycle_days = config.get("lifecycle_days", 0)
        
        try:
            # 创建 bucket
            if create_bucket_if_not_exists(client, bucket_name, description):
                stats["buckets_created"] += 1
            else:
                stats["buckets_existed"] += 1
            
            # 设置生命周期规则
            try:
                if set_lifecycle_rules(client, bucket_name, lifecycle_days):
                    stats["lifecycle_set"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"    ⚠️ 设置生命周期规则失败: {e}")
            
            # 创建子文件夹
            for folder in folders:
                try:
                    if create_folder_placeholder(client, bucket_name, folder):
                        stats["folders_created"] += 1
                    else:
                        stats["folders_existed"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    print(f"    ⚠️ 跳过文件夹 '{folder}': {e}")
            
        except Exception as e:
            stats["errors"] += 1
            print(f"  ⚠️ 处理 bucket '{bucket_name}' 时出错: {e}")
    
    # 打印统计信息
    print()
    print("=" * 50)
    print("📊 初始化完成!")
    print("=" * 50)
    print(f"  Buckets 新创建: {stats['buckets_created']}")
    print(f"  Buckets 已存在: {stats['buckets_existed']}")
    print(f"  生命周期规则: {stats['lifecycle_set']} 个已设置")
    print(f"  文件夹 新创建: {stats['folders_created']}")
    print(f"  文件夹 已存在: {stats['folders_existed']}")
    if stats["errors"] > 0:
        print(f"  ⚠️ 错误数量: {stats['errors']}")
    print()
    
    # 显示最终的 bucket 结构
    print("📂 最终 Bucket 结构:")
    print()
    for bucket_name, config in BUCKETS_CONFIG.items():
        print(f"  ├── {bucket_name}/")
        description = config["description"]
        print(f"  │   # {description}")
        for folder in config["folders"]:
            print(f"  │   ├── {folder}")
        print()
    
    return stats["errors"] == 0


if __name__ == "__main__":
    success = init_minio_buckets()
    sys.exit(0 if success else 1)
