# 深度分析：复合任务解析与 Collect 模式实现方案

> 基于 OpenClaw 源码逆向 + 本项目 `multi_agent_graph.py` / `chat_service.py` 架构分析
> 日期：2026-02-18

---

## 一、问题定义

### 问题 1：复合任务解析与执行

用户一句话包含多个意图时（如"查一下今天天气，再帮我统计上月贷款余额，最后创建一个待办提醒我下周开会"），系统如何解析并执行？

### 问题 2：回复前继续输入

当 AI 正在回复时，用户继续输入新消息，系统如何处理？是丢弃、排队还是合并？

---

## 二、当前架构现状分析

### 2.1 Supervisor 路由机制（`multi_agent_graph.py`）

```
START -> preprocess -> supervisor -> [data_expert | todo_expert] -> evaluate -> postprocess -> END
                                 \-> postprocess (直接回复)
```

核心路由链路：

1. `preprocess`：消息验证、图片分析、技能检索、系统上下文注入
2. `supervisor`：`create_react_agent(llm, handoff_tools + simple_tools, prompt=SUPERVISOR_PROMPT)`
3. `supervisor_should_continue()`：检查 `pending_handoff` → 路由到专家 / evaluate / postprocess
4. 专家执行 → `evaluate` → 条件路由回 supervisor 或 postprocess

关键限制：

| 维度 | 现状 | 问题 |
|------|------|------|
| 路由粒度 | 单次 handoff，一次只能委派一个专家 | 无法并行处理多意图 |
| 状态模型 | `pending_handoff: Optional[Dict]`（单值） | 不支持 handoff 队列 |
| 迭代上限 | `MAX_ITERATIONS = 3` | 理论上可串行处理 3 个意图，但实际依赖 LLM 自主决策 |
| 输入入口 | `sse_stream()` 同步处理单条消息 | 无消息缓冲/合并机制 |

### 2.2 SSE 流入口（`chat_service.py`）

```python
async def sse_stream(prompt, thread_id, user_id, ...):
    svc = ChatService()
    async for chunk in svc.stream(...):
        yield chunk
```

关键特征：

- **同步阻塞模型**：一个 `thread_id` 同一时刻只有一个 `graph.astream()` 在执行
- **无输入缓冲**：前端发送新消息时，如果上一轮还在处理，行为取决于前端实现（通常是等待或报错）
- **无消息合并**：每次调用都是独立的 `input_state`，不会与正在处理的消息合并

### 2.3 现有的"串行多意图"能力

当前架构并非完全不能处理多意图，但依赖 LLM 的自主行为：

```
用户: "查一下上月贷款余额，然后创建一个待办提醒我下周开会"

Supervisor 第 1 轮:
  → 识别到数据查询意图 → assign_to_data_expert(task_description="查询上月贷款余额")
  → data_expert 执行 → 返回结果

evaluate 节点:
  → 检查最后消息有 tool_calls? → 否 → evaluation = "complete"
  → 但如果 Supervisor 在第 1 轮就识别了两个意图并先处理了第一个...

问题: Supervisor 是否会在 data_expert 返回后自动发起第二个 handoff?
答案: 取决于 evaluate → should_continue_routing → "supervisor" 路径
      但当前 evaluate 逻辑只检查 "最后一条消息是否有 tool_calls"
      data_expert 返回的是 AI 消息（无 tool_calls）→ evaluation = "complete" → 直接结束
```

结论：**当前架构在 evaluate 节点会过早终止，无法自动串行处理第二个意图。**

---

## 三、OpenClaw 的解决方案

### 3.1 复合任务：不做 Supervisor 层拆分

OpenClaw 的核心设计哲学：**不在路由层拆分多意图，而是让 Agent 自主 spawn 子 Agent。**

```
用户消息 → Agent（单一入口）
              ├── 自主调用 tool: search_web("天气")
              ├── 自主调用 tool: spawn_subagent("数据分析", "查询贷款余额")
              └── 自主调用 tool: spawn_subagent("待办管理", "创建待办")
```

这与我们的 Supervisor 模式有本质区别：

| 维度 | OpenClaw | 本项目 |
|------|----------|--------|
| 意图拆分 | Agent 自主决策，通过工具调用实现 | Supervisor LLM 决策，通过 handoff 工具实现 |
| 执行模式 | 子 Agent 可并行（spawn 后异步执行） | 串行（一次只能 handoff 一个专家） |
| 结果汇总 | 主 Agent 收集所有子 Agent 结果后统一回复 | 专家直接回复用户，无汇总层 |

### 3.2 Collect 模式：消息队列合并

这是 OpenClaw 处理"回复中继续输入"的核心机制。

#### 3.2.1 完整数据流

```
用户消息 1 → inbound-debounce → 触发 Agent 处理（busy=true）
用户消息 2 → inbound-debounce → 检测到 busy → enqueue(followup_queue)
用户消息 3 → inbound-debounce → 检测到 busy → enqueue(followup_queue)

Agent 处理完消息 1 → 回复用户
                   → scheduleFollowupDrain(key)
                   → drain 检测到 mode="collect"
                   → waitForQueueDebounce(queue)  // 等待 debounce 窗口
                   → buildCollectPrompt(items=[msg2, msg3])
                   → 合并为单条 prompt:
                     "[Queued messages while agent was busy]
                      ---
                      Queued #1
                      {msg2.prompt}
                      ---
                      Queued #2
                      {msg3.prompt}"
                   → runFollowup(merged_prompt)  // 作为一次请求处理
```

#### 3.2.2 源码级解析

**入队（enqueue.ts）**：

```typescript
export function enqueueFollowupRun(key, run, settings, dedupeMode) {
  const queue = getFollowupQueue(key, settings);
  
  // 1. 去重检查（3 种模式）
  //    - "message-id": 按消息 ID 去重
  //    - "prompt": 按 prompt 文本去重
  //    - "none": 不去重
  if (shouldSkipQueueItem({ item: run, items: queue.items, dedupe })) {
    return false;
  }
  
  // 2. 容量控制 + 丢弃策略
  //    - "summarize": 超容量时生成摘要替代
  //    - "old": 丢弃最旧的
  //    - "new": 丢弃最新的
  applyQueueDropPolicy({ queue, summarize: (item) => item.summaryLine });
  
  // 3. 入队
  queue.items.push(run);
  return true;
}
```

**出队（drain.ts）**：

```typescript
export function scheduleFollowupDrain(key, runFollowup) {
  const queue = FOLLOWUP_QUEUES.get(key);
  queue.draining = true;
  
  while (queue.items.length > 0) {
    await waitForQueueDebounce(queue);  // 等待 debounce 窗口关闭
    
    if (queue.mode === "collect") {
      // 跨频道检测：不同来源的消息不能合并
      if (hasCrossChannelItems(queue.items)) {
        // 逐条处理
        await runFollowup(queue.items.shift());
        continue;
      }
      
      // 同频道：合并所有消息为一条
      const items = queue.items.slice();
      const prompt = buildCollectPrompt({
        title: "[Queued messages while agent was busy]",
        items,
        renderItem: (item, idx) => `---\nQueued #${idx + 1}\n${item.prompt}`,
      });
      await runFollowup({ prompt, run: items.at(-1).run });
      queue.items.splice(0, items.length);
    } else {
      // 非 collect 模式：逐条处理
      await runFollowup(queue.items.shift());
    }
  }
}
```

**Debounce（inbound-debounce.ts）**：

```typescript
export function createInboundDebouncer<T>({ debounceMs, buildKey, onFlush }) {
  const buffers = new Map<string, { items: T[], timeout }>();
  
  const enqueue = async (item) => {
    const key = buildKey(item);
    const buffer = buffers.get(key) || { items: [], timeout: null };
    buffer.items.push(item);
    
    // 重置 debounce 定时器
    clearTimeout(buffer.timeout);
    buffer.timeout = setTimeout(() => {
      onFlush(buffer.items);  // 窗口关闭，批量处理
    }, debounceMs);
  };
  
  return { enqueue };
}
```

#### 3.2.3 队列状态模型

```typescript
type FollowupQueueState = {
  items: FollowupRun[];       // 待处理消息队列
  draining: boolean;          // 是否正在出队
  lastEnqueuedAt: number;     // 最后入队时间戳
  mode: QueueMode;            // "collect" | "individual" | "latest" | "drop" | "pause"
  debounceMs: number;         // debounce 窗口（默认 1000ms）
  cap: number;                // 队列容量上限（默认 20）
  dropPolicy: QueueDropPolicy; // "summarize" | "old" | "new"
  droppedCount: number;       // 已丢弃消息计数
  summaryLines: string[];     // 丢弃消息的摘要
};
```

5 种队列模式：

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| `collect` | 等待 debounce 窗口关闭后合并所有消息为一条 | 默认模式，适合连续输入 |
| `individual` | 逐条处理，FIFO | 每条消息都需要独立回复 |
| `latest` | 只处理最新一条，丢弃其余 | 用户频繁修改输入 |
| `drop` | 全部丢弃，不处理 | Agent 忙时拒绝新输入 |
| `pause` | 暂停处理，保留队列 | 手动控制 |

---

## 四、本项目实现方案

### 4.1 方案总览

分两个阶段实施，优先级从高到低：

| 阶段 | 目标 | 复杂度 | 依赖 |
|------|------|--------|------|
| Phase 1 | Collect 模式（输入合并一次回复） | 中 | 前端 + 后端 |
| Phase 2 | 复合任务串行执行（Planner + Handoff 队列） | 高 | Phase 1 + Graph 改造 |

### 4.2 Phase 1：Collect 模式实现

#### 4.2.1 架构设计

```
前端                          后端
┌─────────┐                ┌──────────────────────────────────┐
│ ChatInput│                │  MessageCollector (进程内)        │
│          │  POST /chat    │  ┌─────────────────────────┐     │
│ msg1 ────┼───────────────>│  │ session_buffers          │     │
│ msg2 ────┼───────────────>│  │  key: thread_id          │     │
│ msg3 ────┼───────────────>│  │  items: [msg1,msg2,msg3] │     │
│          │                │  │  timeout: 1.5s           │     │
│          │  SSE /stream   │  └──────────┬──────────────┘     │
│ <────────┼────────────────│             │ flush              │
│ 合并回复  │                │             ▼                    │
│          │                │  sse_stream(merged_prompt)        │
│          │                │             │                    │
│          │                │             ▼                    │
│          │                │  multi_agent_graph.astream()     │
└─────────┘                └──────────────────────────────────┘
```

#### 4.2.2 核心组件：`MessageCollector`

```python
# app/services/message_collector.py

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_DEBOUNCE_MS = 1500      # debounce 窗口
DEFAULT_BUSY_DEBOUNCE_MS = 3000 # Agent 忙时的 debounce 窗口
DEFAULT_CAP = 10                # 队列容量上限


@dataclass
class PendingMessage:
    """待处理消息。"""
    content: str
    user_id: Optional[int] = None
    attachments: Optional[list] = None
    enqueued_at: float = 0.0


@dataclass
class SessionBuffer:
    """单个会话的消息缓冲区。"""
    thread_id: str
    items: list[PendingMessage] = field(default_factory=list)
    is_busy: bool = False           # Agent 是否正在处理
    flush_task: Optional[asyncio.Task] = None
    debounce_ms: int = DEFAULT_DEBOUNCE_MS
    cap: int = DEFAULT_CAP


class MessageCollector:
    """进程内消息收集器，实现 collect 模式。
    
    职责：
    1. 当 Agent 空闲时，debounce 窗口内的连续消息合并为一条
    2. 当 Agent 忙碌时，新消息入队等待，处理完成后批量合并
    3. 超容量时丢弃最旧消息并生成摘要
    """
    
    def __init__(self):
        self._buffers: Dict[str, SessionBuffer] = {}
        self._lock = asyncio.Lock()
    
    async def enqueue(
        self,
        thread_id: str,
        content: str,
        user_id: Optional[int] = None,
        attachments: Optional[list] = None,
        on_flush: Optional[Callable[[str, str, Optional[int], Optional[list]], Awaitable[None]]] = None,
    ) -> bool:
        """将消息加入缓冲区。
        
        Args:
            thread_id: 会话 ID
            content: 消息内容
            user_id: 用户 ID
            attachments: 附件
            on_flush: flush 回调，签名 (thread_id, merged_prompt, user_id, attachments)
            
        Returns:
            True 表示消息已入队（将被合并处理），False 表示直接处理
        """
        import time
        
        async with self._lock:
            buffer = self._buffers.get(thread_id)
            
            if buffer is None:
                # 首条消息，创建缓冲区并启动 debounce 定时器
                buffer = SessionBuffer(thread_id=thread_id)
                self._buffers[thread_id] = buffer
            
            # 容量检查
            if len(buffer.items) >= buffer.cap:
                # 丢弃最旧消息
                dropped = buffer.items.pop(0)
                logger.warning(
                    "消息队列已满，丢弃最旧消息: thread_id=%s, dropped=%s",
                    thread_id, dropped.content[:50]
                )
            
            # 入队
            msg = PendingMessage(
                content=content,
                user_id=user_id,
                attachments=attachments,
                enqueued_at=time.time(),
            )
            buffer.items.append(msg)
            
            # 重置 debounce 定时器
            if buffer.flush_task and not buffer.flush_task.done():
                buffer.flush_task.cancel()
            
            debounce_s = (
                DEFAULT_BUSY_DEBOUNCE_MS if buffer.is_busy else buffer.debounce_ms
            ) / 1000.0
            
            if on_flush:
                buffer.flush_task = asyncio.create_task(
                    self._schedule_flush(thread_id, debounce_s, on_flush)
                )
            
            logger.info(
                "消息入队: thread_id=%s, queue_depth=%d, is_busy=%s",
                thread_id, len(buffer.items), buffer.is_busy
            )
            return len(buffer.items) > 1  # 第一条消息返回 False（直接处理）
    
    async def _schedule_flush(
        self,
        thread_id: str,
        delay_s: float,
        on_flush: Callable,
    ):
        """延迟 flush：等待 debounce 窗口关闭后合并消息。"""
        try:
            await asyncio.sleep(delay_s)
            await self._flush(thread_id, on_flush)
        except asyncio.CancelledError:
            pass  # debounce 被重置，正常行为
    
    async def _flush(self, thread_id: str, on_flush: Callable):
        """合并缓冲区消息并触发处理。"""
        async with self._lock:
            buffer = self._buffers.get(thread_id)
            if not buffer or not buffer.items:
                return
            
            items = buffer.items[:]
            buffer.items.clear()
            buffer.is_busy = True
        
        # 合并消息
        if len(items) == 1:
            merged_prompt = items[0].content
        else:
            lines = []
            for i, item in enumerate(items):
                lines.append(f"--- 消息 {i+1} ---\n{item.content}")
            
            merged_prompt = (
                "[以下是用户在等待回复期间发送的多条消息，请统一理解后一次性回复]\n\n"
                + "\n\n".join(lines)
            )
            logger.info(
                "消息合并: thread_id=%s, count=%d, merged_len=%d",
                thread_id, len(items), len(merged_prompt)
            )
        
        user_id = items[-1].user_id
        attachments = []
        for item in items:
            if item.attachments:
                attachments.extend(item.attachments)
        
        try:
            await on_flush(thread_id, merged_prompt, user_id, attachments or None)
        finally:
            async with self._lock:
                buffer = self._buffers.get(thread_id)
                if buffer:
                    buffer.is_busy = False
                    # 如果处理期间又有新消息入队，触发新一轮 flush
                    if buffer.items:
                        logger.info("处理完成后发现新消息，触发新一轮 flush: thread_id=%s", thread_id)
                    else:
                        del self._buffers[thread_id]
    
    def mark_busy(self, thread_id: str):
        """标记会话为忙碌状态。"""
        buffer = self._buffers.get(thread_id)
        if buffer:
            buffer.is_busy = True
    
    def mark_idle(self, thread_id: str):
        """标记会话为空闲状态。"""
        buffer = self._buffers.get(thread_id)
        if buffer:
            buffer.is_busy = False
    
    def get_queue_depth(self, thread_id: str) -> int:
        """获取队列深度。"""
        buffer = self._buffers.get(thread_id)
        return len(buffer.items) if buffer else 0


# 全局单例
message_collector = MessageCollector()
```

#### 4.2.3 集成到 `chat_service.py`

改造点（最小侵入）：

```python
# chat_service.py 改造示意（非完整代码）

from app.services.message_collector import message_collector

async def sse_stream(prompt, thread_id, user_id, ...):
    # 检查是否有正在处理的会话
    queue_depth = message_collector.get_queue_depth(thread_id)
    
    if queue_depth > 0:
        # 会话忙碌，消息入队
        await message_collector.enqueue(thread_id, prompt, user_id, attachments)
        # 返回 queued 事件通知前端
        yield _format_sse("queued", {
            "thread_id": thread_id,
            "queue_depth": queue_depth + 1,
            "message": "消息已排队，将在当前回复完成后统一处理"
        })
        return
    
    # 正常处理流程（标记忙碌）
    message_collector.mark_busy(thread_id)
    try:
        svc = ChatService()
        async for chunk in svc.stream(prompt, thread_id, user_id, ...):
            yield chunk
    finally:
        message_collector.mark_idle(thread_id)
        # 检查是否有排队消息需要处理
        # （由 MessageCollector 的 flush 机制自动触发）
```

#### 4.2.4 前端配合

```typescript
// 前端需要处理新的 SSE 事件类型
case "queued":
  // 显示"消息已排队"提示
  showToast(`消息已排队 (${data.queue_depth} 条待处理)`);
  break;
```

### 4.3 Phase 2：复合任务串行执行

#### 4.3.1 问题根因

当前 `evaluate` 节点的判断逻辑过于简单：

```python
def _evaluate_expert_work(state):
    last_msg = messages[-1]
    has_tool_calls = hasattr(last_msg, 'tool_calls') and last_msg.tool_calls
    if last_msg.type == "ai" and not has_tool_calls:
        return {"evaluation": "complete"}  # 过早终止！
```

当 data_expert 返回结果后，evaluate 直接判定"complete"，不会让 Supervisor 继续处理第二个意图（创建待办）。

#### 4.3.2 方案：Handoff 队列 + Planner 增强

核心思路：将 `pending_handoff` 从单值升级为队列，让 Supervisor 一次性规划所有意图。

**State 改造**：

```python
# app/ai/state.py 改造

class MultiAgentState(TypedDict):
    # ... 现有字段 ...
    
    # Phase 2: Handoff 队列（替代单值 pending_handoff）
    handoff_queue: Optional[list[Dict[str, Any]]]  # 有序的委派队列
    handoff_index: int  # 当前执行到第几个
    task_plan: Optional[str]  # Supervisor 的任务规划文本
```

**Supervisor Prompt 增强**：

```
当用户消息包含多个独立意图时，你必须：
1. 先列出所有识别到的意图（按执行优先级排序）
2. 为每个意图调用对应的 assign_to_* 工具
3. 等待每个专家返回结果后，再调用下一个
4. 所有专家完成后，生成统一的汇总回复
```

**evaluate 节点改造**：

```python
def _evaluate_expert_work(state):
    handoff_queue = state.get("handoff_queue", [])
    handoff_index = state.get("handoff_index", 0)
    
    # 如果队列中还有未执行的 handoff，继续
    if handoff_index < len(handoff_queue) - 1:
        return {
            "evaluation": "continue",
            "handoff_index": handoff_index + 1,
            "pending_handoff": handoff_queue[handoff_index + 1],
        }
    
    # 所有 handoff 已执行完毕
    return {"evaluation": "complete"}
```

**执行流程**：

```
用户: "查上月贷款余额，然后创建待办提醒下周开会"

Supervisor 第 1 轮:
  → 识别 2 个意图
  → 调用 assign_to_data_expert("查询上月贷款余额")
  → 调用 assign_to_todo_expert("创建待办：下周开会")
  → handoff_queue = [data_handoff, todo_handoff]
  → pending_handoff = data_handoff (第 1 个)

data_expert 执行 → 返回贷款余额数据

evaluate:
  → handoff_index=0, queue_len=2
  → 还有未执行的 → evaluation="continue"
  → pending_handoff = todo_handoff (第 2 个)

todo_expert 执行 → 创建待办成功

evaluate:
  → handoff_index=1, queue_len=2
  → 全部完成 → evaluation="complete"

postprocess → 保存对话 → END
```

#### 4.3.3 复杂度评估

| 改造项 | 影响范围 | 风险 |
|--------|---------|------|
| State 新增 `handoff_queue` | state.py | 低（新增字段，不影响现有） |
| evaluate 节点改造 | multi_agent_graph.py | 中（需要兼容单 handoff 场景） |
| Supervisor Prompt 增强 | agent_prompts.py | 中（LLM 行为不确定性） |
| 结果汇总机制 | 新增 | 高（需要收集多个专家结果并生成统一回复） |

---

## 五、OpenClaw vs 本项目方案对比

| 维度 | OpenClaw | 本项目 Phase 1 | 本项目 Phase 2 |
|------|----------|---------------|---------------|
| 多意图处理 | Agent 自主 spawn 子 Agent | 不处理（单意图） | Supervisor 规划 + Handoff 队列 |
| 输入合并 | Followup Queue + collect 模式 | MessageCollector + debounce | 同 Phase 1 |
| 队列实现 | 进程内 Map（非外部 MQ） | 进程内 Dict（同理念） | 同 Phase 1 |
| Debounce | 可配置（默认 1000ms） | 可配置（默认 1500ms） | 同 Phase 1 |
| 去重 | 3 种模式（message-id/prompt/none） | 简化版（content hash） | 同 Phase 1 |
| 丢弃策略 | 3 种（summarize/old/new） | 简化版（丢弃最旧） | 同 Phase 1 |
| 跨频道检测 | 有（不同来源不合并） | 不需要（单频道 Web） | 不需要 |

---

## 六、实施路线图

### Phase 1：Collect 模式（2 周）

```
Week 1:
  - [ ] 实现 MessageCollector 核心类
  - [ ] 集成到 chat_service.py（sse_stream 入口）
  - [ ] 新增 "queued" SSE 事件类型
  - [ ] 前端处理 queued 事件（显示排队提示）

Week 2:
  - [ ] 单元测试（debounce、合并、容量控制）
  - [ ] 集成测试（多消息合并场景）
  - [ ] 压力测试（并发消息入队）
  - [ ] 文档更新
```

### Phase 2：复合任务串行执行（3 周）

```
Week 3:
  - [ ] State 扩展（handoff_queue, handoff_index）
  - [ ] evaluate 节点改造（队列消费逻辑）
  - [ ] Supervisor Prompt 增强（多意图规划指令）

Week 4:
  - [ ] 结果汇总机制（收集多专家输出 → 统一回复）
  - [ ] 兼容测试（单意图场景不受影响）
  - [ ] 银行场景端到端测试（"查贷款余额 + 创建待办"）

Week 5:
  - [ ] Prompt 调优（多意图识别准确率）
  - [ ] 边界场景处理（3+ 意图、意图间有依赖关系）
  - [ ] 性能测试（串行执行延迟可接受性）
  - [ ] 文档更新
```

### Phase 3：并行执行（远期，4+ 周）

当 Phase 2 稳定后，可考虑引入 LangGraph `Send()` 实现真正的并行分发：

```
Supervisor → Send([data_expert, todo_expert]) → 并行执行 → Join → 汇总回复
```

这需要更大的架构改造，建议作为 Q3 目标。

---

## 七、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 进程内队列在重启时丢失 | 排队消息丢失 | Phase 1 可接受；后续可加 Redis 持久化 |
| debounce 窗口过长导致响应延迟 | 用户体验下降 | 可配置，默认 1.5s，前端显示"正在等待更多输入..." |
| LLM 多意图识别不准确 | 漏处理或错误拆分 | Prompt 工程 + 评估集 + 人工兜底 |
| Handoff 队列中某个专家失败 | 后续意图无法执行 | evaluate 节点增加错误处理，跳过失败的 handoff |
| 合并消息语义冲突 | AI 回复混乱 | 合并 prompt 中明确标注消息边界和顺序 |

---

## 八、关键决策记录

1. **选择进程内队列而非 Redis/RabbitMQ**：与 OpenClaw 一致，复杂度低，单实例部署足够。多实例部署时再引入外部队列。

2. **Collect 模式作为默认模式**：银行场景下用户连续输入是常见行为（如先问余额再补充条件），合并处理比逐条回复更自然。

3. **Phase 2 选择 Handoff 队列而非 Subagent Spawn**：本项目已有成熟的 Supervisor + Expert 架构，改造成本远低于引入全新的 Subagent 机制。

4. **debounce 默认 1500ms（比 OpenClaw 的 1000ms 长）**：银行用户输入通常更长更复杂，需要更大的窗口。
