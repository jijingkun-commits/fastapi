import sys
import os
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add project root to path
# config.py -> core -> app -> fastapi
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import engine, SessionLocal
from app.db.base import Base

# Import all models to ensure they are registered with Base.metadata
from app.models.user import User
from app.models.todo import Todo, TodoHistory, TodoReminderQueue
from app.models.chat_message import ChatMessage
from app.models.chat_asset import ChatAsset
from app.models.data_agent_metadata import MetaTable, MetaColumn, MetaRelation
from app.models.data_permission import DataPermissionTable, DataPermissionRow, DataPermissionColumn
from app.models.token_blacklist import TokenBlacklist

def init_tables():
    print("Dropping existing tables (if any)...")
    try:
        Base.metadata.drop_all(bind=engine)
        print("✅ Old tables dropped.")
    except Exception as e:
        print(f"⚠️  Warning dropping tables: {e}")
    
    print("Creating extensions...")
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("✅ Extension 'vector' created (if not exists).")
    except Exception as e:
        print(f"⚠️  Warning creating extension: {e}")

    print("Creating all tables from SQLAlchemy models...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created.")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

def seed_users():
    print("Seeding users...")
    db: Session = SessionLocal()
    try:
        # Check/Create Admin
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            print("Creating admin user...")
            admin_user = User(
                username="admin",
                password="12345678",
                mobile="13800000000",
                role="admin",
                data_role="head_president",
                org_code="0000",
                org_name="总行",
                is_active=True,
                create_time=None,
                update_time=None
            )
            db.add(admin_user)
        
        # Check/Create Test User 'jjk'
        jjk = db.query(User).filter(User.username == "jjk").first()
        if not jjk:
            print("Creating test user 'jjk'...")
            jjk_user = User(
                username="jjk",
                password="", # Empty password as used in test_todo_api.py
                mobile="13900000000",
                create_time=None,
                update_time=None
            )
            db.add(jjk_user)
        
        db.commit()
        print("✅ Users seeded.")
    except Exception as e:
        print(f"❌ Error seeding users: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    init_tables()
    seed_users()
