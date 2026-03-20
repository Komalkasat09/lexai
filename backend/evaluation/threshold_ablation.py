"""
Confidence Threshold Ablation Study
====================================

Purpose: Select confidence thresholds on a strict holdout
set and report objective-ranked candidates for deployment.
This script now evaluates multiple threshold pairs and should
be treated as the canonical source for paper threshold values.

Requirement: Use a 50-query validation subset that is 
SEPARATE from the 293 main evaluation queries. 
This prevents data leakage. Select these 50 queries 
from verified ground truth, stratified across all 
7 categories (about 7 queries per category).
"""

import json
import time
import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from groq import Groq, RateLimitError
import chromadb
from typing import Dict, List
from pathlib import Path

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics_engine import MetricsEngine

# Six threshold pairs to test
THRESHOLD_PAIRS = [
    (0.90, 0.75),
    (0.85, 0.70),  # Current default — expected to be near optimal
    (0.80, 0.65),
    (0.75, 0.60),
    (0.70, 0.55),
    (0.65, 0.50),
]

def select_validation_subset(
    ground_truth_path: str,
    main_eval_query_ids: list,
    n_per_category: int = 7,
) -> pd.DataFrame:
    """
    Select 50 validation queries NOT in main evaluation set.
    Stratified: ~7 per category across 7 categories.
    
    Holdout-only policy: never sample from main evaluation queries.
    """
    gt_df = pd.read_excel(ground_truth_path, sheet_name='Ground Truth Dataset')
    
    print(f"  Total queries in ground truth: {len(gt_df)}")
    
    # Use all queries (verification column is empty)
    verified = gt_df
    
    print(f"  Available queries: {len(verified)}")
    print(f"  Main eval query IDs to exclude: {len(main_eval_query_ids)}")
    
    # Exclude queries already used in main evaluation
    holdout = verified[
        ~verified['query_id'].isin(main_eval_query_ids)
    ]
    
    print(f"  Holdout queries (after exclusion): {len(holdout)}")
    
    if len(holdout) == 0:
        raise ValueError(
            "No holdout queries available. Holdout-only threshold tuning cannot proceed. "
            "Provide a validation split not present in main evaluation query IDs."
        )
    if len(holdout) < 50:
        print(f"  WARNING: Only {len(holdout)} holdout queries available.")
        print("  Proceeding with all available holdout queries (no overlap).")
    
    # Stratified sample across categories (if category column exists)
    if 'category' in holdout.columns:
        categories = holdout['category'].unique().tolist()
        
        validation_rows = []
        for cat in categories:
            cat_rows = holdout[holdout['category'] == cat]
            n = min(n_per_category, len(cat_rows))
            if n > 0:
                sampled = cat_rows.sample(n=n, random_state=42)
                validation_rows.append(sampled)
            else:
                print(f"  WARNING: No holdout queries for category {cat}")
        
        if validation_rows:
            validation_df = pd.concat(validation_rows, ignore_index=True)
        else:
            # Fallback to random sampling
            n_sample = min(50, len(holdout))
            validation_df = holdout.sample(n=n_sample, random_state=42)
    else:
        # No category column - just sample randomly
        n_sample = min(50, len(holdout))
        validation_df = holdout.sample(n=n_sample, random_state=42)
    
    print(f"\nValidation subset: {len(validation_df)} queries")
    if 'category' in validation_df.columns:
        print(f"Categories: {validation_df['category'].value_counts().to_dict()}")
    
    return validation_df

def _is_abstained(response: dict) -> bool:
    if bool(response.get('trigger_uncertainty')) or bool(response.get('abstained')):
        return True
    answer = str(response.get('answer', '')).lower()
    markers = [
        'cannot provide a reliable answer',
        'cannot answer',
        'insufficient reliable information',
        'please consult primary sources',
    ]
    return any(marker in answer for marker in markers)


def _normalize_metric(value: float) -> float:
    value = float(value)
    return value / 100.0 if value > 1.0 else value


def _extract_main_eval_query_ids(ground_truth_path: str, lexai_checkpoint_path: str) -> list:
    """Map main evaluation checkpoint queries to ground-truth query IDs."""
    gt_df = pd.read_excel(ground_truth_path, sheet_name='Ground Truth Dataset')
    query_col = 'query_text' if 'query_text' in gt_df.columns else 'query'
    query_to_id = {
        str(row.get(query_col, '')): row.get('query_id')
        for _, row in gt_df.iterrows()
    }

    if not os.path.exists(lexai_checkpoint_path):
        raise FileNotFoundError(
            f"Main evaluation checkpoint not found: {lexai_checkpoint_path}. "
            "Cannot enforce holdout-only threshold tuning."
        )

    with open(lexai_checkpoint_path) as f:
        main_responses = json.load(f)

    query_ids = []
    for idx, resp in enumerate(main_responses):
        if isinstance(resp, dict) and resp.get('query_id') is not None:
            query_ids.append(resp.get('query_id'))
            continue
        query_text = str(resp.get('query', '')) if isinstance(resp, dict) else ''
        mapped = query_to_id.get(query_text)
        if mapped is not None:
            query_ids.append(mapped)

    if not query_ids:
        raise ValueError(
            "Unable to infer main evaluation query IDs from checkpoint. "
            "Populate query_id or query text in checkpoint to prevent overlap leakage."
        )

    return list(dict.fromkeys(query_ids))

def run_ablation_for_threshold_pair(
    high_thresh: float,
    medium_thresh: float,
    validation_queries: pd.DataFrame,
    checkpoint_dir: str,
    chroma_path: str = "../chroma_db"
) -> dict:
    """
    Run all validation queries with one threshold pair.
    Returns aggregated metrics.
    """
    from llm.legal_llm import LegalLLM
    
    pair_key = f"h{high_thresh}_m{medium_thresh}"
    checkpoint_path = os.path.join(checkpoint_dir, f"{pair_key}.json")
    
    responses = []
    
    # Load checkpoint if exists
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path) as f:
            responses = json.load(f)
        print(f"  Resuming from {len(responses)} responses")
    
    start_idx = len(responses)
    
    # Initialize LexAI ONCE for this threshold pair (not per query!)
    print(f"  Initializing LexAI with HIGH={high_thresh}, MEDIUM={medium_thresh}...")
    lexai = LegalLLM(
        persist_directory=chroma_path,
        confidence_high=high_thresh,
        confidence_medium=medium_thresh
    )
    print(f"  ✓ LexAI ready (will reuse for all {len(validation_queries)} queries)\n")
    
    for i in range(start_idx, len(validation_queries)):
        row = validation_queries.iloc[i]
        
        retries = 0
        while retries < 3:
            try:
                print(f"    Query {i+1}/{len(validation_queries)}: {row.get('query_text', '')[:50]}...")
                
                # Use the EXISTING lexai instance (no re-initialization!)
                raw_response = lexai.answer_legal_question(row.get('query_text', ''))
                
                # Standardize response format
                if isinstance(raw_response, dict):
                    response = {
                        "answer": raw_response.get('answer', ''),
                        "citations": raw_response.get('citations', []),
                        "confidence": raw_response.get('confidence', 'low'),
                        "abstained": raw_response.get('abstained', False)
                    }
                else:
                    response = {
                        "answer": str(raw_response),
                        "citations": [],
                        "confidence": "low",
                        "abstained": False
                    }
                
                responses.append({
                    "query_id": row.get('query_id', i),
                    "query_text": row.get('query_text', ''),
                    "category": row.get('category', 'unknown'),
                    "response": response
                })
                
                time.sleep(2.0)  # Rate limiting
                break
                
            except RateLimitError:
                wait = 60 * (retries + 1)
                print(f"  Rate limit. Waiting {wait}s...")
                time.sleep(wait)
                retries += 1
                
            except Exception as e:
                print(f"  Error on query {i}: {e}")
                responses.append({
                    "query_id": row.get('query_id', i),
                    "query_text": row.get('query_text', ''),
                    "category": row.get('category', 'unknown'),
                    "response": {
                        "answer": "ERROR",
                        "citations": [],
                        "confidence": "low",
                        "abstained": True,
                        "error": str(e)
                    }
                })
                break
        
        # Save checkpoint every 10 queries
        if (i + 1) % 10 == 0:
            with open(checkpoint_path, 'w') as f:
                json.dump(responses, f, indent=2)
            print(f"  Checkpoint saved: {len(responses)} responses")
    
    # Final save
    with open(checkpoint_path, 'w') as f:
        json.dump(responses, f, indent=2)
    
    # Standardize responses in the same order as validation_queries
    query_col = 'query_text' if 'query_text' in validation_queries.columns else 'query'
    query_to_response = {
        str(saved.get('query_text', '')): saved.get('response', {})
        for saved in responses
    }

    standardized_responses = []
    for _, row in validation_queries.iterrows():
        q_text = str(row.get(query_col, ''))
        raw = query_to_response.get(q_text, {})
        standardized_responses.append({
            'query': q_text,
            'answer': raw.get('answer', ''),
            'confidence': raw.get('confidence', 'LOW'),
            'citations': raw.get('citations', []),
            'trigger_uncertainty': bool(raw.get('trigger_uncertainty', False)) or bool(raw.get('abstained', False)),
        })

    gt_eval = validation_queries.copy()
    if 'query' not in gt_eval.columns and 'query_text' in gt_eval.columns:
        gt_eval = gt_eval.rename(columns={'query_text': 'query'})

    engine = MetricsEngine(gt_eval, None)
    metric_outputs = engine.compute_all_metrics(standardized_responses)

    total = len(standardized_responses)
    if total == 0:
        return {
            "high_threshold": high_thresh,
            "medium_threshold": medium_thresh,
            "accuracy": 0.0,
            "hallucination_rate": 0.0,
            "abstention_rate": 0.0,
            "answered_count": 0,
            "total_count": 0,
            "objective_score": 0.0
        }

    car_overall = _normalize_metric(metric_outputs.get('CAR', {}).get('CAR_overall', 0.0))
    hall_rate = _normalize_metric(metric_outputs.get('HR', {}).get('HR_overall', 0.0))
    abstention_rate = float(metric_outputs.get('AP', {}).get('abstention_rate', 0.0))

    answered_count = sum(1 for r in standardized_responses if not _is_abstained(r))
    
    # Weighted objective function
    # Prioritizes accuracy and hallucination reduction equally
    # Small penalty for abstaining too much
    objective = (
        0.45 * car_overall +
        0.45 * (1 - hall_rate) +
        0.10 * (1 - abstention_rate)
    )
    
    result = {
        "high_threshold": high_thresh,
        "medium_threshold": medium_thresh,
        "accuracy": round(car_overall, 4),
        "hallucination_rate": round(hall_rate, 4),
        "abstention_rate": round(abstention_rate, 4),
        "answered_count": answered_count,
        "total_count": total,
        "objective_score": round(objective, 4),
        "metrics_engine": {
            "CAR_overall": metric_outputs.get('CAR', {}).get('CAR_overall', 0.0),
            "HR_overall": metric_outputs.get('HR', {}).get('HR_overall', 0.0),
            "AP_abstention_rate": metric_outputs.get('AP', {}).get('abstention_rate', 0.0),
            "CCS_calibration_error": metric_outputs.get('CCS', {}).get('calibration_error', 0.0),
        },
    }
    
    print(
        f"  High={high_thresh:.2f}, Med={medium_thresh:.2f}: "
        f"Acc={car_overall:.3f}, HR={hall_rate:.3f}, "
        f"Abst={abstention_rate:.3f}, "
        f"Obj={objective:.3f}"
    )
    
    return result

def run_full_threshold_ablation():
    """
    Main function. Tests all 6 threshold pairs.
    Selects optimal. Generates figure and results.
    """
    print("="*60)
    print("CONFIDENCE THRESHOLD ABLATION STUDY")
    print("="*60)
    
    # Setup directories
    checkpoint_dir = 'evaluation/results/checkpoints/threshold_ablation'
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs('evaluation/results/figures', exist_ok=True)
    
    # Load main evaluation query IDs to exclude
    lexai_checkpoint_path = 'evaluation/results/checkpoints/lexai_responses.json'
    
    main_query_ids = _extract_main_eval_query_ids(
        ground_truth_path='evaluation/ground_truth_verified.xlsx',
        lexai_checkpoint_path=lexai_checkpoint_path,
    )
    
    # Select validation subset
    print("\nSelecting validation subset...")
    validation_df = select_validation_subset(
        ground_truth_path='evaluation/ground_truth_verified.xlsx',
        main_eval_query_ids=main_query_ids,
        n_per_category=7,
    )
    
    # Run all threshold pairs
    print(f"\nTesting {len(THRESHOLD_PAIRS)} threshold pairs...")
    print("="*60)
    
    all_results = []
    
    for high_thresh, medium_thresh in THRESHOLD_PAIRS:
        print(f"\nThreshold pair: HIGH={high_thresh}, MEDIUM={medium_thresh}")
        
        result = run_ablation_for_threshold_pair(
            high_thresh=high_thresh,
            medium_thresh=medium_thresh,
            validation_queries=validation_df,
            checkpoint_dir=checkpoint_dir
        )
        all_results.append(result)
    
    # Find optimal threshold pair
    optimal = max(all_results, key=lambda x: x['objective_score'])
    
    print("\n" + "="*60)
    print("THRESHOLD ABLATION RESULTS")
    print("="*60)
    print(f"{'High':>6} {'Med':>6} {'Acc':>8} {'HR':>8} {'Abst':>8} {'Obj':>8}")
    print("-"*60)
    for r in all_results:
        marker = " ← OPTIMAL" if r == optimal else ""
        print(
            f"{r['high_threshold']:>6.2f} "
            f"{r['medium_threshold']:>6.2f} "
            f"{r['accuracy']:>8.3f} "
            f"{r['hallucination_rate']:>8.3f} "
            f"{r['abstention_rate']:>8.3f} "
            f"{r['objective_score']:>8.3f}"
            f"{marker}"
        )
    
    print(f"\nOptimal: HIGH={optimal['high_threshold']}, "
          f"MEDIUM={optimal['medium_threshold']}")
    print(f"Objective score: {optimal['objective_score']:.4f}")
    
    # Generate publication-quality figure
    _generate_ablation_figure(all_results, optimal)
    
    # Save results table
    results_df = pd.DataFrame(all_results)
    results_df.to_csv(
        'evaluation/results/threshold_ablation_results.csv',
        index=False
    )
    
    print("\n" + "="*60)
    print("OUTPUT FILES")
    print("="*60)
    print("Figure: evaluation/results/figures/threshold_ablation.png")
    print("Results CSV: evaluation/results/threshold_ablation_results.csv")
    print("Checkpoints: evaluation/results/checkpoints/threshold_ablation/")
    
    return optimal, all_results

def _generate_ablation_figure(results: list, optimal: dict):
    """
    Publication-quality figure showing threshold sensitivity.
    4 lines on one plot with optimal threshold marked.
    300 DPI for journal submission.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    thresholds = [r['high_threshold'] for r in results]
    accuracy = [r['accuracy'] for r in results]
    hall_rate = [r['hallucination_rate'] for r in results]
    abstention = [r['abstention_rate'] for r in results]
    objective = [r['objective_score'] for r in results]
    
    ax.plot(
        thresholds, accuracy, 'b-o',
        label='Answer Accuracy', linewidth=2, markersize=8
    )
    ax.plot(
        thresholds, hall_rate, 'r-s',
        label='Hallucination Rate', linewidth=2, markersize=8
    )
    ax.plot(
        thresholds, abstention, 'g-^',
        label='Abstention Rate', linewidth=2, markersize=8
    )
    ax.plot(
        thresholds, objective, 'k--D',
        label='Objective Score', linewidth=2, markersize=8
    )
    
    # Mark optimal threshold
    ax.axvline(
        x=optimal['high_threshold'],
        color='gray',
        linestyle=':',
        linewidth=1.5,
        label=f"Optimal threshold ({optimal['high_threshold']})"
    )
    
    # Annotate optimal point
    ax.annotate(
        f"Optimal\n({optimal['high_threshold']}, {optimal['medium_threshold']})",
        xy=(optimal['high_threshold'], optimal['objective_score']),
        xytext=(optimal['high_threshold'] + 0.02, optimal['objective_score'] - 0.05),
        fontsize=9,
        arrowprops=dict(arrowstyle='->', color='black')
    )
    
    ax.set_xlabel('CONFIDENCE_HIGH Threshold', fontsize=13)
    ax.set_ylabel('Score', fontsize=13)
    ax.set_title(
        'Confidence Threshold Sensitivity Analysis\n'
        'Effect on Answer Accuracy, Hallucination Rate, and Abstention',
        fontsize=13
    )
    ax.legend(fontsize=10, loc='center right')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(-0.05, 1.05)
    
    plt.tight_layout()
    plt.savefig(
        'evaluation/results/figures/threshold_ablation.png',
        dpi=300,
        bbox_inches='tight'
    )
    plt.close()
    
    print("  Figure generated: threshold_ablation.png (300 DPI)")

if __name__ == "__main__":
    optimal, all_results = run_full_threshold_ablation()
