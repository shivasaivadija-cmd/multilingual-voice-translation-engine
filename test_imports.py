import sys
sys.path.insert(0, 'backend')

try:
    from config.settings import get_settings
    print("[OK] Settings loaded")
    
    from database.connection import init_db
    print("[OK] Database imports OK")
    
    from services.model_manager import ModelManager
    print("[OK] Model manager imports OK")
    
    print("\nAll imports successful! Backend should start.")
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
