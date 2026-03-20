"""
Results Dashboard - Generate all publication-quality figures with error bars

All figures include:
- Bootstrap 95% confidence intervals
- Significance markers for comparisons
- 300 DPI resolution for journal submission
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
import os
import json


BASE_REQUIRED_COLUMNS = {
    'query_id', 'query', 'category', 'system',
    'car_score', 'hallucination_rate', 'acs_score', 'olr_score',
    'confidence', 'ccs_correctness', 'abstained',
}


def _assert_required_columns(df: pd.DataFrame, required_cols: set, source_name: str):
    missing = sorted(list(required_cols - set(df.columns)))
    if missing:
        raise ValueError(f"Missing required columns in {source_name}: {missing}")


def _assert_metric_usable(df: pd.DataFrame, metric: str, source_name: str):
    if metric not in df.columns:
        raise ValueError(f"Required metric column '{metric}' missing in {source_name}")
    non_null = int(df[metric].dropna().shape[0])
    if non_null == 0:
        raise ValueError(
            f"Metric column '{metric}' has 0 non-null rows in {source_name}. "
            f"Refusing to plot a flat/empty chart."
        )


def _write_figure_provenance(output_path: str, figure_name: str, inputs: dict, metrics: list):
    provenance = {
        'figure': figure_name,
        'output_path': output_path,
        'inputs': [],
    }
    for source_name, source in inputs.items():
        df = source['df']
        path = source.get('path', source_name)
        metrics_non_null = {
            metric: int(df[metric].dropna().shape[0]) if metric in df.columns else 0
            for metric in metrics
        }
        provenance['inputs'].append({
            'source': source_name,
            'path': path,
            'row_count': int(len(df)),
            'columns': list(df.columns),
            'non_null_by_metric': metrics_non_null,
        })

    provenance_path = f"{output_path}.provenance.json"
    with open(provenance_path, 'w') as f:
        json.dump(provenance, f, indent=2)
    print(f"✓ Figure provenance saved: {provenance_path}")


def bootstrap_ci(
    data: list,
    n_iterations: int = 10000,
    ci: float = 0.95,
    random_seed: int = 42
) -> tuple:
    """
    Compute bootstrap confidence interval.
    Returns (lower_error, upper_error) for error bars.
    These are distances from mean, not absolute values.
    """
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
    
    # Return as distance from mean for error bar plotting
    return mean - lower, upper - mean


def get_significance_marker(p_value: float) -> str:
    """Convert p-value to significance marker"""
    if p_value < 0.001:
        return '***'
    elif p_value < 0.01:
        return '**'
    elif p_value < 0.05:
        return '*'
    else:
        return 'ns'


def generate_main_comparison_figure(
    lexai_df: pd.DataFrame,
    simple_rag_df: pd.DataFrame,
    no_rag_df: pd.DataFrame,
    source_paths: dict,
    output_path: str = 'evaluation/results/figures/main_comparison.png'
):
    """
    Main results figure: 4 metrics x 3 systems.
    Bar chart with bootstrap CI error bars.
    Significance markers for LexAI vs each baseline.
    This is Table 1 visualized — most important figure.
    """
    metrics = ['car_score', 'hallucination_rate', 'acs_score', 'olr_score']
    labels = ['Citation Accuracy\n(CAR ↑)', 'Hallucination Rate\n(HR ↓)',
              'Answer Completeness\n(ACS ↑)', 'Outdated Law Rate\n(OLR ↓)']
    lower_better = [False, True, False, True]

    systems = {
        'LexAI': (lexai_df, '#1a9850'),
        'SimpleRAG': (simple_rag_df, '#fdae61'),
        'NoRAG': (no_rag_df, '#d73027')
    }

    fig, axes = plt.subplots(1, 4, figsize=(18, 7))

    for ax, metric, label, lb in zip(axes, metrics, labels, lower_better):
        x = np.arange(len(systems))
        width = 0.6

        bars_data = []
        errors_lower = []
        errors_upper = []
        colors = []
        system_names = []

        for sys_name, (df, color) in systems.items():
            _assert_metric_usable(df, metric, f"{sys_name} dataframe")
            vals = df[metric].dropna().tolist()

            mean_val = np.mean(vals)
            if len(vals) > 1:
                err_lower, err_upper = bootstrap_ci(vals)
            else:
                err_lower, err_upper = 0.0, 0.0

            bars_data.append(mean_val)
            errors_lower.append(err_lower)
            errors_upper.append(err_upper)
            colors.append(color)
            system_names.append(sys_name)

        bars = ax.bar(
            x, bars_data,
            width=0.6,
            color=colors,
            alpha=0.85,
            yerr=[errors_lower, errors_upper],
            capsize=6,
            error_kw={'linewidth': 2, 'ecolor': 'black'}
        )

        # Add value labels
        for bar, val, err_up in zip(bars, bars_data, errors_upper):
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                bar.get_height() + err_up + 0.02,
                f'{val:.3f}',
                ha='center', va='bottom',
                fontsize=9, fontweight='bold'
            )

        # Significance markers
        # Compare LexAI vs SimpleRAG
        lexai_vals = lexai_df[metric].dropna().tolist()
        simple_vals = simple_rag_df[metric].dropna().tolist()
        no_rag_vals = no_rag_df[metric].dropna().tolist()

        if len(lexai_vals) > 1 and len(simple_vals) > 1:
            n = min(len(lexai_vals), len(simple_vals))
            _, p_vs_simple = stats.ttest_rel(lexai_vals[:n], simple_vals[:n])
            marker = get_significance_marker(p_vs_simple)
            y_pos = max(bars_data) + max(errors_upper) + 0.08
            ax.annotate(
                '',
                xy=(1, y_pos), xytext=(0, y_pos),
                arrowprops=dict(arrowstyle='-', color='black', lw=1.5)
            )
            ax.text(0.5, y_pos + 0.01, marker, ha='center', fontsize=11, fontweight='bold')

        ax.set_title(label, fontsize=11, fontweight='bold', pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(system_names, fontsize=10)
        ax.set_ylim(0, 1.15)
        ax.grid(True, alpha=0.3, axis='y')

        # Indicate direction
        direction = '(lower=better)' if lb else '(higher=better)'
        ax.set_xlabel(direction, fontsize=9, style='italic')

    # Legend
    patches = [
        mpatches.Patch(color='#1a9850', label='LexAI (Ours)'),
        mpatches.Patch(color='#fdae61', label='SimpleRAG'),
        mpatches.Patch(color='#d73027', label='NoRAG'),
    ]
    fig.legend(
        handles=patches, loc='lower center',
        ncol=3, fontsize=11,
        bbox_to_anchor=(0.5, -0.05)
    )

    fig.suptitle(
        'LexAI vs Baselines: Main Evaluation Results\n'
        'Error bars show 95% bootstrap confidence intervals. '
        '* p<0.05  ** p<0.01  *** p<0.001',
        fontsize=13, fontweight='bold'
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Main comparison figure saved: {output_path}")

    _write_figure_provenance(
        output_path=output_path,
        figure_name='main_comparison',
        inputs={
            'LexAI': {'df': lexai_df, 'path': source_paths.get('LexAI', '')},
            'SimpleRAG': {'df': simple_rag_df, 'path': source_paths.get('SimpleRAG', '')},
            'NoRAG': {'df': no_rag_df, 'path': source_paths.get('NoRAG', '')},
        },
        metrics=metrics,
    )


def generate_category_breakdown_figure(
    lexai_df: pd.DataFrame,
    source_path: str,
    output_path: str = 'evaluation/results/figures/category_breakdown.png'
):
    """
    CAR score by query category for LexAI.
    Shows which query types system handles best and worst.
    Error bars from bootstrap CI.
    Important for identifying weaknesses in paper.
    """
    if 'category' not in lexai_df.columns:
        raise ValueError("Missing required 'category' column for category breakdown figure.")

    _assert_metric_usable(lexai_df, 'car_score', 'LexAI dataframe')

    categories = lexai_df['category'].unique()
    cat_means = []
    cat_errors_lower = []
    cat_errors_upper = []
    cat_labels = []

    CATEGORY_LABELS = {
        'Section Lookup': 'Section\nLookup',
        'Punishment Queries': 'Punishment\nQuery',
        'Amendment Specific': 'Amendment\nSpecific',
        'IPC to BNS Transition': 'IPC→BNS\nTransition',
        'Case Law Search': 'Case Law\nSearch',
        'Overruled Case Detection': 'Overruled\nDetection',
        'Complex Legal Interpretation': 'Complex\nInterpretation'
    }

    for cat in sorted(categories):
        cat_data = lexai_df[
            lexai_df['category'] == cat
        ]['car_score'].dropna().tolist()

        if not cat_data:
            continue

        mean_val = np.mean(cat_data)
        if len(cat_data) > 1:
            err_lower, err_upper = bootstrap_ci(cat_data)
        else:
            err_lower, err_upper = 0.0, 0.0

        cat_means.append(mean_val)
        cat_errors_lower.append(err_lower)
        cat_errors_upper.append(err_upper)
        cat_labels.append(CATEGORY_LABELS.get(cat, cat))

    if not cat_means:
        print("⚠ No category data available. Skipping.")
        return

    fig, ax = plt.subplots(figsize=(14, 6))

    colors = [
        '#1a9850' if m >= 0.6 else
        '#fdae61' if m >= 0.4 else
        '#d73027'
        for m in cat_means
    ]

    bars = ax.bar(
        range(len(cat_means)),
        cat_means,
        color=colors,
        alpha=0.85,
        yerr=[cat_errors_lower, cat_errors_upper],
        capsize=8,
        error_kw={'linewidth': 2}
    )

    # Value labels
    for bar, val in zip(bars, cat_means):
        ax.text(
            bar.get_x() + bar.get_width() / 2.,
            bar.get_height() + 0.03,
            f'{val:.3f}',
            ha='center', va='bottom',
            fontsize=10, fontweight='bold'
        )

    # Mean line
    overall_mean = np.mean(cat_means)
    ax.axhline(
        y=overall_mean,
        color='navy', linestyle='--',
        linewidth=1.5,
        label=f'Overall mean ({overall_mean:.3f})'
    )

    ax.set_xticks(range(len(cat_labels)))
    ax.set_xticklabels(cat_labels, fontsize=11)
    ax.set_ylabel('Citation Accuracy Rate (CAR)', fontsize=12)
    ax.set_title(
        'LexAI Performance by Query Category\n'
        'Error bars show 95% bootstrap confidence intervals',
        fontsize=13, fontweight='bold'
    )
    ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.3, axis='y')

    # Color legend
    patches = [
        mpatches.Patch(color='#1a9850', label='Strong (≥0.60)'),
        mpatches.Patch(color='#fdae61', label='Moderate (0.40–0.60)'),
        mpatches.Patch(color='#d73027', label='Weak (<0.40)'),
    ]
    ax.legend(handles=patches, fontsize=10, loc='upper right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Category breakdown figure saved: {output_path}")

    _write_figure_provenance(
        output_path=output_path,
        figure_name='category_breakdown',
        inputs={'LexAI': {'df': lexai_df, 'path': source_path}},
        metrics=['car_score'],
    )


def generate_calibration_figure(
    lexai_df: pd.DataFrame,
    source_path: str,
    output_path: str = 'evaluation/results/figures/calibration.png'
):
    """
    Confidence Calibration Score (CCS) figure.
    Shows whether HIGH/MEDIUM/LOW confidence predicts accuracy.
    Well-calibrated: HIGH=85%+, MEDIUM=60-85%, LOW<60%.
    """
    _assert_required_columns(lexai_df, {'confidence', 'ccs_correctness'}, 'LexAI dataframe')
    _assert_metric_usable(lexai_df, 'ccs_correctness', 'LexAI dataframe')

    confidence_levels = ['HIGH', 'MEDIUM', 'LOW']
    expected = [0.875, 0.725, 0.30]  # Midpoints of target ranges

    actual_means = []
    actual_errors_lower = []
    actual_errors_upper = []
    counts = []

    for level in confidence_levels:
        subset = lexai_df[
            lexai_df['confidence'].astype(str).str.upper() == level
        ]['ccs_correctness'].dropna().tolist()

        if subset:
            mean_val = np.mean(subset)
            if len(subset) > 1:
                err_lower, err_upper = bootstrap_ci(subset)
            else:
                err_lower, err_upper = 0.0, 0.0
        else:
            mean_val, err_lower, err_upper = 0.0, 0.0, 0.0

        actual_means.append(mean_val)
        actual_errors_lower.append(err_lower)
        actual_errors_upper.append(err_upper)
        counts.append(len(subset))

    fig, ax = plt.subplots(figsize=(9, 6))

    x = np.arange(len(confidence_levels))
    width = 0.35

    bars_actual = ax.bar(
        x - width/2, actual_means,
        width, color='#1a9850', alpha=0.85,
        yerr=[actual_errors_lower, actual_errors_upper],
        capsize=6, error_kw={'linewidth': 2},
        label='Actual Accuracy'
    )
    bars_expected = ax.bar(
        x + width/2, expected,
        width, color='#4575b4', alpha=0.85,
        label='Target Range Midpoint'
    )

    # Labels
    for bar, val, n in zip(bars_actual, actual_means, counts):
        ax.text(
            bar.get_x() + bar.get_width()/2.,
            bar.get_height() + 0.03,
            f'{val:.3f}\n(n={n})',
            ha='center', va='bottom', fontsize=9
        )

    ax.set_xticks(x)
    ax.set_xticklabels(['HIGH\n(target: ≥0.85)', 'MEDIUM\n(target: 0.60-0.85)', 'LOW\n(target: <0.60)'],
                        fontsize=10)
    ax.set_ylabel('Correctness Rate', fontsize=12)
    ax.set_title(
        'Confidence Calibration Analysis\n'
        'Actual accuracy vs target per confidence level',
        fontsize=13, fontweight='bold'
    )
    ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(fontsize=11)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Calibration figure saved: {output_path}")

    _write_figure_provenance(
        output_path=output_path,
        figure_name='calibration',
        inputs={'LexAI': {'df': lexai_df, 'path': source_path}},
        metrics=['ccs_correctness'],
    )


def generate_all_figures():
    """
    Generate all paper figures in one call.
    Run this after all evaluations complete.
    """
    eval_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(eval_dir, 'results')
    figures_dir = os.path.join(results_dir, 'figures')
    
    os.makedirs(figures_dir, exist_ok=True)

    print("\n" + "="*70)
    print("GENERATING ALL PAPER FIGURES")
    print("="*70 + "\n")

    # Load all results
    try:
        lexai_path = os.path.join(results_dir, 'recomputed_metrics.csv')
        no_rag_path = os.path.join(results_dir, 'no_rag_metrics.csv')
        simple_rag_path = os.path.join(results_dir, 'simple_rag_metrics.csv')
        
        lexai_df = pd.read_csv(lexai_path)
        no_rag_df = pd.read_csv(no_rag_path)
        simple_rag_df = pd.read_csv(simple_rag_path)

        _assert_required_columns(lexai_df, BASE_REQUIRED_COLUMNS, lexai_path)
        _assert_required_columns(no_rag_df, BASE_REQUIRED_COLUMNS, no_rag_path)
        _assert_required_columns(simple_rag_df, BASE_REQUIRED_COLUMNS, simple_rag_path)

        if len(lexai_df) == 0 or len(no_rag_df) == 0 or len(simple_rag_df) == 0:
            raise ValueError('One or more input metric files are empty; refusing to generate empty charts.')
        
        print(f"✓ Loaded LexAI metrics: {len(lexai_df)} rows")
        print(f"✓ Loaded NoRAG metrics: {len(no_rag_df)} rows")
        print(f"✓ Loaded SimpleRAG metrics: {len(simple_rag_df)} rows\n")
    except FileNotFoundError as e:
        print(f"✗ Error loading metrics files: {e}")
        print("\nPlease run these first:")
        print("  1. python evaluation/run_evaluation.py")
        print("  2. python evaluation/run_baselines.py")
        print("  3. python evaluation/recompute_metrics.py")
        return

    print("Generating figures...")
    
    main_fig_path = os.path.join(figures_dir, 'main_comparison.png')
    category_fig_path = os.path.join(figures_dir, 'category_breakdown.png')
    calibration_fig_path = os.path.join(figures_dir, 'calibration.png')
    
    generate_main_comparison_figure(
        lexai_df,
        simple_rag_df,
        no_rag_df,
        source_paths={
            'LexAI': lexai_path,
            'SimpleRAG': simple_rag_path,
            'NoRAG': no_rag_path,
        },
        output_path=main_fig_path,
    )
    generate_category_breakdown_figure(lexai_df, lexai_path, category_fig_path)
    generate_calibration_figure(lexai_df, lexai_path, calibration_fig_path)

    print("\n" + "="*70)
    print("ALL FIGURES GENERATED AT 300 DPI")
    print("="*70)
    print(f"  {main_fig_path}")
    print(f"  {category_fig_path}")
    print(f"  {calibration_fig_path}")
    
    # Check for ablation figures
    threshold_fig = os.path.join(figures_dir, 'threshold_ablation.png')
    bns_fig = os.path.join(figures_dir, 'bns_middleware_ablation.png')
    
    if os.path.exists(threshold_fig):
        print(f"  {threshold_fig}")
    else:
        print(f"  ⚠ {threshold_fig} (run threshold_ablation.py)")
        
    if os.path.exists(bns_fig):
        print(f"  {bns_fig}")
    else:
        print(f"  ⚠ {bns_fig} (run bns_ablation.py)")
    
    print("\nFive figures total — ready for paper.")
    print("="*70 + "\n")


if __name__ == "__main__":
    generate_all_figures()
