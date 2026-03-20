"""Debug why ChromaDB $eq + $contains returns 0"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
eval_dir = os.path.dirname(os.path.abspath(__file__))
import chromadb

chroma = chromadb.PersistentClient(path=os.path.join(eval_dir, '..', 'chroma_db'))
col = chroma.get_collection('bare_acts')

# Test 1: just $eq on section_number
print("Test 1: only section_number=$eq('302')")
r = col.get(where={"section_number": {"$eq": "302"}})
print(f"  found: {len(r['ids'])} docs")
if r['ids']:
    print(f"  metadata[0]: {r['metadatas'][0]}")

# Test 2: just $contains on act_name
print("\nTest 2: only act_name $contains 'Indian Penal Code'")
try:
    r2 = col.get(where={"act_name": {"$contains": "Indian Penal Code"}})
    print(f"  found: {len(r2['ids'])} docs")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 3: $eq on act_name
print("\nTest 3: act_name $eq 'Indian Penal Code 1860'")
try:
    r3 = col.get(where={"act_name": {"$eq": "Indian Penal Code 1860"}})
    print(f"  found: {len(r3['ids'])} docs")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 4: $and with $eq on both
print("\nTest 4: $and [section_number=$eq('302'), act_name=$eq('Indian Penal Code 1860')]")
try:
    r4 = col.get(where={"$and": [{"section_number": {"$eq": "302"}}, {"act_name": {"$eq": "Indian Penal Code 1860"}}]})
    print(f"  found: {len(r4['ids'])} docs")
    if r4['ids']:
        print(f"  metadata[0]: {r4['metadatas'][0]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 5: $and with $contains on act_name - this is what the code uses
print("\nTest 5: $and [section_number=$eq('302'), act_name=$contains('Indian Penal Code')]")
try:
    r5 = col.get(where={"$and": [{"section_number": {"$eq": "302"}}, {"act_name": {"$contains": "Indian Penal Code"}}]})
    print(f"  found: {len(r5['ids'])} docs")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 6: NI Act - short_name match
print("\nTest 6: NI Act section 141")
try:
    r6 = col.get(where={"$and": [{"section_number": {"$eq": "141"}}, {"act_name": {"$eq": "Negotiable Instruments Act 1881"}}]})
    print(f"  found with $eq: {len(r6['ids'])} docs")
    if r6['ids']:
        print(f"  metadata[0]: {r6['metadatas'][0]}")
except Exception as e:
    print(f"  ERROR: {e}")
