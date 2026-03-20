import json
from pathlib import Path
import sys

import pandas as pd
import chromadb
from chromadb.config import Settings

BASE = Path('/Users/komalkasat09/legal-website/backend')
GT_PATH = BASE / 'evaluation' / 'ground_truth_verified_393_ready.xlsx'
RESP_PATH = BASE / 'evaluation' / 'results_393_postfix' / 'checkpoints' / 'lexai_responses.json'
sys.path.insert(0, str(BASE))

from evaluation.metrics_engine import MetricsEngine


def main():
    gt = pd.read_excel(GT_PATH, sheet_name='Ground Truth Dataset').rename(columns={'query_text': 'query'})
    responses = json.loads(RESP_PATH.read_text(encoding='utf-8'))

    n = min(30, len(gt), len(responses))
    gt_small = gt.head(n).copy()
    resp_small = []
    for i in range(n):
        r = dict(responses[i])
        if 'query_id' not in r:
            r['query_id'] = gt_small.iloc[i].get('query_id')
        resp_small.append(r)

    client = chromadb.PersistentClient(
        path=str(BASE / 'legal_research_db'),
        settings=Settings(anonymized_telemetry=False, allow_reset=False),
    )

    engine = MetricsEngine(gt_small, client)
    metrics = engine.compute_all_metrics(resp_small)

    car = metrics.get('CAR', {})
    hr = metrics.get('HR', {})
    ccs = metrics.get('CCS', {})

    def to_native(val):
        if hasattr(val, 'item'):
            return val.item()
        if isinstance(val, dict):
            return {k: to_native(v) for k, v in val.items()}
        if isinstance(val, list):
            return [to_native(v) for v in val]
        return val

    summary = {
        'sample_size': n,
        'CAR_retrieved_overall': car.get('CAR_retrieved_overall'),
        'CAR_generated_overall': car.get('CAR_generated_overall'),
        'CAR_overall_legacy': car.get('CAR_overall'),
        'HR_overall': hr.get('HR_overall'),
        'HR_citation': hr.get('HR_citation'),
        'HR_case': hr.get('HR_case'),
        'HR_inline': hr.get('HR_inline'),
        'total_claims': hr.get('total_claims'),
        'hallucinated_claims': hr.get('hallucinated_claims'),
        'CCS': ccs,
        'hr_has_direct_counts': isinstance(hr.get('total_claims'), int) and isinstance(hr.get('hallucinated_claims'), int),
    }

    # Mismatch guard test
    mismatch_result = 'not_run'
    try:
        bad = list(resp_small)
        if len(bad) > 1:
            bad[0] = dict(bad[0])
            bad[0]['query_id'] = gt_small.iloc[1].get('query_id')
            engine.compute_citation_accuracy(bad)
            mismatch_result = 'FAILED_NO_ERROR'
        else:
            mismatch_result = 'SKIPPED_SMALL_SAMPLE'
    except ValueError as e:
        mismatch_result = f'OK_RAISED: {str(e)[:120]}'

    summary['query_id_guard_test'] = mismatch_result

    out = BASE / 'evaluation' / 'results_393_postfix' / 'phase12_review_summary.json'
    summary = to_native(summary)

    out.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print(json.dumps(summary, indent=2))
    print(f'saved: {out}')


if __name__ == '__main__':
    main()
