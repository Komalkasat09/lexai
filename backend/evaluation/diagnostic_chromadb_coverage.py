"""Check maximum section numbers in each act in ChromaDB"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
eval_dir = os.path.dirname(os.path.abspath(__file__))
import chromadb
from collections import defaultdict

chroma = chromadb.PersistentClient(path=os.path.join(eval_dir, '..', 'chroma_db'))
col = chroma.get_collection('bare_acts')

all_data = col.get(include=['metadatas'])
# Group sections per act
act_sections = defaultdict(list)
for m in all_data['metadatas']:
    act = m.get('act_name', '')
    sec = m.get('section_number', '')
    try:
        act_sections[act].append(int(sec))
    except ValueError:
        pass  # skip alphanumeric like 104A

print("Act section coverage (numeric sections only):")
for act, nums in sorted(act_sections.items()):
    nums.sort()
    print(f"  {act[:50]}: {len(nums)} sections, range={min(nums)}-{max(nums)}")
    # Show gaps - check if 302 is there for IPC
    if 'Indian Penal Code' in act:
        for sec in [34, 302, 376, 420, 498]:
            print(f"    Section {sec}: {'PRESENT' if sec in nums else 'MISSING'}")
