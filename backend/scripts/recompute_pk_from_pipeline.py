"""Recompute P@K from the documents the LexAI pipeline actually retrieved.

The P@K in the paper so far came from a separate dense-only ChromaDB query
(metrics_engine.compute_retrieval_precision_at_k). This script scores the
reranked context that LexAI stored with each response instead, so the number
describes the hybrid pipeline. It makes no LLM or database calls.

Put this file in backend/scripts/ and run it from backend/:

    python scripts/recompute_pk_from_pipeline.py

Inputs (paths relative to backend/, override with the flags below):
    evaluation/results_393_postfix/checkpoints/lexai_responses.json
    evaluation/ground_truth_verified_393_ready.xlsx
    evaluation/metrics_engine.py   (read only, for the act-name table)

Output:
    evaluation/results_393_postfix/pk_from_pipeline.json
    and a summary printed to the terminal.

Relevance rule (same as the metrics engine, applied to stored chunks):
    statute queries   chunk.section_number == correct_section
                      and chunk.act_name == canonical name of correct_act
    case-law queries  chunk.citation == correct_citation
Section numbers are compared after removing a leading "Section", spaces,
a trailing ".0" and letter case.
"""
import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent


def load_act_table(engine_path):
    """Read _ACT_CANONICAL_NAMES out of metrics_engine.py without importing it."""
    src = engine_path.read_text(encoding="utf-8")
    m = re.search(r"_ACT_CANONICAL_NAMES\s*=\s*\{", src)
    if not m:
        raise SystemExit("Could not find _ACT_CANONICAL_NAMES in " + str(engine_path))
    start = m.end() - 1
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return ast.literal_eval(src[start:i + 1])
    raise SystemExit("Unbalanced braces in _ACT_CANONICAL_NAMES")


def resolve_act(fragment, table):
    """Same logic as MetricsEngine._resolve_act_name."""
    if not fragment:
        return None
    key = fragment.strip().upper()
    if key in table:
        return table[key]
    for k, v in table.items():
        if key.startswith(k) or k.startswith(key):
            return v
    return None


def s(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


def norm_section(value):
    t = s(value).strip().lower()
    t = re.sub(r"^(section|sec\.?|s\.)\s*", "", t)
    t = re.sub(r"\.0$", "", t)
    return t.replace(" ", "")


def norm_text(value):
    return re.sub(r"\s+", " ", s(value)).strip().lower()


def is_case_category(category):
    c = norm_text(category).replace(" ", "_")
    return "case_law" in c or "overruled" in c


def relevance(chunks, gt, table):
    """One True/False per retrieved chunk, in the order the pipeline kept them."""
    out = []
    if is_case_category(gt.get("category")):
        want = norm_text(gt.get("correct_citation"))
        for ch in chunks:
            meta = ch.get("metadata") or {}
            out.append(bool(want) and norm_text(meta.get("citation")) == want)
        return out
    want_sec = norm_section(gt.get("correct_section"))
    raw_act = s(gt.get("correct_act"))
    want_act = resolve_act(raw_act, table) or raw_act
    for ch in chunks:
        meta = ch.get("metadata") or {}
        sec_ok = bool(want_sec) and norm_section(meta.get("section_number")) == want_sec
        act_ok = norm_text(meta.get("act_name")) == norm_text(want_act)
        out.append(sec_ok and act_ok)
    return out


def score(rel):
    """P@1, P@3 as in the metrics engine, plus hit@3 and hit@5."""
    if not rel:
        return dict(p1=0.0, p3=0.0, hit3=0.0, hit5=0.0)
    return dict(
        p1=float(rel[0]),
        p3=sum(rel[:3]) / min(3, len(rel)),
        hit3=float(any(rel[:3])),
        hit5=float(any(rel[:5])),
    )


def mean_pct(rows, key):
    return round(100.0 * sum(r[key] for r in rows) / len(rows), 2) if rows else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", type=Path, default=BACKEND /
                    "evaluation/results_393_postfix/checkpoints/lexai_responses.json")
    ap.add_argument("--ground-truth", type=Path, default=BACKEND /
                    "evaluation/ground_truth_verified_393_ready.xlsx")
    ap.add_argument("--engine", type=Path, default=BACKEND /
                    "evaluation/metrics_engine.py")
    ap.add_argument("--out", type=Path, default=BACKEND /
                    "evaluation/results_393_postfix/pk_from_pipeline.json")
    args = ap.parse_args()

    table = load_act_table(args.engine)
    responses = json.loads(args.responses.read_text(encoding="utf-8"))
    gt = pd.read_excel(args.ground_truth)
    if len(responses) != len(gt):
        raise SystemExit(f"{len(responses)} responses but {len(gt)} ground-truth rows")

    qcol = "query_text" if "query_text" in gt.columns else "query"
    mismatched = sum(
        norm_text(r.get("query")) != norm_text(row.get(qcol))
        for r, (_, row) in zip(responses, gt.iterrows()))

    per_query = []
    for i, (resp, (_, row)) in enumerate(zip(responses, gt.iterrows())):
        g = row.to_dict()
        chunks = resp.get("retrieved_chunks") or []
        rel = relevance(chunks, g, table)
        sc = score(rel)
        sc.update(index=i, query_id=s(g.get("query_id")),
                  category=s(g.get("category")), n_chunks=len(chunks),
                  has_target=bool(norm_section(g.get("correct_section")) or
                                  norm_text(g.get("correct_citation"))))
        per_query.append(sc)

    scored = [r for r in per_query if r["has_target"]]
    with_ctx = [r for r in scored if r["n_chunks"] > 0]

    def block(rows):
        return dict(n=len(rows), P_at_1=mean_pct(rows, "p1"),
                    P_at_3=mean_pct(rows, "p3"), Hit_at_3=mean_pct(rows, "hit3"),
                    Hit_at_5=mean_pct(rows, "hit5"))

    by_cat = defaultdict(list)
    for r in scored:
        by_cat[r["category"]].append(r)

    result = {
        "source": "retrieved_chunks stored in " + args.responses.name,
        "queries_total": len(per_query),
        "queries_without_ground_truth_target": len(per_query) - len(scored),
        "query_text_mismatches_with_ground_truth": mismatched,
        "all_queries_with_target": block(scored),
        "queries_with_retrieved_context": block(with_ctx),
        "queries_with_no_retrieved_context": len(scored) - len(with_ctx),
        "by_category": {k: block(v) for k, v in sorted(by_cat.items())},
    }
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))
    print("\nwrote", args.out)
    if mismatched:
        print(f"WARNING: {mismatched} responses do not line up with the "
              "ground-truth row at the same position. Check the file order "
              "before using these numbers.")


if __name__ == "__main__":
    main()
