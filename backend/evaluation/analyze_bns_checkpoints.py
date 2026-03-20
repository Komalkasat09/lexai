#!/usr/bin/env python3
"""Quick analysis of existing BNS ablation checkpoints"""

import json
import pandas as pd
import numpy as np

# Load checkpoint data
with open('evaluation/checkpoints/bns_ablation/with_middleware.json') as f:
    with_mw = json.load(f)

with open('evaluation/checkpoints/bns_ablation/without_middleware.json') as f:
    without_mw = json.load(f)

# Load ground truth
gt_df = pd.read_excel('evaluation/ground_truth_verified.xlsx', sheet_name='Ground Truth Dataset')
transition_queries = gt_df[gt_df['category'] == 'IPC to BNS Transition']

def compute_olr(response, gt):
    answer = response.get('answer', '').lower()
    warnings = response.get('warnings', [])
    
    has_bns_warning = any('bns' in str(w).lower() or 'bnss' in str(w).lower() for w in warnings)
    mentions_ipc = any(term in answer for term in ['indian penal code', 'ipc', 'i.p.c'])
    
    has_bns_in_answer = any(term in answer for term in [
        'bharatiya nyaya sanhita', 'bns', 'replaced', 'transition'
    ])
    
    has_bns_note = has_bns_warning or has_bns_in_answer
    olr = 1.0 if (mentions_ipc and not has_bns_note) else 0.0
    
    return olr, has_bns_warning, mentions_ipc, has_bns_in_answer

# Compute OLR for each condition
results = {}

for condition, responses in [('with_middleware', with_mw), ('without_middleware', without_mw)]:
    olr_scores = []
    answered = 0
    uncertain = 0
    details = []
    
    for r in responses:
        answer_text = r['response'].get('answer', '')
        if ('cannot provide a reliable answer' in answer_text.lower() or
            'consult primary sources' in answer_text.lower()):
            uncertain += 1
            continue
        
        answered += 1
        query_text = r['query_text']
        gt_row = transition_queries[transition_queries['query_text'] == query_text]
        if not gt_row.empty:
            gt = gt_row.iloc[0].to_dict()
            olr, has_warning, mentions_ipc, has_bns_answer = compute_olr(r['response'], gt)
            olr_scores.append(olr)
            
            if answered <= 5:  # Show first 5
                details.append({
                    'query': query_text[:60],
                    'mentions_ipc': mentions_ipc,
                    'has_warning': has_warning,
                    'has_bns_in_answer': has_bns_answer,
                    'olr': olr
                })
    
    results[condition] = {
        'answered': answered,
        'uncertain': uncertain,
        'olr_mean': np.mean(olr_scores) if olr_scores else 0.0,
        'olr_scores': olr_scores,
        'details': details
    }
    
    print(f'\n{condition.upper()}:')
    print(f'  Total queries: 50')
    print(f'  Answered: {answered}')
    print(f'  Uncertain: {uncertain}')
    print(f'  OLR: {np.mean(olr_scores):.3f}' if olr_scores else '  OLR: N/A')
    
    if details:
        print(f'\n  First {len(details)} answered queries:')
        for d in details:
            print(f"    - {d['query']}")
            print(f"      Mentions IPC: {d['mentions_ipc']}, Has warning: {d['has_warning']}, BNS in answer: {d['has_bns_in_answer']}, OLR: {d['olr']}")

# Compare
print('\n' + '='*70)
print('COMPARISON:')
print('='*70)
with_olr = results['with_middleware']['olr_mean']
without_olr = results['without_middleware']['olr_mean']
reduction = without_olr - with_olr
pct = (reduction / max(without_olr, 0.001)) * 100

print(f"WITHOUT middleware OLR: {without_olr:.3f}")
print(f"WITH middleware OLR: {with_olr:.3f}")
print(f"Reduction: {reduction:.3f} ({pct:.1f}%)")

if reduction > 0:
    print("\n✓ Middleware HELPS - reduces outdated law citations!")
else:
    print("\n✗ Middleware HARMS - need to investigate why")
