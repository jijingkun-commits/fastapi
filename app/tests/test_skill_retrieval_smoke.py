"""Skill Retrieval Smoke Test via Database Integration.

This test simulates the skill retrieval process within the CI environment,
verifying that the vector search mechanism works correctly with the database.
It mocks the embedding generation to avoid external API calls.
"""
import pytest
from unittest.mock import patch
from app.services.skill_service import SkillService
from app.models.agent_skill import AgentSkill
from app.db.session import get_db

# Dimension must match app/models/agent_skill.py definition (2048)
EMBEDDING_DIM = 2048

@pytest.fixture
def db_session():
    """Get database session."""
    db = next(get_db())
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
    # 1. Clean up existing test skills (optional)
    db_session.query(AgentSkill).filter(AgentSkill.skill_id == "smoke-test-skill").delete()
    db_session.commit()

    # 2. Insert a dummy skill with known embedding
    # The embedding matches the mock return value exactly
    vector = [0.0] * EMBEDDING_DIM
    vector[0] = 1.0
    
    skill = AgentSkill(
        skill_id="smoke-test-skill",
        name="Smoke Test Skill",
        description="A dummy skill for CI smoke testing",
        content="This is the content of the smoke test skill.",
        file_hash="dummy_hash",
        embedding=vector
    )
    db_session.add(skill)
    db_session.commit()
    
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
        
        print(f"\n✅ Skill retrieval smoke test passed. Found skill: {found_skill.name}")
        
    finally:
        # 5. Cleanup
        db_session.query(AgentSkill).filter(AgentSkill.skill_id == "smoke-test-skill").delete()
        db_session.commit()
