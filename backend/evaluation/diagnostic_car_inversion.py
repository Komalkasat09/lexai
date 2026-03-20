"""
Diagnostic: show LexAI vs NoRAG responses side by side for the first 50 queries.
Adapted to the actual checkpoint structure.
"""
import json, sys, os, ast, re, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
eval_dir = os.path.dirname(os.path.abspath(__file__))

gt = pd.read_excel(os.path.join(eval_dir, 'ground_truth_verified.xlsx'), sheet_name=0)

with open(os.path.join(eval_dir, 'results', 'checkpoints', 'lexai_responses.json')) as f:
    lexai_all = json.load(f)

with open(os.path.join(eval_dir, 'results', 'checkpoints', 'baseline_responses.json')) as f:
    baseline = json.load(f)
norag_all = baseline.get('NoRAG', [])


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


# --- Normalize structured citations from LexAI ---
def lexai_structured_citations(r):
    sr = r.get('structured_response') or {}
    act = sr.get('act_cited')
    sec = sr.get('section_cited')
    if act in (None, 'None', '', 'null'): act = None
    if sec in (None, 'None', '', 'null'): sec = None
    if act and sec:
        return [{'act': act, 'section': sec}]
    return []


# --- Normalize baseline citations ---
def baseline_citations(r):
    raw = parse_str_list(r.get('citations', []))
    out = []
    for c in raw:
        if isinstance(c, str):
            sm = re.search(r'Section\s+(\d+[A-Z]?)', c, re.I)
            am = re.search(
                r'(IPC|BNS|CrPC|BNSS|NI Act|Companies Act|Evidence Act|'
                r'Indian Penal Code|Bharatiya Nyaya Sanhita)',
                c, re.I
            )
            if sm and am:
                out.append({'act': am.group(1), 'section': sm.group(1)})
            elif c.strip():
                out.append({'raw': c})
        elif isinstance(c, dict):
            out.append(c)
    return out


print("=" * 80)
print("LexAI  vs  NoRAG  —  first 50 queries side by side")
print("=" * 80)

for i in range(min(50, len(lexai_all), len(norag_all))):
    l = lexai_all[i]
    n = norag_all[i]
    gt_row = gt.iloc[i]

    query_text      = l.get('query', gt_row.get('query_text', ''))
    gt_act          = str(gt_row.get('correct_act',     '')).strip()
    gt_section      = str(gt_row.get('correct_section', '')).strip()

    l_cites  = lexai_structured_citations(l)
    n_cites  = baseline_citations(n)

    # Does each system cite the correct act+section?
    def hits(cites, act, sec):
        act_u = act.upper()
        for c in cites:
            ca = str(c.get('act', c.get('act_or_case', ''))).upper()
            cs = str(c.get('section', c.get('section_or_citation', ''))).strip()
            act_ok = (act_u in ca) or (ca in act_u)
            sec_ok = (cs == sec)
            if act_ok and sec_ok:
                return True
        return False

    l_hit = hits(l_cites, gt_act, gt_section)
    n_hit = hits(n_cites, gt_act, gt_section)

    # Only print interesting cases where they differ OR both unusual
    if l_hit == n_hit and l_cites and n_cites:
        continue   # skip boring matches

    print(f"\n[Q{i+1}] {query_text[:85]}")
    print(f"  GT:     section={gt_section!r:8s} act={gt_act!r}")
    print(f"  LexAI:  citations={l_cites}  →  CAR_hit={l_hit}")
    print(f"          answer: {l.get('answer','')[:120]}")
    sr = l.get('structured_response') or {}
    print(f"          act_cited={sr.get('act_cited')!r}  section_cited={sr.get('section_cited')!r}")
    print(f"  NoRAG:  citations={n_cites}  →  CAR_hit={n_hit}")
    print(f"          answer: {n.get('answer','')[:120]}")
    print(f"          raw_citations={parse_str_list(n.get('citations', []))}")
