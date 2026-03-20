import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
eval_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(eval_dir, 'results', 'checkpoints', 'lexai_responses.json')) as f:
    lexai = json.load(f)

import re, ast

def parse_str_list(v):
    if isinstance(v, list): return v
    if isinstance(v, str):
        v = v.strip()
        if v in ('', 'None', '[]'): return []
        try:
            r = ast.literal_eval(v)
            if isinstance(r, list): return r
        except: pass
    return []

ipc_pat = re.compile(r'\b(?:IPC|Indian Penal Code)\b', re.I)
bns_pat = re.compile(r'\b(?:BNS|Bharatiya Nyaya Sanhita)\b', re.I)

for i, r in enumerate(lexai[:5]):
    ans = r.get('answer', '')
    bns_note = r.get('bns_transition_note', '')
    has_ipc = bool(ipc_pat.search(ans))
    has_bns = bool(bns_pat.search(ans)) or (isinstance(bns_note, str) and bns_note.strip() not in ('', 'None', '[]', 'null'))
    print(f"Q{i+1}: has_ipc={has_ipc}, has_bns={has_bns}, bns_note={repr(str(bns_note)[:60])}")
    print(f"     answer snippet: {ans[:100]}")
    print()
