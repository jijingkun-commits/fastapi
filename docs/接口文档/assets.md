# 资产 API

聊天资产（图片、图表）管理接口。

## 代理 RAGFlow 图片

### GET /api/v1/assets/proxy/ragflow/{image_id}

代理访问 RAGFlow 知识库中的图片。

**路径参数**:

| 参数 | 说明 |
|------|------|
| `image_id` | RAGFlow 图片 ID |

**响应**: 图片二进制数据

---

## 获取预签名 URL

### GET /api/v1/assets/{asset_id}/presigned

获取 MinIO 资产的预签名 URL。

**响应**:

```json
{
  "url": "https://minio.example.com/...",
  "expires_at": "2024-01-15T12:00:00"
}
```

---

## 获取资产列表

### GET /api/v1/assets

获取当前用户的资产列表。

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `chat_id` | string | 过滤指定对话 |
| `asset_type` | string | 类型: image/chart/export |

**响应**:

```json
[
  {
    "id": 1,
    "asset_type": "chart",
    "file_name": "sales_chart.png",
    "file_size": 12345,
    "content_type": "image/png",
    "created_at": "2024-01-15T10:00:00"
  }
]
```
