"""
Simple debug test for smart retriever
"""
import sys
import os
from pathlib import Path

# Add parent directory to path (scripts/ -> backend/)
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.chroma_setup import initialize_legal_db
from retrieval.smart_retriever import initialize_smart_retriever

db = initialize_legal_db()
retriever = initialize_smart_retriever(db)

print("Testing retrieval...")
result = retriever.retrieve("What is Section 420 IPC")

print(f"\nResult type: {type(result)}")
print(f"\nResult keys: {list(result.keys())}")
print(f"\nResult: {result}")
