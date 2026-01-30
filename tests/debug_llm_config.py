import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.llm_config_service import LLMConfigService
from app.core import config as app_config
import logging

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)

def debug_llm_config():
    print("=== Debugging LLM Configuration ===")
    
    # 1. Check Environment Variables (Masked)
    print("\n--- Environment Variables ---")
    keys_to_check = [
        "MODEL_API_KEY", "ZHIPU_API_KEY", "DEEPSEEK_API_KEY", "QWEN_API_KEY",
        "DATABASE_URL"
    ]
    for key in keys_to_check:
        val = os.getenv(key)
        masked = f"{val[:4]}...{val[-4:]}" if val and len(val) > 8 else (val or "NOT SET")
        print(f"{key}: {masked}")
        
    print(f"\napp.core.config.MODEL_API_KEY: {app_config.MODEL_API_KEY[:4]}... if set")

    # 2. Check Database Loading
    print("\n--- Loading from DB ---")
    try:
        with SessionLocal() as db:
            LLMConfigService.load_from_db(db)
            
        print("\n--- Loaded Cache ---")
        models = LLMConfigService.list_available_models()
        print(f"Total Models Loaded: {len(models)}")
        for m in models:
            print(f"- {m['model_code']} (Provider: {m['provider']})")
            
        # 3. Specific Model Check
        target_model = "glm-4.5-air"
        cfg = LLMConfigService.get_model_config(target_model)
        if cfg:
            print(f"\n✅ Found config for {target_model}:")
            print(f"  API Key Present: {'Yes' if cfg.api_key else 'No'}")
            if cfg.api_key:
                 print(f"  Key Value: {cfg.api_key[:5]}...")
        else:
            print(f"\n❌ Config for {target_model} NOT FOUND in cache.")
            
    except Exception as e:
        print(f"\n❌ Error during loading: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_llm_config()
