"""测试 MinIO 连接和上传功能。"""
import os
from app.services.asset_service import get_asset_service

def test_minio_connection():
    print("🚀 开始测试 MinIO 连接...")
    
    # 强制重新加载环境变量（模拟 app 启动）
    # 注意：这里仅用于测试脚本，实际 app 需要重启
    from app.core import config
    print(f"当前配置 Endpoint: {config.MINIO_ENDPOINT}")
    print(f"当前配置 Secure: {config.MINIO_SECURE}")
    print(f"当前配置 AccessKey: {config.MINIO_ACCESS_KEY}")
    
    service = get_asset_service()
    
    try:
        # 1. 测试列出 buckets
        buckets = service.client.list_buckets()
        print(f"✅ 连接成功！发现 {len(buckets)} 个 bucket:")
        for b in buckets:
            print(f"  - {b.name}")
            
        # 2. 测试 Bucket 存在性
        service.ensure_bucket("chat-assets")
        print("✅ ensure_bucket('chat-assets') 通过")
        
        # 3. 测试预签名 URL 生成
        test_key = "admin/test_connection.txt"
        url = service.generate_presigned_url(test_key)
        print(f"✅ 生成预签名 URL 成功: {url.split('?')[0]}?...")
        
    except Exception as e:
        print(f"❌ MinIO 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_minio_connection()
