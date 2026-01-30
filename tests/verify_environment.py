import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.llm_config_service import LLMConfigService
from app.services.system_config_service import SystemConfigService
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("PreflightCheck")

def verify_environment():
    print("🚀 Running System Pre-flight Check...")
    errors = []
    
    # Check 1: Database Connection
    print("\n[1/4] Checking Database Connection...")
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            print("  ✅ Database connected.")
            
            # Check 2: LLM Config Tables
            print("\n[2/4] Checking LLM Configuration Tables...")
            providers = db.execute(text("SELECT count(*) FROM t_llm_provider WHERE is_active=true")).scalar()
            models = db.execute(text("SELECT count(*) FROM t_llm_model WHERE is_active=true")).scalar()
            
            if providers > 0:
                print(f"  ✅ Found {providers} active LLM Providers.")
            else:
                errors.append("No active LLM Providers found in DB.")
                print("  ❌ No active LLM Providers found.")
                
            if models > 0:
                print(f"  ✅ Found {models} active LLM Models.")
            else:
                errors.append("No active LLM Models found in DB.")
                print("  ❌ No active LLM Models found.")
                
            # Check 3: LLM Config Service Loading
            print("\n[3/4] Verifying LLM Service Loading...")
            # Force lazy load if not loaded
            if not LLMConfigService.is_type_configured("chat"):
                 LLMConfigService._lazy_init()
                 
            chat_model = LLMConfigService.get_model_by_type("chat")
            if chat_model:
                print(f"  ✅ Chat Model Configured: {chat_model.model_code} (Provider: {chat_model.provider_code})")
                if not chat_model.api_key:
                    errors.append(f"Chat model {chat_model.model_code} is missing API Key.")
                    print(f"  ❌ API Key missing for {chat_model.model_code}")
                else:
                    print(f"  ✅ API Key present for {chat_model.model_code}")
            else:
                errors.append("No default chat model configured.")
                print("  ❌ No default chat model found.")
                
    except Exception as e:
        errors.append(f"Database/Config Error: {str(e)}")
        print(f"  ❌ Critical Error: {e}")

    # Check 4: System Config
    print("\n[4/4] Checking System Configuration...")
    try:
        with SessionLocal() as db:
             SystemConfigService.load_from_db(db)
        print("  ✅ System Config Service initialized.")
    except Exception as e:
        print(f"  ⚠️ System Config Service warning: {e}")

    print("\n=== Summary ===")
    if not errors:
        print("🎉 System Ready! All checks passed.")
        sys.exit(0)
    else:
        print("💥 System Health Issues Found:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

if __name__ == "__main__":
    verify_environment()
