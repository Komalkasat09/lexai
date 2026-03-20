"""Recompute Table V ACS from checkpoint only, preserving existing CAR values.

Workflow:
1) Compute ACS scores using MetricsEngine.compute_completeness_score.
2) Spot-check first 5 queries per new domain (Civil/Corporate/Family).
3) If spot-check means are still identical, print raw scorer outputs and stop.
4) Otherwise update table5 summary/markdown with new ACS and unchanged CAR.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT.parent))

from evaluation.metrics_engine import MetricsEngine


GT_PATH = ROOT / "ground_truth_verified_393.xlsx"
RESP_PATH = ROOT / "evaluation" / "results" / "checkpoints" / "lexai_responses_393.json"
SUMMARY_PATH = ROOT / "evaluation" / "results" / "table5_cross_domain_summary.json"
TABLE_PATH = ROOT / "evaluation" / "results" / "table5_cross_domain.md"

DOMAINS = ["Criminal Law", "Civil Law", "Corporate Law", "Family Law"]
NEW_DOMAINS = ["Civil Law", "Corporate Law", "Family Law"]


def main() -> int:
    gt = pd.read_excel(GT_PATH, sheet_name="Ground Truth Dataset")
    if "query_text" in gt.columns and "query" not in gt.columns:
        gt = gt.rename(columns={"query_text": "query"})

    responses = json.loads(RESP_PATH.read_text(encoding="utf-8"))
    engine = MetricsEngine(gt, chroma_client=None)

    acs = engine.compute_completeness_score(responses)
    acs_scores = acs["individual_scores"]

    print("[Task 3] Spot-check ACS on 5 queries per new domain")
    domain_means = {}
    for domain in NEW_DOMAINS:
        idx = gt.index[gt["domain"] == domain].tolist()[:5]
        vals = [acs_scores[i] for i in idx]
        mean_val = round(sum(vals) / len(vals), 2) if vals else 0.0
        domain_means[domain] = mean_val
        print(f"{domain}: scores={vals} mean={mean_val}")

    # Safeguard: stop if all three means are identical.
    rounded = {d: round(v, 4) for d, v in domain_means.items()}
    if len(set(rounded.values())) == 1:
        print("\n[STOP] New-domain spot-check means are still identical.")
        print("Raw scorer output (first 10 indices per domain):")
        for domain in NEW_DOMAINS:
            idx = gt.index[gt["domain"] == domain].tolist()[:10]
            vals = [acs_scores[i] for i in idx]
            print(f"{domain}: {vals}")
        return 1

    # Preserve CAR values exactly from existing summary.
    prior = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    prior_car = {row["Domain"]: row["CAR"] for row in prior.get("table_rows", [])}
    prior_overall_car = prior.get("overall", {}).get("CAR", 0.0)

    table_rows = []
    for domain in DOMAINS:
        idx = gt.index[gt["domain"] == domain].tolist()
        if not idx:
            continue
        acs_mean = round(sum(acs_scores[i] for i in idx) / len(idx), 2)
        table_rows.append(
            {
                "Domain": domain,
                "Queries": len(idx),
                "CAR": prior_car.get(domain, 0.0),
                "ACS": acs_mean,
            }
        )

    overall_acs = round(sum(acs_scores) / len(acs_scores), 2) if acs_scores else 0.0
    overall = {
        "Domain": "Overall",
        "Queries": len(gt),
        "CAR": prior_overall_car,
        "ACS": overall_acs,
    }

    summary = {
        "table_rows": table_rows,
        "overall": overall,
        "responses_path": str(RESP_PATH),
        "ground_truth": str(GT_PATH),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["| Domain | Queries | CAR | ACS |", "|---|---|---|---|"]
    for r in table_rows:
        lines.append(f"| {r['Domain']} | {r['Queries']} | {r['CAR']}% | {r['ACS']} |")
    lines.append(f"| **Overall** | **{overall['Queries']}** | **{overall['CAR']}%** | **{overall['ACS']}** |")
    TABLE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n[Task 4] Updated Table V (ACS recomputed, CAR unchanged)")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
