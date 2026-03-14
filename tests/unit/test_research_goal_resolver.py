"""research goal resolver 单元测试。"""

from app.ai.intent.goal_resolver import (
    infer_primary_goal_bucket_from_text,
    infer_primary_goal_kind,
    resolve_runtime_goal_specs,
)


def test_infer_primary_goal_kind_should_route_multisource_compare_to_research() -> None:
    """多来源研究/对比请求应在 intent 层落到 research，而不是 external/general。"""
    query = "综合知识库和网页资料，帮我对比两种报销口径的差异"

    assert infer_primary_goal_kind(query) == "research.execute"
    assert infer_primary_goal_bucket_from_text(query) == "research"


def test_infer_primary_goal_kind_should_keep_single_knowledge_lookup_atomic() -> None:
    """单次知识库直查应继续保留 atomic knowledge.lookup 路径。"""
    query = "公司请假流程是什么？"

    assert infer_primary_goal_kind(query) == "knowledge.lookup"
    assert infer_primary_goal_bucket_from_text(query) == "external"


def test_infer_primary_goal_kind_should_keep_tabular_compare_as_data_query() -> None:
    """Excel/贷款余额等强数据语义不应被 research compare 词误升级。"""
    query = "把这个 Excel 里的贷款余额按分行统计一下，并对比趋势"

    assert infer_primary_goal_kind(query) == "data.query"
    assert infer_primary_goal_bucket_from_text(query) == "data"


def test_infer_primary_goal_kind_should_recognize_attachment_research_goal() -> None:
    """带附件语义的研究型总结/证据请求也应暴露 research bucket。"""
    query = "根据这两份 PDF 制度文件，总结差异并给出证据点"

    assert infer_primary_goal_kind(query) == "research.execute"
    assert infer_primary_goal_bucket_from_text(query) == "research"


def test_resolve_runtime_goal_specs_should_preserve_research_and_todo_boundary() -> None:
    """复合请求应同时保留 research goal 和 todo goal，不回退成 general。"""
    goals = resolve_runtime_goal_specs("综合知识库和网页资料，帮我对比两种报销口径的差异，然后列出今天待办")

    assert [goal["kind"] for goal in goals] == ["research.execute", "todo.query"]
    assert [goal["title"] for goal in goals] == ["综合研究", "待办事项"]
