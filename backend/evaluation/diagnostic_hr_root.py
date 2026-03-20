"""
HR root-cause diagnostic:
1. Show what citations are being extracted from LexAI answers
2. Check which ones fail ChromaDB verification (hallucination)
3. Compare with SimpleRAG/NoRAG to understand the gap
"""
import json, re, sys, os
import chromadb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.metrics_engine import MetricsEngine
import pandas as pd

eval_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(eval_dir)

with open(os.path.join(eval_dir, 'results/checkpoints/lexai_responses.json')) as f:
    lexai = json.load(f)
with open(os.path.join(eval_dir, 'results/checkpoints/baseline_responses.json')) as f:
    baseline = json.load(f)

norag  = baseline['NoRAG']
simple = baseline['SimpleRAG']

gt_df = pd.read_excel(os.path.join(eval_dir, 'ground_truth_verified.xlsx'), sheet_name=0)
chroma_client = chromadb.PersistentClient(path=os.path.join(backend_dir, 'chroma_db'))
engine = MetricsEngine(gt_df, chroma_client)

# ── replicate text-scan patterns from recompute_fixed.py ─────────────────────
_ACT_TEXT_ALIASES = [
    r'Indian\s+Penal\s+Code(?:\s+(?:18)?60)?(?:\s*\(IPC\))?',
    r'IPC(?:\s+18?60)?',
    r'Bharatiya\s+Nyaya\s+Sanhita(?:\s+2023)?(?:\s*\(BNS\))?',
    r'BNS(?:\s+2023)?',
    r'Code\s+of\s+Criminal\s+Procedure(?:\s+19?73)?(?:\s*\(CrPC\))?',
    r'CrPC(?:\s+19?73)?',
    r'Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita(?:\s+2023)?(?:\s*\(BNSS\))?',
    r'BNSS(?:\s+2023)?',
    r'Negotiable\s+Instruments\s+Act(?:\s+18?81)?(?:\s*\(NI\s+Act\))?',
    r'NI\s+Act',
    r'Companies\s+Act(?:\s+20?13)?',
    r'Indian\s+Evidence\s+Act(?:\s+18?72)?',
    r'Bharatiya\s+Sakshya\s+(?:Adhiniyam|Act)(?:\s+2023)?',
    r'Arbitration(?:\s+and\s+Conciliation)?\s+Act(?:\s+19?96)?',
]
_ACT_BLOCK = '(?:' + '|'.join(_ACT_TEXT_ALIASES) + ')'
P1 = re.compile(r'\(Citation:\s*(' + _ACT_BLOCK + r')[^)]*?\s+Section\s+(\d+[A-Z]?)\)', re.I)
P2 = re.compile(r'Section\s+(\d+[A-Z]?)\s+of\s+(?:the\s+)?(' + _ACT_BLOCK + r')', re.I)
P3 = re.compile(r'(' + _ACT_BLOCK + r')[,\s]+Section\s+(\d+[A-Z]?)', re.I)

def extract_cites(answer):
    seen, cites = set(), []
    def add(act, sec):
        k = (act.strip().lower(), sec.strip())
        if k not in seen:
            seen.add(k)
            cites.append({
                'type': 'bare_act',
                'act_or_case': act.strip(),
                'section_or_citation': sec.strip(),
            })
    for m in P1.finditer(answer): add(m.group(1), m.group(2))
    for m in P2.finditer(answer): add(m.group(2), m.group(1))
    for m in P3.finditer(answer): add(m.group(1), m.group(2))
    return cites

# ── Step 1: How many LexAI responses have citations after text-scan? ──────────
lexai_with_cites = [(i, r, extract_cites(r.get('answer','') or '')) for i, r in enumerate(lexai)]
non_empty = [(i,r,c) for i,r,c in lexai_with_cites if c]
print(f"LexAI responses with >=1 extracted citation: {len(non_empty)}/{len(lexai)}")
print(f"SimpleRAG with citations: {sum(1 for r in simple if r.get('citations'))}/{len(simple)}")
print(f"NoRAG with citations:     {sum(1 for r in norag  if r.get('citations'))}/{len(norag)}")

# ── Step 2: Manually verify first 15 flagged LexAI citations against ChromaDB ─
print("\n=== LexAI hallucination check on first 15 responses with citations ===")
coll = chroma_client.get_collection('bare_acts')

def check_citation_in_db(act_raw, section):
    resolved = engine._resolve_act_name(act_raw) if hasattr(engine, '_resolve_act_name') else act_raw
    try:
        res = coll.get(where={"$and": [{"act_name": {"$eq": resolved}}, {"section_number": {"$eq": section}}]}, limit=1)
        found = len(res['ids']) > 0
    except Exception as e:
        found = False
        resolved = f"ERROR({e})"
    return resolved, found

for i, r, cites in non_empty[:15]:
    q = r.get('query', '')[:60]
    print(f"\n[{i}] Q: {q}")
    for c in cites:
        act_raw = c['act_or_case']
        sec     = c['section_or_citation']
        resolved, found = check_citation_in_db(act_raw, sec)
        status = "OK   " if found else "MISS "
        print(f"  {status} raw={act_raw!r}  sec={sec}  resolved={resolved!r}")

# ── Step 3: Show full answer for first flagged MISS ───────────────────────────
print("\n=== Full answer for first LexAI citation that fails DB check ===")
for i, r, cites in non_empty[:30]:
    for c in cites:
        act_raw = c['act_or_case']
        sec     = c['section_or_citation']
        _, found = check_citation_in_db(act_raw, sec)
        if not found:
            print(f"Query: {r.get('query','')}")
            print(f"Citation: {act_raw} S.{sec}")
            print(f"Answer:\n{r.get('answer','')[:800]}")
            break
    else:
        continue
    break

# ── Step 4: Check what _resolve_act_name returns for common act strings ────────
print("\n=== _resolve_act_name spot-check ===")
test_acts = [
    'Indian Penal Code',
    'IPC',
    'Indian Penal Code 1860',
    'Code of Criminal Procedure 1973',
    'CrPC',
    'Bharatiya Nyaya Sanhita',
    'BNS',
    'Negotiable Instruments Act',
    'NI Act',
    'Bharatiya Nagarik Suraksha Sanhita 2023',
    'BNSS',
    'Companies Act',
    'Indian Evidence Act',
    'Bharatiya Sakshya Adhiniyam',
]
for act in test_acts:
    resolved = engine._resolve_act_name(act) if hasattr(engine, '_resolve_act_name') else act
    print(f"  {act!r:50s} -> {resolved!r}")
