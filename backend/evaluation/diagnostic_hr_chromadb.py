"""Check what acts/sections LexAI provides as structured citations and whether they exist in ChromaDB"""
import json, sys, os, ast, pandas as pd
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
eval_dir = os.path.dirname(os.path.abspath(__file__))
import chromadb

with open(os.path.join(eval_dir, 'results', 'checkpoints', 'lexai_responses.json')) as f:
    lexai_all = json.load(f)

# Collect all responses that have actual act_cited/section_cited
found_citations = []
for r in lexai_all:
    sr = r.get('structured_response') or {}
    act = sr.get('act_cited')
    sec = sr.get('section_cited')
    if act in (None, 'None', '', 'null'):
        act = None
    if sec in (None, 'None', '', 'null'):
        sec = None
    if act and sec:
        found_citations.append((act, sec))

print(f"Total structured citations (act+section): {len(found_citations)}")
print()
act_counts = Counter(a for a,s in found_citations)
print("Acts distribution:")
for act, cnt in act_counts.most_common(10):
    print(f"  {act!r:55s} -> {cnt}")

print()
# Now check ChromaDB
chroma = chromadb.PersistentClient(path=os.path.join(eval_dir, '..', 'chroma_db'))
try:
    col = chroma.get_collection('bare_acts')
    print(f"bare_acts collection: {col.count()} documents")
    # Peek at all unique act_names
    sample = col.get(limit=100, include=['metadatas'])
    act_names = set(m.get('act_name', '') for m in sample['metadatas'])
    print("Sample act_names in ChromaDB:")
    for a in sorted(act_names):
        print(f"  {a!r}")
except Exception as e:
    print(f"ChromaDB error: {e}")

print()
# Spot-check a few
print("Spot-check lookups:")
for act, sec in found_citations[:5]:
    try:
        results = col.get(
            where={"$and": [{"section_number": {"$eq": sec}}, {"act_name": {"$contains": act[:25]}}]}
        )
        print(f"  act={act!r:.40s} sec={sec!r} -> found={len(results['ids'])} docs")
    except Exception as e:
        print(f"  ERROR: {e}")
