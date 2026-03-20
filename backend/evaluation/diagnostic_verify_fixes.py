"""
Quick sanity check: run all 4 fixed metrics on 5 LexAI + 5 NoRAG responses
and print the individual scores to verify the fixes work as expected.
"""
import json, sys, os, re, ast, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

eval_dir = os.path.dirname(os.path.abspath(__file__))

import chromadb
from evaluation.metrics_engine import MetricsEngine

gt = pd.read_excel(os.path.join(eval_dir, 'ground_truth_verified.xlsx'), sheet_name=0)

with open(os.path.join(eval_dir, 'results', 'checkpoints', 'lexai_responses.json')) as f:
    lexai_all = json.load(f)

with open(os.path.join(eval_dir, 'results', 'checkpoints', 'baseline_responses.json')) as f:
    baseline = json.load(f)
norag_all = baseline.get('NoRAG', [])


def parse_str_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s in ('', 'None', 'null', '[]'):
            return []
        try:
            r = ast.literal_eval(s)
            if isinstance(r, list):
                return r
        except Exception:
            pass
        try:
            import json as _j
            r = _j.loads(s)
            if isinstance(r, list):
                return r
        except Exception:
            pass
    return []


def normalize_lexai(response):
    n = response.copy()
    structured = response.get('structured_response') or {}
    citations = []
    act = structured.get('act_cited')
    section = structured.get('section_cited')
    if act in (None, 'None', '', 'null'):
        act = None
    if section in (None, 'None', '', 'null'):
        section = None
    if act and section:
        citations.append({'type': 'bare_act', 'act_or_case': act, 'section_or_citation': section})
    raw = parse_str_list(structured.get('case_citations', []))
    for c in raw:
        if isinstance(c, str) and 'VIBER_' not in c:
            if re.search(r'(?:AIR|SCC|SCR|SCALE|ALL|BLJR)\s+\d{4}', c, re.I):
                citations.append({'type': 'case_law', 'act_or_case': c, 'section_or_citation': c})
    n['citations'] = citations
    return n


def normalize_baseline(response):
    n = response.copy()
    raw = parse_str_list(response.get('citations', []))
    citations = []
    for cite in raw:
        if isinstance(cite, str):
            sm = re.search(r'Section\s+(\d+[A-Z]?)', cite, re.I)
            am = re.search(r'(IPC|BNS|CrPC|BNSS|NI Act|Companies Act|Evidence Act|Indian Penal Code|Bharatiya Nyaya Sanhita)', cite, re.I)
            if sm and am:
                citations.append({'type': 'bare_act', 'act_or_case': am.group(1), 'section_or_citation': sm.group(1)})
        elif isinstance(cite, dict):
            citations.append(cite)
    n['citations'] = citations
    return n


chroma_client = chromadb.PersistentClient(path=os.path.join(eval_dir, '..', 'chroma_db'))

# Use first 5 responses
N = 5
lexai_5 = [normalize_lexai(r) for r in lexai_all[:N]]
norag_5 = [normalize_baseline(r) for r in norag_all[:N]]

for system_name, responses in [('LexAI', lexai_5), ('NoRAG', norag_5)]:
    engine = MetricsEngine(gt.iloc[:N].reset_index(drop=True), chroma_client)
    car = engine.compute_citation_accuracy(responses)
    hr = engine.compute_hallucination_rate(responses)
    olr = engine.compute_outdated_law_rate(responses)
    acs = engine.compute_completeness_score(responses)

    print(f"\n{'='*55}")
    print(f"  {system_name}  (N={N})")
    print(f"{'='*55}")
    print(f"  CAR overall:  {car['CAR_overall']:.1f}%")
    print(f"  CAR individual: {[round(s,2) for s in car['individual_scores']]}")
    print()
    print(f"  HR  overall:  {hr['HR_overall']:.1f}%")
    print(f"  HR  total_claims: {hr['total_claims']}")
    print(f"  HR  hallucinated: {hr['hallucinated_claims']}")
    print()
    print(f"  OLR overall:  {olr['OLR_overall']:.1f}%")
    print(f"  OLR IPC→BNS:  {olr['OLR_ipc_bns']:.1f}%  (cited={olr['applicable_cases']['ipc_cited']})")
    print()
    print(f"  ACS overall:  {acs['ACS_overall']:.1f}%")
    print(f"  ACS individual: {[round(s,2) for s in acs['individual_scores']]}")

    # Show normalised citations for first 3
    print()
    for i, r in enumerate(responses[:3]):
        print(f"  [{system_name}][Q{i+1}] citations: {r.get('citations', [])}")
