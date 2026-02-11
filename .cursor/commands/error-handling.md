---
description: 为代码添加健壮的错误处理
---

> 参考规则: @dual-database

# 错误处理增强 (Error Handling)

为当前代码实现全面的错误处理，提高系统健壮性。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 为代码添加错误处理 | `/error-handling` ✅ |
| 安全漏洞审计 | `/security-audit` |
| 代码重构 | `/refactor` |

---

## 执行步骤

### 1. 识别风险点

- 潜在的失败点和边界情况
- 未处理的异常和错误条件
- 缺失的输入验证
- 异步操作和网络调用

### 2. 错误处理策略

**后端 (FastAPI)**:
```python
from fastapi import HTTPException
from app.core.exceptions import BusinessException

# 使用自定义异常
raise BusinessException(code="ITEM_NOT_FOUND", message="找不到指定项")

# 或使用 HTTP 异常
raise HTTPException(status_code=404, detail="资源不存在")
```

**前端 (React)**:
```typescript
try {
  const result = await api.fetchData();
} catch (error) {
  // 记录错误
  console.error('获取数据失败:', error);
  // 显示用户友好的错误信息
  toast.error('数据加载失败，请重试');
}
```

### 3. 检查清单

- [ ] 所有数据库操作都有错误处理
- [ ] 所有外部 API 调用都有超时和重试机制
- [ ] 输入验证完整（类型、范围、格式）
- [ ] 错误消息对用户友好
- [ ] 敏感信息不会泄露到错误消息中
- [ ] 日志记录了足够的调试信息

### 4. 恢复机制

- 对临时失败实现重试逻辑
- 为服务不可用添加降级方案
- 对外部依赖添加熔断机制

## 文档同步

> **强制要求**: 如果添加了新的错误码或改变了错误响应格式，必须更新文档。

**Checklist**:
- [ ] 新增错误码 -> 更新 `docs/API文档/接口文档.md`
- [ ] 错误处理逻辑变更 -> 更新相关架构文档

---
*使用 `/error-handling` 触发此流程。*
