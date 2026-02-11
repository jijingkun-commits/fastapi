"""chat_repo 序列化兼容性测试。"""

from datetime import date

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
