import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import DATABASE_URL
from app.services.llm_config_service import LLMConfigService
from app.ai.semantic.vanna_client import get_vanna

def init_services():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        LLMConfigService.load_from_db(session)
    finally:
        session.close()

def test_retrieval():
    init_services()
    print("Initializing Vanna Client...")
    vn = get_vanna()
    
    question = "存贷利差怎么算的？"
    print(f"\nQuestion: {question}")
    
    print("Retrieving related metrics...")
    docs = vn.get_related_documentation(question)
    
    print("\n--- Retrieved Documentation ---")
    for doc in docs:
        print(doc)
        print("-" * 30)
        
    if not docs:
        print("No matches found.")
    else:
        print(f"Found {len(docs)} matches.")

if __name__ == "__main__":
    test_retrieval()
