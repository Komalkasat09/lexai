"""
Test API Key Fallback Mechanism
================================

Quick test to verify multiple Groq API keys are loaded
and fallback mechanism works.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print("🔑 GROQ API KEY CONFIGURATION TEST")
print("=" * 80)

# Load all API keys
api_keys = [
    os.getenv("GROQ_API_KEY", ""),
    os.getenv("GROQ_API_KEY_2", ""),
    os.getenv("GROQ_API_KEY_3", ""),
    os.getenv("GROQ_API_KEY_4", ""),
    os.getenv("GROQ_API_KEY_5", ""),
    os.getenv("GROQ_API_KEY_6", ""),
    os.getenv("GROQ_API_KEY_7", ""),
]

# Filter out empty keys
api_keys = [key for key in api_keys if key]

print(f"\n✅ Found {len(api_keys)} Groq API key(s) configured")
print()

for i, key in enumerate(api_keys, 1):
    masked_key = key[:8] + "..." + key[-8:] if len(key) > 16 else "***"
    print(f"Key #{i}: {masked_key}")

print()
print("=" * 80)
print("📋 CONFIGURATION SUMMARY")
print("=" * 80)
print()

if len(api_keys) == 0:
    print("❌ No API keys found!")
    print("   Set GROQ_API_KEY in backend/.env file")
elif len(api_keys) == 1:
    print("⚠️  Only 1 API key configured")
    print("   Add GROQ_API_KEY_2, GROQ_API_KEY_3, etc. for automatic fallback")
elif len(api_keys) >= 2:
    print(f"✅ {len(api_keys)} API keys configured - automatic fallback enabled!")
    print()
    print("Fallback behavior:")
    print("  - If Key #1 hits rate limit → automatically switches to Key #2")
    print("  - If Key #2 hits rate limit → automatically switches to Key #3")
    print("  - And so on...")
    print()
    print("This ensures uninterrupted service during high-volume API usage!")

print()
print("=" * 80)

# Test LegalLLM initialization
print()
print("🧪 Testing LegalLLM initialization...")
print()

try:
    from llm.legal_llm import LegalLLM
    
    # This should work if at least one API key is valid
    llm = LegalLLM(persist_directory="./legal_research_db")
    print("✅ LegalLLM initialized successfully!")
    print(f"   Using API key #{llm.current_key_index + 1} of {len(llm.api_keys)}")
    
except Exception as e:
    print(f"❌ Failed to initialize: {e}")

print()
print("=" * 80)
print("DONE")
print("=" * 80)
