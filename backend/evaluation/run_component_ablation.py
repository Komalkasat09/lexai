"""
Run 393-query component ablation without reusing ablation checkpoints.
Uses existing full-system checkpoint only, then runs three disabled-component variants.

Outputs:
- evaluation/evaluation/results/checkpoints/lexai_no_reranker_393.json
- evaluation/evaluation/results/checkpoints/lexai_no_bm25_393.json
- evaluation/evaluation/results/checkpoints/lexai_no_routing_393.json
- evaluation/evaluation/results/ablation_table5.json
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import chromadb
from chromadb.config import Settings

from llm.legal_llm import LegalLLM
from evaluation.metrics_engine import MetricsEngine
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.smart_retriever import SmartRetriever


def bootstrap_ci(scores: List[float], n_bootstrap: int = 10000, ci: float = 0.95, seed: int = 42):
    rng = np.random.default_rng(seed)
    arr = np.array(scores, dtype=float)
    means = [float(np.mean(rng.choice(arr, len(arr), replace=True))) for _ in range(n_bootstrap)]
    lower = float(np.percentile(means, (1 - ci) / 2 * 100))
    upper = float(np.percentile(means, (1 + ci) / 2 * 100))
    return lower, upper


def _load_ground_truth(path: Path) -> pd.DataFrame:
    # Required by prompt: use evaluation/ground_truth_verified_393.xlsx for all conditions.
    try:
        df = pd.read_excel(path, sheet_name="Ground Truth Dataset")
    except Exception:
        # Fallback to first sheet while still using the same file path.
        df = pd.read_excel(path)

    if "query_text" in df.columns and "query" not in df.columns:
        df = df.rename(columns={"query_text": "query"})
    return df


def _to_eval_response(query: str, result: Dict) -> Dict:
    citations = result.get("citations")
    if citations is None:
        citations = []
    return {
        "query": query,
        "answer": result.get("answer", ""),
        "confidence": result.get("confidence", "UNKNOWN"),
        "citation": result.get("citation"),
        "citations": citations,
        "structured_response": result.get("structured_response", {}),
        "bns_transition_note": result.get("bns_transition_note"),
        "overruling_note": result.get("overruling_note"),
        "amendment_note": result.get("amendment_note"),
        "retrieved_chunks": result.get("sources", {}).get("retrieved_chunks", []),
        "query_type": result.get("query_type", "unknown"),
        "trigger_uncertainty": result.get("trigger_uncertainty", False),
    }


def _run_condition(
    name: str,
    checkpoint_path: Path,
    queries: List[str],
    llm_kwargs: Dict,
) -> List[Dict]:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    responses: List[Dict] = []
    if checkpoint_path.exists():
        try:
            responses = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except Exception:
            responses = []

    done = len(responses)
    total = len(queries)
    if done >= total:
        print(f"[{name}] checkpoint already complete: {done}/{total}")
        return responses[:total]

    print(f"[{name}] initializing LegalLLM with ablation args: {llm_kwargs}")
    llm = LegalLLM(**llm_kwargs)

    for i in range(done, total):
        q = queries[i]
        print(f"[{name}] {i+1}/{total}", end="\r")
        try:
            out = llm.answer_legal_question(q, include_reasoning=True, eval_mode=True)
            responses.append(_to_eval_response(q, out))
        except Exception as e:
            responses.append(
                {
                    "query": q,
                    "answer": f"ERROR: {e}",
                    "confidence": "ERROR",
                    "citation": None,
                    "citations": [],
                    "structured_response": {},
                    "bns_transition_note": None,
                    "overruling_note": None,
                    "amendment_note": None,
                    "retrieved_chunks": [],
                    "query_type": "unknown",
                    "trigger_uncertainty": True,
                }
            )

        # Persist continuously so long runs are resumable.
        checkpoint_path.write_text(json.dumps(responses, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n[{name}] completed: {len(responses)}/{total}")
    return responses


def _metric_arrays(engine: MetricsEngine, responses: List[Dict]) -> Dict[str, List[float]]:
    car = engine.compute_citation_accuracy(responses)
    car_ret = [float(v) for v in car.get("individual_scores_retrieved", [])]
    car_gen = [float(v) for v in car.get("individual_scores_generated", [])]
    car_scores = [((r + g) / 2.0) * 100.0 for r, g in zip(car_ret, car_gen)]

    hr = engine.compute_hallucination_rate(responses)
    hr_scores = [float(r.get("hallucination_rate", 0.0)) * 100.0 for r in hr.get("individual_results", [])]

    olr_scores = [100.0 if engine._response_has_outdated_citation(r) else 0.0 for r in responses]

    n = min(len(car_scores), len(hr_scores), len(olr_scores), len(responses))
    return {
        "CAR": car_scores[:n],
        "HR": hr_scores[:n],
        "OLR": olr_scores[:n],
    }


def main() -> None:
    base = Path(__file__).resolve().parent.parent

    # Step 1: print ablation parameter names before any runs.
    print("=== Step 1: Ablation toggle parameters (before running) ===")
    hr_sig = inspect.signature(HybridRetriever.__init__)
    sr_sig = inspect.signature(SmartRetriever.__init__)
    llm_sig = inspect.signature(LegalLLM.__init__)

    print("HybridRetriever.__init__ params:", list(hr_sig.parameters.keys()))
    print("SmartRetriever.__init__ params:", list(sr_sig.parameters.keys()))
    print("LegalLLM.__init__ params:", list(llm_sig.parameters.keys()))
    print("Toggles used:")
    print("- Cross-encoder reranking on/off:", "use_reranker")
    print("- BM25 sparse retrieval on/off:", "use_bm25")
    print("- Query-type routing on/off:", "use_query_routing")

    gt_path = base / "evaluation/ground_truth_verified_393.xlsx"
    gt = _load_ground_truth(gt_path)
    queries = gt["query"].astype(str).tolist()
    print(f"Loaded ground truth from {gt_path} with {len(queries)} queries")

    checkpoints_dir = base / "evaluation/evaluation/results/checkpoints"
    full_path = checkpoints_dir / "lexai_responses_393.json"
    no_reranker_path = checkpoints_dir / "lexai_no_reranker_393.json"
    no_bm25_path = checkpoints_dir / "lexai_no_bm25_393.json"
    no_routing_path = checkpoints_dir / "lexai_no_routing_393.json"

    if not full_path.exists():
        raise FileNotFoundError(f"Required full-system checkpoint missing: {full_path}")

    # Step 2: run ablation conditions (full reused, no rerun).
    full_responses = json.loads(full_path.read_text(encoding="utf-8"))
    print(f"[full] reusing existing checkpoint: {full_path} ({len(full_responses)} responses)")

    common_llm_kwargs = {
        "persist_directory": str(base / "legal_research_db"),
        "use_bns_middleware": True,
    }

    no_reranker = _run_condition(
        "no_reranker",
        no_reranker_path,
        queries,
        {
            **common_llm_kwargs,
            "use_reranker": False,
            "use_bm25": True,
            "use_query_routing": True,
        },
    )

    no_bm25 = _run_condition(
        "no_bm25",
        no_bm25_path,
        queries,
        {
            **common_llm_kwargs,
            "use_reranker": True,
            "use_bm25": False,
            "use_query_routing": True,
        },
    )

    no_routing = _run_condition(
        "no_routing",
        no_routing_path,
        queries,
        {
            **common_llm_kwargs,
            "use_reranker": True,
            "use_bm25": True,
            "use_query_routing": False,
        },
    )

    # Step 3: compute CAR/HR/OLR using MetricsEngine.
    gt_eval = gt.copy()
    if "query_text" in gt_eval.columns and "query" not in gt_eval.columns:
        gt_eval = gt_eval.rename(columns={"query_text": "query"})

    client = chromadb.PersistentClient(
        path=str(base / "legal_research_db"),
        settings=Settings(anonymized_telemetry=False, allow_reset=False),
    )
    engine = MetricsEngine(gt_eval, client)

    conditions = {
        "Full LexAI": full_responses,
        "- Cross-encoder reranking": no_reranker,
        "- BM25 (dense only)": no_bm25,
        "- Query routing": no_routing,
    }

    ablation_rows = []
    for name, responses in conditions.items():
        arrays = _metric_arrays(engine, responses)
        row = {"configuration": name}
        for metric in ["CAR", "HR", "OLR"]:
            vals = arrays[metric]
            mean = float(np.mean(vals)) if vals else 0.0
            lo, hi = bootstrap_ci(vals) if vals else (0.0, 0.0)
            row[metric] = {
                "mean": mean,
                "ci95_lower": lo,
                "ci95_upper": hi,
                "n": len(vals),
            }
        ablation_rows.append(row)

    out = {
        "ground_truth_file": str(gt_path),
        "n_queries": len(queries),
        "checkpoints": {
            "full": str(full_path),
            "no_reranker": str(no_reranker_path),
            "no_bm25": str(no_bm25_path),
            "no_routing": str(no_routing_path),
        },
        "rows": ablation_rows,
    }

    out_path = base / "evaluation/evaluation/results/ablation_table5.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved {out_path}")

    # Console summary for quick copy into paper.
    for row in ablation_rows:
        print(row["configuration"])
        for metric in ["CAR", "HR", "OLR"]:
            m = row[metric]
            print(f"  {metric}: {m['mean']:.4f} ({m['ci95_lower']:.4f}, {m['ci95_upper']:.4f})")


if __name__ == "__main__":
    main()
