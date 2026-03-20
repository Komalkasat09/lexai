"""
Extract per-query CAR/HR/OLR/ACS from existing checkpoints and run
bootstrap CI + paired t-tests without rerunning model inference.

Outputs:
- evaluation/evaluation/results/per_query_metric_arrays.json
- evaluation/evaluation/results/statistical_significance.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import chromadb
from chromadb.config import Settings
from scipy import stats

from evaluation.metrics_engine import MetricsEngine


def bootstrap_ci(scores: List[float], n_bootstrap: int = 10000, ci: float = 0.95, seed: int = 42) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    arr = np.array(scores, dtype=float)
    means = [
        float(np.mean(rng.choice(arr, len(arr), replace=True)))
        for _ in range(n_bootstrap)
    ]
    lower = float(np.percentile(means, (1 - ci) / 2 * 100))
    upper = float(np.percentile(means, (1 + ci) / 2 * 100))
    return lower, upper


def cohens_d(x: List[float], y: List[float]) -> float:
    xa = np.array(x, dtype=float)
    ya = np.array(y, dtype=float)
    diff = xa - ya
    sd = np.std(diff, ddof=1)
    if sd == 0:
        return 0.0
    return float(np.mean(diff) / sd)


def _response_fields(rows: List[dict]) -> List[str]:
    keys = set()
    for row in rows:
        if isinstance(row, dict):
            keys.update(row.keys())
    return sorted(keys)


def _extract_per_query_metric_arrays(engine: MetricsEngine, responses: List[dict]) -> Dict[str, List[float]]:
    # CAR: use overall per-query score = mean(retrieved, generated) * 100
    car = engine.compute_citation_accuracy(responses)
    car_ret = [float(v) for v in car.get("individual_scores_retrieved", [])]
    car_gen = [float(v) for v in car.get("individual_scores_generated", [])]
    car_scores = [((r + g) / 2.0) * 100.0 for r, g in zip(car_ret, car_gen)]

    # HR: per-query hallucination_rate from individual_results * 100
    hr = engine.compute_hallucination_rate(responses)
    hr_rows = hr.get("individual_results", [])
    hr_scores = [float(row.get("hallucination_rate", 0.0)) * 100.0 for row in hr_rows]

    # OLR: per-query binary violation at response level (0 or 100)
    olr_scores = [100.0 if engine._response_has_outdated_citation(resp) else 0.0 for resp in responses]

    # ACS: already produced as per-query individual_scores in [0, 100]
    acs = engine.compute_completeness_score(responses)
    acs_scores = [float(v) for v in acs.get("individual_scores", [])]

    # Keep aligned lengths (all should be equal).
    n = min(len(car_scores), len(hr_scores), len(olr_scores), len(acs_scores), len(responses))
    return {
        "CAR": car_scores[:n],
        "HR": hr_scores[:n],
        "OLR": olr_scores[:n],
        "ACS": acs_scores[:n],
    }


def main() -> None:
    base = Path(__file__).resolve().parent.parent

    requested_paths = {
        "lexai": base / "evaluation/evaluation/results/checkpoints/lexai_responses.json",
        "simplerag": base / "evaluation/evaluation/results/checkpoints/simplerag_responses.json",
        "norag": base / "evaluation/evaluation/results/checkpoints/norag_responses.json",
    }

    # Canonical fallback paths (existing checkpoints only).
    lex_path = requested_paths["lexai"]
    if not lex_path.exists():
        lex_path = base / "evaluation/results_393_postfix/checkpoints/lexai_responses.json"

    simple_path = requested_paths["simplerag"]
    norag_path = requested_paths["norag"]

    baseline_path = base / "evaluation/results_393_postfix/checkpoints/baseline_responses.json"

    # Load checkpoint responses without re-running inference.
    if not lex_path.exists():
        raise FileNotFoundError(f"LexAI checkpoint not found: {lex_path}")

    lex_responses = json.loads(lex_path.read_text(encoding="utf-8"))

    if simple_path.exists() and norag_path.exists():
        simple_responses = json.loads(simple_path.read_text(encoding="utf-8"))
        norag_responses = json.loads(norag_path.read_text(encoding="utf-8"))
        used_paths = {
            "lexai": str(lex_path),
            "simplerag": str(simple_path),
            "norag": str(norag_path),
        }
    else:
        if not baseline_path.exists():
            raise FileNotFoundError(
                "SimpleRAG/NoRAG requested files missing and baseline fallback missing."
            )
        base_obj = json.loads(baseline_path.read_text(encoding="utf-8"))
        simple_responses = base_obj.get("SimpleRAG", [])
        norag_responses = base_obj.get("NoRAG", [])
        used_paths = {
            "lexai": str(lex_path),
            "simplerag": str(baseline_path) + "::SimpleRAG",
            "norag": str(baseline_path) + "::NoRAG",
        }

    gt_path = base / "evaluation/ground_truth_verified_393_ready.xlsx"
    gt = pd.read_excel(gt_path, sheet_name="Ground Truth Dataset").rename(columns={"query_text": "query"})

    client = chromadb.PersistentClient(
        path=str(base / "legal_research_db"),
        settings=Settings(anonymized_telemetry=False, allow_reset=False),
    )
    engine = MetricsEngine(gt, client)

    systems = {
        "LexAI": lex_responses,
        "SimpleRAG": simple_responses,
        "NoRAG": norag_responses,
    }

    per_query = {
        system: _extract_per_query_metric_arrays(engine, rows)
        for system, rows in systems.items()
    }

    # Use aligned query count for paired tests.
    n = min(
        len(per_query["LexAI"]["CAR"]),
        len(per_query["SimpleRAG"]["CAR"]),
        len(per_query["NoRAG"]["CAR"]),
    )

    for system in per_query:
        for metric in ["CAR", "HR", "OLR", "ACS"]:
            per_query[system][metric] = per_query[system][metric][:n]

    bootstrap_summary: Dict[str, Dict[str, Dict[str, float]]] = {}
    paired_tests: Dict[str, Dict[str, Dict[str, float]]] = {}
    alpha_corrected = 0.05 / (4 * 2)

    for metric in ["CAR", "HR", "OLR", "ACS"]:
        bootstrap_summary[metric] = {}
        for system in ["LexAI", "SimpleRAG", "NoRAG"]:
            arr = per_query[system][metric]
            lo, hi = bootstrap_ci(arr)
            bootstrap_summary[metric][system] = {
                "mean": float(np.mean(arr)),
                "ci_lower": lo,
                "ci_upper": hi,
                "n": len(arr),
            }

        lx = per_query["LexAI"][metric]
        sp = per_query["SimpleRAG"][metric]
        nr = per_query["NoRAG"][metric]

        t1, p1 = stats.ttest_rel(lx, sp)
        t2, p2 = stats.ttest_rel(lx, nr)

        paired_tests[metric] = {
            "LexAI_vs_SimpleRAG": {
                "t_stat": float(t1),
                "p_value": float(p1),
                "cohens_d": float(cohens_d(lx, sp)),
                "significant": bool(p1 < alpha_corrected),
            },
            "LexAI_vs_NoRAG": {
                "t_stat": float(t2),
                "p_value": float(p2),
                "cohens_d": float(cohens_d(lx, nr)),
                "significant": bool(p2 < alpha_corrected),
            },
        }

    arrays_out = {
        "requested_paths": {k: str(v) for k, v in requested_paths.items()},
        "requested_paths_exist": {k: v.exists() for k, v in requested_paths.items()},
        "used_paths": used_paths,
        "available_fields": {
            "LexAI": _response_fields(lex_responses),
            "SimpleRAG": _response_fields(simple_responses),
            "NoRAG": _response_fields(norag_responses),
        },
        "n_aligned": n,
        "per_query_scores": per_query,
    }

    stats_out = {
        "feasible": True,
        "requested_paths": {k: str(v) for k, v in requested_paths.items()},
        "requested_paths_exist": {k: v.exists() for k, v in requested_paths.items()},
        "used_paths": used_paths,
        "available_fields": arrays_out["available_fields"],
        "n_aligned": n,
        "bootstrap": {
            "n_bootstrap": 10000,
            "ci": 0.95,
            "summary": bootstrap_summary,
        },
        "paired_t_tests": paired_tests,
        "bonferroni_alpha": alpha_corrected,
    }

    out_arrays = base / "evaluation/evaluation/results/per_query_metric_arrays.json"
    out_stats = base / "evaluation/evaluation/results/statistical_significance.json"
    out_arrays.parent.mkdir(parents=True, exist_ok=True)

    out_arrays.write_text(json.dumps(arrays_out, indent=2), encoding="utf-8")
    out_stats.write_text(json.dumps(stats_out, indent=2), encoding="utf-8")

    print("Saved:")
    print(out_arrays)
    print(out_stats)

    print("\nField names by checkpoint:")
    for system, fields in arrays_out["available_fields"].items():
        print(f"{system}: {fields}")

    print("\nPaired t-tests (Bonferroni alpha = 0.00625):")
    for metric in ["CAR", "HR", "OLR", "ACS"]:
        s = paired_tests[metric]["LexAI_vs_SimpleRAG"]
        n = paired_tests[metric]["LexAI_vs_NoRAG"]
        print(
            f"{metric}: LexAI vs SimpleRAG p={s['p_value']:.6g} d={s['cohens_d']:.3f} | "
            f"LexAI vs NoRAG p={n['p_value']:.6g} d={n['cohens_d']:.3f}"
        )


if __name__ == "__main__":
    main()
