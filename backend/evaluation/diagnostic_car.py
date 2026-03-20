import json
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.metrics_engine import MetricsEngine
import chromadb

# Load all three systems
with open('results/checkpoints/lexai_responses.json') as f:
    lexai_responses = json.load(f)
    
with open('results/checkpoints/baseline_responses.json') as f:
    baseline_data = json.load(f)
    
no_rag = baseline_data['NoRAG']
simple_rag = baseline_data['SimpleRAG']

gt_df = pd.read_excel('ground_truth_verified.xlsx', sheet_name=0)

chroma_client = chromadb.PersistentClient(path='../legal_research_db')
engine = MetricsEngine(gt_df, chroma_client)

# Test on first 5 responses
print('Testing first 5 queries:')
print('='*80)

for i in range(5):
    gt_row = gt_df.iloc[i]
    lex_r = lexai_responses[i]
    norag_r = no_rag[i]
    
    print(f'\nQuery {i+1}: {gt_row["query_text"]}')
    print(f'GT: {gt_row["correct_act"]} Section {gt_row["correct_section"]}')
    print()
    
    # LexAI
    lex_car = engine.compute_citation_accuracy([lex_r])
    lex_score = lex_car['individual_scores'][0]
    print(f'LexAI CAR: {lex_score:.2f}')
    print(f'  Citations: {lex_r.get("citations")}')
    print(f'  Structured: {lex_r.get("structured_response")}')
    
    # NoRAG
    norag_car = engine.compute_citation_accuracy([norag_r])
    norag_score = norag_car['individual_scores'][0]
    print(f'NoRAG CAR: {norag_score:.2f}')
    print(f'  Citations: {norag_r.get("citations")}')
    print(f'  Answer snippet: {norag_r.get("answer", "")[:150]}')
    
    print('-'*80)
