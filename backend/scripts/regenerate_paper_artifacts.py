#!/usr/bin/env python3
"""Regenerate paper-ready evaluation artifacts from existing checkpoints/results.

This script is checkpoint-first: it does not require a fresh full live evaluation run.
It rebuilds system-comparison and paper tables from canonical complete_results JSON.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from evaluation.metrics_engine import MetricsEngine, METRIC_SCHEMA_VERSION

EVAL_DIR = BASE / "evaluation"
RESULTS_DIR = EVAL_DIR / "results"
POSTFIX_DIR = EVAL_DIR / "results_393_postfix"
PHASE5_DIR = EVAL_DIR / "results_phase5_threshold_ablation_fixed"


def _latest_complete_results() -> Path:
    candidates: List[Path] = []
    candidates.extend(Path(p) for p in glob.glob(str(POSTFIX_DIR / "complete_results_*.json")))
    candidates.extend(Path(p) for p in glob.glob(str(RESULTS_DIR / "complete_results_*.json")))
    if not candidates:
        raise FileNotFoundError("No complete_results_*.json found in evaluation/results* directories")

    def score(path: Path) -> tuple:
        try:
            with path.open("r", encoding="utf-8") as f:
                d = json.load(f)
            return (int(d.get("ground_truth_size", 0)), path.stat().st_mtime)
        except Exception:
            return (0, path.stat().st_mtime)

    return sorted(candidates, key=score, reverse=True)[0]


def _to_float_or_none(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _pick_metric(d: Dict, *keys: str):
    for k in keys:
        if k in d and d.get(k) is not None:
            return d.get(k)
    return None


def _build_system_table(complete_results_path: Path) -> pd.DataFrame:
    with complete_results_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    run_schema = data.get("metric_schema_version")
    if run_schema != METRIC_SCHEMA_VERSION:
        raise ValueError(
            "Metric schema mismatch during artifact regeneration: "
            f"run has {run_schema!r}, code expects {METRIC_SCHEMA_VERSION!r}. "
            "Re-run evaluation with current metric schema before regenerating paper artifacts."
        )

    all_metrics: Dict[str, Dict] = data.get("all_metrics", {})

    # Backfill CAR generated/retrieved if missing in serialized metrics.
    gt_path = Path(
        data.get("config", {}).get(
            "ground_truth_path",
            str(EVAL_DIR / "ground_truth_verified_393_ready.xlsx"),
        )
    )
    if not gt_path.exists():
        gt_path = EVAL_DIR / "ground_truth_verified_393_ready.xlsx"

    car_backfill: Dict[str, Dict[str, float]] = {}
    checkpoint_dir = complete_results_path.parent / "checkpoints"
    baseline_path = checkpoint_dir / "baseline_responses.json"
    lexai_path = checkpoint_dir / "lexai_responses.json"
    if gt_path.exists() and lexai_path.exists() and baseline_path.exists():
        gt_df = pd.read_excel(gt_path, sheet_name="Ground Truth Dataset")
        engine = MetricsEngine(gt_df, chroma_client=None)

        with lexai_path.open("r", encoding="utf-8") as f:
            lexai_responses = json.load(f)
        with baseline_path.open("r", encoding="utf-8") as f:
            baseline_responses = json.load(f)

        sources = {"LexAI": lexai_responses}
        if isinstance(baseline_responses, dict):
            sources.update(baseline_responses)

        for sys_name, responses in sources.items():
            if not isinstance(responses, list):
                continue
            car = engine.compute_citation_accuracy(responses)
            car_backfill[sys_name] = {
                "CAR_generated": _to_float_or_none(car.get("CAR_generated_overall")),
                "CAR_retrieved": _to_float_or_none(car.get("CAR_retrieved_overall")),
            }
    systems = ["LexAI", "SimpleRAG", "NoRAG"]

    rows = []
    for system in systems:
        m = all_metrics.get(system, {})
        car = m.get("CAR", {})
        hr = m.get("HR", {})
        olr = m.get("OLR", {})
        acs = m.get("ACS", {})
        ccs = m.get("CCS", {})

        rows.append(
            {
                "System": system,
                "CAR_overall": _to_float_or_none(car.get("CAR_overall")),
                "CAR_generated": _to_float_or_none(
                    _pick_metric(car, "CAR_generated", "CAR_generated_overall")
                ),
                "CAR_retrieved": _to_float_or_none(
                    _pick_metric(car, "CAR_retrieved", "CAR_retrieved_overall")
                ),
                "HR_overall": _to_float_or_none(hr.get("HR_overall")),
                "HR_inline": _to_float_or_none(hr.get("HR_inline")),
                "OLR_overall": _to_float_or_none(olr.get("OLR_overall")),
                "OLR_transition_overall": _to_float_or_none(olr.get("OLR_transition_overall")),
                "AP_overall": _to_float_or_none(
                    _pick_metric(m.get("AP", {}), "AP_overall", "abstention_precision", "f1_abstention")
                ),
                "ACS_overall": _to_float_or_none(acs.get("ACS_overall")),
                "CCS_calibration_error": _to_float_or_none(ccs.get("calibration_error")),
            }
        )

        # Use checkpoint-derived CAR split values when serialized keys are absent.
        if rows[-1]["CAR_generated"] is None and system in car_backfill:
            rows[-1]["CAR_generated"] = car_backfill[system].get("CAR_generated")
        if rows[-1]["CAR_retrieved"] is None and system in car_backfill:
            rows[-1]["CAR_retrieved"] = car_backfill[system].get("CAR_retrieved")

        # Keep CAR_overall consistent with split values from the same run.
        car_g = rows[-1].get("CAR_generated")
        car_r = rows[-1].get("CAR_retrieved")
        if car_g is not None and car_r is not None:
            rows[-1]["CAR_overall"] = (float(car_g) + float(car_r)) / 2.0

    return pd.DataFrame(rows)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    complete_results_path = _latest_complete_results()
    print(f"Using complete results: {complete_results_path}")

    system_df = _build_system_table(complete_results_path)

    # Publication table (human-readable rounded values)
    pretty_df = system_df.copy()
    for col in ["CAR_overall", "CAR_generated", "CAR_retrieved", "HR_overall", "HR_inline", "OLR_overall", "OLR_transition_overall", "AP_overall"]:
        if col in pretty_df.columns:
            pretty_df[col] = pretty_df[col].apply(lambda x: round(x, 4) if pd.notna(x) else "N/A")
    for col in ["ACS_overall", "CCS_calibration_error"]:
        if col in pretty_df.columns:
            pretty_df[col] = pretty_df[col].apply(lambda x: round(x, 4) if pd.notna(x) else "N/A")

    out_system = RESULTS_DIR / "paper_table_03_system_comparison.csv"
    pretty_df.to_csv(out_system, index=False)
    print(f"Wrote {out_system}")

    # Keep canonical numeric export for downstream stats/plots if needed.
    out_system_numeric = RESULTS_DIR / "paper_table_03_system_comparison.numeric.csv"
    system_df.to_csv(out_system_numeric, index=False)
    print(f"Wrote {out_system_numeric}")

    # Threshold ablation copy to stable paper filename.
    threshold_src = PHASE5_DIR / "threshold_ablation_summary.csv"
    if threshold_src.exists():
        threshold_df = pd.read_csv(threshold_src)
        keep = [
            c
            for c in [
                "high_threshold",
                "medium_threshold",
                "accuracy",
                "hallucination_rate",
                "abstention_rate",
                "answered_count",
                "total_count",
                "objective_score",
            ]
            if c in threshold_df.columns
        ]
        threshold_out = RESULTS_DIR / "paper_table_01_threshold_ablation.csv"
        threshold_df[keep].to_csv(threshold_out, index=False)
        print(f"Wrote {threshold_out}")

    # Standardize BNS paper table copies if sources exist.
    bns_attrition_src = RESULTS_DIR / "bns_ablation_attrition.csv"
    bns_metrics_src = RESULTS_DIR / "bns_ablation_table.csv"
    if bns_attrition_src.exists():
        out_attr = RESULTS_DIR / "paper_table_02_bns_ablation_attrition.csv"
        pd.read_csv(bns_attrition_src).to_csv(out_attr, index=False)
        print(f"Wrote {out_attr}")
    if bns_metrics_src.exists():
        out_metrics = RESULTS_DIR / "paper_table_02b_bns_ablation_metrics.csv"
        pd.read_csv(bns_metrics_src).to_csv(out_metrics, index=False)
        print(f"Wrote {out_metrics}")

    # Quick provenance check for figure reproducibility status.
    figure_sidecars = [
        RESULTS_DIR / "figures" / "main_comparison.png.provenance.json",
        RESULTS_DIR / "figures" / "category_breakdown.png.provenance.json",
        RESULTS_DIR / "figures" / "calibration.png.provenance.json",
    ]
    missing = [str(p) for p in figure_sidecars if not p.exists()]
    if missing:
        print("Missing figure provenance sidecars:")
        for p in missing:
            print(f"  - {p}")
    else:
        print("All figure provenance sidecars present.")


if __name__ == "__main__":
    main()
