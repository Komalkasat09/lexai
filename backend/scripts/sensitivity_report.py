"""Report every paper claim under two fixed scoring rules, including the ablations.

Analysis plan, fixed and committed before the ablation results were read:

Rules (every claim is reported under both, never only one)
    A  any acceptable citation   the answer cites any acceptable target
                                 (citations already written in the query excluded
                                 when the claim is about non-echo rows)
    B  first new citation        the first section the answer cites that is not
                                 already in the query is an acceptable target
                                 (statute rows only; there is no ordering of
                                 cases to apply it to)

Claims
    1  overall                   rule A, full benchmark and non-echo rows
    2  statute rows              rules A and B, non-echo rows
    3  case-law rows             rule A, non-echo rows
    4  IPC to BNS transition     rules A and B, non-echo rows
    5  transition, map split     rules A and B, split by whether the IPC/CrPC
                                 section named in the query is in the
                                 hand-written transition map (counts reported)
    Ablations                    each LexAI variant against full LexAI on the same
                                 queries, rules A and B, transition and punishment

Comparisons use the exact two-sided McNemar test on paired outcomes, with the
discordant counts reported alongside.

Run from backend/:

    python scripts/sensitivity_report.py --main evaluation/results_rerun_full \
        --ablation evaluation/results_rerun_ablation_no_replacement_fetch \
        --ablation evaluation/results_rerun_ablation_no_transition_middleware
"""
import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluation.answer_key import _act_patterns, _normalise, base_section, case_cited, row_targets, statute_cited  # noqa: E402
from evaluation.citation_validity import LAST_SECTION  # noqa: E402
from score_rerun import mcnemar_exact  # noqa: E402

SYSTEMS = ("LexAI", "NoRAG", "SimpleRAG")
WINDOW = 30  # characters either side of an act name searched for its section number


def load(run_dir, system):
    """{query_id: response} for one system; empty when the file is missing."""
    path = Path(run_dir) / f"{system.lower()}_responses.jsonl"
    if not path.exists():
        return {}
    return {json.loads(l)["query_id"]: json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}


def citations_in_order(text, acts):
    """(act, base section) pairs in the order they appear in the text."""
    low = _normalise(text)
    found = []
    for act in acts:
        for pattern in _act_patterns(act):
            for m in re.finditer(pattern, low):
                start = max(0, m.start() - WINDOW)
                for n in re.finditer(r"(?<![0-9a-z])(\d{1,4}[a-z]{0,2})(?![0-9a-z])", low[start:m.end() + WINDOW]):
                    if 1800 <= int(re.match(r"\d+", n.group(1)).group()) <= 2099:
                        continue  # a year, not a section
                    found.append((start + n.start(), act, base_section(n.group(1))))
    return [(act, sec) for _, act, sec in sorted(found)]


def first_new_citation_correct(answer, query, targets, acts):
    """Rule B: is the first section cited that the query does not already name a target?"""
    new = [c for c in citations_in_order(answer, acts) if not statute_cited(query, *c)]
    return bool(new) and new[0] in set(targets)


def query_sections(query):
    """IPC/CrPC sections a query names, as ('IPC'|'CRPC', section)."""
    named = re.findall(r"\b(IPC|CrPC)\s*(?:Section\s*|s\.\s*)?(\d+[A-Z]*)", query, re.I)
    named += [(a, s) for s, a in re.findall(r"Section\s*(\d+[A-Z]*)\s*(?:of\s+the\s+)?(IPC|CrPC)", query, re.I)]
    return sorted({(a.upper(), s.upper()) for a, s in named})


def map_group(query, ipc_map, crpc_map):
    """'in map', 'not in map' or 'no section named' for a transition query."""
    named = query_sections(query)
    if not named:
        return "no section named"
    hits = [(a, s) for a, s in named if (a == "IPC" and s in ipc_map) or (a == "CRPC" and s in crpc_map)]
    return "in map" if hits else "not in map"


def score_rows(gt, runs):
    """One row per scored query with rule A (full and non-echo) and rule B outcomes per system."""
    from retrieval.smart_retriever import CRPC_BNSS_MAP, IPC_BNS_MAP

    rows = []
    for g in gt.to_dict("records"):
        ttype, primary, acceptable, cases = row_targets(g)
        if ttype not in ("S", "C"):
            continue
        query = g["query"]
        rec = {"query_id": g["query_id"], "category": g["category"], "type": ttype}
        if ttype == "S":
            new_targets = [c for c in acceptable if not statute_cited(query, *c)]
            acts = set(LAST_SECTION) | {a for a, _ in acceptable}
        else:
            new_targets = [c for c in cases if not case_cited(query, c)]
        rec["echo"] = not new_targets
        if g["category"] == "IPC to BNS Transition":
            rec["map_group"] = map_group(query, IPC_BNS_MAP, CRPC_BNSS_MAP)
        for name, responses in runs.items():
            if g["query_id"] not in responses:
                continue
            answer = responses[g["query_id"]].get("answer") or ""
            if ttype == "S":
                rec[f"{name}|A_full"] = float(any(statute_cited(answer, *c) for c in acceptable))
                rec[f"{name}|A_new"] = float(any(statute_cited(answer, *c) for c in new_targets)) if new_targets else None
                rec[f"{name}|B_new"] = float(first_new_citation_correct(answer, query, new_targets, acts)) if new_targets else None
            else:
                rec[f"{name}|A_full"] = float(any(case_cited(answer, c) for c in cases))
                rec[f"{name}|A_new"] = float(any(case_cited(answer, c) for c in new_targets)) if new_targets else None
                rec[f"{name}|B_new"] = None
        rows.append(rec)
    return pd.DataFrame(rows)


def compare(frame, a, b, rule):
    """Paired comparison of systems a and b under one rule on the rows where both are scored."""
    cols = [f"{a}|{rule}", f"{b}|{rule}"]
    if not all(c in frame for c in cols):
        return None
    sub = frame[cols].dropna()
    if sub.empty:
        return None
    p, a_only, b_only = mcnemar_exact(sub[cols[0]], sub[cols[1]])
    return {"n": int(len(sub)), a: round(100 * sub[cols[0]].mean(), 1), b: round(100 * sub[cols[1]].mean(), 1),
            f"{a}_only": a_only, f"{b}_only": b_only, "mcnemar_p": round(p, 4)}


def claims(frame, systems):
    """The pre-specified claims, each under both rules where the rule applies."""
    new = frame[~frame.echo]
    blocks = {
        "1 overall (full benchmark)": (frame, ["A_full"]),
        "1 overall (non-echo rows)": (new, ["A_new"]),
        "2 statute rows (non-echo)": (new[new.type == "S"], ["A_new", "B_new"]),
        "3 case-law rows (non-echo)": (new[new.type == "C"], ["A_new"]),
        "4 IPC to BNS transition (non-echo)": (new[new.category == "IPC to BNS Transition"], ["A_new", "B_new"]),
    }
    trans = new[new.category == "IPC to BNS Transition"]
    if "map_group" in trans:
        for group in ("in map", "not in map", "no section named"):
            blocks[f"5 transition, {group} (non-echo)"] = (trans[trans.map_group == group], ["A_new", "B_new"])
    out = {}
    for label, (sub, rules) in blocks.items():
        out[label] = {rule: {f"LexAI vs {b}": compare(sub, "LexAI", b, rule) for b in systems if b != "LexAI"}
                      for rule in rules}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", type=Path, required=True)
    ap.add_argument("--ablation", type=Path, action="append", default=[])
    ap.add_argument("--ground-truth", default="evaluation/ground_truth_lexeval_key_393.xlsx")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    gt = pd.read_excel(BACKEND / args.ground_truth).rename(columns={"query_text": "query"})
    runs = {s: load(args.main, s) for s in SYSTEMS}
    frame = score_rows(gt, runs)
    report = {"rules": {"A": "any acceptable citation", "B": "first new citation correct (statute rows)"},
              "main": claims(frame, SYSTEMS), "ablations": {}}

    for ablation in args.ablation:
        variant = Path(ablation).name.replace("results_rerun_ablation_", "")
        abl = {"LexAI": runs["LexAI"], variant: load(ablation, "LexAI")}
        f = score_rows(gt, abl)
        f = f[f[f"{variant}|A_full"].notna()] if f"{variant}|A_full" in f else f.iloc[0:0]
        new = f[~f.echo]
        report["ablations"][variant] = {
            "answers": int(len(f)),
            "transition (non-echo)": {r: compare(new[new.category == "IPC to BNS Transition"], "LexAI", variant, r)
                                      for r in ("A_new", "B_new")},
            "punishment (non-echo)": {r: compare(new[new.category == "Punishment Queries"], "LexAI", variant, r)
                                      for r in ("A_new", "B_new")},
            "all ablation rows (full)": {"A_full": compare(f, "LexAI", variant, "A_full")},
        }

    out = args.out or args.main / "sensitivity_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    frame.to_csv(out.with_suffix(".csv"), index=False)
    print(json.dumps(report, indent=2))
    print("\nwrote", out)


if __name__ == "__main__":
    main()
