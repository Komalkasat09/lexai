"""Recompute cross-domain CAR/ACS from existing checkpoints only (no inference).

Workflow:
1) Diagnose citation format mismatch examples (5 per domain).
2) Spot-check citation matcher (5 per domain) and gate recompute.
3) Recompute CAR + ACS on all 393 responses if gate passes.
4) If new-domain CAR remains 0, print raw response objects for debugging.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT.parent))

from evaluation.metrics_engine import MetricsEngine


RESULTS_DIR = ROOT / "evaluation" / "results"
CHECKPOINT_DIR = RESULTS_DIR / "checkpoints"

GT_PATH = ROOT / "ground_truth_verified_393.xlsx"
RESP_393 = CHECKPOINT_DIR / "lexai_responses_393.json"
RESP_293 = CHECKPOINT_DIR / "lexai_responses.json"
SUMMARY_PATH = RESULTS_DIR / "table5_cross_domain_summary.json"
TABLE_PATH = RESULTS_DIR / "table5_cross_domain.md"

DOMAINS = ["Civil Law", "Corporate Law", "Family Law"]


def load_gt() -> pd.DataFrame:
    gt = pd.read_excel(GT_PATH, sheet_name="Ground Truth Dataset")
    if "query_text" in gt.columns and "query" not in gt.columns:
        gt["query"] = gt["query_text"]
    if "domain" not in gt.columns:
        gt["domain"] = "Criminal Law"
    return gt


def load_responses() -> List[Dict]:
    if RESP_393.exists():
        return json.loads(RESP_393.read_text(encoding="utf-8"))
    return json.loads(RESP_293.read_text(encoding="utf-8"))


def predicted_citation_field(response: Dict) -> str:
    # Task prompt requested citation/source_section display first.
    c = response.get("citation")
    if isinstance(c, str) and c.strip():
        return c.strip()
    ss = response.get("source_section")
    if isinstance(ss, str) and ss.strip():
        return ss.strip()

    # Fallback for real LexAI payload format.
    sr = response.get("structured_response", {})
    if isinstance(sr, dict):
        act = str(sr.get("act_cited", "")).strip()
        sec = str(sr.get("section_cited", "")).strip()
        if act or sec:
            return f"{act} {sec}".strip()

    citations = response.get("citations", [])
    if isinstance(citations, list) and citations:
        first = citations[0]
        if isinstance(first, dict):
            act = str(first.get("act_or_case", "")).strip()
            sec = str(first.get("section_or_citation", "")).strip()
            return f"{act} {sec}".strip()
        return str(first).strip()

    return ""


def print_task1_examples(gt: pd.DataFrame, by_query: Dict[str, Dict]) -> None:
    print("\n[TASK 1] Citation format diagnostics (first 5 per domain)")
    for domain in DOMAINS:
        print(f"\n=== {domain} ===")
        for _, row in gt[gt["domain"] == domain].head(5).iterrows():
            q = str(row["query"]).strip()
            r = by_query.get(q, {})
            print(f"Query: {q}")
            print(f"Predicted citation: {predicted_citation_field(r)}")
            print(f"Ground truth citation: {row.get('correct_citation', '')}")
            print("---")


def run_spot_check(gt: pd.DataFrame, by_query: Dict[str, Dict], engine: MetricsEngine) -> Dict[str, Tuple[int, int]]:
    print("\n[TASK 3] Spot check citations_match() (5 per domain)")
    result: Dict[str, Tuple[int, int]] = {}
    for domain in DOMAINS:
        match_count = 0
        sample = gt[gt["domain"] == domain].head(5)
        print(f"\n=== {domain} spot check ===")
        for _, row in sample.iterrows():
            q = str(row["query"]).strip()
            gt_c = str(row.get("correct_citation", "")).strip()
            resp = by_query.get(q, {})
            candidates = engine._extract_predicted_citation_candidates(resp)
            matched = any(engine.citations_match(c, gt_c) for c in candidates if c)
            if matched:
                match_count += 1
            best_pred = candidates[0] if candidates else predicted_citation_field(resp)
            print(f"MATCH={matched} | Query: {q}")
            print(f"Predicted: {best_pred}")
            print(f"GT: {gt_c}")
            print("---")
        result[domain] = (match_count, 5)
        print(f"{domain}: {match_count}/5 matched")
    return result


def recompute_all(gt: pd.DataFrame, responses: List[Dict], engine: MetricsEngine) -> Dict:
    car = engine.compute_citation_accuracy(responses)
    acs = engine.compute_completeness_score(responses)

    car_scores = car["individual_scores"]
    acs_scores = acs["individual_scores"]

    rows = []
    for domain in ["Criminal Law", "Civil Law", "Corporate Law", "Family Law"]:
        idx = gt.index[gt["domain"] == domain].tolist()
        if not idx:
            continue
        rows.append(
            {
                "Domain": domain,
                "Queries": len(idx),
                "CAR": round(sum(car_scores[i] for i in idx) / len(idx) * 100, 2),
                "ACS": round(sum(acs_scores[i] for i in idx) / len(idx), 2),
            }
        )

    overall = {
        "Domain": "Overall",
        "Queries": len(gt),
        "CAR": round(sum(car_scores) / len(car_scores) * 100, 2),
        "ACS": round(sum(acs_scores) / len(acs_scores), 2),
    }

    summary = {
        "table_rows": rows,
        "overall": overall,
        "responses_path": str(RESP_393 if RESP_393.exists() else RESP_293),
        "ground_truth": str(GT_PATH),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "| Domain | Queries | CAR | ACS |",
        "|---|---|---|---|",
    ]
    for r in rows:
        md_lines.append(f"| {r['Domain']} | {r['Queries']} | {r['CAR']}% | {r['ACS']} |")
    md_lines.append(
        f"| **Overall** | **{overall['Queries']}** | **{overall['CAR']}%** | **{overall['ACS']}** |"
    )
    TABLE_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("\n[TASK 4] Recomputed domain table from checkpoint")
    print("\n".join(md_lines))
    print(f"\n[save] {SUMMARY_PATH}")
    print(f"[save] {TABLE_PATH}")
    return summary


def debug_missing_citation_field(gt: pd.DataFrame, by_query: Dict[str, Dict], engine: MetricsEngine) -> None:
    print("\n[TASK 5] CAR still 0 in new domains; printing raw response objects for failing queries")
    printed = 0
    for domain in DOMAINS:
        for _, row in gt[gt["domain"] == domain].iterrows():
            q = str(row["query"]).strip()
            gt_c = str(row.get("correct_citation", "")).strip()
            resp = by_query.get(q, {})
            candidates = engine._extract_predicted_citation_candidates(resp)
            matched = any(engine.citations_match(c, gt_c) for c in candidates if c)
            if matched:
                continue
            print(f"\n[Failing Query] {q}")
            print(json.dumps(resp, ensure_ascii=False, indent=2)[:4000])
            printed += 1
            if printed >= 3:
                return


def main() -> int:
    gt = load_gt()
    responses = load_responses()
    by_query = {str(r.get("query", "")).strip(): r for r in responses}

    # Engine only needs ground truth for CAR/ACS recomputation.
    engine = MetricsEngine(gt, chroma_client=None)

    print_task1_examples(gt, by_query)

    spot = run_spot_check(gt, by_query, engine)
    gate_ok = all(spot[d][0] >= 3 for d in DOMAINS)

    print("\nSpot-check gate:")
    for d in DOMAINS:
        print(f"- {d}: {spot[d][0]}/{spot[d][1]}")

    if not gate_ok:
        print("\nSpot check did not pass threshold (>=3/5 per domain).")
        print("Stopping before full recomputation per safeguard.")
        return 1

    summary = recompute_all(gt, responses, engine)

    # Task 5 fallback
    rows = {r["Domain"]: r for r in summary["table_rows"]}
    if all(rows.get(d, {}).get("CAR", 0.0) == 0.0 for d in DOMAINS):
        debug_missing_citation_field(gt, by_query, engine)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
