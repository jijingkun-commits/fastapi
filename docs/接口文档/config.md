# 配置 API

系统配置和 LLM 模型管理接口。

## 获取可用模型

### GET /api/v1/llm/models

获取可用的 LLM 模型列表。

**响应**:

```json
[
  {
    "model_code": "qwen-max",
    "model_name": "通义千问 Max",
    "provider": "qwen",
    "supports_thinking": true,
    "is_default": true
  },
  {
    "model_code": "deepseek-chat",
    "model_name": "DeepSeek Chat",
    "provider": "deepseek",
    "supports_thinking": true,
    "is_default": false
  }
]
```

---

## 获取系统配置

### GET /api/v1/config/{key}

获取系统配置值。

**响应**:

```json
{
  "key": "max_tokens",
  "value": "4096",
  "description": "最大 Token 数"
}
```

---

## 健康检查

### GET /api/v1/health

服务健康检查。

**响应**:

```json
{
  "status": "healthy",
  "database": "connected",
  "minio": "connected"
}
```
