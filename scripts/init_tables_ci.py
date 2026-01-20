import sys
import os
from pathlib import Path
from sqlalchemy.orm import Session

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
# If there are other models, they should be imported here.

def init_tables():
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
                password="12345678", # Match docker-compose env or simple default
                mobile="13800000000",
                createtime=None, # Allow default
                updatetime=None
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
                createtime=None,
                updatetime=None
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
