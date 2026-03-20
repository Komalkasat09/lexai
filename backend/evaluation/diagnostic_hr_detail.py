"""Check what claims HR inline scanner is finding and hallucinating for LexAI"""
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
engine = MetricsEngine(gt.iloc[:10].reset_index(drop=True), chroma_client)

# Test on first 10 responses
lexai_10 = [normalize_lexai(r) for r in lexai_all[:10]]
hr_result = engine.compute_hallucination_rate(lexai_10)

print(f"HR overall: {hr_result['HR_overall']:.1f}%")
print(f"Total claims: {hr_result['total_claims']}")
print(f"Hallucinated: {hr_result['hallucinated_claims']}")
print()
for i, item in enumerate(hr_result['individual_results'][:10]):
    print(f"Q{i+1}:")
    print(f"  claims={item['total_claims']}, hallucinated={item['hallucinated_count']}, rate={item['hallucination_rate']:.2f}")
    for h in item.get('hallucinated_items', [])[:3]:
        print(f"  HALLUCINATED: {h}")
