#!/usr/bin/env python3
"""
Quick test script to verify config management is working
"""
import sys
from pathlib import Path

# Add backend_ai to path
sys.path.insert(0, str(Path(__file__).parent / "backend_ai"))

def test_config():
    print("=" * 60)
    print("Testing Config Management (TASK 1)")
    print("=" * 60)
    
    try:
        from app.core.config import settings
        print("✅ Config module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import config: {e}")
        return False
    
    # Test 1: Basic config values
    print("\n📋 Basic Config:")
    print(f"  App Name: {settings.app_name}")
    print(f"  Version: {settings.app_version}")
    print(f"  Environment: {settings.environment}")
    print(f"  Port: {settings.port}")
    print(f"  Debug: {settings.debug}")
    
    # Test 2: AI config
    print("\n🤖 AI Config:")
    print(f"  LLM Model: {settings.llm_model}")
    print(f"  Temperature: {settings.ai_temperature}")
    print(f"  Max Tokens: {settings.max_tokens}")
    if settings.openai_api_key:
        print(f"  OpenAI Key: {settings.openai_api_key[:10]}...")
    else:
        print("  OpenAI Key: ⚠️  Not set (will use mock)")
    
    # Test 3: RAG config
    print("\n📚 RAG Config:")
    print(f"  Embedding Model: {settings.embedding_model}")
    print(f"  SQLite Path: {settings.sqlite_path}")
    print(f"  FAISS Path: {settings.faiss_path}")
    print(f"  Retrieval Top K: {settings.retrieval_top_k}")
    
    # Test 4: Security config
    print("\n🔒 Security Config:")
    if settings.agent_api_key:
        print(f"  API Key: {settings.agent_api_key[:5]}...")
    else:
        print("  API Key: ⚠️  Not set")
    print(f"  Allowed Origins: {settings.allowed_origins}")
    
    # Test 5: Redis config
    print("\n💾 Redis Config:")
    print(f"  Redis URL: {settings.redis_url}")
    print(f"  Redis Enabled: {settings.redis_enabled}")
    
    # Test 6: Rate limiting config
    print("\n⏱️  Rate Limiting Config:")
    print(f"  Enabled: {settings.rate_limit_enabled}")
    print(f"  Per Minute: {settings.rate_limit_per_minute}")
    
    # Test 7: Cost guard config
    print("\n💰 Cost Guard Config:")
    print(f"  Enabled: {settings.cost_guard_enabled}")
    print(f"  Monthly Budget: ${settings.monthly_budget_usd}")
    
    # Test 8: Logging config
    print("\n📝 Logging Config:")
    print(f"  Log Level: {settings.log_level}")
    print(f"  Log Format: {settings.log_format}")
    
    # Test 9: File paths exist
    print("\n📁 File Checks:")
    sqlite_exists = Path(settings.sqlite_path).exists()
    faiss_exists = Path(settings.faiss_path).exists()
    print(f"  SQLite DB: {'✅ Found' if sqlite_exists else '⚠️  Not found'}")
    print(f"  FAISS Index: {'✅ Found' if faiss_exists else '⚠️  Not found'}")
    
    # Test 10: Validation
    print("\n🔍 Validation:")
    try:
        settings.validate_production()
        print("  ✅ Config validation passed")
    except ValueError as e:
        print(f"  ⚠️  Validation warning: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    warnings = []
    if not settings.openai_api_key:
        warnings.append("OpenAI API key not set")
    if not settings.agent_api_key and settings.environment == "production":
        warnings.append("Agent API key not set (required for production)")
    if not sqlite_exists:
        warnings.append("SQLite DB not found (run setup_db.py)")
    if not faiss_exists:
        warnings.append("FAISS index not found (run setup_db.py)")
    
    if warnings:
        print("\n⚠️  Warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("\n✅ All checks passed!")
    
    print("\n💡 Next Steps:")
    print("  1. Copy .env.example to .env")
    print("  2. Fill in OPENAI_API_KEY and AGENT_API_KEY")
    print("  3. Run: python data_pipeline/db_setup/setup_db.py")
    print("  4. Run: python backend_ai/app/main_v3.py")
    
    return True


if __name__ == "__main__":
    try:
        success = test_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
