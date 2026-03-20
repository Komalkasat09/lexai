"""Debug script to check what metrics engine returns"""
import json
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.metrics_engine import MetricsEngine
import chromadb

# Load data
eval_dir = os.path.dirname(os.path.abspath(__file__))
gt_df = pd.read_excel(os.path.join(eval_dir, 'ground_truth_verified.xlsx'), sheet_name=1)
lex = json.load(open(os.path.join(eval_dir, 'results/checkpoints/lexai_responses.json')))
baseline_data = json.load(open(os.path.join(eval_dir, 'results/checkpoints/baseline_responses.json')))
sr = baseline_data['SimpleRAG']

# Create engine
backend_dir = os.path.dirname(eval_dir)
chroma_path = os.path.join(backend_dir, 'chroma_db')
chroma_client = chromadb.PersistentClient(path=chroma_path)
engine = MetricsEngine(gt_df, chroma_client)

# Test on first 5 responses
print('Testing metrics on first 5 LexAI responses...')
car_result = engine.compute_citation_accuracy(lex[:5])
hr_result = engine.compute_hallucination_rate(lex[:5])

print('\n=== CAR Result ===')
print('Type:', type(car_result))
print('Keys:', list(car_result.keys()) if isinstance(car_result, dict) else 'N/A')
print('CAR_overall:', car_result.get('CAR_overall'))
print('individual_scores:', car_result.get('individual_scores'))

print('\n=== HR Result ===')
print('Type:', type(hr_result))
print('Keys:', list(hr_result.keys()) if isinstance(hr_result, dict) else 'N/A')
print('HR_overall:', hr_result.get('HR_overall'))
ind_results = hr_result.get('individual_results', [])
print('individual_results length:', len(ind_results))
print('First 2 individual_results:')
for i, r in enumerate(ind_results[:2]):
    print(f'  [{i}] hallucination_rate={r.get("hallucination_rate")}, total_claims={r.get("total_claims")}')

# Now test SimpleRAG
print('\n\nTesting metrics on first 5 SimpleRAG responses...')
car_result_sr = engine.compute_citation_accuracy(sr[:5])
hr_result_sr = engine.compute_hallucination_rate(sr[:5])

print('\n=== SimpleRAG CAR Result ===')
print('CAR_overall:', car_result_sr.get('CAR_overall'))
print('individual_scores:', car_result_sr.get('individual_scores'))

print('\n=== SimpleRAG HR Result ===')
print('HR_overall:', hr_result_sr.get('HR_overall'))
ind_results_sr = hr_result_sr.get('individual_results', [])
print('First 2 individual_results:')
for i, r in enumerate(ind_results_sr[:2]):
    print(f'  [{i}] hallucination_rate={r.get("hallucination_rate")}, total_claims={r.get("total_claims")}')

# Check actual response structure
print('\n\n=== Response Structure ===')
print('LexAI[0] keys:', list(lex[0].keys()))
print('LexAI[0] citations:', lex[0].get('citations', []))
print()
print('SimpleRAG[0] keys:', list(sr[0].keys()))
print('SimpleRAG[0] citations:', sr[0].get('citations', []))
