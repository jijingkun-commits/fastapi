# Refactor Report: document_memory_embedding_wrapper_retirement

- 日期：2026-03-12
- 主题：移除文档记忆向量补偿服务旧包装壳 `process_pending_chunks`
- 范围：`app/services/document_memory_embedding_service.py`、`app/api/v1/endpoints/memory_admin_api.py`、`scripts/memory/rebuild_document_embeddings.py`、相关定向测试与文档锚点
- 结论：服务层唯一入口收口到 `compensate_pending_embeddings`，不再保留兼容转发壳
- 最佳实践依据：删除显式 dead code / wrapper，保留单一 canonical path，并用最小定向回归验证真实行为
- obsolete_paths：`process_pending_chunks` 函数、旧函数名测试锚点、旧实施文档符号
- retained_paths：`compensate_pending_embeddings`、memory-admin API、重建脚本、集成补偿回归
- single_entry_owner：`app/services/document_memory_embedding_service.py::compensate_pending_embeddings`
- 变更摘要：删除 1 个兼容包装壳；后台 API 与脚本改为直连 canonical 入口；单测与集成测试改为锚定真实入口；实施文档与架构文档同步收口
- 行数预算：运行时代码与测试净删除；新增仅为审计报告
- 验证计划：`tests/unit/test_document_memory_embedding_service.py`、`tests/integration/test_document_memory_embedding_compensation.py`、`tests/api/test_memory_admin_api.py`
- 风险：若仍有仓外脚本直接 import 旧函数，会在运行时暴露 `AttributeError`
- 回滚点：如发现隐藏依赖，可临时恢复别名或先在调用方完成替换后再删
