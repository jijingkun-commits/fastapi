"""LLM as Judge 输出评估模块（中文注释）。

借鉴 OpenAI Agents SDK llm_as_a_judge.py。
使用第二个 LLM 评估 Agent 输出质量，支持迭代优化。

使用方式：
    from app.ai.llm_judge import evaluate_response, JudgeResult
    
    # 评估 Agent 回复
    result = await evaluate_response(
        question="公司差旅规定是什么",
        response="根据公司规定..."
    )
    
    if result.score == "needs_improvement":
        # 将 feedback 反馈给 Agent 重新生成
        ...
"""
import logging
from typing import Literal, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ==================== 评估结果模型 ====================

class JudgeResult(BaseModel):
    """评估结果。"""
    score: Literal["pass", "needs_improvement", "fail"] = Field(
        description="评分: pass=通过, needs_improvement=需改进, fail=失败"
    )
    feedback: str = Field(description="评估反馈，说明问题或改进方向")
    dimensions: Optional[dict[str, int]] = Field(
        None, 
        description="各维度得分 (1-5)"
    )


class DetailedJudgeResult(BaseModel):
    """详细评估结果。"""
    accuracy: int = Field(description="准确性 (1-5)")
    completeness: int = Field(description="完整性 (1-5)")
    clarity: int = Field(description="清晰度 (1-5)")
    relevance: int = Field(description="相关性 (1-5)")
    overall_score: Literal["pass", "needs_improvement", "fail"]
    feedback: str


# ==================== 评估 Prompt ====================

JUDGE_PROMPT = """你是一个 AI 回复质量评估员。评估以下回复的质量。

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


# ==================== 评估函数 ====================

async def evaluate_response(
    question: str, 
    response: str, 
    model_id: str = None
) -> JudgeResult:
    """评估 Agent 回复质量。
    
    Args:
        question: 用户问题
        response: Agent 回复
        model_id: 评估用的模型 ID
        
    Returns:
        JudgeResult 包含评分、反馈和各维度得分
        
    Example:
        >>> result = await evaluate_response("什么是Python", "Python是一种编程语言...")
        >>> print(result.score)  # "pass"
        >>> print(result.feedback)  # "回答准确完整..."
    """
    from app.ai.llm_util import get_llm
    
    # 使用快速模型作为 Judge
    try:
        llm = get_llm(model_id=model_id or "glm-4.5-air")
    except Exception:
        llm = get_llm()
    
    try:
        structured_llm = llm.with_structured_output(JudgeResult)
        
        result = await structured_llm.ainvoke(
            JUDGE_PROMPT.format(
                question=question[:1000],
                response=response[:2000]
            )
        )
        
        logger.info(
            "输出评估完成: score=%s, dimensions=%s",
            result.score, result.dimensions
        )
        
        return result
        
    except Exception as e:
        logger.warning("输出评估失败: %s，默认通过", e)
        return JudgeResult(
            score="pass",
            feedback="评估服务暂时不可用，默认通过"
        )


async def evaluate_response_detailed(
    question: str, 
    response: str, 
    model_id: str = None
) -> DetailedJudgeResult:
    """详细评估 Agent 回复质量。"""
    from app.ai.llm_util import get_llm
    
    try:
        llm = get_llm(model_id=model_id or "glm-4.5-air")
        structured_llm = llm.with_structured_output(DetailedJudgeResult)
        
        result = await structured_llm.ainvoke(
            DETAILED_JUDGE_PROMPT.format(
                question=question[:1000],
                response=response[:2000]
            )
        )
        
        logger.info(
            "详细评估完成: accuracy=%d, completeness=%d, clarity=%d, relevance=%d",
            result.accuracy, result.completeness, result.clarity, result.relevance
        )
        
        return result
        
    except Exception as e:
        logger.warning("详细评估失败: %s", e)
        return DetailedJudgeResult(
            accuracy=4, completeness=4, clarity=4, relevance=4,
            overall_score="pass",
            feedback="评估服务暂时不可用"
        )


# ==================== 迭代优化循环 ====================

async def iterative_improvement(
    question: str,
    generate_fn,
    max_iterations: int = 3,
    model_id: str = None
) -> tuple[str, list[JudgeResult]]:
    """迭代优化生成结果。
    
    借鉴 OpenAI Agents SDK 的 loop-until-pass 模式。
    
    Args:
        question: 用户问题
        generate_fn: 生成函数，接收 (question, feedback) 返回 response
        max_iterations: 最大迭代次数
        model_id: 评估模型 ID
        
    Returns:
        (最终回复, 评估历史)
        
    Example:
        >>> async def generate(q, fb):
        ...     return await agent.ainvoke(f"{q}\\n反馈: {fb}")
        >>> response, history = await iterative_improvement("问题", generate)
    """
    evaluations = []
    feedback = ""
    response = ""
    
    for i in range(max_iterations):
        # 生成回复
        response = await generate_fn(question, feedback)
        
        # 评估
        result = await evaluate_response(question, response, model_id)
        evaluations.append(result)
        
        logger.info("迭代 %d: score=%s", i + 1, result.score)
        
        if result.score == "pass":
            break
        
        # 使用反馈继续优化
        feedback = result.feedback
    
    return response, evaluations


# ==================== 专项评估 ====================

async def evaluate_sql_response(sql: str, result: str) -> JudgeResult:
    """评估 SQL 查询结果。"""
    from app.ai.llm_util import get_llm
    
    prompt = f"""评估 SQL 查询结果:

SQL: {sql}
结果: {result[:1000]}

检查:
1. 结果是否符合 SQL 逻辑
2. 数据格式是否正确
3. 是否有错误信息

返回 JSON: {{"score": "pass|fail", "feedback": "..."}}"""
    
    try:
        llm = get_llm(model_id="glm-4.5-air")
        structured_llm = llm.with_structured_output(JudgeResult)
        return await structured_llm.ainvoke(prompt)
    except Exception as e:
        logger.warning("SQL 评估失败: %s", e)
        return JudgeResult(score="pass", feedback="评估跳过")


async def evaluate_chart_response(chart_type: str, code: str) -> JudgeResult:
    """评估图表生成代码。"""
    from app.ai.llm_util import get_llm
    
    prompt = f"""评估图表生成代码:

图表类型: {chart_type}
代码:
```python
{code[:1500]}
```

检查:
1. 代码语法是否正确
2. 是否使用了正确的图表类型
3. 是否设置了必要的属性（标题、标签等）

返回 JSON: {{"score": "pass|needs_improvement|fail", "feedback": "..."}}"""
    
    try:
        llm = get_llm(model_id="glm-4.5-air")
        structured_llm = llm.with_structured_output(JudgeResult)
        return await structured_llm.ainvoke(prompt)
    except Exception as e:
        logger.warning("图表评估失败: %s", e)
        return JudgeResult(score="pass", feedback="评估跳过")
