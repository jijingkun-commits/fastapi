---
description: 📖 生成 API 文档：OpenAPI/Swagger 格式，包含示例和错误码
---

> 参考规则: @dual-database

# 📖 生成 API 文档 (API Docs)

为当前端点生成全面的 API 文档，符合 OpenAPI/Swagger 规范。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 文档结构

### 1. API 概述
- 服务描述和用途
- Base URL 和版本信息
- 认证方式
- 限流策略

### 2. 端点文档

每个端点需包含：

```markdown
## POST /api/v1/chat/send

发送聊天消息

### 请求

**Headers**
| Header | Type | Required | Description |
|--------|------|----------|-------------|
| Authorization | string | Yes | Bearer token |

**Body**
```json
{
  "conversation_id": "string",
  "content": "string",
  "role": "user"
}
```

### 响应

**200 OK**
```json
{
  "id": "msg_123",
  "content": "回复内容",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**错误码**
| Code | Description |
|------|-------------|
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 会话不存在 |
| 500 | 服务器错误 |
```

### 3. 数据模型

```markdown
## Message

聊天消息对象

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | 消息唯一标识 |
| conversation_id | string | Yes | 所属会话 ID |
| role | enum | Yes | user/assistant/system |
| content | string | Yes | 消息内容 |
| created_at | datetime | Yes | 创建时间 |
```

### 4. 使用示例

```markdown
## cURL 示例

```bash
curl -X POST 'https://api.example.com/v1/chat/send' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "conversation_id": "conv_123",
    "content": "你好"
  }'
```

## Python 示例

```python
import requests

response = requests.post(
    'https://api.example.com/v1/chat/send',
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
    json={'conversation_id': 'conv_123', 'content': '你好'}
)
```
```

## FastAPI 自动文档增强

对于本项目（FastAPI），确保：

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

class MessageCreate(BaseModel):
    """创建消息的请求体"""
    conversation_id: str = Field(..., description="会话 ID")
    content: str = Field(..., description="消息内容", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv_123",
                "content": "你好，请帮我分析一下数据"
            }
        }

@router.post(
    "/send",
    response_model=MessageResponse,
    summary="发送消息",
    description="向指定会话发送一条新消息",
    responses={
        400: {"description": "请求参数错误"},
        404: {"description": "会话不存在"},
    }
)
async def send_message(data: MessageCreate):
    ...
```

## 文档检查清单

- [ ] API 概述完整（认证、版本、Base URL）
- [ ] 所有端点已文档化
- [ ] 请求/响应 schema 完整
- [ ] 错误码和描述清晰
- [ ] 包含实际可用的示例
- [ ] 数据模型关系清晰

## 输出位置

生成的文档应放置于：
- `docs/API文档/接口文档.md`
- 或直接增强 FastAPI 的 docstring

---
*提示：使用 `/api-docs` 触发此工作流。可指定特定端点或模块。*
