#!/usr/bin/env python3
"""Extract audited failure cases with query IDs for paper appendix."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
GT_PATH = BASE / "evaluation" / "ground_truth_verified_393_ready.xlsx"
LEXAI_PATH = BASE / "evaluation" / "results_393_postfix" / "checkpoints" / "lexai_responses.json"
OUT_PATH = BASE / "evaluation" / "results" / "audited_failure_cases.csv"


def _is_abstained(resp: dict) -> bool:
    if resp.get("trigger_uncertainty") is True:
        return True
    ans = str(resp.get("answer", "")).lower()
    markers = [
        "cannot provide a reliable answer",
        "cannot answer",
        "insufficient reliable information",
        "please consult primary sources",
    ]
    return any(m in ans for m in markers)


def _snippet(text: str, n: int = 170) -> str:
    t = " ".join(str(text).split())
    return t[:n] + ("..." if len(t) > n else "")


def main() -> None:
    gt = pd.read_excel(GT_PATH, sheet_name="Ground Truth Dataset").reset_index(drop=True)
    with LEXAI_PATH.open("r", encoding="utf-8") as f:
        responses = json.load(f)

    rows = []
    limit = min(len(gt), len(responses))

    for i in range(limit):
        g = gt.iloc[i]
        r = responses[i]

        qid = str(g.get("query_id", ""))
        query = str(g.get("query_text", g.get("query", "")))
        category = str(g.get("category", ""))
        answer = str(r.get("answer", ""))
        confidence = str(r.get("confidence", "")).upper()
        citations = r.get("citations", [])

        bns_required = str(g.get("bns_bnss_transition_applies", "")).strip().lower() == "yes"
        lower_answer = answer.lower()

        # Failure class 1: Transition citation drift.
        if bns_required and ("ipc" in lower_answer or "crpc" in lower_answer) and ("bns" not in lower_answer and "bnss" not in lower_answer):
            rows.append(
                {
                    "class": "transition_citation_drift",
                    "query_id": qid,
                    "category": category,
                    "confidence": confidence,
                    "reason": "transition query answered with legacy-law framing but no explicit BNS/BNSS grounding",
                    "query": _snippet(query, 140),
                    "answer_snippet": _snippet(answer),
                }
            )

        # Failure class 2: Over-abstention under conservative policy.
        if _is_abstained(r) and confidence in {"HIGH", "MEDIUM"}:
            rows.append(
                {
                    "class": "over_abstention_high_conf",
                    "query_id": qid,
                    "category": category,
                    "confidence": confidence,
                    "reason": "response abstained despite medium/high confidence label",
                    "query": _snippet(query, 140),
                    "answer_snippet": _snippet(answer),
                }
            )

        # Failure class 3: Retrieval-generation mismatch.
        if isinstance(citations, list) and len(citations) == 0 and len(answer.split()) > 80 and confidence in {"HIGH", "MEDIUM"}:
            rows.append(
                {
                    "class": "retrieval_generation_mismatch",
                    "query_id": qid,
                    "category": category,
                    "confidence": confidence,
                    "reason": "long high-confidence answer emitted with no structured citations",
                    "query": _snippet(query, 140),
                    "answer_snippet": _snippet(answer),
                }
            )

        # Failure class 4: Calibration gap (high confidence, expected act missing).
        correct_act = str(g.get("correct_act", "")).strip().upper()
        if confidence == "HIGH" and correct_act:
            blob = answer.upper()
            if isinstance(citations, list):
                for c in citations:
                    if isinstance(c, dict):
                        blob += " " + str(c.get("act_or_case", "")).upper()
                        blob += " " + str(c.get("section_or_citation", "")).upper()
                    else:
                        blob += " " + str(c).upper()
            if correct_act not in blob:
                rows.append(
                    {
                        "class": "calibration_gap_high_conf_wrong",
                        "query_id": qid,
                        "category": category,
                        "confidence": confidence,
                        "reason": "high-confidence output does not mention the expected ground-truth act",
                        "query": _snippet(query, 140),
                        "answer_snippet": _snippet(answer),
                    }
                )

    # Keep up to 3 unique query IDs per class for concise appendix.
    out = []
    seen_ids = set()
    for cls in [
        "transition_citation_drift",
        "over_abstention_high_conf",
        "retrieval_generation_mismatch",
        "calibration_gap_high_conf_wrong",
    ]:
        n = 0
        for r in rows:
            if r["class"] != cls:
                continue
            if r["query_id"] in seen_ids:
                continue
            out.append(r)
            seen_ids.add(r["query_id"])
            n += 1
            if n == 3:
                break

    out_df = pd.DataFrame(out)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUT_PATH, index=False)

    print(f"saved {OUT_PATH}")
    print(out_df.to_string(index=False))


if __name__ == "__main__":
    main()
