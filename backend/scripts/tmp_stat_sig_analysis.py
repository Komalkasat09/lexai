import json
from pathlib import Path
import numpy as np
import pandas as pd
import chromadb
from chromadb.config import Settings
from scipy import stats

from evaluation.metrics_engine import MetricsEngine


def bootstrap_ci(scores, n_bootstrap=10000, ci=0.95, seed=42):
    rng = np.random.default_rng(seed)
    arr = np.array(scores, dtype=float)
    means = [
        float(np.mean(rng.choice(arr, len(arr), replace=True)))
        for _ in range(n_bootstrap)
    ]
    lower = float(np.percentile(means, (1 - ci) / 2 * 100))
    upper = float(np.percentile(means, (1 + ci) / 2 * 100))
    return lower, upper


def cohens_d(x, y):
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    diff = x - y
    sd = np.std(diff, ddof=1)
    if sd == 0:
        return 0.0
    return float(np.mean(diff) / sd)


def pick_series(per_query_rows, metric_name):
    # Prefer explicit keys if present.
    preferred = {
        "CAR": ["car_score", "CAR", "car", "citation_accuracy", "score"],
        "HR": ["hr_score", "HR", "hr", "hallucination", "hallucination_score"],
        "OLR": ["olr_score", "OLR", "olr", "outdated_law", "outdated_law_score"],
        "ACS": ["acs_score", "ACS", "acs", "answer_completeness", "completeness_score"],
    }
    cols = set()
    for r in per_query_rows:
        if isinstance(r, dict):
            cols.update(r.keys())
    for k in preferred[metric_name]:
        if k in cols:
            return [float(r.get(k, np.nan)) for r in per_query_rows]
    # As fallback, map to generic field names if available.
    if "score" in cols and metric_name == "CAR":
        return [float(r.get("score", np.nan)) for r in per_query_rows]
    raise KeyError(f"No per-query field found for {metric_name}. Available keys: {sorted(cols)}")


def main():
    base = Path("/Users/komalkasat09/legal-website/backend")

    requested_paths = {
        "lexai": base / "evaluation/evaluation/results/checkpoints/lexai_responses.json",
        "simplerag": base / "evaluation/evaluation/results/checkpoints/simplerag_responses.json",
        "norag": base / "evaluation/evaluation/results/checkpoints/norag_responses.json",
    }

    print("=== Requested checkpoint paths ===")
    for name, p in requested_paths.items():
        print(name, str(p), "EXISTS" if p.exists() else "MISSING")

    # Use canonical existing checkpoints without rerunning inference.
    lex_path = base / "evaluation/results_393_postfix/checkpoints/lexai_responses.json"
    baseline_path = base / "evaluation/results_393_postfix/checkpoints/baseline_responses.json"

    print("\n=== Using existing checkpoint paths ===")
    print("lexai", str(lex_path), "EXISTS" if lex_path.exists() else "MISSING")
    print("baseline", str(baseline_path), "EXISTS" if baseline_path.exists() else "MISSING")

    if not lex_path.exists() or not baseline_path.exists():
        raise FileNotFoundError("Required existing checkpoint files not found.")

    lex_responses = json.loads(lex_path.read_text(encoding="utf-8"))
    baselines = json.loads(baseline_path.read_text(encoding="utf-8"))
    simple_responses = baselines.get("SimpleRAG", [])
    norag_responses = baselines.get("NoRAG", [])

    print("\n=== Step 1: response object field names ===")
    def fields(rows):
        if not rows:
            return []
        all_keys = set()
        for r in rows:
            if isinstance(r, dict):
                all_keys.update(r.keys())
        return sorted(all_keys)

    print("LexAI fields:", fields(lex_responses))
    print("SimpleRAG fields:", fields(simple_responses))
    print("NoRAG fields:", fields(norag_responses))

    # Ground truth and metrics engine (no inference rerun; scoring only).
    gt_path = base / "evaluation/ground_truth_verified_393_ready.xlsx"
    gt = pd.read_excel(gt_path, sheet_name="Ground Truth Dataset").rename(columns={"query_text": "query"})
    client = chromadb.PersistentClient(
        path=str(base / "legal_research_db"),
        settings=Settings(anonymized_telemetry=False, allow_reset=False),
    )
    engine = MetricsEngine(gt, client)

    # Attempt to get per-query metrics from engine output.
    systems = {
        "LexAI": lex_responses,
        "SimpleRAG": simple_responses,
        "NoRAG": norag_responses,
    }

    per_query = {}
    summary_means = {}
    summary_ci = {}
    feasible = True
    reason = None

    for name, responses in systems.items():
        m = engine.compute_all_metrics(responses)
        pq = m.get("per_query_metrics")
        if pq is None:
            feasible = False
            reason = "per_query_metrics not present in computed metrics output"
            break
        per_query[name] = pq

    if not feasible:
        output = {
            "feasible": False,
            "reason": reason,
            "requested_paths": {k: str(v) for k, v in requested_paths.items()},
            "requested_paths_exist": {k: v.exists() for k, v in requested_paths.items()},
            "used_paths": {
                "lexai": str(lex_path),
                "baseline": str(baseline_path),
            },
            "available_fields": {
                "LexAI": fields(lex_responses),
                "SimpleRAG": fields(simple_responses),
                "NoRAG": fields(norag_responses),
            },
            "note": "Per-query CAR/HR/OLR/ACS were not directly available in checkpoint response objects; tests not run.",
        }
        out_path = base / "evaluation/evaluation/results/statistical_significance.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print("\nSaved", out_path)
        print(json.dumps(output, indent=2))
        return

    # Extract per-query vectors
    scores = {"LexAI": {}, "SimpleRAG": {}, "NoRAG": {}}
    for metric in ["CAR", "HR", "OLR", "ACS"]:
        for sys_name in ["LexAI", "SimpleRAG", "NoRAG"]:
            vec = pick_series(per_query[sys_name], metric)
            vec = [float(v) for v in vec if not np.isnan(v)]
            scores[sys_name][metric] = vec

    # Compute means + CI
    for metric in ["CAR", "HR", "OLR", "ACS"]:
        summary_means[metric] = {}
        summary_ci[metric] = {}
        for sys_name in ["LexAI", "SimpleRAG", "NoRAG"]:
            arr = scores[sys_name][metric]
            summary_means[metric][sys_name] = float(np.mean(arr))
            lo, hi = bootstrap_ci(arr)
            summary_ci[metric][sys_name] = {"lower": lo, "upper": hi}

    # Paired tests
    alpha_corrected = 0.05 / (4 * 2)
    paired_tests = {}
    for metric in ["CAR", "HR", "OLR", "ACS"]:
        x = np.array(scores["LexAI"][metric], dtype=float)
        y = np.array(scores["SimpleRAG"][metric], dtype=float)
        z = np.array(scores["NoRAG"][metric], dtype=float)

        n = min(len(x), len(y), len(z))
        x = x[:n]
        y = y[:n]
        z = z[:n]

        t1, p1 = stats.ttest_rel(x, y)
        t2, p2 = stats.ttest_rel(x, z)
        d1 = cohens_d(x, y)
        d2 = cohens_d(x, z)

        paired_tests[metric] = {
            "LexAI_vs_SimpleRAG": {
                "t_stat": float(t1),
                "p_value": float(p1),
                "cohens_d": float(d1),
                "significant_bonferroni": bool(p1 < alpha_corrected),
            },
            "LexAI_vs_NoRAG": {
                "t_stat": float(t2),
                "p_value": float(p2),
                "cohens_d": float(d2),
                "significant_bonferroni": bool(p2 < alpha_corrected),
            },
        }

    output = {
        "feasible": True,
        "requested_paths": {k: str(v) for k, v in requested_paths.items()},
        "requested_paths_exist": {k: v.exists() for k, v in requested_paths.items()},
        "used_paths": {
            "lexai": str(lex_path),
            "baseline": str(baseline_path),
        },
        "available_fields": {
            "LexAI": fields(lex_responses),
            "SimpleRAG": fields(simple_responses),
            "NoRAG": fields(norag_responses),
        },
        "bootstrap": {
            "n_bootstrap": 10000,
            "ci": 0.95,
            "means": summary_means,
            "confidence_intervals": summary_ci,
        },
        "paired_t_tests": paired_tests,
        "bonferroni_alpha": alpha_corrected,
    }

    out_path = base / "evaluation/evaluation/results/statistical_significance.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("\nSaved", out_path)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
