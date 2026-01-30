"""LLM Judge 专用提示词。

包含:
- 输出质量评估 (Output Judge)
- 详细评分 (Detailed Judge)
"""

# ==================== 输出质量评估 ====================

OUTPUT_JUDGE_PROMPT = """你是一个 AI 回复质量评估员。评估以下回复的质量。

## 用户问题
{question}

## Agent 回复
{response}

## 评估维度

1. **准确性**: 回答是否正确、无事实错误
2. **完整性**: 是否回答了用户的所有问题
3. **清晰度**: 表述是否清楚易懂
4. **相关性**: 是否切题，没有无关信息

## 评分标准

- **pass**: 所有维度达到4分以上，无明显问题
- **needs_improvement**: 有1-2个维度需要改进（3分左右）
- **fail**: 有严重错误或完全偏题

## 返回格式

返回 JSON:
{{
    "score": "pass|needs_improvement|fail",
    "feedback": "具体的评估反馈和改进建议",
    "dimensions": {{
        "accuracy": 1-5,
        "completeness": 1-5,
        "clarity": 1-5,
        "relevance": 1-5
    }}
}}"""


# ==================== 详细评分 ====================

DETAILED_JUDGE_PROMPT = """评估 AI 回复质量，返回详细评分。

用户问题: {question}
Agent 回复: {response}

按 1-5 分评估:
- accuracy: 准确性
- completeness: 完整性  
- clarity: 清晰度
- relevance: 相关性

overall_score 规则:
- 平均 >= 4.0: "pass"
- 平均 >= 2.5: "needs_improvement"
- 平均 < 2.5: "fail"

返回 JSON 格式。"""
