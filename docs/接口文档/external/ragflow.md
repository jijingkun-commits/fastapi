# RAGFlow API 集成

项目集成了 RAGFlow 知识库系统用于文档检索。

## 配置

在 `.env.dev` 中配置：

```bash
RAGFLOW_BASE_URL=http://localhost:9380
RAGFLOW_API_URL=http://localhost:9380/api/v1
RAGFLOW_API_KEY=ragflow-xxx
RAGFLOW_DATASET_IDS=dataset1,dataset2
```

---

## 使用方式

### AI 工具调用

通过 `knowledge_search` 工具自动检索：

```python
# AI 自动调用，无需手动处理
# 用户输入："在知识库里搜索关于销售的文档"
# AI 调用 -> knowledge_search(query="销售")
```

### 检索参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `RAGFLOW_SIMILARITY_THRESHOLD` | 0.2 | 相似度阈值 |
| `RAGFLOW_TOP_K` | 5 | 返回数量 |
| `RAGFLOW_VECTOR_WEIGHT` | 0.6 | 向量权重 |

---

## API 接口

### 检索文档

**内部调用路径**: `app/ai/tools/ragflow_tool.py`

```python
POST {RAGFLOW_API_URL}/retrieval
Headers:
  Authorization: Bearer {RAGFLOW_API_KEY}
Body:
  {
    "dataset_ids": ["xxx"],
    "question": "查询内容",
    "top_n": 5,
    "similarity_threshold": 0.2
  }
```

### 图片代理

知识库图片通过本地代理访问：

```
GET /api/v1/assets/proxy/ragflow/{image_id}
```
