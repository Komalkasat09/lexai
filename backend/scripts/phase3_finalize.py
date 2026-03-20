import json
import os
import sys
from pathlib import Path

import chromadb
import pandas as pd
from chromadb.config import Settings

BASE = Path('/Users/komalkasat09/legal-website/backend')
GT_PATH = BASE / 'evaluation' / 'ground_truth_verified_393_ready.xlsx'
OUT_DIR = BASE / 'evaluation' / 'results_phase3_final'

sys.path.insert(0, str(BASE))

from evaluation.run_evaluation import EvaluationRunner
from evaluation.metrics_engine import MetricsEngine


def to_native(value):
    if hasattr(value, 'item'):
        return value.item()
    if isinstance(value, dict):
        return {k: to_native(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_native(v) for v in value]
    return value


def is_abstained(resp: dict) -> bool:
    if bool(resp.get('trigger_uncertainty')):
        return True
    answer = str(resp.get('answer', '')).lower()
    markers = [
        'cannot provide a reliable answer',
        'cannot answer',
        'insufficient reliable information',
        'please consult primary sources',
    ]
    return any(m in answer for m in markers)


def pick_summary(metrics: dict) -> dict:
    return {
        'AP': metrics.get('AP', {}),
        'CCS': metrics.get('CCS', {}),
        'HR': {
            k: metrics.get('HR', {}).get(k)
            for k in ['HR_overall', 'HR_inline', 'total_claims', 'hallucinated_claims']
        },
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    n_queries = int(os.getenv('PHASE3_N', '20'))
    model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

    gt = pd.read_excel(GT_PATH, sheet_name='Ground Truth Dataset').rename(columns={'query_text': 'query'})
    subset = gt.head(n_queries).copy()
    queries = subset['query'].tolist()

    print(f'Running Phase 3 finalization with {len(queries)} queries using model={model}')

    runner = EvaluationRunner(
        ground_truth_path=str(GT_PATH),
        output_dir=str(OUT_DIR),
        debug=False,
        eval_regime='forced-answer',
        compare_regimes=False,
    )

    lex_forced = runner.run_lexai(queries, eval_mode=True)
    lex_abstain = runner.run_lexai(queries, eval_mode=False)

    forced_abstentions = sum(1 for r in lex_forced if is_abstained(r))
    abstain_abstentions = sum(1 for r in lex_abstain if is_abstained(r))

    client = chromadb.PersistentClient(
        path=str(BASE / 'legal_research_db'),
        settings=Settings(anonymized_telemetry=False, allow_reset=False),
    )
    engine = MetricsEngine(subset, client)

    metrics_forced = engine.compute_all_metrics(lex_forced)
    metrics_abstain = engine.compute_all_metrics(lex_abstain)

    summary = {
        'n': len(queries),
        'model': model,
        'forced_abstentions': forced_abstentions,
        'abstain_abstentions': abstain_abstentions,
        'FORCED': pick_summary(metrics_forced),
        'ABSTAIN': pick_summary(metrics_abstain),
        'DELTA': {
            'abstentions': abstain_abstentions - forced_abstentions,
            'AP_abstention_rate': metrics_abstain.get('AP', {}).get('abstention_rate', 0.0)
            - metrics_forced.get('AP', {}).get('abstention_rate', 0.0),
            'CCS_calibration_error': metrics_abstain.get('CCS', {}).get('calibration_error', 0.0)
            - metrics_forced.get('CCS', {}).get('calibration_error', 0.0),
            'HR_overall': metrics_abstain.get('HR', {}).get('HR_overall', 0.0)
            - metrics_forced.get('HR', {}).get('HR_overall', 0.0),
            'hallucinated_claims': metrics_abstain.get('HR', {}).get('hallucinated_claims', 0)
            - metrics_forced.get('HR', {}).get('hallucinated_claims', 0),
        },
    }

    summary = to_native(summary)

    (OUT_DIR / 'lexai_forced_responses.json').write_text(
        json.dumps(to_native(lex_forced), indent=2), encoding='utf-8'
    )
    (OUT_DIR / 'lexai_abstain_responses.json').write_text(
        json.dumps(to_native(lex_abstain), indent=2), encoding='utf-8'
    )
    (OUT_DIR / 'phase3_final_summary.json').write_text(
        json.dumps(summary, indent=2), encoding='utf-8'
    )

    print(json.dumps(summary, indent=2))
    print(f'saved: {OUT_DIR / "phase3_final_summary.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
