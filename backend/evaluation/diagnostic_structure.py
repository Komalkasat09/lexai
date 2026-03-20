import json, pandas as pd, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

eval_dir = os.path.dirname(os.path.abspath(__file__))

gt = pd.read_excel(os.path.join(eval_dir, 'ground_truth_verified.xlsx'), sheet_name=0)
print('GT columns:', list(gt.columns))
print()

for col in ['bns_bnss_transition_applies', 'amendment_applies', 'overruling_applies']:
    if col in gt.columns:
        vc = gt[col].value_counts(dropna=False)
        print(f'{col}: {dict(vc)}')
    else:
        print(f'{col}: MISSING')
print()

with open(os.path.join(eval_dir, 'results', 'checkpoints', 'lexai_responses.json')) as f:
    lexai = json.load(f)

print('LexAI[0] keys:', list(lexai[0].keys()))
print()
for i in [0, 1, 2]:
    r = lexai[i]
    print(f'--- Response {i} ---')
    print('  bns_bnss_notes:', repr(r.get('bns_bnss_notes', 'MISSING')))
    print('  amendment_notes:', repr(r.get('amendment_notes', 'MISSING')))
    sr = r.get('structured_response') or {}
    print('  structured_response keys:', list(sr.keys()) if sr else 'None/empty')
    for k,v in (sr or {}).items():
        print(f'    {k}: {repr(str(v))[:100]}')
    print()

with open(os.path.join(eval_dir, 'results', 'checkpoints', 'baseline_responses.json')) as f:
    baseline = json.load(f)

norag = baseline.get('NoRAG', [])
print('NoRAG[0] keys:', list(norag[0].keys()) if norag else 'empty')
if norag:
    print('NoRAG[0] sample:')
    for k,v in norag[0].items():
        print(f'  {k}: {repr(str(v))[:150]}')
