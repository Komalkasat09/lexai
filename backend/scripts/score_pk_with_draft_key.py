"""Score LexAI's retrieved context against the advocate-reviewed answer key.

Uses the same stored pipeline chunks as recompute_pk_from_pipeline.py, but
takes citation targets from the LexEval answer key (via
evaluation/answer_key.py) instead of the 393 ground-truth file, which has no
target for 204 queries.

Run from backend/:

    python scripts/score_pk_with_draft_key.py --key "<path to answer key .xlsx>"

Targets
    Section Lookup (143)   original ground-truth file (that sheet of the key
                           was not reviewed); a variant applies the three
                           act fixes the key flags (Q032-Q034 are BNSS)
    Other categories (250) the key's "Draft key" sheet with the advocate
                           corrections in answer_key.CORRECTIONS; Reject and
                           Type O rows are excluded from scoring

Relevance
    Type S  chunk act == target act and chunk section == target section, at
            section level ("310(3)" matches chunk "310"). Strict uses the
            primary citations only; lenient also accepts "also acceptable".
    Type C  chunk is a case_law chunk whose case name matches a key case.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluation.answer_key import (  # noqa: E402
    base_section, build_ground_truth, case_cited, is_qa_entry, row_targets,
)
from recompute_pk_from_pipeline import norm_text, s, score  # noqa: E402


def statute_rel(chunks, targets):
    """One True/False per chunk: is it a bare-act chunk for one of the target sections."""
    wanted = {(norm_text(act), sec) for act, sec in targets}
    out = []
    for ch in chunks:
        md = ch.get("metadata") or {}
        key = (norm_text(md.get("act_name")), base_section(md.get("section_number")))
        out.append(ch.get("type") == "bare_act" and key in wanted)
    return out


def case_rel(chunks, cases):
    """One True/False per chunk: is it a judgment chunk for one of the key cases.

    Q&A entries never count, even when their question names the case: they
    are not the judgment, and the clean index no longer stores the question
    as the case name, so counting them would make runs incomparable.
    """
    out = []
    for ch in chunks:
        md = ch.get("metadata") or {}
        label = f"{s(md.get('case_name'))} {s(md.get('citation'))}"
        out.append(ch.get("type") == "case_law" and not is_qa_entry(md)
                   and any(case_cited(label, c) for c in cases))
    return out


def block(rows, key="rel"):
    if not rows:
        return dict(n=0)
    sc = [score(r[key]) for r in rows]
    pct = lambda k: round(100.0 * sum(x[k] for x in sc) / len(sc), 2)
    return dict(n=len(rows), P_at_1=pct("p1"), P_at_3=pct("p3"),
                Hit_at_3=pct("hit3"), Hit_at_5=pct("hit5"))


def summarise(rows, key):
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    return {"all": block(rows, key),
            "with_retrieved_context": block([r for r in rows if r["n_chunks"]], key),
            "by_category": {k: block(v, key) for k, v in sorted(by_cat.items())}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", type=Path, required=True)
    ap.add_argument("--responses", type=Path, default=BACKEND /
                    "evaluation/results_393_postfix/checkpoints/lexai_responses.json")
    ap.add_argument("--ground-truth", type=Path, default=BACKEND /
                    "evaluation/ground_truth_verified_393_ready.xlsx")
    ap.add_argument("--out", type=Path, default=BACKEND /
                    "evaluation/results_393_postfix/pk_with_draft_key.json")
    args = ap.parse_args()

    responses = json.loads(args.responses.read_text(encoding="utf-8"))
    gt = build_ground_truth(str(args.key), str(args.ground_truth))
    gt_fixed = build_ground_truth(str(args.key), str(args.ground_truth), apply_section_lookup_fixes=True)
    if len(responses) != len(gt):
        raise SystemExit(f"{len(responses)} responses but {len(gt)} ground-truth rows")

    statute, statute_fixed, cases, excluded, per_query = [], [], [], defaultdict(list), []
    for i, (row, row_fixed) in enumerate(zip(gt.to_dict("records"), gt_fixed.to_dict("records"))):
        chunks = responses[i].get("retrieved_chunks") or []
        ttype, primary, acceptable, key_cases = row_targets(row)
        base = dict(query_id=row["query_id"], category=row["category"], n_chunks=len(chunks))
        if ttype == "S":
            rec = dict(base, rel=statute_rel(chunks, primary), rel_lenient=statute_rel(chunks, acceptable))
            statute.append(rec)
            fixed_primary = row_targets(row_fixed)[1]
            statute_fixed.append(dict(rec, rel=statute_rel(chunks, fixed_primary)))
            per_query.append(dict(base, type="S", source=row["target_source"], primary=sorted(primary),
                                  also=sorted(set(acceptable) - set(primary)),
                                  hit3_strict=any(rec["rel"][:3]), hit3_lenient=any(rec["rel_lenient"][:3])))
        elif ttype == "C":
            rec = dict(base, rel=case_rel(chunks, key_cases), rel_statute_anchor=[False] * len(chunks))
            cases.append(rec)
            per_query.append(dict(base, type="C", source=row["target_source"], primary=key_cases, also=[],
                                  hit3_strict=any(rec["rel"][:3])))
        else:
            excluded[{"X": "Reject", "O": "Type O"}.get(ttype, "No target")].append(row["query_id"])

    case_names = sorted({s((ch.get("metadata") or {}).get("case_name")) for r in responses
                         for ch in r.get("retrieved_chunks") or []
                         if ch.get("type") == "case_law"
                         and not s((ch.get("metadata") or {}).get("citation")).startswith("VIBER")})
    result = {
        "source": "retrieved_chunks stored in " + args.responses.name,
        "key_file": args.key.name,
        "queries_total": len(gt),
        "scored_statute": len(statute),
        "scored_case": len(cases),
        "excluded": {k: dict(n=len(v), query_ids=v) for k, v in excluded.items()},
        "statute_strict_primary_only": summarise(statute, "rel"),
        "statute_lenient_with_also_acceptable": summarise(statute, "rel_lenient"),
        "statute_strict_with_section_lookup_fixes": summarise(statute_fixed, "rel"),
        "case_law_key_case_match": summarise(cases, "rel"),
        "non_qa_case_names_in_retrieved_chunks": case_names,
    }
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    pq = args.out.with_name(args.out.stem + "_per_query.csv")
    pd.DataFrame(per_query).to_csv(pq, index=False)

    print(json.dumps({k: result[k] for k in ("scored_statute", "scored_case", "excluded")}, indent=2))
    for k in ("statute_strict_primary_only", "statute_lenient_with_also_acceptable",
              "statute_strict_with_section_lookup_fixes", "case_law_key_case_match"):
        print(k, result[k]["all"])
    print("\nwrote", args.out)
    print("wrote", pq)


if __name__ == "__main__":
    main()
