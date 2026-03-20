"""
BNS/BNSS Middleware Ablation Study

Purpose: Prove the BNS middleware contribution is real by measuring
Outdated Law Rate (OLR) with middleware ON vs OFF.

This quantifies whether the middleware actually reduces outdated law
citations on IPC-to-BNS transition queries.
"""

import json
import time
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from groq import RateLimitError
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.legal_llm import LegalLLM


def load_transition_queries(
    ground_truth_path: str,
    lexai_responses_path: str
) -> pd.DataFrame:
    """
    Load only IPC to BNS Transition category queries
    from the main evaluation set.
    These are the queries where BNS middleware applies.
    """
    # Get absolute path to ground truth
    if not os.path.isabs(ground_truth_path):
        eval_dir = os.path.dirname(os.path.abspath(__file__))
        ground_truth_path = os.path.join(eval_dir, ground_truth_path)
    
    # Get absolute path to responses
    if not os.path.isabs(lexai_responses_path):
        eval_dir = os.path.dirname(os.path.abspath(__file__))
        lexai_responses_path = os.path.join(eval_dir, lexai_responses_path)
    
    gt_df = pd.read_excel(ground_truth_path, sheet_name='Ground Truth Dataset')
    
    # Filter to transition category only
    transition_queries = gt_df[
        gt_df['category'] == 'IPC to BNS Transition'
    ]
    
    # Also load main eval responses to match queries
    with open(lexai_responses_path) as f:
        main_responses = json.load(f)
    
    main_queries = {r['query'] for r in main_responses}
    
    # Keep only queries that were in main evaluation
    transition_queries = transition_queries[
        transition_queries['query_text'].isin(main_queries)
    ]
    
    print(f"Transition queries for ablation: {len(transition_queries)}")
    return transition_queries


def run_with_middleware_flag(
    query_text: str,
    use_middleware: bool,
    chroma_path: str = None
) -> dict:
    """
    Run full LexAI pipeline with middleware ON or OFF.
    Everything else identical — same retriever, same LLM,
    same thresholds from config.
    """
    # Use absolute path to chroma_db (same as run_evaluation.py)
    if chroma_path is None:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        chroma_path = os.path.join(backend_dir, "chroma_db")
    
    # Initialize LLM with middleware flag
    llm = LegalLLM(
        persist_directory=chroma_path,
        use_bns_middleware=use_middleware
    )
    
    # Answer question (internally uses retriever with middleware flag)
    response = llm.answer_legal_question(query_text)
    
    # Add middleware flag to response for tracking
    response['middleware_applied'] = use_middleware
    
    return response


def compute_olr_ipc_bns(
    response: dict,
    ground_truth: dict
) -> dict:
    """
    Compute Outdated Law Rate specifically for 
    IPC to BNS transition queries.
    
    OLR_ipc_bns = system cited IPC section WITHOUT
    noting BNS equivalent when transition applies.
    
    Three sub-metrics:
    1. cited_ipc_without_bns: mentioned IPC, no BNS note
    2. cited_crpc_without_bnss: mentioned CrPC, no BNSS note  
    3. correct_transition: correctly mapped IPC to BNS
    """
    answer = response.get('answer', '').lower()
    warnings = response.get('warnings', [])
    
    # Check if BNS/BNSS warning was added
    has_bns_warning = any(
        'bns' in str(w).lower() or 'bnss' in str(w).lower() 
        for w in warnings
    )
    
    # Check if response mentions IPC
    mentions_ipc = any(term in answer for term in [
        'indian penal code', 'ipc', 'i.p.c'
    ])
    
    # Check if response mentions CrPC  
    mentions_crpc = any(term in answer for term in [
        'code of criminal procedure', 'crpc', 'cr.p.c'
    ])
    
    # Check if BNS transition note present in answer
    has_bns_note = (
        has_bns_warning or
        any(term in answer for term in [
            'bharatiya nyaya sanhita', 'bns',
            'replaced', 'transition', 'july 2024',
            'new law', 'equivalent', '2023'
        ])
    )
    
    # Check if BNSS transition note present
    has_bnss_note = (
        has_bns_warning or  # Same warning covers both
        'bnss' in answer or
        'bharatiya nagarik suraksha sanhita' in answer
    )
    
    # Check if correct BNS section cited
    correct_section = str(ground_truth.get('correct_section', ''))
    correct_act = str(ground_truth.get('correct_act', '')).lower()
    
    cited_correct_bns = (
        ('bharatiya nyaya sanhita' in correct_act or 'bns' in correct_act) and
        (correct_section in answer if correct_section else False)
    )
    
    # OLR: cited old law without noting transition
    olr_ipc = 1.0 if (mentions_ipc and not has_bns_note) else 0.0
    olr_crpc = 1.0 if (mentions_crpc and not has_bnss_note) else 0.0
    
    # Transition accuracy: correctly used BNS not IPC
    transition_correct = 1.0 if (cited_correct_bns or has_bns_note) else 0.0
    
    return {
        "olr_ipc_bns": olr_ipc,
        "olr_crpc_bnss": olr_crpc,
        "olr_combined": max(olr_ipc, olr_crpc),
        "transition_accuracy": transition_correct,
        "mentions_ipc": mentions_ipc,
        "has_bns_note": has_bns_note
    }


def run_bns_ablation():
    """
    Main ablation function.
    
    Runs transition queries with middleware ON and OFF.
    Compares OLR and transition accuracy.
    This quantifies the middleware contribution.
    """
    # Get absolute paths for all files
    eval_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = eval_dir.parent
    chroma_db_path = str(backend_dir / "chroma_db")
    checkpoint_dir = str(eval_dir / 'results' / 'checkpoints' / 'bns_ablation')
    results_dir = str(eval_dir / 'results')
    figures_dir = str(Path(results_dir) / 'figures')
    
    print("\n" + "="*70)
    print("BNS MIDDLEWARE ABLATION STUDY")
    print("="*70)
    print(f"Database: {chroma_db_path}")
    print(f"Checkpoint dir: {checkpoint_dir}")
    print(f"Results dir: {results_dir}")
    print("="*70 + "\n")
    
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)
    
    # Load transition queries
    transition_queries = load_transition_queries(
        ground_truth_path='evaluation/ground_truth_verified.xlsx',
        lexai_responses_path='evaluation/results/checkpoints/lexai_responses.json'
    )
    
    if len(transition_queries) < 10:
        raise ValueError(
            f"Only {len(transition_queries)} transition queries found. "
            f"Need at least 10 for meaningful ablation. "
            f"Add more IPC to BNS Transition queries to ground truth."
        )
    
    queries_list = transition_queries.to_dict('records')
    
    # Run both conditions
    results = {}
    
    for use_middleware in [True, False]:
        condition = "with_middleware" if use_middleware else "without_middleware"
        checkpoint_path = os.path.join(checkpoint_dir, f"{condition}.json")
        
        print(f"\n{'='*60}")
        print(f"Running: {condition}")
        print(f"{'='*60}")
        
        responses = []
        
        # Load checkpoint
        if os.path.exists(checkpoint_path):
            with open(checkpoint_path) as f:
                responses = json.load(f)
            print(f"Resuming from {len(responses)} responses")
        
        start_idx = len(responses)
        
        for i, query_data in enumerate(queries_list[start_idx:], start=start_idx):
            retries = 0
            while retries < 3:
                try:
                    print(f"  Query {i+1}/{len(queries_list)}: {query_data['query_text'][:60]}...")
                    
                    response = run_with_middleware_flag(
                        query_data['query_text'],
                        use_middleware
                    )
                    
                    responses.append({
                        "query_text": query_data['query_text'],
                        "category": query_data['category'],
                        "response": response,
                        "condition": condition
                    })
                    time.sleep(2.0)
                    break
                    
                except RateLimitError:
                    wait = 60 * (retries + 1)
                    print(f"  Rate limit. Waiting {wait}s...")
                    time.sleep(wait)
                    retries += 1
                    
                except Exception as e:
                    print(f"  Error: {e}")
                    responses.append({
                        "query_text": query_data['query_text'],
                        "category": query_data['category'],
                        "response": {
                            "answer": "ERROR",
                            "confidence": "LOW",
                            "warnings": [],
                            "error": str(e)
                        },
                        "condition": condition
                    })
                    break
            
            if (i + 1) % 10 == 0:
                with open(checkpoint_path, 'w') as f:
                    json.dump(responses, f, indent=2)
                print(f"  Checkpoint: {len(responses)}/{len(queries_list)}")
        
        # Final save
        with open(checkpoint_path, 'w') as f:
            json.dump(responses, f, indent=2)
        
        # Compute OLR metrics
        all_query_scores = {}
        answered_query_scores = {}
        skipped_uncertain = 0
        error_count = 0
        
        for idx, saved in enumerate(responses):
            response_answer = saved['response'].get('answer', '')
            
            if saved['response'].get('answer') == 'ERROR':
                error_count += 1
                continue

            is_uncertain = (
                'cannot provide a reliable answer' in response_answer.lower() or
                'consult primary sources' in response_answer.lower() or
                saved['response'].get('trigger_uncertainty', False)
            )
            if is_uncertain:
                skipped_uncertain += 1
            
            query_text = saved['query_text']
            gt_row = transition_queries[
                transition_queries['query_text'] == query_text
            ]
            if gt_row.empty:
                continue
                
            gt = gt_row.iloc[0].to_dict()
            olr = compute_olr_ipc_bns(saved['response'], gt)
            all_query_scores[query_text] = {
                'olr': olr['olr_combined'],
                'transition': olr['transition_accuracy'],
            }
            if not is_uncertain:
                answered_query_scores[query_text] = {
                    'olr': olr['olr_combined'],
                    'transition': olr['transition_accuracy'],
                }
        
        print(f"  Analyzed {len(answered_query_scores)} answered queries (skipped {skipped_uncertain} uncertain)")
        
        if len(answered_query_scores) < 5:
            print(f"  WARNING: Only {len(answered_query_scores)} answered queries - results may not be reliable")

        all_olr_scores = [v['olr'] for v in all_query_scores.values()]
        all_transition_scores = [v['transition'] for v in all_query_scores.values()]
        answered_olr_scores = [v['olr'] for v in answered_query_scores.values()]
        answered_transition_scores = [v['transition'] for v in answered_query_scores.values()]

        total_queries = len(transition_queries)
        answered_queries = len(answered_query_scores)
        abstained_or_uncertain = total_queries - answered_queries - error_count
        
        results[condition] = {
            "intention": {
                "olr_mean": np.mean(all_olr_scores) if all_olr_scores else 0.0,
                "olr_std": np.std(all_olr_scores) if all_olr_scores else 0.0,
                "transition_accuracy_mean": np.mean(all_transition_scores) if all_transition_scores else 0.0,
                "transition_accuracy_std": np.std(all_transition_scores) if all_transition_scores else 0.0,
                "n_queries": len(all_olr_scores),
                "olr_scores": all_olr_scores,
                "transition_scores": all_transition_scores,
            },
            "conditional": {
                "olr_mean": np.mean(answered_olr_scores) if answered_olr_scores else 0.0,
                "olr_std": np.std(answered_olr_scores) if answered_olr_scores else 0.0,
                "transition_accuracy_mean": np.mean(answered_transition_scores) if answered_transition_scores else 0.0,
                "transition_accuracy_std": np.std(answered_transition_scores) if answered_transition_scores else 0.0,
                "n_queries": len(answered_olr_scores),
                "olr_scores": answered_olr_scores,
                "transition_scores": answered_transition_scores,
            },
            "query_scores": {
                "all": all_query_scores,
                "answered": answered_query_scores,
            },
            "attrition": {
                "total_queries": total_queries,
                "answered_queries": answered_queries,
                "abstained_or_uncertain": max(abstained_or_uncertain, 0),
                "errors": error_count,
            },
        }
        
        print(f"\n{condition} results:")
        print(f"  Intention OLR (all queries): {results[condition]['intention']['olr_mean']:.3f}")
        print(f"  Conditional OLR (answered):  {results[condition]['conditional']['olr_mean']:.3f}")
        print(f"  Answered queries: {results[condition]['attrition']['answered_queries']}/{results[condition]['attrition']['total_queries']}")
    
    # Compute improvement statistics
    with_olr = results['with_middleware']['conditional']['olr_mean']
    without_olr = results['without_middleware']['conditional']['olr_mean']
    with_trans = results['with_middleware']['conditional']['transition_accuracy_mean']
    without_trans = results['without_middleware']['conditional']['transition_accuracy_mean']
    
    olr_reduction_abs = without_olr - with_olr
    olr_reduction_pct = (
        (without_olr - with_olr) / max(without_olr, 0.001) * 100
    )
    transition_gain = with_trans - without_trans
    
    # Statistical significance tests on matched query sets
    from scipy import stats

    matched_all = sorted(
        set(results['with_middleware']['query_scores']['all'].keys())
        & set(results['without_middleware']['query_scores']['all'].keys())
    )
    matched_answered = sorted(
        set(results['with_middleware']['query_scores']['answered'].keys())
        & set(results['without_middleware']['query_scores']['answered'].keys())
    )

    if len(matched_answered) >= 2:
        with_scores = [results['with_middleware']['query_scores']['answered'][q]['olr'] for q in matched_answered]
        without_scores = [results['without_middleware']['query_scores']['answered'][q]['olr'] for q in matched_answered]
        t_stat, p_value = stats.ttest_rel(without_scores, with_scores)
    else:
        t_stat, p_value = np.nan, np.nan

    if len(matched_all) >= 2:
        with_scores_all = [results['with_middleware']['query_scores']['all'][q]['olr'] for q in matched_all]
        without_scores_all = [results['without_middleware']['query_scores']['all'][q]['olr'] for q in matched_all]
        t_stat_all, p_value_all = stats.ttest_rel(without_scores_all, with_scores_all)
    else:
        t_stat_all, p_value_all = np.nan, np.nan
    
    print("\n" + "="*70)
    print("BNS MIDDLEWARE ABLATION RESULTS")
    print("="*70)
    print(f"Total queries tested: {len(transition_queries)}")
    print("Attrition table:")
    print(
        f"  with_middleware: answered={results['with_middleware']['attrition']['answered_queries']}, "
        f"abstained_or_uncertain={results['with_middleware']['attrition']['abstained_or_uncertain']}, "
        f"errors={results['with_middleware']['attrition']['errors']}"
    )
    print(
        f"  without_middleware: answered={results['without_middleware']['attrition']['answered_queries']}, "
        f"abstained_or_uncertain={results['without_middleware']['attrition']['abstained_or_uncertain']}, "
        f"errors={results['without_middleware']['attrition']['errors']}"
    )
    print(f"\nOutdated Law Rate (OLR) — lower is better:")
    print(f"  Without middleware: {without_olr:.3f}")
    print(f"  With middleware:    {with_olr:.3f}")
    print(f"  Absolute reduction: {olr_reduction_abs:.3f}")
    print(f"  Relative reduction: {olr_reduction_pct:.1f}%")
    print(f"\nTransition Accuracy — higher is better:")
    print(f"  Without middleware: {without_trans:.3f}")
    print(f"  With middleware:    {with_trans:.3f}")
    print(f"  Absolute gain:      {transition_gain:.3f}")
    print(f"\nStatistical significance:")
    print(f"  Conditional-on-answer paired t-statistic: {t_stat:.4f}")
    print(f"  Conditional-on-answer paired p-value:     {p_value:.4f}")
    print(f"  Intention-to-answer paired t-statistic:   {t_stat_all:.4f}")
    print(f"  Intention-to-answer paired p-value:       {p_value_all:.4f}")
    if np.isfinite(p_value):
        print(f"  Conditional significant: {'YES (p < 0.05)' if p_value < 0.05 else 'NO'}")
    
    # Paper-ready sentence
    print("\n" + "="*70)
    print("PAPER RESULT SENTENCE:")
    print("="*70)
    p_str = 'n/a' if not np.isfinite(p_value) else ('<0.001' if p_value < 0.001 else f'={p_value:.3f}')
    print(
        f"Our BNS/BNSS transition middleware reduced outdated law "
        f"citations from {without_olr:.1%} to {with_olr:.1%} "
        f"(absolute reduction: {olr_reduction_abs:.1%}, "
        f"relative: {olr_reduction_pct:.0f}%) "
        f"on IPC-to-BNS transition queries (p{p_str})."
    )
    
    # Save results
    summary = {
        "with_middleware": {
            k: float(v) if isinstance(v, (np.floating, np.integer)) else v
            for k, v in results['with_middleware'].items()
            if k != 'query_scores'
        },
        "without_middleware": {
            k: float(v) if isinstance(v, (np.floating, np.integer)) else v
            for k, v in results['without_middleware'].items()
            if k != 'query_scores'
        },
        "improvement": {
            "olr_reduction_absolute": float(olr_reduction_abs),
            "olr_reduction_percent": float(olr_reduction_pct),
            "transition_accuracy_gain": float(transition_gain),
            "p_value_conditional": None if not np.isfinite(p_value) else float(p_value),
            "t_statistic_conditional": None if not np.isfinite(t_stat) else float(t_stat),
            "p_value_intention": None if not np.isfinite(p_value_all) else float(p_value_all),
            "t_statistic_intention": None if not np.isfinite(t_stat_all) else float(t_stat_all),
            "significant_conditional": bool(np.isfinite(p_value) and p_value < 0.05),
            "matched_pairs_conditional": len(matched_answered),
            "matched_pairs_intention": len(matched_all),
        },
    }
    
    results_file = os.path.join(results_dir, 'bns_ablation_results.json')
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✓ Results saved: {results_file}")

    # Save paper-ready tables
    attrition_rows = []
    for condition in ['with_middleware', 'without_middleware']:
        a = results[condition]['attrition']
        attrition_rows.append({
            'condition': condition,
            'total_queries': a['total_queries'],
            'answered_queries': a['answered_queries'],
            'abstained_or_uncertain': a['abstained_or_uncertain'],
            'errors': a['errors'],
        })
    attrition_df = pd.DataFrame(attrition_rows)
    attrition_csv = os.path.join(results_dir, 'bns_ablation_attrition.csv')
    attrition_df.to_csv(attrition_csv, index=False)
    print(f"✓ Attrition table saved: {attrition_csv}")

    metric_rows = []
    for condition in ['with_middleware', 'without_middleware']:
        intention = results[condition]['intention']
        conditional = results[condition]['conditional']
        metric_rows.append({
            'condition': condition,
            'intention_olr_mean': intention['olr_mean'],
            'intention_transition_accuracy_mean': intention['transition_accuracy_mean'],
            'intention_n_queries': intention['n_queries'],
            'conditional_olr_mean': conditional['olr_mean'],
            'conditional_transition_accuracy_mean': conditional['transition_accuracy_mean'],
            'conditional_n_queries': conditional['n_queries'],
        })
    metric_df = pd.DataFrame(metric_rows)
    metrics_csv = os.path.join(results_dir, 'bns_ablation_table.csv')
    metric_df.to_csv(metrics_csv, index=False)
    print(f"✓ Metrics table saved: {metrics_csv}")
    
    # Generate figure
    _generate_ablation_figure(results, summary, figures_dir)
    
    return summary


def _generate_ablation_figure(results: dict, summary: dict, figures_dir: str):
    """
    Side-by-side bar chart comparing middleware ON vs OFF.
    Two metrics: OLR and Transition Accuracy.
    Error bars from standard deviation.
    Publication quality 300 DPI.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    conditions = ['Without\nMiddleware', 'With\nMiddleware']
    colors = ['#d73027', '#1a9850']
    
    # Plot 1: OLR (lower is better)
    olr_values = [
        results['without_middleware']['conditional']['olr_mean'],
        results['with_middleware']['conditional']['olr_mean']
    ]
    olr_stds = [
        results['without_middleware']['conditional']['olr_std'],
        results['with_middleware']['conditional']['olr_std']
    ]
    
    bars1 = ax1.bar(
        conditions, olr_values,
        color=colors, alpha=0.85,
        yerr=olr_stds, capsize=8,
        error_kw={'linewidth': 2}
    )
    ax1.set_title(
        'Outdated Law Rate\n(Lower is Better)',
        fontsize=13, fontweight='bold'
    )
    ax1.set_ylabel('OLR Score', fontsize=12)
    ax1.set_ylim(0, 1.0)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, val in zip(bars1, olr_values):
        ax1.text(
            bar.get_x() + bar.get_width()/2.,
            bar.get_height() + 0.02,
            f'{val:.3f}',
            ha='center', va='bottom', fontsize=11,
            fontweight='bold'
        )
    
    # Add significance marker
    p_val = summary['improvement']['p_value_conditional']
    if p_val is None:
        sig_text = 'n/a'
    else:
        sig_text = (
            '***' if p_val < 0.001 else
            '**' if p_val < 0.01 else
            '*' if p_val < 0.05 else 'ns'
        )
    y_pos = max(olr_values) + max(olr_stds) + 0.1
    ax1.text(
        0.5, y_pos,
        sig_text,
        ha='center', fontsize=14, fontweight='bold'
    )
    
    # Plot 2: Transition Accuracy (higher is better)
    trans_values = [
        results['without_middleware']['conditional']['transition_accuracy_mean'],
        results['with_middleware']['conditional']['transition_accuracy_mean']
    ]
    trans_stds = [
        results['without_middleware']['conditional']['transition_accuracy_std'],
        results['with_middleware']['conditional']['transition_accuracy_std']
    ]
    
    bars2 = ax2.bar(
        conditions, trans_values,
        color=colors, alpha=0.85,
        yerr=trans_stds, capsize=8,
        error_kw={'linewidth': 2}
    )
    ax2.set_title(
        'Transition Accuracy\n(Higher is Better)',
        fontsize=13, fontweight='bold'
    )
    ax2.set_ylabel('Accuracy Score', fontsize=12)
    ax2.set_ylim(0, 1.0)
    ax2.grid(True, alpha=0.3, axis='y')
    
    for bar, val in zip(bars2, trans_values):
        ax2.text(
            bar.get_x() + bar.get_width()/2.,
            bar.get_height() + 0.02,
            f'{val:.3f}',
            ha='center', va='bottom', fontsize=11,
            fontweight='bold'
        )
    
    # Overall title
    olr_pct = summary['improvement']['olr_reduction_percent']
    fig.suptitle(
        f'Impact of BNS/BNSS Transition Middleware\n'
        f'OLR reduced by {olr_pct:.0f}% on transition queries',
        fontsize=14, fontweight='bold', y=1.02
    )
    
    plt.tight_layout()
    
    figure_path = os.path.join(figures_dir, 'bns_middleware_ablation.png')
    plt.savefig(
        figure_path,
        dpi=300,
        bbox_inches='tight'
    )
    plt.close()
    print(f"\n✓ Figure saved: {figure_path}")


if __name__ == "__main__":
    summary = run_bns_ablation()
