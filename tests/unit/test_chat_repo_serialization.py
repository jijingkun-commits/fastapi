"""chat_repo 序列化兼容性测试。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from app.core.message_content import normalize_legacy_message_content
from app.repositories import chat_repo
from app.repositories.chat_repo import save_message


class _FakeSession:
    def __init__(self):
        self.added = None

    def add(self, obj):
        self.added = obj

    def commit(self):
        return None

    def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 1


def test_save_message_serializes_metadata_with_date():
    """metadata 含 date 时应可入库，不应抛异常。"""

    db = _FakeSession()
    msg = save_message(
        db,
        user_id=1,
        thread_id="thread-ser",
        role="ai",
        content_type="markdown",
        content="ok",
        extra_data={
            "data_type": "sql_result",
            "data": {"rows": [{"业务日期": date(2025, 6, 30), "贷款余额": 1.23}]},
        },
    )

    assert msg.id == 1
    assert db.added.extra_data["data"]["rows"][0]["业务日期"] == "2025-06-30"


def test_save_conversation_from_messages_normalizes_ai_block_content():
    """后处理保存时，AI 的 block 列表应归一化为可读文本。"""

    messages = [
        SimpleNamespace(type="human", content="请总结", id="human-1", name=None),
        SimpleNamespace(
            type="ai",
            content=[
                {"type": "text", "text": "第一段。"},
                {"type": "text", "text": "第二段。"},
            ],
            additional_kwargs={},
            name=None,
        ),
    ]

    with patch("app.repositories.chat_repo.save_message") as mock_save:
        chat_repo.save_conversation_from_messages(
            db=object(),
            user_id=1,
            thread_id="thread-fmt",
            messages=messages,
        )

    kwargs = mock_save.call_args.kwargs
    assert kwargs["role"] == "ai"
    assert kwargs["content"] == "第一段。第二段。"


def test_normalize_legacy_message_content_parses_python_literal():
    """历史遗留的 Python repr 字符串应被解析为正文文本。"""

    legacy_content = "[{'type': 'text', 'text': '历史回复内容'}]"

    assert normalize_legacy_message_content(legacy_content) == "历史回复内容"


def test_normalize_legacy_message_content_keeps_plain_text():
    """普通文本不应被误处理。"""

    plain_content = "普通 Markdown 正文"

    assert normalize_legacy_message_content(plain_content) == plain_content



def test_save_conversation_from_messages_preserves_structured_sql_result_for_refresh_replay():
    """最终总结消息不带结构化结果时，落库仍应保留本轮 sql_result 图表/表格。"""

    chart_payload = {
        "type": "bar",
        "x_key": "客户名称",
        "y_key": "贷款余额",
        "data": [
            {"客户名称": "张三", "贷款余额": 100},
            {"客户名称": "李四", "贷款余额": 80},
        ],
    }
    sql_payload = {
        "data_type": "sql_result",
        "data": {
            "rows": [
                {"客户名称": "张三", "贷款余额": 100},
                {"客户名称": "李四", "贷款余额": 80},
            ],
            "columns": ["客户名称", "贷款余额"],
            "chart": chart_payload,
            "total_rows": 2,
            "sql": "select * from loan_balance order by 贷款余额 desc limit 2",
        },
        "message": "数据查询完成，共返回 2 条记录。",
        "sequence_number": 4,
        "envelope": {"id": "evt-sql-1", "sequence_number": 4},
    }
    messages = [
        SimpleNamespace(type="human", content="查前两名贷款客户", id="human-1", name=None),
        SimpleNamespace(
            type="ai",
            content="数据查询完成，共返回 2 条记录。",
            additional_kwargs={
                "data_type": "sql_result",
                "data": sql_payload["data"],
                "message": sql_payload["message"],
                "sequence_number": sql_payload["sequence_number"],
                "envelope": sql_payload["envelope"],
            },
            name=None,
        ),
        SimpleNamespace(
            type="ai",
            content="按你的问题顺序，逐项回复如下：1. 外部信息... 2. 数据查询...",
            additional_kwargs={
                "skill_runtime": {"runtime_mode": "session", "catalog_version": "v1", "visible_skill_count": 1, "loaded_skills": [], "replay_source": "live"},
            },
            name=None,
        ),
    ]

    with patch("app.repositories.chat_repo.save_message") as mock_save:
        chat_repo.save_conversation_from_messages(
            db=object(),
            user_id=1,
            thread_id="thread-refresh-sql",
            messages=messages,
        )

    kwargs = mock_save.call_args.kwargs
    extra_data = kwargs["extra_data"]
    assert extra_data["skill_runtime"]["runtime_mode"] == "session"
    assert extra_data["data_type"] == "sql_result"
    assert extra_data["data"]["chart"] == chart_payload
    assert extra_data["data"]["rows"][0]["客户名称"] == "张三"
    assert extra_data["result_events"][0]["data"]["chart"] == chart_payload
    assert extra_data["result_events"][0]["envelope"]["id"] == "evt-sql-1"
