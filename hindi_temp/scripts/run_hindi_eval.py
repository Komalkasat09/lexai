import json
import os
import sys
import pandas as pd

backend_dir = '/Users/komalkasat09/legal-website/backend'
sys.path.insert(0, backend_dir)

from evaluation.run_evaluation import EvaluationRunner

hindi_path = 'evaluation/hindi_queries.xlsx'
out_path = 'evaluation/evaluation/results/checkpoints/lexai_hindi_responses.json'
os.makedirs(os.path.dirname(out_path), exist_ok=True)

df = pd.read_excel(hindi_path)
queries = df['hindi_query'].astype(str).tolist()

runner = EvaluationRunner(
    ground_truth_path='evaluation/ground_truth_verified.xlsx',
    output_dir='evaluation/results'
)
responses = runner.run_lexai(queries)

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(responses, f, ensure_ascii=False, indent=2, default=str)

print('saved', out_path)
print('responses', len(responses))
