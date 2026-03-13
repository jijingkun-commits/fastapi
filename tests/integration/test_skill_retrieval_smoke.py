"""Skill Retrieval Smoke Test via Database Integration.

This test simulates the skill retrieval process within the CI environment,
verifying that the vector search mechanism works correctly with the database.
It mocks the embedding generation to avoid external API calls.
"""
from datetime import datetime, timezone

import pytest
from unittest.mock import patch
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from app.services.skill_service import SkillService
from app.models.agent_skill import AgentSkillDefinition, AgentSkillVersion
from app.db.session import get_db

# Dimension must match app/models/agent_skill.py definition (2048)
EMBEDDING_DIM = 2048

@pytest.fixture
def db_session():
    """Get database session."""
    try:
        db = next(get_db())
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"数据库不可用，跳过 skill retrieval smoke 测试: {exc}")
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def mock_embedding():
    """Mock get_embedding to return a fixed vector."""
    with patch("app.services.skill_service.get_embedding") as mock:
        # Return a normalized vector of correct dimension
        # Using a simple vector where only first element is 1.0 for simplicity
        vector = [0.0] * EMBEDDING_DIM
        vector[0] = 1.0
        mock.return_value = vector
        yield mock

def test_skill_retrieval_smoke(db_session, mock_embedding):
    """Smoke test: Verify skill retrieval infrastructure works."""
    required_tables = {
        "t_agent_skill_definitions": {"skill_id", "name", "is_enabled", "scope"},
        "t_agent_skill_versions": {
            "definition_id",
            "skill_id",
            "version",
            "status",
            "name",
            "content",
            "embedding",
            "is_enabled",
            "auto_enabled",
            "priority",
            "scope",
            "trigger_phrases",
            "conflicts_with",
        },
    }
    inspector = inspect(db_session.bind)

    for table_name, required_columns in required_tables.items():
        try:
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        except SQLAlchemyError as exc:
            pytest.skip(f"无法读取 {table_name} 结构，跳过 smoke 测试: {exc}")
        missing_columns = sorted(required_columns - existing_columns)
        if missing_columns:
            pytest.skip(f"{table_name} 缺少列: {missing_columns}")

    # 1. Clean up existing test skills (optional)
    try:
        db_session.query(AgentSkillVersion).filter(AgentSkillVersion.skill_id == "smoke-test-skill").delete()
        db_session.query(AgentSkillDefinition).filter(AgentSkillDefinition.skill_id == "smoke-test-skill").delete()
        db_session.commit()
    except SQLAlchemyError as exc:
        pytest.skip(f"数据库不可写，跳过 smoke 测试: {exc}")

    # 2. Insert a dummy published skill version with known embedding
    # The embedding matches the mock return value exactly
    vector = [0.0] * EMBEDDING_DIM
    vector[0] = 1.0

    definition = AgentSkillDefinition(
        skill_id="smoke-test-skill",
        name="Smoke Test Skill",
        description="A dummy skill for CI smoke testing",
        scope="global",
        is_enabled=True,
    )
    try:
        db_session.add(definition)
        db_session.flush()

        version = AgentSkillVersion(
            definition_id=definition.id,
            skill_id="smoke-test-skill",
            version="v1",
            status=SkillService.VERSION_STATUS_PUBLISHED,
            name="Smoke Test Skill",
            description="A dummy skill for CI smoke testing",
            content="This is the content of the smoke test skill.",
            file_hash="dummy_hash",
            embedding=vector,
            is_enabled=True,
            auto_enabled=True,
            priority=100,
            scope="global",
            trigger_phrases=[],
            conflicts_with=[],
            published_at=datetime.now(timezone.utc),
        )
        db_session.add(version)
        db_session.commit()
    except SQLAlchemyError as exc:
        pytest.skip(f"数据库不可写，跳过 smoke 测试: {exc}")
    
    try:
        # 3. Search using the SkillService
        # limit=1, threshold=0.0 (to ensure match even if floating point issues, though exact match should be 1.0)
        # We rely on mock returning the SAME vector for the query
        results = SkillService.search_skills("test query", top_k=1, threshold=0.9)
        
        # 4. Verify
        assert len(results) > 0, "Should find at least one skill"
        found_skill = results[0]
        assert found_skill.skill_id == "smoke-test-skill", "Should find the smoke test skill"
        assert found_skill.name == "Smoke Test Skill"

        debug = SkillService.search_skills_debug(
            "test query",
            top_k=2,
            threshold=0.0,
            auto_only=False,
        )
        assert "skill_candidates" in debug
        assert "selected_skill_ids" in debug
        assert "skill_injection_meta" in debug
        assert "retrieval_log" in debug
        assert any(item.get("skill_id") == "smoke-test-skill" for item in debug["skill_candidates"])
        assert debug["retrieval_log"]["selected_skill_ids"] == debug["selected_skill_ids"]
        assert debug["retrieval_log"]["query_hash"]

        print(f"\n✅ Skill retrieval smoke test passed. Found skill: {found_skill.name}")
        
    finally:
        # 5. Cleanup
        try:
            db_session.query(AgentSkillVersion).filter(AgentSkillVersion.skill_id == "smoke-test-skill").delete()
            db_session.query(AgentSkillDefinition).filter(AgentSkillDefinition.skill_id == "smoke-test-skill").delete()
            db_session.commit()
        except SQLAlchemyError:
            pass
