"""Check IPC sections in ChromaDB"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
eval_dir = os.path.dirname(os.path.abspath(__file__))
import chromadb

chroma = chromadb.PersistentClient(path=os.path.join(eval_dir, '..', 'chroma_db'))
col = chroma.get_collection('bare_acts')

# Check a specific IPC section
for sec_num in ['34', '302', '420', '498A', '376', '354']:
    try:
        results = col.get(
            where={"$and": [{"section_number": {"$eq": sec_num}}, {"act_name": {"$contains": "Indian Penal Code"}}]}
        )
        print(f"IPC Section {sec_num}: found={len(results['ids'])} docs")
        if results['ids']:
            print(f"  metadata sample: {results['metadatas'][0]}")
    except Exception as e:
        print(f"IPC Section {sec_num}: ERROR {e}")

print()
# Check what sections exist entirely
sample = col.get(limit=20, include=['metadatas'])
print("Sample metadata (first 20):")
for m in sample['metadatas'][:10]:
    print(f"  section_number={m.get('section_number')!r}, act_name={m.get('act_name')!r:.40s}, short_name={m.get('short_name')!r}")

print()
# Get section number range
all_meta = col.get(include=['metadatas'])
sections = [m.get('section_number') for m in all_meta['metadatas']]
acts = set(m.get('act_name') for m in all_meta['metadatas'])
print(f"Total docs: {len(sections)}")
print(f"Unique acts: {acts}")
print(f"Sample section numbers: {sorted(set(sections))[:30]}")
