
import os
import sys
from sqlalchemy import text
from app.db.session import SessionLocal
import logging

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_feedback_table():
    db = SessionLocal()
    try:
        logger.info("Checking/Creating t_chat_feedback table...")
        sql = text("""
        CREATE TABLE IF NOT EXISTS t_chat_feedback (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            message_id BIGINT NOT NULL,
            score INTEGER NOT NULL CHECK (score IN (-1, 0, 1)),
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_feedback_user_message UNIQUE (user_id, message_id)
        );
        CREATE INDEX IF NOT EXISTS idx_feedback_message_id ON t_chat_feedback(message_id);
        """)
        db.execute(sql)
        db.commit()
        logger.info("Successfully created t_chat_feedback table.")
    except Exception as e:
        logger.error(f"Error creating table: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_feedback_table()
