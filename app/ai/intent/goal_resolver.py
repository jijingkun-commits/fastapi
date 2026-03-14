"""运行态 goal resolver。"""

from __future__ import annotations

import re
from typing import Any

_COMPOSITE_GOAL_SPLIT_PATTERN = re.compile(
    r"(?:\n+|(?:另外|然后|顺便|并且|以及|同时)\s*[，,、 ]*|再(?=(?:查|看|帮|创建|新建|加|补|问)))"
)

TODO_DOMAIN_HINTS = ("待办", "任务", "提醒", "清单", "todo")
TODO_QUERY_HINTS = ("查询", "查看", "列出", "列表", "清单", "有哪些", "显示", "看看")
TODO_CREATE_HINTS = ("创建", "新建", "新增", "添加", "记录", "记一下")
TODO_ENRICHMENT_HINTS = ("补充", "添加", "加上", "写入", "写到", "备注", "描述", "追加")
WEATHER_HINTS = ("天气", "气温", "预报")
KNOWLEDGE_HINTS = ("知识库", "文档", "规定", "流程", "手册", "开户怎么开", "怎么开")
CHART_HINTS = ("画图", "画一个", "画", "图表", "折线图", "柱状图", "饼图", "散点图", "圆")
DATA_DOMAIN_HINTS = ("数据", "指标", "报表", "统计", "数据库", "sql", "分析", "贷款", "存款", "余额")
DATA_STRONG_HINTS = ("sql", "报表", "数据库", "指标", "字段", "表", "贷款", "存款", "余额")
EXTERNAL_ENRICHMENT_HINTS = WEATHER_HINTS + ("股价", "股票", "指数", "汇率", "黄金", "油价", "行情", "基金")
RESEARCH_COMPARE_HINTS = ("对比", "比较", "差异", "区别", "异同")
RESEARCH_SYNTHESIS_HINTS = ("综合", "结合", "归纳", "汇总", "研究", "调研", "总结", "整理")
RESEARCH_EVIDENCE_HINTS = ("证据", "证据点", "出处", "来源", "依据", "引用")
RESEARCH_WEB_HINTS = ("网页", "网页资料", "网站", "联网", "网上", "网络", "web", "搜索")
RESEARCH_ATTACHMENT_HINTS = ("附件", "pdf", "pdfs", "制度文件", "材料")
RESEARCH_MULTI_SOURCE_HINTS = (
    "多来源",
    "多个来源",
    "知识库和网页",
    "网页和知识库",
    "联网和知识库",
    "结合知识库和网页",
    "两份",
    "多份",
)

TODO_OBSERVATION_COMBINE_HINTS = ("结合", "参考", "根据", "同步", "汇总", "回复用户", "结果")


def should_compile_data_handoff_from_task_description(task_description: str) -> bool:
    normalized = _normalize_text(task_description)
    if not normalized:
        return False
    return infer_primary_goal_bucket_from_text(normalized) == "data"


def should_attach_todo_observations(
    user_text: str,
    task_description: str,
    *,
    todo_action: str,
    has_todo_target: bool,
) -> bool:
    normalized_task = _normalize_text(task_description).lower()
    normalized_action = _normalize_text(todo_action).lower()
    if not normalized_action:
        if has_todo_target:
            normalized_action = "update"
        elif _contains_any(normalized_task, TODO_DOMAIN_HINTS):
            normalized_action = (
                "create"
                if _contains_any(normalized_task, TODO_CREATE_HINTS) and not _contains_any(normalized_task, TODO_QUERY_HINTS)
                else "query"
            )
        else:
            normalized_user = _normalize_text(user_text).lower()
            if _contains_any(normalized_user, TODO_DOMAIN_HINTS):
                normalized_action = (
                    "create"
                    if _contains_any(normalized_user, TODO_CREATE_HINTS) and not _contains_any(normalized_user, TODO_QUERY_HINTS)
                    else "query"
                )
    has_task_external_context = _contains_any(normalized_task, EXTERNAL_ENRICHMENT_HINTS) or _contains_any(normalized_task, KNOWLEDGE_HINTS)
    has_task_combine_hint = _contains_any(normalized_task, TODO_OBSERVATION_COMBINE_HINTS)

    if normalized_action == "query":
        return has_task_external_context and has_task_combine_hint

    if normalized_action in {"create", "update"} or has_todo_target:
        return is_todo_external_enrichment_request(user_text) or (has_task_external_context and has_task_combine_hint)

    return False


def _normalize_text(text: Any) -> str:
    return str(text or "").strip()


def _first_hint_position(text: str, hints: tuple[str, ...]) -> int:
    lowered = _normalize_text(text).lower()
    positions = [lowered.find(hint.lower()) for hint in hints if hint and lowered.find(hint.lower()) >= 0]
    return min(positions) if positions else 10**9


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    lowered = _normalize_text(text).lower()
    return any(hint.lower() in lowered for hint in hints)


def _default_goal_title(kind: str) -> str:
    if kind.startswith("research"):
        return "综合研究"
    if kind == "knowledge.lookup":
        return "知识库检索"
    if kind == "chart.render":
        return "图表结果"
    if kind.startswith("todo"):
        return "待办事项"
    if kind.startswith("data"):
        return "数据查询"
    if kind.startswith("external"):
        return "外部信息"
    return "问题回复"


def split_composite_query(user_query: str) -> list[str]:
    normalized = _normalize_text(user_query)
    if not normalized:
        return []
    parts = [
        part.strip(" ，,。；;\t")
        for part in _COMPOSITE_GOAL_SPLIT_PATTERN.split(normalized)
        if str(part).strip(" ，,。；;\t")
    ]
    return parts or [normalized]


def infer_primary_goal_kind(query_text: str) -> str:
    normalized = _normalize_text(query_text)
    lowered = normalized.lower()
    if not lowered:
        return "general.reply"

    candidates: list[tuple[int, str]] = []

    if _contains_any(lowered, TODO_DOMAIN_HINTS):
        todo_kind = "todo.create" if _contains_any(lowered, TODO_CREATE_HINTS) and not _contains_any(lowered, TODO_QUERY_HINTS) else "todo.query"
        candidates.append((_first_hint_position(lowered, TODO_DOMAIN_HINTS), todo_kind))

    if _contains_any(lowered, CHART_HINTS):
        candidates.append((_first_hint_position(lowered, CHART_HINTS), "chart.render"))

    if _is_research_request(lowered):
        candidates.append(
            (
                _first_hint_position(
                    lowered,
                    RESEARCH_COMPARE_HINTS + RESEARCH_SYNTHESIS_HINTS + RESEARCH_EVIDENCE_HINTS,
                ),
                "research.execute",
            )
        )

    if _contains_any(lowered, KNOWLEDGE_HINTS):
        candidates.append((_first_hint_position(lowered, KNOWLEDGE_HINTS), "knowledge.lookup"))

    if _contains_any(lowered, WEATHER_HINTS):
        candidates.append((_first_hint_position(lowered, WEATHER_HINTS), "external.lookup"))

    if _contains_any(lowered, DATA_DOMAIN_HINTS):
        has_todo = _contains_any(lowered, TODO_DOMAIN_HINTS)
        has_data_strong = _contains_any(lowered, DATA_STRONG_HINTS)
        if not has_todo or has_data_strong:
            candidates.append((_first_hint_position(lowered, DATA_DOMAIN_HINTS), "data.query"))

    if not candidates:
        return "general.reply"

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def infer_primary_goal_bucket_from_text(query_text: str) -> str:
    kind = infer_primary_goal_kind(query_text)
    if kind.startswith("research"):
        return "research"
    if kind.startswith("todo"):
        return "todo"
    if kind.startswith("data"):
        return "data"
    if kind.startswith("chart"):
        return "chart"
    if kind.startswith("knowledge") or kind.startswith("external"):
        return "external"
    return "general"


def resolve_runtime_goal_specs(user_query: str) -> list[dict[str, Any]]:
    parts = split_composite_query(user_query)
    if not parts:
        return [{"kind": "general.reply", "title": "问题回复", "must_answer": True, "order_hint": 0}]

    goals: list[dict[str, Any]] = []
    for index, part in enumerate(parts):
        kind = infer_primary_goal_kind(part)
        title = _default_goal_title(kind)
        if kind == "external.lookup" and _contains_any(part.lower(), WEATHER_HINTS):
            title = "天气信息"
        goals.append(
            {
                "kind": kind,
                "title": title,
                "must_answer": True,
                "order_hint": index,
            }
        )
    return goals


def is_todo_external_enrichment_request(user_text: str) -> bool:
    normalized = _normalize_text(user_text).lower()
    if not normalized:
        return False
    has_enrichment = _contains_any(normalized, TODO_ENRICHMENT_HINTS)
    has_external = _contains_any(normalized, EXTERNAL_ENRICHMENT_HINTS) or _contains_any(normalized, KNOWLEDGE_HINTS)
    return has_enrichment and has_external


def _is_research_request(normalized_query: str) -> bool:
    """判定是否属于 research.execute 语义出口。"""
    if not normalized_query:
        return False

    has_compare = _contains_any(normalized_query, RESEARCH_COMPARE_HINTS)
    has_synthesis = _contains_any(normalized_query, RESEARCH_SYNTHESIS_HINTS)
    has_evidence = _contains_any(normalized_query, RESEARCH_EVIDENCE_HINTS)
    has_attachment_source = _contains_any(normalized_query, RESEARCH_ATTACHMENT_HINTS)
    has_multi_source_phrase = _contains_any(normalized_query, RESEARCH_MULTI_SOURCE_HINTS)
    has_data_signal = _contains_any(normalized_query, DATA_STRONG_HINTS)

    source_family_count = 0
    if _contains_any(normalized_query, KNOWLEDGE_HINTS):
        source_family_count += 1
    if _contains_any(normalized_query, RESEARCH_WEB_HINTS):
        source_family_count += 1
    if has_attachment_source:
        source_family_count += 1

    if has_data_signal and not (has_multi_source_phrase or source_family_count >= 2):
        return False

    if has_compare:
        return has_multi_source_phrase or source_family_count >= 2 or not has_data_signal

    if has_synthesis or has_evidence:
        return has_multi_source_phrase or source_family_count >= 2 or (has_attachment_source and (has_evidence or has_compare))

    return False
