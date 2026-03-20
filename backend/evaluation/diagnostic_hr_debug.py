import json, sys, os, ast, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
eval_dir = os.path.dirname(os.path.abspath(__file__))
import chromadb
from evaluation.metrics_engine import MetricsEngine

gt = pd.read_excel(os.path.join(eval_dir, 'ground_truth_verified.xlsx'), sheet_name=0)
with open(os.path.join(eval_dir, 'results', 'checkpoints', 'lexai_responses.json')) as f:
    lexai_all = json.load(f)

def norm(r):
    n = r.copy()
    sr = r.get('structured_response') or {}
    act = sr.get('act_cited')
    sec = sr.get('section_cited')
    if act in (None, 'None', '', 'null'):
        act = None
    if sec in (None, 'None', '', 'null'):
        sec = None
    cites = []
    if act and sec:
        cites.append({'type': 'bare_act', 'act_or_case': act, 'section_or_citation': sec})
    n['citations'] = cites
    return n

chroma = chromadb.PersistentClient(path=os.path.join(eval_dir, '..', 'chroma_db'))
engine = MetricsEngine(gt.reset_index(drop=True), chroma)
responses = [norm(r) for r in lexai_all]
hr = engine.compute_hallucination_rate(responses)
print('HR_overall (batch):', hr['HR_overall'])
print('total_claims:', hr['total_claims'])
print('hallucinated:', hr['hallucinated_claims'])
cnt_pos = sum(1 for r in hr['individual_results'] if r['total_claims'] > 0)
print('responses with >=1 structured claim:', cnt_pos)

# Find some that have actual structured claims
shown = 0
for i, r in enumerate(hr['individual_results']):
    if r['total_claims'] > 0 and shown < 8:
        print(f"  Q{i+1}: claims={r['total_claims']}, hall={r['hallucinated_count']}, items={r['hallucinated_items'][:2]}")
        shown += 1
