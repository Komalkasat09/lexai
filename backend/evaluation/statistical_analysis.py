"""
Statistical Analysis for Paper Table 1

Generates complete statistics for all metrics:
- Mean ± 95% CI for each system
- Paired t-tests (LexAI vs baselines)
- Cohen's d effect sizes
- Output ready for LaTeX table

This is the source for Table 1 in the paper.
"""

import numpy as np
import pandas as pd
from scipy import stats
import os


def bootstrap_ci(data, n_iterations=10000, ci=0.95, random_seed=42):
    """Compute bootstrap confidence interval."""
    np.random.seed(random_seed)
    data = np.array(data)
    mean = np.mean(data)
    
    boot_means = []
    for _ in range(n_iterations):
        sample = np.random.choice(data, size=len(data), replace=True)
        boot_means.append(np.mean(sample))
    
    alpha = 1 - ci
    lower = np.percentile(boot_means, 100 * alpha / 2)
    upper = np.percentile(boot_means, 100 * (1 - alpha / 2))
    
    return lower, upper


def cohens_d(group1, group2):
    """Compute Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return 0.0
    
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def interpret_effect_size(d):
    """Interpret Cohen's d."""
    d = abs(d)
    if d < 0.2:
        return 'negligible'
    elif d < 0.5:
        return 'small'
    elif d < 0.8:
        return 'medium'
    else:
        return 'large'


def format_p_value(p):
    """Format p-value with appropriate precision."""
    if p < 0.001:
        return '<0.001'
    else:
        return f'{p:.3f}'


def generate_paper_statistics_table(
    output_path: str = 'evaluation/results/paper_table1.csv'
):
    """
    Generate complete statistics table for paper.
    
    Output CSV with columns:
    - Metric
    - LexAI (mean ± CI)
    - SimpleRAG (mean ± CI)
    - NoRAG (mean ± CI)
    - p-value (LexAI vs SimpleRAG)
    - Effect size (Cohen's d)
    - p-value (LexAI vs NoRAG)
    - Effect size (Cohen's d)
    """
    eval_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(eval_dir, 'results')
    
    # Load all results
    try:
        lexai_df = pd.read_csv(os.path.join(results_dir, 'recomputed_metrics.csv'))
        simple_rag_df = pd.read_csv(os.path.join(results_dir, 'simple_rag_metrics.csv'))
        no_rag_df = pd.read_csv(os.path.join(results_dir, 'no_rag_metrics.csv'))
    except FileNotFoundError as e:
        print(f"✗ Error: Missing metrics files.")
        print(f"  {e}")
        print("\nRun these first:")
        print("  1. python evaluation/run_evaluation.py")
        print("  2. python evaluation/run_baselines.py")
        print("  3. python evaluation/recompute_metrics.py")
        return

    # Build a query-aligned merged DataFrame for paired tests.
    # Inner join on query_id guarantees row i in each system corresponds to the
    # same query — avoids the silent truncation bug of using [:n] head-slices.
    _metric_cols = ['car_score', 'hallucination_rate', 'acs_score', 'olr_score']
    merged_df = (
        lexai_df[['query_id'] + _metric_cols]
        .merge(
            simple_rag_df[['query_id', 'car_score', 'hallucination_rate', 'acs_score', 'olr_score']],
            on='query_id', suffixes=('_lexai', '_simple')
        )
        .merge(
            no_rag_df[['query_id', 'car_score', 'hallucination_rate', 'acs_score', 'olr_score']],
            on='query_id'
        )
    )
    # Rename the no_rag columns (third merge has no suffix)
    merged_df = merged_df.rename(columns={
        'car_score': 'car_score_norag',
        'hallucination_rate': 'hallucination_rate_norag',
        'acs_score': 'acs_score_norag',
        'olr_score': 'olr_score_norag',
    })
    
    metrics = [
        ('car_score', 'Citation Accuracy Rate (CAR)', True),
        ('hallucination_rate', 'Hallucination Rate (HR)', False),
        ('acs_score', 'Answer Completeness Score (ACS)', True),
        ('olr_score', 'Outdated Law Rate (OLR)', False)
    ]
    
    results = []
    
    print("\n" + "="*100)
    print("STATISTICAL ANALYSIS FOR PAPER TABLE 1")
    print("="*100 + "\n")
    
    for metric_col, metric_name, higher_is_better in metrics:
        print(f"Analyzing: {metric_name}")
        print("-" * 100)
        
        # Per-system means and CIs (use all available rows per system)
        lexai_vals = lexai_df[metric_col].dropna().values
        simple_vals = simple_rag_df[metric_col].dropna().values
        no_rag_vals = no_rag_df[metric_col].dropna().values

        # Compute means and CIs
        lexai_mean = np.mean(lexai_vals)
        lexai_lower, lexai_upper = bootstrap_ci(lexai_vals)

        simple_mean = np.mean(simple_vals)
        simple_lower, simple_upper = bootstrap_ci(simple_vals)

        no_rag_mean = np.mean(no_rag_vals)
        no_rag_lower, no_rag_upper = bootstrap_ci(no_rag_vals)

        # Paired t-tests — use query_id-aligned rows so observation i is the
        # same query across all three systems (no head-slice truncation).
        paired = merged_df[[
            f'{metric_col}_lexai',
            f'{metric_col}_simple',
            f'{metric_col}_norag',
        ]].dropna()
        pa_lexai  = paired[f'{metric_col}_lexai'].values
        pa_simple = paired[f'{metric_col}_simple'].values
        pa_norag  = paired[f'{metric_col}_norag'].values

        _, p_vs_simple = stats.ttest_rel(pa_lexai, pa_simple)
        d_vs_simple = cohens_d(pa_lexai, pa_simple)

        _, p_vs_no_rag = stats.ttest_rel(pa_lexai, pa_norag)
        d_vs_no_rag = cohens_d(pa_lexai, pa_norag)

        print(f"  Paired on {len(paired)} query-aligned rows (of {len(merged_df)} total joined)")
        
        results.append({
            'Metric': metric_name,
            'Direction': '↑' if higher_is_better else '↓',
            'LexAI_mean': lexai_mean,
            'LexAI_CI_lower': lexai_lower,
            'LexAI_CI_upper': lexai_upper,
            'SimpleRAG_mean': simple_mean,
            'SimpleRAG_CI_lower': simple_lower,
            'SimpleRAG_CI_upper': simple_upper,
            'NoRAG_mean': no_rag_mean,
            'NoRAG_CI_lower': no_rag_lower,
            'NoRAG_CI_upper': no_rag_upper,
            'p_vs_SimpleRAG': p_vs_simple,
            'cohens_d_vs_SimpleRAG': d_vs_simple,
            'effect_vs_SimpleRAG': interpret_effect_size(d_vs_simple),
            'p_vs_NoRAG': p_vs_no_rag,
            'cohens_d_vs_NoRAG': d_vs_no_rag,
            'effect_vs_NoRAG': interpret_effect_size(d_vs_no_rag)
        })
        
        # Print readable summary
        print(f"  LexAI:     {lexai_mean:.4f} [95% CI: {lexai_lower:.4f}–{lexai_upper:.4f}]")
        print(f"  SimpleRAG: {simple_mean:.4f} [95% CI: {simple_lower:.4f}–{simple_upper:.4f}]")
        print(f"  NoRAG:     {no_rag_mean:.4f} [95% CI: {no_rag_lower:.4f}–{no_rag_upper:.4f}]")
        print()
        
        sig_simple = '***' if p_vs_simple < 0.001 else '**' if p_vs_simple < 0.01 else '*' if p_vs_simple < 0.05 else 'ns'
        sig_no_rag = '***' if p_vs_no_rag < 0.001 else '**' if p_vs_no_rag < 0.01 else '*' if p_vs_no_rag < 0.05 else 'ns'
        
        print(f"  LexAI vs SimpleRAG: p={format_p_value(p_vs_simple)} ({sig_simple}), Cohen's d={d_vs_simple:.3f} ({interpret_effect_size(d_vs_simple)})")
        print(f"  LexAI vs NoRAG:     p={format_p_value(p_vs_no_rag)} ({sig_no_rag}), Cohen's d={d_vs_no_rag:.3f} ({interpret_effect_size(d_vs_no_rag)})")
        print()
    
    # Save to CSV
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_path, index=False)
    
    print("="*100)
    print(f"✓ Statistics table saved: {output_path}")
    print("="*100)
    
    # Create LaTeX-ready version
    latex_output = output_path.replace('.csv', '_latex.txt')
    with open(latex_output, 'w') as f:
        f.write("% LaTeX Table 1: Main Results\n")
        f.write("% Copy this into your paper\n\n")
        f.write("\\begin{table*}[t]\n")
        f.write("\\centering\n")
        f.write("\\caption{Main evaluation results comparing LexAI against baselines. "
                "Values show mean with 95\\% bootstrap confidence intervals. "
                "Statistical significance: *$p<0.05$, **$p<0.01$, ***$p<0.001$.}\n")
        f.write("\\label{tab:main_results}\n")
        f.write("\\begin{tabular}{lcccccc}\n")
        f.write("\\toprule\n")
        f.write("Metric & LexAI & SimpleRAG & NoRAG & $p$ (vs SimpleRAG) & $d$ & $p$ (vs NoRAG) & $d$ \\\\\n")
        f.write("\\midrule\n")
        
        for row in results:
            metric = row['Metric'].split('(')[0].strip()
            direction = row['Direction']
            
            lexai_str = f"{row['LexAI_mean']:.3f} [{row['LexAI_CI_lower']:.3f}--{row['LexAI_CI_upper']:.3f}]"
            simple_str = f"{row['SimpleRAG_mean']:.3f} [{row['SimpleRAG_CI_lower']:.3f}--{row['SimpleRAG_CI_upper']:.3f}]"
            no_rag_str = f"{row['NoRAG_mean']:.3f} [{row['NoRAG_CI_lower']:.3f}--{row['NoRAG_CI_upper']:.3f}]"
            
            p_simple_str = format_p_value(row['p_vs_SimpleRAG'])
            if row['p_vs_SimpleRAG'] < 0.001:
                p_simple_str += '***'
            elif row['p_vs_SimpleRAG'] < 0.01:
                p_simple_str += '**'
            elif row['p_vs_SimpleRAG'] < 0.05:
                p_simple_str += '*'
            
            p_no_rag_str = format_p_value(row['p_vs_NoRAG'])
            if row['p_vs_NoRAG'] < 0.001:
                p_no_rag_str += '***'
            elif row['p_vs_NoRAG'] < 0.01:
                p_no_rag_str += '**'
            elif row['p_vs_NoRAG'] < 0.05:
                p_no_rag_str += '*'
            
            d_simple_str = f"{row['cohens_d_vs_SimpleRAG']:.2f}"
            d_no_rag_str = f"{row['cohens_d_vs_NoRAG']:.2f}"
            
            f.write(f"{metric} {direction} & {lexai_str} & {simple_str} & {no_rag_str} & "
                   f"{p_simple_str} & {d_simple_str} & {p_no_rag_str} & {d_no_rag_str} \\\\\n")
        
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table*}\n")
    
    print(f"✓ LaTeX table saved: {latex_output}")
    print("\nCopy the LaTeX code into your paper's results section.\n")


if __name__ == "__main__":
    generate_paper_statistics_table()
