"""Skill admin catalog metadata 专项测试。"""

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.skill_admin_api import SkillMetadataUpdateRequest, update_skill_metadata
from app.services.skill_service import SkillService


def test_update_skill_metadata_routes_to_catalog_truth_source(monkeypatch) -> None:
    """管理面更新应写入 definition/version 真理源，而不是直接改 legacy 表。"""

    captured = {}

    def _fake_update(cls, db, *, skill_id, updates):
        captured["db"] = db
        captured["skill_id"] = skill_id
        captured["updates"] = updates
        return {"skill_id": skill_id, "updated": True, "updated_fields": sorted(updates.keys())}

    monkeypatch.setattr(SkillService, "update_skill_catalog_metadata", classmethod(_fake_update))

    payload = update_skill_metadata(
        "sql.query.author",
        SkillMetadataUpdateRequest(
            catalog_path=" finance/sql ",
            catalog_order=10,
            catalog_description=" 目录说明 ",
            when_to_use=" 统计贷款余额 ",
            trigger_phrases=[" 贷款余额 ", ""],
            conflicts_with=["copywriter", "copywriter"],
        ),
        db=object(),
    )

    assert captured["skill_id"] == "sql.query.author"
    assert captured["updates"]["catalog_path"] == "finance/sql"
    assert captured["updates"]["catalog_order"] == 10
    assert captured["updates"]["catalog_description"] == "目录说明"
    assert captured["updates"]["when_to_use"] == "统计贷款余额"
    assert captured["updates"]["trigger_phrases"] == ["贷款余额"]
    assert captured["updates"]["conflicts_with"] == ["copywriter"]
    assert payload["updated"] is True


def test_update_skill_metadata_rejects_self_conflict() -> None:
    """conflicts_with 不得包含自身 skill_id。"""

    with pytest.raises(HTTPException) as exc_info:
        update_skill_metadata(
            "sql.query.author",
            SkillMetadataUpdateRequest(conflicts_with=["sql.query.author"]),
            db=object(),
        )

    assert exc_info.value.status_code == 400
    assert "不能包含自身" in str(exc_info.value.detail)
