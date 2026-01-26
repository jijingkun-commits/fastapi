# MinIO 存储

项目使用 MinIO 作为对象存储服务，存储聊天资产（图片、图表、导出文件）。

## 配置

在 `.env.dev` 中配置：

```bash
MINIO_ENDPOINT=localhost:19000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=12345678
MINIO_SECURE=false
MINIO_BUCKET_ASSETS=chat-assets
```

---

## Bucket 结构

| Bucket | 用途 |
|--------|------|
| `chat-assets` | 聊天资产（图表、导出） |
| `uploads` | 用户上传文件 |

---

## 使用方式

### 上传资产

**文件**: `app/core/storage.py`

```python
from app.core.storage import upload_to_minio

# 上传文件
object_key = upload_to_minio(
    file_content=data,
    file_name="chart.png",
    content_type="image/png",
    bucket="chat-assets"
)
```

### 获取预签名 URL

```python
from app.core.storage import get_presigned_url

url = get_presigned_url(object_key, expires=3600)
```

---

## 生命周期策略

资产默认 30 天后过期，在 `install/scripts/init_minio_buckets.py` 中配置：

```python
MINIO_ASSETS_EXPIRE_DAYS = 30
```
