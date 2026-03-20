import json
import pandas as pd
from pathlib import Path

responses = json.loads(Path('evaluation/evaluation/results/checkpoints/lexai_responses_393.json').read_text())
gt = pd.read_excel('evaluation/ground_truth_verified_393.xlsx', sheet_name='Ground Truth Dataset')
if 'query_text' in gt.columns:
    gt = gt.rename(columns={'query_text': 'query'})

print('GT columns:', list(gt.columns))
print('Has correct_answer_summary:', 'correct_answer_summary' in gt.columns)

for domain in ['Civil Law', 'Corporate Law', 'Family Law']:
    sub_gt = gt[gt['domain'] == domain].head(3)
    sub_queries = set(sub_gt['query'].astype(str).str.strip())
    sub_responses = [r for r in responses if str(r.get('query', '')).strip() in sub_queries]

    print(f"\n=== {domain} ===")
    for r, (_, row) in zip(sub_responses, sub_gt.iterrows()):
        summary = row.get('correct_answer_summary', None)
        print(f"Query: {str(r.get('query',''))[:80]}")
        print(f"Answer length: {len(str(r.get('answer','')))} chars")
        print(f"Answer preview: {str(r.get('answer',''))[:150]}")
        print(f"Ground truth summary: {str(summary)[:150]}")
        print(f"correct_answer_summary is null: {pd.isna(summary)}")
        print('---')

for domain in ['Civil Law', 'Corporate Law', 'Family Law']:
    d = gt[gt['domain'] == domain]
    if 'correct_answer_summary' in d.columns:
        nulls = d['correct_answer_summary'].isna().sum()
        blanks = (d['correct_answer_summary'].astype(str).str.strip() == '').sum()
        print(f"{domain}: rows={len(d)} null_summary={nulls} blank_summary={blanks}")
