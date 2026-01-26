# LLM 提供商

项目支持多个 LLM 提供商，通过统一接口调用。

## 支持的提供商

| 提供商 | 模型示例 | API 兼容 |
|--------|----------|----------|
| OpenAI | gpt-4o, gpt-4-turbo | OpenAI |
| Qwen | qwen-max, qwen-plus | OpenAI 兼容 |
| DeepSeek | deepseek-chat | OpenAI 兼容 |

---

## 配置方式

### 环境变量

```bash
MODEL_PROVIDER=qwen
MODEL_NAME=qwen-max
MODEL_API_KEY=sk-xxx
MODEL_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 数据库配置（推荐）

通过 `t_llm_provider` 和 `t_llm_model` 表管理：

```sql
INSERT INTO t_llm_provider (name, api_base, api_key, is_active)
VALUES ('qwen', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'sk-xxx', true);

INSERT INTO t_llm_model (provider_id, model_code, model_name, is_default)
VALUES (1, 'qwen-max', '通义千问 Max', true);
```

---

## 代码使用

```python
from app.ai.llm_util import get_llm, get_llm_by_model_id

# 获取默认模型
llm = get_llm()

# 获取指定模型
llm = get_llm_by_model_id("deepseek-chat")

# 启用深度思考
llm = get_llm(enable_thinking=True)
```

---

## 特性支持

| 特性 | OpenAI | Qwen | DeepSeek |
|------|--------|------|----------|
| 流式输出 | ✅ | ✅ | ✅ |
| 工具调用 | ✅ | ✅ | ✅ |
| 深度思考 | ❌ | ✅ | ✅ |
| 多模态 | ✅ | ✅ | ❌ |
