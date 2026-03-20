"""
Run LexAI evaluation on expanded 393-query LexEval-India dataset and report
CAR/ACS by domain for Table V.

Uses cached 293 responses if available and evaluates only missing/new queries.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
import pandas as pd

from llm.legal_llm import LegalLLM
from evaluation.metrics_engine import MetricsEngine


EVAL_DIR = ROOT / "evaluation"
RESULTS_DIR = EVAL_DIR / "evaluation" / "results"
CHECKPOINT_DIR = RESULTS_DIR / "checkpoints"

GT_PATH = EVAL_DIR / "ground_truth_verified_393.xlsx"
BASE_RESPONSES_PATH = CHECKPOINT_DIR / "lexai_responses.json"
RESPONSES_393_PATH = CHECKPOINT_DIR / "lexai_responses_393.json"
SUMMARY_393_PATH = RESULTS_DIR / "table5_cross_domain_summary.json"
TABLE5_MD_PATH = RESULTS_DIR / "table5_cross_domain.md"


def _select_chroma_path() -> Path:
    # Use the workspace-local Chroma path consistently for loading and evaluation.
    p = ROOT / "chroma_db"
    print(f"[chroma] using {p}")
    return p


def _extract_structured_response(result: Dict) -> Dict:
    sources = result.get("sources", {})
    bare_acts = sources.get("bare_acts", [])
    act_cited = None
    section_cited = None

    if bare_acts:
        md = bare_acts[0].get("metadata", {})
        act_cited = md.get("act_name")
        section_cited = md.get("section_number")

    case_citations = []
    for case in sources.get("case_laws", [])[:3]:
        md = case.get("metadata", {})
        case_name = md.get("case_name", "")
        citation = md.get("citation", "")
        if case_name and citation:
            case_citations.append(f"{case_name} - {citation}")

    return {
        "act_cited": act_cited,
        "section_cited": section_cited,
        "case_citations": case_citations,
    }


def _format_sources(sources: Dict) -> List[Dict]:
    chunks: List[Dict] = []
    for act in sources.get("bare_acts", []):
        chunks.append(
            {
                "type": "bare_act",
                "text": act.get("text", ""),
                "metadata": act.get("metadata", {}),
                "confidence": act.get("confidence_score", 0),
            }
        )
    for case in sources.get("case_laws", []):
        chunks.append(
            {
                "type": "case_law",
                "text": case.get("text", ""),
                "metadata": case.get("metadata", {}),
                "confidence": case.get("confidence_score", 0),
            }
        )
    return chunks


def run():
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    gt = pd.read_excel(GT_PATH, sheet_name="Ground Truth Dataset")
    if "domain" not in gt.columns:
        gt["domain"] = "Criminal Law"
    gt = gt.rename(columns={"query_text": "query"})

    base_responses = []
    if BASE_RESPONSES_PATH.exists():
        base_responses = json.loads(BASE_RESPONSES_PATH.read_text(encoding="utf-8"))

    response_by_query = {}
    for r in base_responses:
        q = r.get("query")
        if q:
            response_by_query[q] = r

    chroma_path = _select_chroma_path()
    llm = LegalLLM(persist_directory=str(chroma_path))

    responses_393 = []
    to_run = 0
    reused = 0

    for _, row in gt.iterrows():
        q = str(row["query"]).strip()
        if q in response_by_query:
            responses_393.append(response_by_query[q])
            reused += 1
            continue

        to_run += 1
        result = llm.answer_legal_question(q, include_reasoning=True, eval_mode=True)
        formatted = {
            "query": q,
            "answer": result.get("answer", ""),
            "confidence": result.get("confidence", "UNKNOWN"),
            "structured_response": _extract_structured_response(result),
            "bns_transition_note": None,
            "overruling_note": None,
            "amendment_note": None,
            "retrieved_chunks": _format_sources(result.get("sources", {})),
            "query_type": result.get("query_type", "unknown"),
            "trigger_uncertainty": result.get("trigger_uncertainty", False),
            "citations": result.get("citations", []),
        }
        responses_393.append(formatted)
        print(f"[run] new query {to_run}: {q[:90]}")

    RESPONSES_393_PATH.write_text(json.dumps(responses_393, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[save] responses={len(responses_393)} reused={reused} newly_ran={to_run}")

    engine = MetricsEngine(gt, llm.db.client)

    car = engine.compute_citation_accuracy(responses_393)
    acs = engine.compute_completeness_score(responses_393)

    car_scores = car["individual_scores"]
    acs_scores = acs["individual_scores"]

    table_rows = []
    for domain in ["Criminal Law", "Civil Law", "Corporate Law", "Family Law"]:
        idx = gt.index[gt["domain"] == domain].tolist()
        if not idx:
            continue
        table_rows.append(
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
        "table_rows": table_rows,
        "overall": overall,
        "responses_path": str(RESPONSES_393_PATH),
        "ground_truth": str(GT_PATH),
    }
    SUMMARY_393_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "| Domain | Queries | CAR | ACS |",
        "|---|---|---|---|",
    ]
    for r in table_rows:
        md_lines.append(f"| {r['Domain']} | {r['Queries']} | {r['CAR']}% | {r['ACS']} |")
    md_lines.append(
        f"| **Overall** | **{overall['Queries']}** | **{overall['CAR']}%** | **{overall['ACS']}** |"
    )
    TABLE5_MD_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("\n" + "\n".join(md_lines))
    print(f"\n[save] summary -> {SUMMARY_393_PATH}")
    print(f"[save] markdown -> {TABLE5_MD_PATH}")


if __name__ == "__main__":
    run()
