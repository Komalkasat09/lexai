"""Score a rerun's saved answers against the answer key and compare the systems.

Reads the *_responses.jsonl files rerun_eval.py writes, scores each answer
with the metrics engine (rows without a citation target are left out), and
reports for every system: citation accuracy (structured citations, answer
text, and "fully correct" = either cites an acceptable target), citation
validity (sections that do not exist, placeholder cases), abstention,
calibration and, for LexAI, P@K over the chunks it actually retrieved. Then
compares LexAI with each baseline on the same queries with a paired
bootstrap and McNemar's exact test.

This analysis was written and committed before the full run's results were
read, so its choices (metrics, tests, seed) do not depend on them.

Run from backend/:

    python scripts/score_rerun.py --run evaluation/results_rerun_full
"""
import argparse
import json
import sys
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluation.answer_key import row_targets  # noqa: E402
from evaluation.citation_validity import check_answer  # noqa: E402
from evaluation.metrics_engine import MetricsEngine  # noqa: E402
from score_pk_with_draft_key import statute_rel  # noqa: E402
from recompute_pk_from_pipeline import score as pk_score  # noqa: E402

SYSTEMS = ("LexAI", "NoRAG", "SimpleRAG")
BOOTSTRAP_SAMPLES = 10000
SEED = 42


def load_responses(run_dir, system, query_ids):
    """Responses of one system in ground-truth order; raises if any query is missing."""
    path = run_dir / f"{system.lower()}_responses.jsonl"
    by_id = {json.loads(line)["query_id"]: json.loads(line)
             for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    missing = [q for q in query_ids if q not in by_id]
    if missing:
        raise SystemExit(f"{system}: {len(missing)} queries missing, e.g. {missing[:5]}")
    return [by_id[q] for q in query_ids]


def bootstrap_ci(values, rng, samples=BOOTSTRAP_SAMPLES):
    """95% percentile bootstrap interval of the mean, in percent."""
    values = np.asarray(values, dtype=float)
    means = values[rng.integers(0, len(values), size=(samples, len(values)))].mean(axis=1)
    return [round(100 * float(np.percentile(means, 2.5)), 2), round(100 * float(np.percentile(means, 97.5)), 2)]


def mcnemar_exact(a, b):
    """Two-sided exact McNemar p-value for paired 0/1 outcomes."""
    a, b = np.asarray(a, dtype=int), np.asarray(b, dtype=int)
    only_a, only_b = int(((a == 1) & (b == 0)).sum()), int(((a == 0) & (b == 1)).sum())
    n = only_a + only_b
    if n == 0:
        return 1.0, only_a, only_b
    tail = sum(comb(n, k) for k in range(0, min(only_a, only_b) + 1)) / 2 ** n
    return min(1.0, 2 * tail), only_a, only_b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--ground-truth", default="evaluation/ground_truth_lexeval_key_393.xlsx")
    ap.add_argument("--subset", type=Path, default=None,
                    help="JSON file with a 'query_ids' list, e.g. the dev sample")
    args = ap.parse_args()

    gt = pd.read_excel(BACKEND / args.ground_truth).rename(columns={"query_text": "query"})
    if args.subset:
        wanted = set(json.loads(args.subset.read_text(encoding="utf-8"))["query_ids"])
        gt = gt[gt["query_id"].isin(wanted)].reset_index(drop=True)
    engine = MetricsEngine(gt, None)
    query_ids = list(gt["query_id"])
    rng = np.random.default_rng(SEED)

    per_query, summary = [], {}
    for system in SYSTEMS:
        responses = load_responses(args.run, system, query_ids)
        car = engine.compute_citation_accuracy(responses)
        ap_metrics = engine.compute_abstention_metrics(responses)
        ccs = engine.compute_confidence_calibration(responses)
        pk_rows = []
        for i, response in enumerate(responses):
            row = gt.iloc[i].to_dict()
            scored = engine._score_against_key(response, row)
            if scored is None:
                continue
            rec = dict(system=system, query_id=row["query_id"], category=row["category"],
                       target_type=row["target_type"], from_citations=scored[0], from_answer=scored[1],
                       fully_correct=float(max(scored) == 1.0),
                       refused=bool(response.get("trigger_uncertainty")))
            ttype, primary, acceptable, _ = row_targets(row)
            chunks = [c for c in response.get("retrieved_chunks") or [] if isinstance(c, dict)]
            if system == "LexAI" and ttype == "S":
                rel = statute_rel(chunks, acceptable)
                rec.update({f"pk_{k}": v for k, v in pk_score(rel).items()}, n_chunks=len(chunks))
                pk_rows.append(rec)
            per_query.append(rec)
        frame = pd.DataFrame([r for r in per_query if r["system"] == system])
        summary[system] = {
            "n_scored": int(len(frame)),
            "fully_correct_pct": round(100 * frame.fully_correct.mean(), 2),
            "fully_correct_ci95": bootstrap_ci(frame.fully_correct, rng),
            "CAR_retrieved": round(car["CAR_retrieved_overall"], 2),
            "CAR_generated": round(car["CAR_generated_overall"], 2),
            "CAR_overall": round(car["CAR_overall"], 2),
            "refused_pct": round(100 * frame.refused.mean(), 2),
            "fully_correct_by_category": frame.groupby("category").fully_correct.mean().mul(100).round(2).to_dict(),
            "fully_correct_by_target_type": frame.groupby("target_type").fully_correct.mean().mul(100).round(2).to_dict(),
            # The engine calls a response an abstention when its confidence label is
            # low and no citations were extracted; NoRAG labels itself low whenever
            # its citation regex finds nothing, so this is not a refusal rate.
            "abstention_engine_definition": {k: ap_metrics[k] for k in ("abstention_precision", "abstention_recall", "TP", "FP", "FN", "TN")},
            "calibration": ccs,
        }
        checks = [check_answer(r.get("answer") or "") for r in responses]
        claims = sum(c["section_claims"] for c in checks)
        summary[system]["citation_validity"] = {
            "answers": len(checks),
            "section_claims_checked": claims,
            "invented_sections": sum(len(c["invented_sections"]) for c in checks),
            "placeholder_case_citations": sum(len(c["placeholder_cases"]) for c in checks),
            "invented_per_100_section_claims": round(100 * sum(len(c["invented_sections"]) for c in checks) / max(claims, 1), 2),
            "answers_with_any_invented_pct": round(100 * sum(c["invented"] > 0 for c in checks) / len(checks), 2),
            "examples": [f"{query_ids[i]}: {', '.join(c['invented_sections'] + c['placeholder_cases'])}"
                         for i, c in enumerate(checks) if c["invented"]][:20],
        }
        if pk_rows:
            pk = pd.DataFrame(pk_rows)
            summary[system]["retrieval_statute_rows"] = {
                "n": int(len(pk)),
                "P_at_1": round(100 * pk.pk_p1.mean(), 2),
                "P_at_3": round(100 * pk.pk_p3.mean(), 2),
                "Hit_at_3": round(100 * pk.pk_hit3.mean(), 2),
                "Hit_at_5": round(100 * pk.pk_hit5.mean(), 2),
                "no_context": int((pk.n_chunks == 0).sum()),
            }

    frame = pd.DataFrame(per_query)
    wide = frame.pivot(index="query_id", columns="system", values="fully_correct")
    comparisons = {}
    for baseline in ("NoRAG", "SimpleRAG"):
        diff = (wide["LexAI"] - wide[baseline]).to_numpy()
        p, lexai_only, baseline_only = mcnemar_exact(wide["LexAI"], wide[baseline])
        comparisons[f"LexAI_vs_{baseline}"] = {
            "difference_pct": round(100 * diff.mean(), 2),
            "difference_ci95": bootstrap_ci(diff, rng),
            "lexai_right_baseline_wrong": lexai_only,
            "baseline_right_lexai_wrong": baseline_only,
            "mcnemar_p": round(p, 5),
        }

    result = {"run": str(args.run), "systems": summary, "comparisons": comparisons,
              "bootstrap_samples": BOOTSTRAP_SAMPLES, "seed": SEED}
    (args.run / "scores.json").write_text(json.dumps(result, indent=2, default=float), encoding="utf-8")
    frame.to_csv(args.run / "scores_per_query.csv", index=False)
    print(json.dumps({s: {k: v for k, v in summary[s].items() if k in
                          ("n_scored", "fully_correct_pct", "fully_correct_ci95", "CAR_overall",
                           "refused_pct", "retrieval_statute_rows", "citation_validity")} for s in SYSTEMS}, indent=2))
    print(json.dumps(comparisons, indent=2))
    print("\nwrote", args.run / "scores.json", "and scores_per_query.csv")


if __name__ == "__main__":
    main()
