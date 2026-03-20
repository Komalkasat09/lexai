"""Deep check of HR: find which LexAI queries have hallucinated claims"""
import json, sys, os, re, ast, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
eval_dir = os.path.dirname(os.path.abspath(__file__))

import chromadb
from evaluation.metrics_engine import MetricsEngine

gt = pd.read_excel(os.path.join(eval_dir, 'ground_truth_verified.xlsx'), sheet_name=0)

with open(os.path.join(eval_dir, 'results', 'checkpoints', 'lexai_responses.json')) as f:
    lexai_all = json.load(f)

def parse_str_list(v):
    if isinstance(v, list): return v
    if isinstance(v, str):
        s = v.strip()
        if s in ('', 'None', '[]'): return []
        try:
            r = ast.literal_eval(s)
            if isinstance(r, list): return r
        except: pass
    return []

def normalize_lexai(response):
    n = response.copy()
    structured = response.get('structured_response') or {}
    citations = []
    act = structured.get('act_cited')
    section = structured.get('section_cited')
    if act in (None, 'None', '', 'null'): act = None
    if section in (None, 'None', '', 'null'): section = None
    if act and section:
        citations.append({'type': 'bare_act', 'act_or_case': act, 'section_or_citation': section})
    raw = parse_str_list(structured.get('case_citations', []))
    for c in raw:
        if isinstance(c, str) and 'VIBER_' not in c:
            if re.search(r'(?:AIR|SCC|SCR|SCALE|ALL|BLJR)\s+\d{4}', c, re.I):
                citations.append({'type': 'case_law', 'act_or_case': c, 'section_or_citation': c})
    n['citations'] = citations
    return n

chroma_client = chromadb.PersistentClient(path=os.path.join(eval_dir, '..', 'chroma_db'))

# Test ALL 293
all_norm = [normalize_lexai(r) for r in lexai_all]
engine = MetricsEngine(gt.reset_index(drop=True), chroma_client)
hr_result = engine.compute_hallucination_rate(all_norm)

print(f"HR overall (batch): {hr_result['HR_overall']:.2f}%")
print(f"HR individual mean: {sum(r['hallucination_rate'] for r in hr_result['individual_results'])/293*100:.2f}%")
print(f"Total claims: {hr_result['total_claims']}")
print(f"Total hallucinated: {hr_result['hallucinated_claims']}")
print()

# Find queries with hallucination
hall_queries = [
    (i, r) for i, r in enumerate(hr_result['individual_results'])
    if r['hallucinated_count'] > 0
]
print(f"Queries with ≥1 hallucinated claim: {len(hall_queries)}")
print()
for i, item in hall_queries[:10]:
    print(f"  Q{i+1}: claims={item['total_claims']}, hallucinated={item['hallucinated_count']}")
    for h in item.get('hallucinated_items', [])[:2]:
        print(f"    → {h}")

# Check zero-claim queries
zero_claim = sum(1 for r in hr_result['individual_results'] if r['total_claims'] == 0)
print(f"\nQueries with 0 claims: {zero_claim}/293")
