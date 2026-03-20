import json
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.metrics_engine import MetricsEngine
import chromadb

# Load LexAI response
with open('results/checkpoints/lexai_responses.json') as f:
    lexai_responses = json.load(f)

gt_df = pd.read_excel('ground_truth_verified.xlsx', sheet_name=0)

chroma_client = chromadb.PersistentClient(path='../legal_research_db')
engine = MetricsEngine(gt_df, chroma_client)

# Test on first response with ground truth citation
r = lexai_responses[0]
gt_row = gt_df.iloc[0]

print('Query:', r.get('query', ''))
print('Ground truth section:', gt_row.get('correct_section'))
print('Ground truth act:', gt_row.get('correct_act'))
print()
print('Response citations:', r.get('citations'))
print('Structured response:', r.get('structured_response'))
print()

# Test hallucination detection on this one response
hr_result = engine.compute_hallucination_rate([r])
print('HR result:', hr_result)
print()
print('Individual result:', hr_result.get('individual_results', [None])[0])
