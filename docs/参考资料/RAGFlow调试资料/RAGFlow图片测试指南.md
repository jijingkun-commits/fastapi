# RAGFlow 图片调试测试指南

## 已添加的调试日志

### 1. 工具层（ragflow_tool.py）
```
RAGFlow 检索完成: chunks=X, 结果长度=Y, 包含图片=Z
knowledge_search 工具返回值（前 1000 字符）:
【0】内容...
   📄 来源: xxx.docx | 相关度: 75%
   ![xxx.docx](/api/v1/assets/proxy/ragflow/xxx-yyy)
```

### 2. Agent 层（multi_agent_graph.py）
```
[supervisor] LLM 输入消息（最后 3 条）:
  [0] type=human, name=None
      content=新电子渠道功能
  [1] type=ai, name=None
      content=...
  [2] type=tool, name=knowledge_search
      content=【0】内容...![xxx](/api/v1/assets/proxy/ragflow/...)
      📸 包含图片数量: 5

[supervisor] LLM 输出统计:
  总长度: 1234 字符
  包含图片: 0 张  ← 关键指标
  输出预览（前 500 字符）:
  根据知识库内容...
```

## 测试步骤

1. **发起查询**
   ```
   新电子渠道功能
   ```

2. **检查日志输出**
   ```bash
   # 查看后端日志（终端）
   tail -f logs/app.log | grep -E "RAGFlow|LLM|图片|knowledge_search"
   ```

3. **关键检查点**
   
   | 阶段 | 日志关键字 | 期望值 |
   |------|-----------|--------|
   | 工具返回 | `包含图片=` | > 0 |
   | LLM 输入 | `📸 包含图片数量:` | > 0 |
   | LLM 输出 | `包含图片:` | **应该 > 0，但实际可能是 0** |

## 分析路径

### 情况 A：工具返回包含图片，LLM 输入也有，但 LLM 输出没有
**结论**：LLM 主动过滤了图片 Markdown

**可能原因**：
1. 系统提示词不够强制
2. LLM 模型特性（某些模型倾向于省略工具返回中的格式化内容）
3. 工具返回内容过长，LLM 自动做了摘要

**解决方案**：
- 加强系统提示词措辞
- 在工具返回中突出图片重要性
- 测试不同模型的行为

### 情况 B：工具返回包含图片，但 LLM 输入没有
**结论**：消息封装或传递过程中丢失

**可能原因**：
1. ToolMessage 封装时内容被截断
2. LangGraph 消息传递机制问题

**解决方案**：
- 检查 ToolMessage 的长度限制
- 添加更详细的消息传递日志

### 情况 C：工具返回就没有图片
**结论**：`_format_retrieval_results` 逻辑问题

**可能原因**：
1. RAGFlow API 返回的 image_id 为空
2. 格式化逻辑有 bug

**解决方案**：
- 检查 RAGFlow API 原始返回
- 调试 `_format_retrieval_results` 函数

## 下一步

根据日志输出，我们将能够精确定位问题在哪一层。
