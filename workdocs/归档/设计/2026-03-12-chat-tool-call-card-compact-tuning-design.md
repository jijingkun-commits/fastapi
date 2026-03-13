# 聊天工具调用卡片紧凑化微调设计

> 日期：2026-03-12
> 状态：APPROVED
> 适用范围：`web/src/components/chat/messages/tool-calls.tsx`、`web/src/app/globals.css`

## 背景

当前工具调用卡片已经并入聊天主题，但视觉上仍然偏像“独立系统面板”：

- 短工具名也会被 `min-width: 320px` 撑宽；
- 头部与展开体的 `padding/gap` 偏大；
- 放在聊天消息流里时，横向存在感比消息工具条和人类气泡更重。

本轮目标不是重做样式，只做一轮紧凑化微调，让工具卡片更像聊天里的附属卡片。

## 最终方案

### 模块边界

- `tool-calls.tsx` 继续只负责工具调用/结果的结构与展开交互，不新增局部 inline 样式。
- `globals.css` 中现有 `chat-tool-call-*` 继续作为唯一视觉 owner。

### 依赖方向

- 工具卡片继续消费聊天主题 token 与现有 `chat-*` 视觉语言；
- 不反向依赖消息壳层，也不新增第二套 `tool-*` 样式分支。

### 状态归属

- 展开/收起状态仍由 `ToolCalls` / `ToolResult` 组件本地持有；
- 宽度、间距、内边距只在 `chat-tool-call-*` 样式层单写。

### 错误处理责任

- 不修改工具数据结构与渲染逻辑；
- 超长参数/结果仍由现有 `break-all`、`pre-wrap` 与滚动容器兜底。

## 最佳实践依据

- 小型信息卡片应优先使用稳定 spacing scale，而不是额外一套松散节奏；
- 内容宽度应优先随内容收口，不应被过大的最小宽度强行撑胖；
- 微调优先改现有 token，不新增样式分叉。

## 决策

采用用户确认的 **A 紧凑版**：

1. 将工具卡片头部的最小宽度从 `320px` 收紧到 `280px`；
2. 将头部与展开内容的内边距从 `10px 14px` 收紧到 `8px 12px`；
3. 将键值对间距从 `10px` 收紧到 `8px`；
4. 保持现有配色、边框、交互和展开动画不变。

## 瘦身合同

- `obsolete_paths`: `none`，本轮不新增旧新双轨；
- `retained_paths`: 保留 `chat-tool-call-*` 作为唯一入口，因为它已经是聊天主题的单一 owner；
- `single_entry_owner`: `web/src/app/globals.css` 中的 `chat-tool-call-*`；
- `line_budget`: 代码层只改现有声明值，不新增组件 helper。
