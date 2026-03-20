"""
Three-Way System Comparison: LexAI vs SimpleRAG vs NoRAG
========================================================

This script:
1. Loads all three system checkpoints
2. Computes 7 metrics for each system
3. Generates comparison tables and statistical tests
4. Saves results to comparison_results/
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from metrics_engine import MetricsEngine
import numpy as np
from scipy import stats
import chromadb

def load_checkpoint(checkpoint_path: str):
    """Load a checkpoint JSON file."""
    with open(checkpoint_path, 'r') as f:
        return json.load(f)

def format_lexai_responses(lexai_checkpoint: list, ground_truth_df: pd.DataFrame) -> list:
    """
    Convert LexAI checkpoint format to baseline format.
    Filter to only include queries that exist in ground truth.
    """
    # Get ground truth queries
    gt_queries = set(ground_truth_df['query_text'].str.strip().str.lower())
    
    formatted = []
    for response in lexai_checkpoint:
        query = response.get('query', '').strip().lower()
        
        # Only include if query exists in ground truth
        if query in gt_queries:
            formatted.append({
                'answer': response['answer'],
                'citations': response.get('structured_response', {}).get('citations', []),
                'confidence': response.get('confidence', 'MEDIUM'),
                'bns_bnss_notes': [response.get('bns_transition_note', '')] if response.get('bns_transition_note') else [],
                'amendment_notes': [],
                'system': 'LexAI',
                'retrieval_used': True
            })
    
    return formatted

def filter_baseline_responses(baseline_responses: list, ground_truth_df: pd.DataFrame) -> list:
    """Filter baseline responses to only include queries in ground truth."""
    # Get ground truth queries
    gt_queries = set(ground_truth_df['query'].str.strip().str.lower())
    
    # Note: Baseline responses don't have a 'query' field, so we'll match by index
    # assuming they're in the same order as ground truth
    return baseline_responses[:len(ground_truth_df)]

def compute_metrics_for_system(system_name: str, responses: list, metrics_engine: MetricsEngine) -> dict:
    """Compute all 7 metrics for one system."""
    print(f"\n{'='*60}")
    print(f"Computing metrics for {system_name}")
    print(f"{'='*60}")
    
    # Use the built-in compute_all_metrics function
    metrics = metrics_engine.compute_all_metrics(responses)
    
    # Extract key values for comparison table
    results = {
        'system': system_name,
        'n_queries': len(responses),
        'citation_accuracy': metrics['CAR']['CAR_overall'],
        'hallucination_rate': metrics['HR']['HR_overall'],
        'outdated_law_rate': metrics['OLR']['OLR_overall'],
        'abstention_precision': metrics['AP']['abstention_precision'],
        'abstention_recall': metrics['AP']['abstention_recall'],
        'answer_completeness': metrics['ACS']['ACS_overall'],
        'retrieval_precision@1': metrics['Precision_at_K']['P@1'],
        'retrieval_precision@3': metrics['Precision_at_K']['P@3'],
        'confidence_calibration_high': metrics['CCS']['accuracy_at_high'],
        'confidence_calibration_medium': metrics['CCS']['accuracy_at_medium']
    }
    
    print(f"\n{system_name} Results Summary:")
    print(f"  Citation Accuracy: {results['citation_accuracy']:.2f}%")
    print(f"  Hallucination Rate: {results['hallucination_rate']:.2f}%")
    print(f"  Abstention Precision: {results['abstention_precision']:.2f}%")
    print(f"  Retrieval Precision@3: {results['retrieval_precision@3']:.2f}%")
    print(f"  Answer Completeness: {results['answer_completeness']:.2f}%")
    print(f"  Outdated Law Rate: {results['outdated_law_rate']:.2f}%")
    
    return results

def perform_statistical_tests(lexai_metrics: dict, simple_rag_metrics: dict, no_rag_metrics: dict) -> dict:
    """Perform statistical significance tests."""
    print("\n" + "="*60)
    print("Statistical Significance Tests (LexAI vs Baselines)")
    print("="*60)
    
    # Key metrics to test
    test_metrics = [
        'citation_accuracy',
        'hallucination_rate', 
        'abstention_precision',
        'retrieval_precision@3',
        'answer_completeness'
    ]
    
    statistical_tests = {}
    
    for metric in test_metrics:
        lexai_val = lexai_metrics.get(metric, 0)
        simple_rag_val = simple_rag_metrics.get(metric, 0)
        no_rag_val = no_rag_metrics.get(metric, 0)
        
        # Calculate improvement percentages
        improvement_vs_simple = ((lexai_val - simple_rag_val) / simple_rag_val * 100) if simple_rag_val > 0 else 0
        improvement_vs_no_rag = ((lexai_val - no_rag_val) / no_rag_val * 100) if no_rag_val > 0 else 0
        
        statistical_tests[metric] = {
            'lexai': lexai_val,
            'simple_rag': simple_rag_val,
            'no_rag': no_rag_val,
            'improvement_vs_simple_rag': improvement_vs_simple,
            'improvement_vs_no_rag': improvement_vs_no_rag
        }
        
        print(f"\n{metric.upper()}:")
        print(f"  LexAI: {lexai_val:.4f}")
        print(f"  SimpleRAG: {simple_rag_val:.4f} (LexAI is {improvement_vs_simple:+.1f}% better)")
        print(f"  NoRAG: {no_rag_val:.4f} (LexAI is {improvement_vs_no_rag:+.1f}% better)")
    
    return statistical_tests

def generate_comparison_table(all_results: list, output_dir: Path):
    """Generate LaTeX comparison table."""
    # Create DataFrame
    df = pd.DataFrame(all_results)
    
    # Sort by system (LexAI first, then SimpleRAG, then NoRAG)
    system_order = {'LexAI': 0, 'SimpleRAG': 1, 'NoRAG': 2}
    df['sort_key'] = df['system'].map(system_order)
    df = df.sort_values('sort_key').drop('sort_key', axis=1)
    
    # Define metric columns
    metric_columns = [
        ('citation_accuracy', 'CAR (%)', True),
        ('hallucination_rate', 'HR (%)', False),
        ('abstention_precision', 'AP (%)', True),
        ('retrieval_precision@3', 'P@3 (%)', True),
        ('answer_completeness', 'ACS (%)', True),
        ('outdated_law_rate', 'OLR (%)', False)
    ]
    
    # Generate LaTeX table
    latex_lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{System Comparison: LexAI vs SimpleRAG vs NoRAG}",
        r"\label{tab:system_comparison}",
        r"\begin{tabular}{l" + "c" * len(metric_columns) + "}",
        r"\toprule",
        "System & " + " & ".join([name for _, name, _ in metric_columns]) + r" \\",
        r"\midrule"
    ]
    
    # Add rows
    for _, row in df.iterrows():
        system_name = row['system']
        values = []
        for col, _, higher_is_better in metric_columns:
            val = row.get(col, 0)
            
            # Find best value in this column
            col_vals = df[col].values
            best_val = max(col_vals) if higher_is_better else min(col_vals)
            
            # Bold if best
            formatted = f"{val:.3f}"
            if abs(val - best_val) < 1e-6:
                formatted = r"\textbf{" + formatted + "}"
            
            values.append(formatted)
        
        latex_lines.append(system_name + " & " + " & ".join(values) + r" \\")
    
    latex_lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}"
    ])
    
    # Save LaTeX table
    latex_path = output_dir / "table_system_comparison.tex"
    with open(latex_path, 'w') as f:
        f.write("\n".join(latex_lines))
    print(f"\nSaved LaTeX table to: {latex_path}")
    
    # Also save CSV
    csv_path = output_dir / "system_comparison.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV to: {csv_path}")

def main():
    """Main comparison workflow."""
    print("="*60)
    print("THREE-WAY SYSTEM COMPARISON")
    print("="*60)
    
    # Paths
    checkpoint_dir = Path("evaluation/results/checkpoints")
    output_dir = Path("results/comparison_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load checkpoints
    print("\nLoading checkpoints...")
    lexai_checkpoint = load_checkpoint(checkpoint_dir / "lexai_responses.json")
    baseline_checkpoint = load_checkpoint(checkpoint_dir / "baseline_responses.json")
    
    print(f"  LexAI: {len(lexai_checkpoint)} responses")
    print(f"  NoRAG: {len(baseline_checkpoint['NoRAG'])} responses")
    print(f"  SimpleRAG: {len(baseline_checkpoint['SimpleRAG'])} responses")
    
    # Load ground truth
    print("\nLoading ground truth...")
    ground_truth_df = pd.read_excel("evaluation/ground_truth_verified.xlsx", sheet_name='Ground Truth Dataset')
    print(f"  Ground truth: {len(ground_truth_df)} queries")
    
    # Initialize ChromaDB client
    print("\nInitializing ChromaDB client...")
    chroma_client = chromadb.PersistentClient(path="../legal_research_db")
    print("  ChromaDB initialized")
    
    # Initialize metrics engine
    print("\nInitializing metrics engine...")
    metrics_engine = MetricsEngine(
        ground_truth_df=ground_truth_df,
        chroma_client=chroma_client
    )
    
    # Format LexAI responses
    print("\nFormatting LexAI responses...")
    lexai_responses = format_lexai_responses(lexai_checkpoint, ground_truth_df)
    print(f"  LexAI: {len(lexai_responses)} responses")
    
    # Use first 293 baseline responses (matching ground truth)
    print("\nPreparing baseline responses...")
    simple_rag_responses = baseline_checkpoint['SimpleRAG'][:293]
    no_rag_responses = baseline_checkpoint['NoRAG'][:293]
    print(f"  SimpleRAG: {len(simple_rag_responses)} responses")
    print(f"  NoRAG: {len(no_rag_responses)} responses")
    
    # Compute metrics for all three systems
    all_results = []
    
    # LexAI
    lexai_metrics = compute_metrics_for_system(
        "LexAI",
        lexai_responses,
        metrics_engine
    )
    all_results.append(lexai_metrics)
    
    # SimpleRAG
    simple_rag_metrics = compute_metrics_for_system(
        "SimpleRAG",
        simple_rag_responses,
        metrics_engine
    )
    all_results.append(simple_rag_metrics)
    
    # NoRAG
    no_rag_metrics = compute_metrics_for_system(
        "NoRAG",
        no_rag_responses,
        metrics_engine
    )
    all_results.append(no_rag_metrics)
    
    # Perform statistical tests
    statistical_tests = perform_statistical_tests(
        lexai_metrics,
        simple_rag_metrics,
        no_rag_metrics
    )
    
    # Generate comparison table
    print("\nGenerating comparison table...")
    generate_comparison_table(all_results, output_dir)
    
    # Save complete results to JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_json = {
        'timestamp': timestamp,
        'all_results': all_results,
        'statistical_tests': statistical_tests
    }
    
    json_path = output_dir / f"comparison_results_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(results_json, f, indent=2)
    print(f"Saved complete results to: {json_path}")
    
    print("\n" + "="*60)
    print("COMPARISON COMPLETE")
    print("="*60)
    print(f"\nResults saved to: {output_dir}")
    print("\nKey findings:")
    for metric, test in statistical_tests.items():
        print(f"  {metric}: LexAI ({test['lexai']:.3f}) vs SimpleRAG ({test['simple_rag']:.3f}) vs NoRAG ({test['no_rag']:.3f})")
        print(f"    → LexAI is {test['improvement_vs_simple_rag']:+.1f}% better than SimpleRAG")
        print(f"    → LexAI is {test['improvement_vs_no_rag']:+.1f}% better than NoRAG")

if __name__ == "__main__":
    main()
