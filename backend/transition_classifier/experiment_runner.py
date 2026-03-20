"""
Step 6 — OLR ablation: compare use_hardcoded vs use_learned transition logic.
Measures OLR, classifier accuracy on transition queries, and error cases.
Prints comparison table.

When ChromaDB is empty, runs in synthetic mode: builds section references from
query text and applies hardcoded vs learned middleware so results are meaningful
without a populated database.
"""

import os
import re
import sys
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Paths
EVAL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "evaluation")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


def _parse_section_from_query(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract section number and act name from a query. Returns (section_number, act_name) or (None, None)."""
    query = (query or "").strip()
    # Pattern: "Section 302 of the Indian Penal Code" or "Section 420 IPC"
    m = re.search(r"[Ss]ection\s+(\d+[A-Z]?)\s+(?:of\s+(?:the\s+)?)?([^.?]+?)(?:\?|\.|$)", query)
    if m:
        sec, act = m.group(1), m.group(2).strip()
        if act.lower().startswith("the "):
            act = act[4:].strip()
        return sec, act
    m = re.search(r"[Ss]ection\s+(\d+[A-Z]?)\s+(IPC|CrPC|Indian Penal Code|Code of Criminal Procedure)", query, re.I)
    if m:
        return m.group(1), m.group(2).strip()
    return None, None


def _synthetic_result_for_query(query: str) -> List[Dict]:
    """Build one synthetic bare_act-style result from query text (for use when DB is empty)."""
    section_number, act_name = _parse_section_from_query(query)
    if not section_number or not act_name:
        return []
    # Normalize act for middleware: IPC_BNS_MAP keys on section_number; middleware checks "IPC" in act_name
    if act_name.upper() in ("IPC", "INDIAN PENAL CODE"):
        act_name = "Indian Penal Code 1860"
    elif act_name.upper() in ("CRPC", "CR.P.C", "CODE OF CRIMINAL PROCEDURE"):
        act_name = "Code of Criminal Procedure 1973"
    return [{
        "metadata": {"act_name": act_name, "section_number": section_number},
        "document": "",
    }]


def run_experiment(
    use_hardcoded: bool,
    transition_queries: pd.DataFrame = None,
    chroma_path: str = None,
    use_synthetic: bool = None,
) -> Dict[str, Any]:
    """
    Run retrieval + (optional) LLM pipeline with either:
    - use_hardcoded=True: current IPC_BNS_MAP / CRPC_BNSS_MAP lookup in smart_retriever
    - use_hardcoded=False: learned TransitionClassifier for transition detection

    If use_synthetic=True (or ChromaDB returns 0 results for every query), uses
    synthetic section references parsed from query text so the experiment works
    without a populated database.

    Returns dict with: olr_score, accuracy (on transition applicability), error_cases, responses.
    """
    from retrieval.smart_retriever import apply_bns_bnss_middleware

    if chroma_path is None:
        chroma_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")

    # If no transition queries provided, use a minimal in-memory set for structure demo
    if transition_queries is None or transition_queries.empty:
        queries = [
            "What is Section 302 of the Indian Penal Code?",
            "What is Section 138 of the Negotiable Instruments Act?",
            "Explain Section 420 IPC",
        ]
        transition_queries = pd.DataFrame({
            "query_text": queries,
            "category": ["IPC to BNS Transition", "Other", "IPC to BNS Transition"],
        })

    query_texts = transition_queries["query_text"].tolist()
    results = []

    if use_synthetic is True:
        # No retriever: build synthetic results from query text and apply middleware
        for q in query_texts:
            all_items = _synthetic_result_for_query(q)
            if use_hardcoded:
                all_items = apply_bns_bnss_middleware(all_items, "bare_act")
            else:
                all_items = _apply_learned_middleware(all_items)
            results.append({"query": q, "results": all_items})
    else:
        # Use real retriever
        from database.chroma_setup import LegalResearchDB
        from retrieval.smart_retriever import SmartRetriever

        db = LegalResearchDB(persist_directory=chroma_path)
        retriever = SmartRetriever(db=db, use_bns_middleware=use_hardcoded)
        all_retrieved_empty = True
        for q in query_texts:
            raw = retriever.retrieve(q)
            all_items = raw.get("bare_acts", []) + raw.get("case_laws", [])
            if all_items:
                all_retrieved_empty = False
            if not use_hardcoded:
                all_items = _apply_learned_middleware(all_items)
            results.append({"query": q, "results": all_items})

        # If every query returned 0 results, re-run in synthetic mode for meaningful metrics
        if all_retrieved_empty and use_synthetic is not True:
            return run_experiment(
                use_hardcoded=use_hardcoded,
                transition_queries=transition_queries,
                chroma_path=chroma_path,
                use_synthetic=True,
            )

    olr_score, accuracy, error_cases = _compute_olr_and_errors(
        results, transition_queries, use_hardcoded
    )
    return {
        "use_hardcoded": use_hardcoded,
        "olr_score": olr_score,
        "accuracy": accuracy,
        "error_cases": error_cases,
        "n_queries": len(query_texts),
    }


def _apply_learned_middleware(results: List[Dict]) -> List[Dict]:
    """Apply transition notes using TransitionClassifier instead of dict lookup."""
    from transition_classifier import TransitionClassifier

    classifier = TransitionClassifier()
    enhanced = []
    for result in results:
        meta = result.get("metadata", {})
        act_name = meta.get("act_name", "")
        section_number = meta.get("section_number", "")
        text = f"Section {section_number} of the {act_name}" if act_name else ""
        if not text:
            text = result.get("document", "")[:200]
        if text:
            pred = classifier.predict(text)
            if pred["is_superseded"] and pred["replacement"]:
                result["bns_transition"] = {
                    "original": f"Section {section_number}",
                    "replaced_by": pred["replacement"],
                    "note": f"⚠️ Superseded by {pred['replacement']}.",
                }
        enhanced.append(result)
    return enhanced


def _compute_olr_and_errors(
    results: List[Dict],
    transition_queries: pd.DataFrame,
    use_hardcoded: bool,
) -> tuple:
    """
    OLR: fraction of IPC-to-BNS transition queries where no transition note was added.
    Accuracy: fraction of queries where we correctly applied or withheld transition.
    error_cases: list of {query, expected, got}.
    """
    query_to_category = dict(zip(transition_queries["query_text"], transition_queries["category"]))
    is_transition = lambda c: (c or "").strip() == "IPC to BNS Transition"
    outdated_count = 0
    transition_total = 0
    correct = 0
    total = 0
    error_cases = []

    for r in results:
        q = r["query"]
        cat = query_to_category.get(q, "")
        expects_transition = is_transition(cat)
        has_note = any(
            res.get("bns_transition") or res.get("bnss_transition")
            for res in r["results"]
        )
        total += 1
        if expects_transition:
            transition_total += 1
            if not has_note:
                outdated_count += 1
                error_cases.append({"query": q, "expected": "transition note", "got": "no note"})
            else:
                correct += 1
        else:
            if has_note:
                error_cases.append({"query": q, "expected": "no note", "got": "transition note"})
            else:
                correct += 1

    olr = (outdated_count / transition_total) if transition_total else 0.0
    accuracy = (correct / total) if total else 0.0
    return olr, accuracy, error_cases


def print_comparison_table(hardcoded_run: Dict, learned_run: Dict):
    """Print side-by-side comparison for paper/notebook."""
    print("\n" + "=" * 60)
    print("  OLR Ablation: Hardcoded vs Learned Transition Classifier")
    print("=" * 60)
    print(f"{'Metric':<25} {'Hardcoded':<15} {'Learned':<15}")
    print("-" * 60)
    print(f"{'OLR (lower is better)':<25} {hardcoded_run['olr_score']:<15.4f} {learned_run['olr_score']:<15.4f}")
    print(f"{'Accuracy':<25} {hardcoded_run['accuracy']:<15.4f} {learned_run['accuracy']:<15.4f}")
    print(f"{'N queries':<25} {hardcoded_run['n_queries']:<15} {learned_run['n_queries']:<15}")
    print(f"{'Error cases':<25} {len(hardcoded_run['error_cases']):<15} {len(learned_run['error_cases']):<15}")
    print("=" * 60 + "\n")
    if hardcoded_run["error_cases"] or learned_run["error_cases"]:
        print("Error cases (Hardcoded):")
        for e in hardcoded_run["error_cases"][:5]:
            print(f"  - {e}")
        print("Error cases (Learned):")
        for e in learned_run["error_cases"][:5]:
            print(f"  - {e}")


if __name__ == "__main__":
    # Optional: load real transition queries from evaluation data
    transition_queries = None
    use_synthetic = None  # None = try retrieval, fall back to synthetic if DB empty
    gt_path = os.path.join(EVAL_DIR, "ground_truth", "ground_truth_dataset.xlsx")
    if os.path.exists(gt_path):
        try:
            gt_df = pd.read_excel(gt_path, sheet_name="Ground Truth Dataset")
            transition_queries = gt_df[gt_df["category"] == "IPC to BNS Transition"]
            if transition_queries.empty:
                transition_queries = None
        except Exception:
            transition_queries = None
    # When using built-in 3-query demo, use synthetic mode so we don't need a populated ChromaDB
    if transition_queries is None or transition_queries.empty:
        use_synthetic = True

    hardcoded_run = run_experiment(
        use_hardcoded=True,
        transition_queries=transition_queries,
        use_synthetic=use_synthetic,
    )
    learned_run = run_experiment(
        use_hardcoded=False,
        transition_queries=transition_queries,
        use_synthetic=use_synthetic,
    )
    if use_synthetic:
        print("(Synthetic mode: section references derived from query text; no ChromaDB retrieval.)\n")
    print_comparison_table(hardcoded_run, learned_run)
