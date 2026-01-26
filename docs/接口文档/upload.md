# 上传 API

文件上传接口。

## 上传文件

### POST /api/v1/upload

上传文件到 MinIO 存储。

**请求**: `multipart/form-data`

| 参数 | 类型 | 说明 |
|------|------|------|
| `file` | file | 文件 |
| `thread_id` | string | 关联对话 ID (可选) |

**响应**:

```json
{
  "file_id": "abc123",
  "file_name": "image.png",
  "file_size": 12345,
  "content_type": "image/png",
  "url": "/api/v1/assets/abc123/presigned"
}
```

**支持的文件类型**:

| 类型 | MIME |
|------|------|
| 图片 | image/png, image/jpeg, image/gif, image/webp |
| 文档 | application/pdf, text/plain |
| 表格 | application/vnd.ms-excel, text/csv |

**大小限制**: 10MB
