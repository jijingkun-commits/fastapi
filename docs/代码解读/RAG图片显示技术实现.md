# RAGFlow 知识库图片显示技术文档

> 本文档详细描述了 RAGFlow 知识库检索结果中图片的完整显示流程，包括问题背景、技术方案、代码实现和测试方法。

## 目录

1. [问题背景](#问题背景)
2. [技术方案](#技术方案)
3. [完整流程图](#完整流程图)
4. [代码实现详解](#代码实现详解)
5. [关键文件清单](#关键文件清单)
6. [测试验证](#测试验证)
7. [常见问题](#常见问题)

---

## 问题背景

### 原始问题

RAGFlow 知识库检索返回的结果中包含图片，这些图片在我们系统中通过代理 URL 访问：

```
/api/v1/assets/proxy/ragflow/{image_id}
```

**问题现象**：当 `knowledge_search` 工具返回包含完整 Markdown 图片语法的内容时：

```markdown
这是功能介绍：
![参考图片](/api/v1/assets/proxy/ragflow/xxx-yyy)
```

LLM（特别是 DeepSeek Chat 模型）在生成回复时经常会：
1. 完全忽略图片
2. 修改图片 URL 格式
3. 只保留文字描述，丢弃图片标记

### 根本原因分析

通过多轮测试发现，问题的根本原因是：

1. **长 URL 干扰 LLM**：完整的代理 URL 包含随机字符，LLM 可能将其视为"噪音"
2. **LLM 的简化倾向**：模型倾向于简化输出，可能认为图片链接不重要
3. **Token 分割问题**：流式输出时，完整的 `![alt](url)` 可能被拆分到多个 token 中

---

## 技术方案

### 核心思路：占位符 + 后置替换

采用**两阶段处理**策略：

1. **阶段一：工具输出阶段**
   - 使用简短的占位符 `[IMG-N]` 代替完整图片语法
   - 将索引到 URL 的映射嵌入为 HTML 注释（LLM 不会处理）

2. **阶段二：渲染/存储阶段**
   - 前端渲染时：从 SSE 事件获取映射，替换占位符为实际图片
   - 数据库存储时：后端替换占位符后再保存

### 为什么选择这个方案

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 直接输出完整 URL | 简单 | LLM 经常丢失/修改 | ❌ 不可行 |
| 强化 Prompt 约束 | 无需改代码 | 效果不稳定 | ❌ 不可靠 |
| **占位符 + 后置替换** | 稳定、LLM 友好 | 需要前后端配合 | ✅ 采用 |

---

## 完整流程图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RAGFlow 图片显示流程                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

1. 用户提问
   │
   ▼
2. Supervisor 调用 knowledge_search 工具
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ ragflow_tool.py::knowledge_search()                                             │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │ _format_retrieval_results() 处理每个检索结果:                              │   │
│  │                                                                          │   │
│  │   if image_id:                                                           │   │
│  │       kb_images[i] = image_url          # 存储映射                        │   │
│  │       result_text += f"[IMG-{i}]"       # 输出占位符                       │   │
│  │                                                                          │   │
│  │ 返回: ("格式化文本", {1: url1, 2: url2, ...})                              │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  最终返回字符串:                                                                  │
│    "...文本内容...[IMG-1]...[IMG-2]..."                                          │
│    + "<!--KB_IMAGES:{"1":"url1","2":"url2"}-->"                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
3. 工具结果作为 ToolMessage 进入 LangGraph state
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ multi_agent_graph.py::streaming_wrapper()                                        │
│                                                                                  │
│  async for mode, chunk in agent.astream(..., stream_mode=["messages", "values"]):│
│                                                                                  │
│      if mode == "values":                                                        │
│          # 遍历所有消息，查找 ToolMessage                                          │
│          for msg in messages:                                                    │
│              if isinstance(msg, ToolMessage):                                    │
│                  # 提取 <!--KB_IMAGES:{...}-->                                   │
│                  match = re.search(r'<!--KB_IMAGES:(\{.*?\})-->', content)      │
│                  kb_images.update(json.loads(match.group(1)))                   │
│                  emit_kb_images(writer, kb_images)  # ⬅️ 发送到前端               │
│                                                                                  │
│      if mode == "messages":                                                      │
│          # LLM 流式输出 token（包含 [IMG-N] 占位符）                               │
│          emit_token(writer, content)                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
   │
   │  SSE Event: {"type": "kb_images", "data": {"images": {...}}}
   │  SSE Event: {"type": "token", "data": {"content": "...[IMG-1]..."}}
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 前端 React                                                                       │
│                                                                                  │
│  useSSEStream.ts:                                                                │
│    onKbImages: (images) => setKbImages(prev => ({...prev, ...images}))           │
│                                                                                  │
│  ai.tsx (AssistantMessage):                                                      │
│    const kbImages = thread.kbImages;                                             │
│    const displayContent = replaceImagePlaceholders(contentString, kbImages);     │
│            │                                                                     │
│            ▼                                                                     │
│    utils.ts::replaceImagePlaceholders():                                         │
│      "[IMG-1]" → "![参考图片](/api/v1/assets/proxy/ragflow/xxx)"                 │
│                                                                                  │
│    <MarkdownText>{displayContent}</MarkdownText>  // ✅ 图片正常显示              │
└─────────────────────────────────────────────────────────────────────────────────┘

同时：

┌─────────────────────────────────────────────────────────────────────────────────┐
│ 数据库保存 (chat_repo.py::save_conversation_from_messages)                        │
│                                                                                  │
│  # 1. 从 ToolMessage 提取 kb_images                                              │
│  for msg in messages:                                                            │
│      if msg.type == "tool":                                                      │
│          match = re.search(r'<!--KB_IMAGES:(\{.*?\})-->', content)              │
│          kb_images.update(json.loads(match.group(1)))                            │
│                                                                                  │
│  # 2. 替换 AI 消息中的占位符                                                       │
│  for idx, url in kb_images.items():                                              │
│      ai_content = ai_content.replace(f"[IMG-{idx}]", f"![参考图片]({url})")       │
│                                                                                  │
│  # 3. 保存到数据库（内容已包含完整图片 URL）                                         │
│  save_message(db, content=ai_content)                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 代码实现详解

### 1. 工具层：生成占位符（ragflow_tool.py）

**文件**：`app/ai/tools/ragflow_tool.py`

**核心函数**：`_format_retrieval_results()`

```python
def _format_retrieval_results(chunks: list[dict]) -> tuple[str, dict[int, str]]:
    """格式化检索结果，返回 (格式化文本, 图片映射)。
    
    图片使用 [IMG-N] 占位符，避免 LLM 干扰完整 URL。
    """
    kb_images: dict[int, str] = {}  # 索引 -> URL 映射
    results = []
    
    for i, chunk in enumerate(chunks):
        # ...处理文本内容...
        
        # 处理图片：生成占位符
        image_id = chunk.get("image_id")
        if image_id:
            image_url = f"/api/v1/assets/proxy/ragflow/{image_id}"
            kb_images[i] = image_url
            result_text += f"\n   [IMG-{i}]"  # 🔑 占位符格式
        
        results.append(result_text)
    
    return "\n\n".join(results), kb_images
```

**工具返回值处理**：`knowledge_search()`

```python
def knowledge_search(query: str, datasets: list[str] = None) -> str:
    # ...调用 RAGFlow API...
    
    formatted_text, kb_images = _format_retrieval_results(chunks)
    
    # 将映射嵌入为 HTML 注释（LLM 不会处理注释内容）
    if kb_images:
        kb_images_json = json.dumps(kb_images)
        formatted_text += f"\n<!--KB_IMAGES:{kb_images_json}-->"
    
    return formatted_text
```

**设计要点**：
- 占位符格式 `[IMG-N]` 简短易记，LLM 容易保留
- HTML 注释 `<!--...-->` 不会被 LLM 处理或删除
- JSON 格式便于解析

---

### 2. 流式层：提取并发送映射（multi_agent_graph.py）

**文件**：`app/ai/workflow/multi_agent_graph.py`

**关键代码**：`streaming_wrapper()` 中的 values 模式处理

```python
async def streaming_wrapper(state, config):
    writer = get_stream_writer()
    kb_images = {}  # 存储图片映射
    
    async for mode, chunk in agent.astream(
        state, config, 
        stream_mode=["messages", "values"]
    ):
        if mode == "values":
            # values 模式包含完整的 state，包括 ToolMessage
            messages = chunk.get("messages", [])
            for msg in messages:
                if isinstance(msg, ToolMessage):
                    tool_content = str(getattr(msg, "content", ""))
                    
                    # 提取 KB_IMAGES 映射
                    kb_images_match = re.search(
                        r'<!--KB_IMAGES:(\{.*?\})-->', 
                        tool_content
                    )
                    if kb_images_match:
                        new_images = json.loads(kb_images_match.group(1))
                        kb_images.update(new_images)
                        
                        # 🔑 发送映射到前端
                        emit_kb_images(writer, kb_images, node=name)
        
        elif mode == "messages":
            # 处理 LLM 流式输出（token 中包含 [IMG-N]）
            if isinstance(msg, AIMessageChunk):
                content = getattr(msg, "content", "")
                emit_token(writer, content, node=name)
```

**为什么在 values 模式提取**：

`stream_mode="messages"` 只返回 `AIMessageChunk`，不返回 `ToolMessage`。
`stream_mode="values"` 返回完整的 state 快照，包含所有消息类型。

---

### 3. 事件层：发送图片映射事件（events.py）

**文件**：`app/ai/events.py`

```python
def emit_kb_images(writer: StreamWriter, kb_images: dict, node: str = "") -> None:
    """发送知识库图片映射事件。
    
    用于通知前端图片占位符 [IMG-N] 与实际 URL 的映射关系，
    前端在渲染时进行替换。
    
    Args:
        writer: LangGraph StreamWriter
        kb_images: 图片映射字典 {索引: URL}
        node: 来源节点名称
    """
    writer({
        "type": "kb_images",
        "data": {"images": kb_images},
        "node": node
    })
```

**SSE 事件格式**：

```
event: kb_images
data: {"images": {"1": "/api/v1/...", "2": "/api/v1/..."}}
```

---

### 4. 数据库层：保存前替换（chat_repo.py）

**文件**：`app/repositories/chat_repo.py`

**函数**：`save_conversation_from_messages()`

```python
def save_conversation_from_messages(db, messages, user_id, thread_id):
    kb_images = {}  # 收集所有图片映射
    
    # 第一遍：从 ToolMessage 提取 kb_images
    for msg in messages:
        if msg.type == "tool":
            content = str(getattr(msg, "content", ""))
            match = re.search(r'<!--KB_IMAGES:(\{.*?\})-->', content)
            if match:
                new_images = json.loads(match.group(1))
                kb_images.update(new_images)  # 合并映射
    
    # 第二遍：保存消息
    for msg in messages:
        if msg.type == "ai":
            ai_content = str(getattr(msg, "content", ""))
            
            # 🔑 替换占位符为实际图片
            if kb_images:
                for idx_str, url in kb_images.items():
                    placeholder = f"[IMG-{idx_str}]"
                    if placeholder in ai_content:
                        markdown_img = f"![参考图片]({url})"
                        ai_content = ai_content.replace(placeholder, markdown_img)
            
            save_message(db, role="ai", content=ai_content, ...)
```

**为什么需要数据库层替换**：

确保用户刷新页面后，从数据库加载的消息也能正确显示图片（而不是占位符）。

---

### 5. 前端层：SSE 事件处理（backend.ts）

**文件**：`web/src/lib/backend.ts`

**回调接口**：

```typescript
export interface StreamCallbacks {
  onToken?: (token: string) => void;
  onThinking?: (content: string) => void;
  // ...其他回调...
  
  /** 知识库图片映射（用于替换占位符） */
  onKbImages?: (images: Record<string, string>) => void;
}
```

**事件处理**：

```typescript
// streamLLM 函数中
if (type === "kb_images") {
    onKbImages?.(data.images);
}
```

---

### 6. 前端层：状态管理（useSSEStream.ts）

**文件**：`web/src/hooks/useSSEStream.ts`

```typescript
export function useSSEStream(): StreamContextValue {
    // ...其他状态...
    
    // 知识库图片映射（用于替换 [IMG-N] 占位符）
    const [kbImages, setKbImages] = useState<KbImages>({});
    
    const { stop, promise } = startLLMStream(prompt, {
        onToken: (token) => appendToAiMessage(aiId, token),
        
        // 处理知识库图片映射事件
        onKbImages: (images) => {
            console.log(`🖼️ 收到 kb_images 映射: ${Object.keys(images).length} 张图片`);
            setKbImages(prev => ({ ...prev, ...images }));
        },
        
        // ...其他回调...
    });
    
    return {
        // ...其他值...
        kbImages,  // 暴露给组件使用
    };
}
```

---

### 7. 前端层：替换函数（utils.ts）

**文件**：`web/src/components/chat/utils.ts`

```typescript
/**
 * 知识库图片映射类型
 */
export type KbImages = Record<string, string>;

/**
 * 将内容中的 [IMG-N] 占位符替换为实际的 Markdown 图片语法
 * 
 * @param content 包含占位符的内容
 * @param kbImages 图片映射 {索引: URL}
 * @returns 替换后的内容
 */
export function replaceImagePlaceholders(
    content: string, 
    kbImages: KbImages
): string {
    if (!kbImages || Object.keys(kbImages).length === 0) {
        return content;
    }
    
    let result = content;
    for (const [idx, url] of Object.entries(kbImages)) {
        const placeholder = `[IMG-${idx}]`;
        if (result.includes(placeholder)) {
            result = result.replace(placeholder, `![参考图片](${url})`);
        }
    }
    return result;
}
```

---

### 8. 前端层：渲染应用（ai.tsx）

**文件**：`web/src/components/chat/messages/ai.tsx`

```tsx
import { getContentString, replaceImagePlaceholders } from "../utils";

export function AssistantMessage({ message, isLoading, handleRegenerate }) {
    const content = message?.content ?? [];
    const contentString = getContentString(content);
    
    const thread = useStreamContext();
    const kbImages = thread.kbImages;
    
    // 🔑 应用图片占位符替换
    const displayContent = replaceImagePlaceholders(contentString, kbImages);
    
    return (
        <div>
            {/* 使用替换后的内容渲染 */}
            <MarkdownText>{displayContent}</MarkdownText>
        </div>
    );
}
```

---

## 关键文件清单

| 文件 | 作用 | 关键函数/变量 |
|------|------|---------------|
| `app/ai/tools/ragflow_tool.py` | 生成占位符 | `_format_retrieval_results()`, `knowledge_search()` |
| `app/ai/workflow/multi_agent_graph.py` | 提取并发送映射 | `streaming_wrapper()` |
| `app/ai/events.py` | 事件发送函数 | `emit_kb_images()` |
| `app/repositories/chat_repo.py` | 保存前替换 | `save_conversation_from_messages()` |
| `web/src/lib/backend.ts` | SSE 事件处理 | `onKbImages` 回调 |
| `web/src/hooks/useSSEStream.ts` | 状态管理 | `kbImages` state |
| `web/src/components/chat/utils.ts` | 替换函数 | `replaceImagePlaceholders()` |
| `web/src/components/chat/messages/ai.tsx` | 渲染应用 | `displayContent` |
| `web/src/providers/StreamContext.tsx` | 类型定义 | `kbImages: Record<string, string>` |

---

## 测试验证

### 后端验证

查看日志：

```bash
tail -f logs/assistant.log | grep -E "kb_images|KB_IMAGES"
```

预期输出：

```
[supervisor] 从 values 模式提取 kb_images: 22 个
```

### 前端验证

打开浏览器控制台，预期输出：

```
🖼️ 收到 kb_images 映射: 22 张图片
```

### 数据库验证

```sql
SELECT content FROM t_chat_message 
WHERE role = 'ai' 
ORDER BY create_time DESC 
LIMIT 1;
```

内容应包含 `![参考图片](/api/v1/assets/proxy/ragflow/...)` 而不是 `[IMG-N]`。

---

## 常见问题

### Q1: 为什么流式输出时不能直接替换占位符？

**A**: LLM 的流式输出是逐 token 返回的，例如：
- Token 1: `"...[IM"`
- Token 2: `"G-1]..."`

完整的 `[IMG-1]` 被拆分到两个 token 中，无法在单个 token 内完成匹配和替换。

### Q2: 为什么选择 HTML 注释嵌入映射？

**A**: HTML 注释 `<!--...-->` 有以下优点：
1. LLM 通常不会处理或删除注释内容
2. 不会影响文本的可读性
3. 易于使用正则表达式提取

### Q3: 如何添加新的图片来源？

1. 在工具返回值中添加 `[IMG-N]` 占位符
2. 将映射加入嵌入的 JSON：`<!--KB_IMAGES:{新映射}-->`
3. 前端无需修改，会自动处理所有收到的映射

### Q4: 图片不显示怎么排查？

1. **检查工具输出**：日志中是否有 `kb_images 映射: {N} 个`
2. **检查 SSE 事件**：前端控制台是否有 `收到 kb_images 映射`
3. **检查替换结果**：审查 `displayContent` 是否包含 `![参考图片](...)`
4. **检查图片代理**：直接访问 `/api/v1/assets/proxy/ragflow/{id}` 是否返回图片
