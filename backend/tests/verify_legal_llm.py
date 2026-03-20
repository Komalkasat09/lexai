"""
Quick verification that legal_llm.py is properly structured.
This checks imports and class structure without calling Groq API.
"""

import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("LEGAL LLM - STRUCTURE VERIFICATION")
print("=" * 80)
print()

# Test 1: Import modules
print("✓ Testing imports...")
try:
    from llm.legal_llm import (
        LegalLLM, 
        LEGAL_SYSTEM_PROMPT, 
        GROQ_MODEL, 
        GROQ_TEMPERATURE,
        GROQ_SEED
    )
    print(f"  ✓ Imported LegalLLM class")
    print(f"  ✓ Imported system prompt")
    print(f"  ✓ Imported configuration constants")
except ImportError as e:
    print(f"  ❌ Import failed: {e}")
    exit(1)

# Test 2: Check configuration
print()
print("✓ Testing configuration...")
print(f"  Model: {GROQ_MODEL}")
print(f"  Temperature: {GROQ_TEMPERATURE}")
print(f"  Seed: {GROQ_SEED}")
print(f"  System Prompt Length: {len(LEGAL_SYSTEM_PROMPT)} characters")

# Test 3: Check system prompt content
print()
print("✓ Checking system prompt rules...")
critical_rules = [
    "Only use information from the provided context",
    "Always cite sources",
    "Acknowledge limitations",
    "Never fabricate",
    "BNS/BNSS"
]

for rule in critical_rules:
    if rule.lower() in LEGAL_SYSTEM_PROMPT.lower():
        print(f"  ✓ Contains rule: '{rule}'")
    else:
        print(f"  ⚠️  Missing rule: '{rule}'")

# Test 4: Check class methods
print()
print("✓ Testing LegalLLM class structure...")
expected_methods = [
    '__init__',
    'answer_legal_question',
    'explain_section',
    'summarize_judgment',
    'compare_sections',
    'get_legal_opinion',
    '_format_retrieval_context',
    '_call_groq_llm'
]

for method in expected_methods:
    if hasattr(LegalLLM, method):
        print(f"  ✓ Method exists: {method}()")
    else:
        print(f"  ❌ Method missing: {method}()")

# Summary
print()
print("=" * 80)
print("✅ STRUCTURE VERIFICATION COMPLETE")
print("=" * 80)
print()
print("To test with actual Groq API:")
print("  1. Set GROQ_API_KEY: export GROQ_API_KEY='your-key'")
print("  2. Run: python demo_legal_llm.py")
print()
