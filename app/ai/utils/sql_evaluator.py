"""SQL 质量评估模块（中文注释）。

提供多维度的 SQL 质量评估：
1. 语法正确性（sqlglot 解析）
2. 语义正确性（LLM 评估）
3. 检索质量（DDL/指标匹配）
4. 性能评估（索引、复杂度）

使用方式：
    from app.ai.utils.sql_evaluator import evaluate_sql_quality, SQLEvaluationResult
    
    result = await evaluate_sql_quality(
        question="本月存款余额是多少",
        sql="SELECT SUM(balance) FROM deposits WHERE ...",
        ddl_context=["CREATE TABLE deposits ..."],
        metric_matched="存款余额"
    )
    
    print(result.overall_score)  # "good" | "acceptable" | "poor"
    print(result.suggestions)    # ["建议添加 LIMIT", "..."]
"""
import logging
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ==================== 评估结果模型 ====================

class SQLSyntaxResult(BaseModel):
    """语法检查结果。"""
    is_valid: bool = Field(description="语法是否正确")
    error: Optional[str] = Field(None, description="语法错误信息")
    tables: List[str] = Field(default_factory=list, description="引用的表名")
    query_type: str = Field("UNKNOWN", description="查询类型")


class SQLSemanticResult(BaseModel):
    """语义评估结果（LLM 评估）。"""
    score: Literal["correct", "partial", "incorrect"] = Field(
        description="语义正确性: correct=完全正确, partial=部分正确, incorrect=错误"
    )
    alignment: int = Field(description="与用户意图的对齐度 (1-5)")
    explanation: str = Field(description="评估说明")
    issues: List[str] = Field(default_factory=list, description="发现的问题")


class RetrievalQualityResult(BaseModel):
    """检索质量结果。"""
    ddl_coverage: float = Field(description="DDL 覆盖率 (0-1)")
    metric_matched: bool = Field(description="是否匹配到指标")
    metric_similarity: Optional[float] = Field(None, description="指标相似度")
    missing_tables: List[str] = Field(default_factory=list, description="缺失的表")


class PerformanceResult(BaseModel):
    """性能评估结果。"""
    has_limit: bool = Field(description="是否有 LIMIT")
    has_index_hint: bool = Field(False, description="是否使用索引")
    complexity: Literal["low", "medium", "high"] = Field(description="查询复杂度")
    warnings: List[str] = Field(default_factory=list, description="性能警告")


class SQLEvaluationResult(BaseModel):
    """综合评估结果。"""
    overall_score: Literal["good", "acceptable", "poor"] = Field(
        description="综合评分: good=优秀, acceptable=可接受, poor=较差"
    )
    syntax: SQLSyntaxResult
    semantic: Optional[SQLSemanticResult] = None
    retrieval: Optional[RetrievalQualityResult] = None
    performance: PerformanceResult
    suggestions: List[str] = Field(default_factory=list, description="改进建议")
    confidence: float = Field(description="评估置信度 (0-1)")


# ==================== 评估函数 ====================

def evaluate_syntax(sql: str) -> SQLSyntaxResult:
    """评估 SQL 语法正确性。
    
    使用 sqlglot 进行语法解析。
    """
    from app.ai.utils.sql_parser import (
        validate_sql_syntax, 
        extract_tables_from_sql,
        get_query_type
    )
    
    is_valid, error = validate_sql_syntax(sql)
    tables = list(extract_tables_from_sql(sql)) if is_valid else []
    query_type = get_query_type(sql)
    
    return SQLSyntaxResult(
        is_valid=is_valid,
        error=error,
        tables=tables,
        query_type=query_type
    )


def evaluate_performance(sql: str) -> PerformanceResult:
    """评估 SQL 性能。"""
    sql_upper = sql.upper()
    warnings = []
    
    # 检查 LIMIT
    has_limit = "LIMIT" in sql_upper
    if not has_limit:
        warnings.append("缺少 LIMIT 子句，可能返回大量数据")
    
    # 检查 SELECT *
    if "SELECT *" in sql_upper or "SELECT  *" in sql_upper:
        warnings.append("使用 SELECT * 可能影响性能，建议指定具体列")
    
    # 检查子查询嵌套
    subquery_count = sql_upper.count("SELECT") - 1
    if subquery_count > 2:
        warnings.append(f"嵌套子查询过多 ({subquery_count} 层)，可能影响性能")
    
    # 检查 CROSS JOIN
    if "CROSS JOIN" in sql_upper:
        warnings.append("使用 CROSS JOIN 可能产生笛卡尔积")
    
    # 评估复杂度
    complexity = "low"
    if any(kw in sql_upper for kw in ["JOIN", "UNION", "INTERSECT", "EXCEPT"]):
        complexity = "medium"
    if subquery_count > 1 or ("JOIN" in sql_upper and "GROUP BY" in sql_upper):
        complexity = "high"
    
    return PerformanceResult(
        has_limit=has_limit,
        has_index_hint=False,  # PostgreSQL 通常不需要显式索引提示
        complexity=complexity,
        warnings=warnings
    )


def evaluate_retrieval(
    sql: str,
    ddl_context: List[str] = None,
    metric_matched: str = None,
    metric_similarity: float = None
) -> RetrievalQualityResult:
    """评估检索质量。"""
    from app.ai.utils.sql_parser import extract_tables_from_sql
    
    # 提取 SQL 中使用的表
    used_tables = extract_tables_from_sql(sql)
    
    # 计算 DDL 覆盖率
    ddl_tables = set()
    if ddl_context:
        import re
        for ddl in ddl_context:
            # 从 CREATE TABLE 语句中提取表名
            match = re.search(r'CREATE TABLE\s+(\w+)', ddl, re.IGNORECASE)
            if match:
                ddl_tables.add(match.group(1).lower())
    
    # 计算覆盖率
    if used_tables:
        covered = sum(1 for t in used_tables if t.lower() in ddl_tables or t.split('.')[-1].lower() in ddl_tables)
        ddl_coverage = covered / len(used_tables)
    else:
        ddl_coverage = 1.0
    
    # 缺失的表
    missing = [t for t in used_tables if t.lower() not in ddl_tables and t.split('.')[-1].lower() not in ddl_tables]
    
    return RetrievalQualityResult(
        ddl_coverage=ddl_coverage,
        metric_matched=bool(metric_matched),
        metric_similarity=metric_similarity,
        missing_tables=missing
    )


async def evaluate_semantic(
    question: str,
    sql: str,
    ddl_context: List[str] = None,
    model_id: str = None
) -> SQLSemanticResult:
    """使用 LLM 评估语义正确性。
    
    检查 SQL 是否准确回答了用户问题。
    """
    from app.ai.llm_util import get_llm
    
    ddl_str = "\n".join(ddl_context[:3]) if ddl_context else "无可用 DDL"
    
    prompt = f"""你是一个 SQL 质量评估专家。评估以下 SQL 是否正确回答了用户问题。

## 用户问题
{question}

## 生成的 SQL
```sql
{sql}
```

## 可用表结构
{ddl_str[:2000]}

## 评估维度

1. **意图对齐**: SQL 是否准确理解了用户想要查询的内容
2. **逻辑正确**: WHERE、GROUP BY、聚合函数等是否符合业务逻辑
3. **完整性**: 是否包含了必要的筛选条件（如时间范围）

## 返回格式

返回 JSON:
{{
    "score": "correct|partial|incorrect",
    "alignment": 1-5,
    "explanation": "评估说明",
    "issues": ["问题1", "问题2"]
}}

注意: 
- score="correct": 完全正确，可直接执行
- score="partial": 大体正确但有小问题
- score="incorrect": 明显错误，需要重新生成"""

    try:
        llm = get_llm(model_id=model_id or "glm-4.5-air")
        structured_llm = llm.with_structured_output(SQLSemanticResult)
        result = await structured_llm.ainvoke(prompt)
        
        logger.info(
            "SQL 语义评估完成: score=%s, alignment=%d",
            result.score, result.alignment
        )
        
        return result
        
    except Exception as e:
        logger.warning("SQL 语义评估失败: %s", e)
        return SQLSemanticResult(
            score="partial",
            alignment=3,
            explanation="评估服务暂时不可用",
            issues=[]
        )


async def evaluate_sql_quality(
    question: str,
    sql: str,
    ddl_context: List[str] = None,
    metric_matched: str = None,
    metric_similarity: float = None,
    skip_semantic: bool = False,
    model_id: str = None
) -> SQLEvaluationResult:
    """综合评估 SQL 质量。
    
    Args:
        question: 用户原始问题
        sql: 生成的 SQL
        ddl_context: 检索到的 DDL 上下文
        metric_matched: 匹配到的指标名称
        metric_similarity: 指标匹配相似度
        skip_semantic: 是否跳过语义评估（节省 API 调用）
        model_id: LLM 模型 ID
        
    Returns:
        SQLEvaluationResult 综合评估结果
    """
    suggestions = []
    
    # 1. 语法检查
    syntax = evaluate_syntax(sql)
    if not syntax.is_valid:
        return SQLEvaluationResult(
            overall_score="poor",
            syntax=syntax,
            performance=PerformanceResult(
                has_limit=False, complexity="low", warnings=["语法错误"]
            ),
            suggestions=["修复语法错误: " + (syntax.error or "未知错误")],
            confidence=1.0
        )
    
    # 2. 性能评估
    performance = evaluate_performance(sql)
    suggestions.extend(performance.warnings)
    
    # 3. 检索质量评估
    retrieval = evaluate_retrieval(sql, ddl_context, metric_matched, metric_similarity)
    if retrieval.missing_tables:
        suggestions.append(f"DDL 未覆盖表: {', '.join(retrieval.missing_tables)}")
    if retrieval.ddl_coverage < 0.5:
        suggestions.append("DDL 检索覆盖率较低，建议优化检索策略")
    
    # 4. 语义评估（可选）
    semantic = None
    if not skip_semantic:
        semantic = await evaluate_semantic(question, sql, ddl_context, model_id)
        if semantic.issues:
            suggestions.extend(semantic.issues)
    
    # 5. 计算综合评分
    overall_score = _calculate_overall_score(syntax, semantic, retrieval, performance)
    
    # 6. 计算置信度
    confidence = _calculate_confidence(syntax, semantic, retrieval)
    
    return SQLEvaluationResult(
        overall_score=overall_score,
        syntax=syntax,
        semantic=semantic,
        retrieval=retrieval,
        performance=performance,
        suggestions=suggestions,
        confidence=confidence
    )


def _calculate_overall_score(
    syntax: SQLSyntaxResult,
    semantic: Optional[SQLSemanticResult],
    retrieval: Optional[RetrievalQualityResult],
    performance: PerformanceResult
) -> Literal["good", "acceptable", "poor"]:
    """计算综合评分。"""
    
    # 语法错误 -> poor
    if not syntax.is_valid:
        return "poor"
    
    # 语义评估
    semantic_score = 3  # 默认中等
    if semantic:
        if semantic.score == "correct":
            semantic_score = 5
        elif semantic.score == "partial":
            semantic_score = 3
        else:
            semantic_score = 1
    
    # 检索质量
    retrieval_score = 3
    if retrieval:
        if retrieval.ddl_coverage >= 0.8 and retrieval.metric_matched:
            retrieval_score = 5
        elif retrieval.ddl_coverage >= 0.5:
            retrieval_score = 3
        else:
            retrieval_score = 2
    
    # 性能评分
    perf_score = 4
    if len(performance.warnings) >= 2:
        perf_score = 2
    elif len(performance.warnings) == 1:
        perf_score = 3
    
    # 加权平均
    avg = (semantic_score * 0.5 + retrieval_score * 0.3 + perf_score * 0.2)
    
    if avg >= 4.0:
        return "good"
    elif avg >= 2.5:
        return "acceptable"
    else:
        return "poor"


def _calculate_confidence(
    syntax: SQLSyntaxResult,
    semantic: Optional[SQLSemanticResult],
    retrieval: Optional[RetrievalQualityResult]
) -> float:
    """计算评估置信度。"""
    confidence = 0.5  # 基础置信度
    
    # 语法检查完成 +0.2
    if syntax.is_valid:
        confidence += 0.2
    
    # 语义评估完成 +0.2
    if semantic:
        confidence += 0.2
    
    # 检索质量评估完成 +0.1
    if retrieval:
        confidence += 0.1
        # 高覆盖率 +0.1
        if retrieval.ddl_coverage >= 0.8:
            confidence += 0.1
    
    return min(confidence, 1.0)


# ==================== 快捷评估函数 ====================

def quick_evaluate(sql: str) -> dict:
    """快速评估（仅语法和性能，不调用 LLM）。
    
    用于流水线中的快速检查。
    
    Returns:
        {"is_valid": bool, "warnings": List[str], "query_type": str}
    """
    syntax = evaluate_syntax(sql)
    performance = evaluate_performance(sql)
    
    return {
        "is_valid": syntax.is_valid,
        "error": syntax.error,
        "warnings": performance.warnings,
        "query_type": syntax.query_type,
        "tables": syntax.tables,
        "complexity": performance.complexity
    }


async def should_retry(
    question: str,
    sql: str,
    error_message: str = None,
    model_id: str = None
) -> tuple[bool, str]:
    """判断是否应该重试 SQL 生成。
    
    Args:
        question: 用户问题
        sql: 当前生成的 SQL
        error_message: 执行错误信息
        model_id: LLM 模型 ID
        
    Returns:
        (should_retry: bool, feedback: str)
    """
    from app.ai.llm_util import get_llm
    
    prompt = f"""分析以下 SQL 生成失败的原因，判断是否应该重试。

用户问题: {question}
生成的 SQL: {sql}
错误信息: {error_message or "无"}

判断标准:
- 如果是语法错误或表/列名错误，可以重试（修正后可能成功）
- 如果是逻辑错误或不可恢复的错误，不应重试
- 如果 SQL 本身没问题但执行超时，可以重试（添加 LIMIT）

返回 JSON:
{{
    "should_retry": true/false,
    "feedback": "给 LLM 的反馈，指导如何修正 SQL"
}}"""

    try:
        llm = get_llm(model_id=model_id or "glm-4.5-air")
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        import json
        result = json.loads(content)
        return result.get("should_retry", False), result.get("feedback", "")
        
    except Exception as e:
        logger.warning("重试判断失败: %s", e)
        # 默认策略：语法错误不重试，其他重试
        from app.ai.utils.sql_parser import validate_sql_syntax
        is_valid, _ = validate_sql_syntax(sql)
        
        if not is_valid:
            return True, "SQL 语法错误，请检查并修正"
        elif error_message and "does not exist" in error_message.lower():
            return True, f"表或列不存在，请检查可用的表结构。错误: {error_message}"
        else:
            return False, ""
