"""Prepare canonical per-query dashboard CSVs from complete_results schema."""

import argparse
import glob
import json
import os
import shutil
from typing import Dict

import pandas as pd


REQUIRED_COLUMNS = [
    'query_id', 'query', 'category', 'system',
    'car_score', 'hallucination_rate', 'acs_score', 'olr_score',
    'confidence', 'ccs_correctness', 'abstained',
]

FILENAME_MAP = {
    'LexAI': 'recomputed_metrics.csv',
    'SimpleRAG': 'simple_rag_metrics.csv',
    'NoRAG': 'no_rag_metrics.csv',
}


def _require_columns(df: pd.DataFrame, path: str):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")


def _resolve_latest_complete_results(results_dir: str) -> str:
    pattern = os.path.join(results_dir, 'complete_results_*.json')
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No complete_results files found in {results_dir}")
    return max(files, key=os.path.getmtime)


def _copy_canonical_artifacts(run_dir: str, out_dir: str) -> Dict[str, str]:
    per_query_dir = os.path.join(run_dir, 'per_query_metrics')
    if not os.path.isdir(per_query_dir):
        raise FileNotFoundError(
            f"Canonical per_query_metrics directory not found at {per_query_dir}. "
            f"Re-run evaluation with updated run_evaluation.py."
        )

    copied = {}
    for system_name, target_name in FILENAME_MAP.items():
        slug = ''.join(ch.lower() if ch.isalnum() else '_' for ch in system_name).strip('_')
        src = os.path.join(per_query_dir, f"{slug}_per_query_metrics.csv")
        if not os.path.exists(src):
            raise FileNotFoundError(f"Missing canonical per-query file for {system_name}: {src}")

        df = pd.read_csv(src)
        _require_columns(df, src)

        dst = os.path.join(out_dir, target_name)
        df.to_csv(dst, index=False)
        copied[system_name] = dst

    return copied


def main():
    parser = argparse.ArgumentParser(description='Prepare dashboard CSVs from complete_results schema')
    parser.add_argument('--results-file', default='', help='Path to complete_results_*.json (optional)')
    parser.add_argument('--results-dir', default='evaluation/results', help='Directory containing complete_results files')
    parser.add_argument('--output-dir', default='evaluation/results', help='Directory for dashboard CSV outputs')
    args = parser.parse_args()

    eval_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = args.results_dir
    if not os.path.isabs(results_dir):
        results_dir = os.path.join(eval_dir, os.path.relpath(results_dir, 'evaluation'))

    out_dir = args.output_dir
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(eval_dir, os.path.relpath(out_dir, 'evaluation'))
    os.makedirs(out_dir, exist_ok=True)

    results_file = args.results_file or _resolve_latest_complete_results(results_dir)
    if not os.path.isabs(results_file):
        results_file = os.path.join(eval_dir, os.path.relpath(results_file, 'evaluation'))

    print(f"Loading complete results: {results_file}")
    with open(results_file) as f:
        data = json.load(f)

    run_dir = os.path.dirname(results_file)
    copied = _copy_canonical_artifacts(run_dir, out_dir)

    provenance = {
        'source_complete_results': results_file,
        'run_timestamp': data.get('run_timestamp', 'unknown'),
        'ground_truth_size': int(data.get('ground_truth_size', 0) or 0),
        'outputs': {},
    }

    for system_name, out_path in copied.items():
        df = pd.read_csv(out_path)
        _require_columns(df, out_path)
        provenance['outputs'][system_name] = {
            'path': out_path,
            'row_count': int(len(df)),
            'columns': list(df.columns),
        }
        print(f"  ✓ {system_name}: {len(df)} rows -> {out_path}")

    provenance_path = os.path.join(out_dir, 'dashboard_data_provenance.json')
    with open(provenance_path, 'w') as f:
        json.dump(provenance, f, indent=2)

    print(f"\n✓ Provenance: {provenance_path}")
    print("\nNow run:")
    print("  python evaluation/results_dashboard.py")
    print("  python evaluation/statistical_analysis.py")


if __name__ == '__main__':
    main()
