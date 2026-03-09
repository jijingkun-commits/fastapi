"""通用功能提示词。

包含:
- 意图分类 (Intent Classification)
- 参数提取 (Parameter Extraction)
  - 待办参数
  - 查询参数
  - 图表参数
"""

# ==================== 意图分类 ====================

INTENT_CLASSIFY_PROMPT = """分类用户意图，返回 JSON。

意图类型:
- greeting: 问候、闲聊
- web_search: 联网查询（天气/新闻/价格）
- knowledge_query: 知识库查询（公司规定/文档）
- data_query: 简单数据库查询
- data_analysis: 复杂数据分析（多步骤处理）
- todo_management: 待办事项管理
- chart_drawing: 绘图请求
- image_analysis: 图片识别
- file_processing: 文件处理

用户消息: {message}

返回格式: {{"intent": "类型", "confidence": 0.0-1.0, "route_to": "目标"}}

route_to 规则:
- greeting/web_search/knowledge_query/data_query/chart_drawing/image_analysis → "supervisor"
- data_analysis/file_processing → "data_expert"
- todo_management → "todo_expert"

特殊排除:
- 讨论/删除/撤销长期记忆、用户偏好、刚才那条记忆，不属于 todo_management，应返回 route_to="supervisor"。

只返回 JSON，不要其他内容。"""


# ==================== 参数提取 ====================

# 1. 待办参数提取
TODO_PARAM_EXTRACT_PROMPT = """从用户消息中提取待办事项参数。

用户消息: {message}
当前时间: {now}

提取以下信息:
- title: 待办事项标题（必填）
- due_date: 截止时间（ISO格式，如 "2026-01-15T15:00:00"）
- priority: 优先级（low/medium/high）
- category: 分类（如: 工作/生活/学习）
- reminder: 提醒内容
- description: 详细描述

时间理解规则:
- "明天" = 当前日期 + 1天
- "下周一" = 最近的下一个周一
- "下午3点" = 15:00
- "晚上8点" = 20:00

返回 JSON 格式，无法确定的字段置为 null。"""


# 2. 查询参数提取
QUERY_PARAM_EXTRACT_PROMPT = """从用户消息中提取数据库查询参数。

用户消息: {message}

提取以下信息:
- table_name: 表名
- columns: 查询字段列表
- conditions: 查询条件字典
- limit: 结果数量限制
- order_by: 排序字段

返回 JSON 格式。"""


# 3. 图表参数提取
CHART_PARAM_EXTRACT_PROMPT = """从用户消息中提取图表绘制参数。

用户消息: {message}

提取以下信息:
- chart_type: 图表类型（line/bar/pie/scatter/circle/rectangle）
- title: 图表标题
- x_label: X轴标签
- y_label: Y轴标签
- data: 数据（如有）
- style: 样式参数

返回 JSON 格式。"""
