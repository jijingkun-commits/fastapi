# RAG 与知识库集成设计详解

> 更新时间：2026-03-13
> **状态**: 已发布
> **验证日期**: 2026-01-21
> **代码对应**: `app/ai/tools/ragflow_tool.py`, `app/api/v1/endpoints/assets_api.py`


## 文档导航

- 全局架构入口：[系统总览](系统总览.md)
- AI 核心设计：[AI模块设计](AI模块设计.md)
- 后端分层设计：[后端架构](后端架构.md)
- 前端分层设计：[前端架构](前端架构.md)
- 数据模型与双库：[数据库设计](数据库设计.md)
- 对外接口定义：[接口文档](../../API文档/接口文档.md)
- 需求来源总览：[系统需求](../../产品文档/系统需求.md)

## 1. 概述

本系统集成 RAGFlow 作为核心知识库引擎，支持企业文档的语义检索。重点解决了**RAG 检索结果中的图片显示问题**，实现了从 RAGFlow 内部图片 ID 到前端可访问 URL 的自动转换代理。

## 2. 核心流程

### 2.1 知识检索 (`knowledge_search` 工具)

当 Agent 决定查询知识库时：

1.  调用 `ragflow_tool.py/knowledge_search`。
2.  工具向 RAGFlow API 发起检索请求。
3.  **结果解析**:
    *   解析返回的 Chunks。
    *   提取 Chunk 中的 `image_id`。
    *   **映射转换**: 生成图片映射表 `{index: image_url}`，其中 `image_url` 转换为本地代理地址 `/api/v1/assets/proxy/ragflow/{image_id}`。
4.  **Prompt 格式化**:
    *   文本中插入 `[IMG-N]` 占位符。
    *   通过隐藏注释 `<!--KB_IMAGES:...-->` 将图片映射表传递给上层（或直接处理）。

### 2.2 图片/文档代理 (Assets API)

为了解决 MinIO 桶权限（通常为 Private）和跨域问题，后端提供了统一代理：

1.  **图片代理**: `GET /api/v1/assets/proxy/ragflow/{image_id}`
    *   后端请求 `RAGFLOW_BASE_URL/v1/document/image/{image_id}`。
    *   流式转发响应给前端。
    *   添加缓存头 `Cache-Control: public, max-age=86400` 优化加载。

2.  **文档下载代理**: `GET /api/v1/assets/proxy/ragflow/doc/{doc_id}`
    *   支持源文档下载，自动处理 Content-Disposition 以支持中文文件名。

## 3. 实现细节差异

实际实现与早期设计方案（Service 层处理）略有不同，逻辑被封装在 Tool 层：

*   **设计方案**: 在 `RAGService` 中统一处理 Chunks 并替换 URL。
*   **实际代码**: 在 `ragflow_tool.py` 中处理。工具直接返回经过格式化的文本（含占位符），让 LLM 在生成的回答中引用这些占位符。

这种方式的优势是解耦了 Service 层与特定工具的逻辑，Tool 自治性更强。

## 4. 配置项

*   `RAGFLOW_API_URL`: RAGFlow 服务地址。
*   `RAGFLOW_API_KEY`: 认证密钥。
*   `RAGFLOW_DATASET_IDS`: 默认知识库 ID 列表。
*   `RAGFLOW_SIMILARITY_THRESHOLD`: 相似度阈值。
