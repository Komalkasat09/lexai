"""
Recompute all metrics on existing 293 saved responses
using the corrected metric functions.

Does NOT call Groq API — only recomputes scores.
Estimated runtime: 20-30 minutes (ChromaDB queries).
"""

import json
import pandas as pd
import chromadb
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics_engine import MetricsEngine


def recompute_all_metrics():
    """Recompute metrics on saved responses with fixed functions."""
    
    print("\n" + "="*80)
    print("RECOMPUTING METRICS WITH FIXED FUNCTIONS")
    print("="*80)
    
    # Load existing responses from checkpoint
    eval_dir = os.path.dirname(os.path.abspath(__file__))
    checkpoint_file = os.path.join(eval_dir, 'results', 'checkpoints', 'lexai_responses.json')
    
    if not os.path.exists(checkpoint_file):
        # Try old path
        checkpoint_file = os.path.join(eval_dir, 'evaluation', 'results', 'checkpoints', 'lexai_responses.json')
    
    if not os.path.exists(checkpoint_file):
        print(f"\n❌ Error: Could not find saved responses at {checkpoint_file}")
        print("   Please ensure you have run the evaluation first.")
        return
    
    with open(checkpoint_file) as f:
        saved_responses = json.load(f)
    
    print(f"\n✓ Loaded {len(saved_responses)} saved responses")
    
    # Load ground truth
    gt_file = os.path.join(eval_dir, 'ground_truth_verified.xlsx')
    if not os.path.exists(gt_file):
        gt_file = os.path.join(eval_dir, 'ground_truth.xlsx')
    
    gt_df = pd.read_excel(gt_file)
    
    # Only use verified rows
    verified = gt_df[
        gt_df['verified_by_lawyer'].notna() & 
        (gt_df['verified_by_lawyer'] != '')
    ]
    print(f"✓ Verified ground truth rows: {len(verified)}")
    
    # Initialize ChromaDB
    backend_dir = os.path.dirname(eval_dir)
    chroma_path = os.path.join(backend_dir, 'chroma_db')
    
    print(f"✓ Loading ChromaDB from: {chroma_path}")
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    
    # Initialize metrics engine with fixed functions
    metrics_engine = MetricsEngine(verified, chroma_client)
    
    print("\n" + "="*80)
    print("RECOMPUTING METRICS FOR EACH QUERY")
    print("="*80)
    
    # Match responses to ground truth by query_id
    results = []
    
    for idx, saved in enumerate(saved_responses):
        query_id = saved.get('query_id')
        gt_row = verified[verified['query_id'] == query_id]
        
        if gt_row.empty:
            print(f"  ⚠️  No verified GT for query {query_id}, skipping")
            continue
        
        gt = gt_row.iloc[0].to_dict()
        response = saved.get('response', {})
        query_text = saved.get('query_text', '')
        
        # Recompute all metrics with fixed functions
        car = metrics_engine.compute_citation_accuracy([response], pd.DataFrame([gt]))
        hr = metrics_engine._detect_hallucination(response, gt)
        olr_result = metrics_engine.compute_outdated_law_rate([response])
        abstention = metrics_engine._is_abstention(response)
        acs = metrics_engine.compute_answer_completeness(response, gt)
        pak = metrics_engine.compute_retrieval_precision_at_k(query_text, gt, k=3)
        
        results.append({
            "query_id": query_id,
            "category": gt.get('category'),
            "car_score": car['individual_scores'][0],
            "hallucination_rate": hr['hallucination_rate'],
            "hallucinated_count": hr['hallucinated_count'],
            "total_claims": hr['total_claims'],
            "olr_score": olr_result.get('OLR_overall', 0),
            "is_abstention": abstention,
            "acs_score": acs['acs_score'],
            "p_at_1": pak['p_at_1'],
            "p_at_3": pak.get('p_at_3', 0),
            "confidence": response.get('confidence', ''),
        })
        
        if (idx + 1) % 25 == 0:
            print(f"  Recomputed {idx + 1}/{len(saved_responses)} queries...")
    
    print(f"\n✓ Recomputed {len(results)} queries")
    
    # Compute abstention metrics across all
    print("\nComputing abstention metrics...")
    responses_list = [s['response'] for s in saved_responses 
                      if any(r['query_id'] == s['query_id'] for r in results)]
    gt_list = [verified[verified['query_id'] == r['query_id']].iloc[0].to_dict() 
               for r in results]
    
    abstention_metrics = metrics_engine.compute_abstention_metrics(
        responses_list, gt_list
    )
    
    # Save recomputed results
    results_dir = os.path.join(eval_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)
    results_df = pd.DataFrame(results)
    output_path = os.path.join(results_dir, 'recomputed_metrics.csv')
    results_df.to_csv(output_path, index=False)
    
    # Print summary
    print("\n" + "="*80)
    print("RECOMPUTED METRICS SUMMARY (Fixed Functions)")
    print("="*80)
    print(f"\nQueries evaluated: {len(results)}")
    
    print(f"\n📊 CAR (Citation Accuracy):")
    print(f"  Mean: {results_df['car_score'].mean():.3f}")
    print(f"  Std:  {results_df['car_score'].std():.3f}")
    print(f"  Median: {results_df['car_score'].median():.3f}")
    
    print(f"\n📊 HR (Hallucination Rate):")
    print(f"  Mean: {results_df['hallucination_rate'].mean():.3f}")
    print(f"  Std:  {results_df['hallucination_rate'].std():.3f}")
    print(f"  Total Claims: {results_df['total_claims'].sum()}")
    print(f"  Total Hallucinated: {results_df['hallucinated_count'].sum()}")
    
    print(f"\n📊 ACS (Answer Completeness):")
    print(f"  Mean: {results_df['acs_score'].mean():.1f}%")
    print(f"  Std:  {results_df['acs_score'].std():.1f}%")
    print(f"  Median: {results_df['acs_score'].median():.1f}%")
    
    print(f"\n📊 P@1 (Retrieval Precision):")
    print(f"  Mean: {results_df['p_at_1'].mean():.3f}")
    print(f"  Std:  {results_df['p_at_1'].std():.3f}")
    
    print(f"\n📊 P@3 (Retrieval Precision):")
    print(f"  Mean: {results_df['p_at_3'].mean():.3f}")
    print(f"  Std:  {results_df['p_at_3'].std():.3f}")
    
    print(f"\n📊 OLR (Outdated Law Rate):")
    print(f"  Mean: {results_df['olr_score'].mean():.1f}%")
    
    print(f"\n📊 Abstention:")
    print(f"  Rate: {abstention_metrics['abstention_rate']:.3f}")
    print(f"  Precision: {abstention_metrics['abstention_precision']:.3f}")
    print(f"  Recall: {abstention_metrics['abstention_recall']:.3f}")
    print(f"  F1: {abstention_metrics['f1_abstention']:.3f}")
    print(f"  TP: {abstention_metrics['TP']}, FP: {abstention_metrics['FP']}, FN: {abstention_metrics['FN']}, TN: {abstention_metrics['TN']}")
    
    print(f"\n📊 By Category:")
    category_summary = results_df.groupby('category').agg({
        'car_score': 'mean',
        'hallucination_rate': 'mean',
        'acs_score': 'mean',
        'p_at_1': 'mean'
    }).round(3)
    print(category_summary)
    
    print("\n" + "="*80)
    print(f"✅ Results saved to: {output_path}")
    print("="*80)
    
    return results_df, abstention_metrics


if __name__ == "__main__":
    recompute_all_metrics()
