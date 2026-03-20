#!/usr/bin/env python3
"""
Quick diagnostic script to verify backend setup
Run this to check if all dependencies and modules are working
"""

import sys
import os

def check_imports():
    """Check all required imports"""
    print("🔍 Checking Python imports...")
    
    required_modules = [
        ("chromadb", "ChromaDB for vector database"),
        ("groq", "Groq LLM client"),
        ("fitz", "PyMuPDF for PDF extraction"),
        ("docx", "python-docx for DOCX extraction"),
        ("fastapi", "FastAPI web framework"),
        ("dotenv", "python-dotenv for environment variables"),
        ("uvicorn", "Uvicorn ASGI server"),
    ]
    
    all_ok = True
    for module, description in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module:20s} - {description}")
        except ImportError as e:
            print(f"  ❌ {module:20s} - MISSING ({description})")
            all_ok = False
    
    return all_ok

def check_project_files():
    """Check if all project files exist"""
    print("\n🔍 Checking project files...")
    
    required_files = [
        "main.py",
        "document_extractor.py",
        "clause_segmenter.py",
        "chroma_setup.py",
        "rag_retrieval.py",
        "hallucination_guard.py",
        "groq_prompts.py",
        "orchestrator.py",
        ".env",
        "requirements.txt",
    ]
    
    all_ok = True
    for filename in required_files:
        if os.path.exists(filename):
            print(f"  ✅ {filename}")
        else:
            print(f"  ❌ {filename} - MISSING")
            all_ok = False
    
    return all_ok

def check_env_vars():
    """Check environment variables"""
    print("\n🔍 Checking environment variables...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key != "your_groq_api_key_here":
        print(f"  ✅ GROQ_API_KEY is configured")
        return True
    else:
        print(f"  ⚠️  GROQ_API_KEY not configured (won't be able to run AI analysis)")
        return False

def main():
    print("=" * 60)
    print("BACKEND DIAGNOSTIC TOOL")
    print("=" * 60)
    
    print(f"\n📍 Python: {sys.executable}")
    print(f"📍 Version: {sys.version.split()[0]}")
    print(f"📍 Working Directory: {os.getcwd()}")
    
    imports_ok = check_imports()
    files_ok = check_project_files()
    env_ok = check_env_vars()
    
    print("\n" + "=" * 60)
    if imports_ok and files_ok:
        print("✅ BACKEND IS READY!")
        if not env_ok:
            print("⚠️  Configure GROQ_API_KEY in .env to enable AI features")
        print("\nRun server: python main.py")
    else:
        print("❌ BACKEND HAS ISSUES - Fix the errors above")
        if not imports_ok:
            print("\n   Run: pip install -r requirements.txt")
    print("=" * 60)

if __name__ == "__main__":
    main()
