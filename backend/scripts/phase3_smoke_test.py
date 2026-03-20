import json
from pathlib import Path
import sys

import pandas as pd
import chromadb
from chromadb.config import Settings


BASE = Path('/Users/komalkasat09/legal-website/backend')
GT_PATH = BASE / 'evaluation' / 'ground_truth_verified_393_ready.xlsx'
OUT_DIR = BASE / 'evaluation' / 'results_phase3_smoke'
sys.path.insert(0, str(BASE))

from evaluation.run_evaluation import EvaluationRunner
from evaluation.baselines import BaselineRunner
from evaluation.metrics_engine import MetricsEngine


def is_abstained(resp: dict) -> bool:
    answer = str(resp.get('answer', '')).lower()
    if resp.get('trigger_uncertainty') is True:
        return True
    markers = [
        'cannot provide a reliable answer',
        'cannot answer',
        'insufficient reliable information',
        'please consult primary sources',
    ]
    return any(m in answer for m in markers)


def count_abstentions(responses):
    return sum(1 for r in responses if is_abstained(r))


def main():
    gt = pd.read_excel(GT_PATH, sheet_name='Ground Truth Dataset').rename(columns={'query_text': 'query'})
    gt_small = gt.head(8).copy()
    queries = gt_small['query'].tolist()

    runner = EvaluationRunner(
        ground_truth_path=str(GT_PATH),
        output_dir=str(OUT_DIR),
        debug=False,
        eval_regime='forced-answer',
        compare_regimes=False,
    )

    # LexAI: forced vs abstain regimes
    lex_forced = runner.run_lexai(queries, eval_mode=True)
    lex_abstain = runner.run_lexai(queries, eval_mode=False)

    # Baselines: forced vs abstain regimes
    baseline_runner = BaselineRunner()

    norag_forced = [baseline_runner.run_no_rag(q, eval_mode=True) for q in queries]
    norag_abstain = [baseline_runner.run_no_rag(q, eval_mode=False) for q in queries]

    simple_forced = [baseline_runner.run_simple_rag(q, eval_mode=True) for q in queries]
    simple_abstain = [baseline_runner.run_simple_rag(q, eval_mode=False) for q in queries]

    # Hallucination-rate semantics check (uses direct claim counts)
    chroma_client = chromadb.PersistentClient(
        path=str(BASE / 'legal_research_db'),
        settings=Settings(anonymized_telemetry=False, allow_reset=False),
    )
    metrics = MetricsEngine(gt_small, chroma_client).compute_all_metrics(lex_forced)
    hr = metrics.get('HR', {})

    summary = {
        'num_queries': len(queries),
        'abstentions': {
            'LexAI_forced': count_abstentions(lex_forced),
            'LexAI_abstain': count_abstentions(lex_abstain),
            'NoRAG_forced': count_abstentions(norag_forced),
            'NoRAG_abstain': count_abstentions(norag_abstain),
            'SimpleRAG_forced': count_abstentions(simple_forced),
            'SimpleRAG_abstain': count_abstentions(simple_abstain),
        },
        'hallucination_metric_shape': {
            'HR_overall': hr.get('HR_overall'),
            'HR_citation': hr.get('HR_citation'),
            'HR_case': hr.get('HR_case'),
            'HR_inline': hr.get('HR_inline'),
            'total_claims': hr.get('total_claims'),
            'hallucinated_claims': hr.get('hallucinated_claims'),
            'uses_direct_counts': (
                isinstance(hr.get('total_claims'), int)
                and isinstance(hr.get('hallucinated_claims'), int)
            ),
        },
    }

    out_path = OUT_DIR / 'phase3_smoke_summary.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print(json.dumps(summary, indent=2))
    print(f'saved: {out_path}')


if __name__ == '__main__':
    main()
