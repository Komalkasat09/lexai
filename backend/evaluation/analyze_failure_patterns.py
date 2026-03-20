"""
Analyze category-wise errors and top failing query patterns.

Usage:
  python evaluation/analyze_failure_patterns.py \
    --ground-truth evaluation/ground_truth_verified_393_ready.xlsx \
    --responses evaluation/results_393_repaired/checkpoints/lexai_responses.json \
    --out-dir evaluation/results_393_repaired
"""

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from evaluation.metrics_engine import MetricsEngine


def normalize_query_pattern(query: str) -> str:
    q = str(query or "").lower().strip()
    q = re.sub(r"\b(18|19|20)\d{2}\b", "<YEAR>", q)
    q = re.sub(r"\b\d+[a-z]?\b", "<NUM>", q)
    q = re.sub(r"\s+", " ", q)
    # Keep patterns compact and readable in reports.
    return q[:140]


def per_query_car_score(engine: MetricsEngine, response: dict, gt_row: pd.Series) -> float:
    correct_act = str(gt_row.get("correct_act", "") or "").strip().upper()
    correct_section = str(gt_row.get("correct_section", "") or "").strip()
    correct_citation = str(gt_row.get("correct_citation", "") or "").strip()
    if not correct_citation and correct_act and correct_section:
        correct_citation = f"{correct_act} Section {correct_section}"

    candidates = engine._extract_predicted_citation_candidates(response)
    citation_match = any(engine.citations_match(pred, correct_citation) for pred in candidates if pred)

    if not correct_act:
        return 1.0

    act_found = engine._check_act_mentioned(correct_act, response.get("citations", []), response.get("answer", ""))
    sec_found = engine._check_section_mentioned(correct_section, response.get("citations", []), response.get("answer", ""))

    if citation_match or (act_found and sec_found):
        return 1.0
    if act_found:
        return 0.5
    return 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--responses", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    gt = pd.read_excel(args.ground_truth, sheet_name="Ground Truth Dataset")
    responses = json.loads(Path(args.responses).read_text(encoding="utf-8"))

    n = min(len(gt), len(responses))
    gt = gt.iloc[:n].reset_index(drop=True)
    responses = responses[:n]

    engine = MetricsEngine(gt, None)

    rows = []
    for i in range(n):
        resp = responses[i]
        gt_row = gt.iloc[i]
        query_text = (
            gt_row.get("query")
            or gt_row.get("english_query")
            or gt_row.get("hindi_query")
            or resp.get("query")
            or ""
        )

        car_score = per_query_car_score(engine, resp, gt_row)
        answer_text = str(resp.get("answer", "") or "")
        acs_proxy = 1.0 if len(answer_text) >= 450 else (0.5 if len(answer_text) >= 180 else 0.0)

        rows.append(
            {
                "idx": i,
                "query": query_text,
                "query_id": gt_row.get("query_id", ""),
                "category": gt_row.get("category", "unknown"),
                "correct_act": gt_row.get("correct_act", ""),
                "correct_section": gt_row.get("correct_section", ""),
                "query_pattern": normalize_query_pattern(query_text),
                "car_score": car_score,
                "acs_proxy": acs_proxy,
            }
        )

    df = pd.DataFrame(rows)
    failing = df[(df["car_score"] < 1.0) | (df["acs_proxy"] < 1.0)].copy()

    category_breakdown = (
        failing.groupby("category")
        .agg(
            total_fails=("idx", "count"),
            mean_car=("car_score", "mean"),
            mean_acs_proxy=("acs_proxy", "mean"),
        )
        .sort_values("total_fails", ascending=False)
        .reset_index()
    )

    top_patterns = (
        failing.groupby(["query_pattern", "category", "correct_act"])
        .agg(
            fail_count=("idx", "count"),
            mean_car=("car_score", "mean"),
            mean_acs_proxy=("acs_proxy", "mean"),
        )
        .sort_values(["fail_count", "mean_car", "mean_acs_proxy"], ascending=[False, True, True])
        .head(20)
        .reset_index()
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    category_csv = out_dir / "category_error_breakdown.csv"
    patterns_csv = out_dir / "top20_failing_query_patterns.csv"
    summary_json = out_dir / "failure_analysis_summary.json"

    category_breakdown.to_csv(category_csv, index=False)
    top_patterns.to_csv(patterns_csv, index=False)

    summary = {
        "total_queries": int(n),
        "failing_queries": int(len(failing)),
        "category_breakdown_file": str(category_csv),
        "top20_patterns_file": str(patterns_csv),
        "top_category": category_breakdown.iloc[0]["category"] if len(category_breakdown) else None,
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("Saved:")
    print(f"  - {category_csv}")
    print(f"  - {patterns_csv}")
    print(f"  - {summary_json}")


if __name__ == "__main__":
    main()
