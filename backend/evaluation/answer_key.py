"""The LexEval-India answer key, and one rule for whether an answer matches it.

Builds the ground-truth table the metrics engine reads from the advocate-
reviewed key workbook, and decides whether a piece of text cites a target.
Queries with no target are marked, so no metric can score them as correct.
"""
import json
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd

# Advocate corrections from the key's "Advocate correction" column, translated
# into targets. "primary"/"also" replace the draft values; type "O" (open, no
# single citation) or "X" (rejected) removes the row from citation scoring.
# Case-row corrections that only reword the answer note (Q227, Q233, Q238,
# Q240, Q242, Q247) leave the key cases unchanged.
CORRECTIONS: Dict[str, Dict[str, str]] = {
    "Q050": {"primary": "IPC 403; BNS 314"},
    "Q054": {"primary": "IPC 304; BNS 105"},
    "Q056": {"primary": "IPC 396; BNS 310(3)"},
    "Q060": {"primary": "IPC 342; BNS 127(2)"},
    "Q086": {"primary": "BNSS 479", "also": "BNSS 478, 480, 482, 483"},
    "Q090": {"type": "O"},
    "Q092": {"type": "O"},
    "Q094": {"also": "CrPC 438"},
    "Q096": {"type": "O"},
    "Q104": {"type": "O"},
    "Q107": {"also": "BSA 61, 62, 2(1)(c); Evidence Act 65B"},
    "Q111": {"primary": "BNSS 180(3), 183(6)(a)", "also": "BNSS 105, 176"},
    "Q118": {"primary": "SC/ST (Prevention of Atrocities) Act 1989 s.18, 18A", "also": ""},
    "Q120": {"type": "O"},
    "Q121": {"primary": "BSA 2(1)(c)"},
    "Q148": {"type": "O"},
    "Q150": {"also": "IPC 306"},
    "Q157": {"type": "O"},
    "Q206": {"type": "O"},
    "Q216": {"type": "X"},
    "Q258": {"also": "IPC 90; BNS 63, 28; Evidence Act 114A; BSA 120"},
    "Q270": {"also": "CrPC 436, 437; BNSS 2(1)(d), 478, 480"},
}

# Section Lookup rows the key flags as recorded under the wrong act. Not applied
# by default: the advocate left that sheet undecided.
SECTION_LOOKUP_FIXES: Dict[str, str] = {"Q032": "BNSS", "Q033": "BNSS", "Q034": "BNSS"}

CANONICAL_ACTS: Dict[str, str] = {
    "IPC": "Indian Penal Code 1860",
    "INDIAN PENAL CODE": "Indian Penal Code 1860",
    "BNS": "Bharatiya Nyaya Sanhita 2023",
    "BHARATIYA NYAYA SANHITA": "Bharatiya Nyaya Sanhita 2023",
    "CRPC": "Code of Criminal Procedure 1973",
    "CR.P.C": "Code of Criminal Procedure 1973",
    "CODE OF CRIMINAL PROCEDURE": "Code of Criminal Procedure 1973",
    "BNSS": "Bharatiya Nagarik Suraksha Sanhita 2023",
    "BHARATIYA NAGARIK SURAKSHA SANHITA": "Bharatiya Nagarik Suraksha Sanhita 2023",
    "IEA": "Indian Evidence Act 1872",
    "EVIDENCE ACT": "Indian Evidence Act 1872",
    "INDIAN EVIDENCE ACT": "Indian Evidence Act 1872",
    "BSA": "Bharatiya Sakshya Adhiniyam 2023",
    "BHARATIYA SAKSHYA ADHINIYAM": "Bharatiya Sakshya Adhiniyam 2023",
    "NI ACT": "Negotiable Instruments Act 1881",
    "NIA": "Negotiable Instruments Act 1881",
    "NEGOTIABLE INSTRUMENTS ACT": "Negotiable Instruments Act 1881",
    "CPC": "Code of Civil Procedure 1908",
    "CODE OF CIVIL PROCEDURE": "Code of Civil Procedure 1908",
    "HMA": "Hindu Marriage Act 1955",
    "HINDU MARRIAGE ACT": "Hindu Marriage Act 1955",
    "CA": "Companies Act 2013",
    "COMPANIES ACT": "Companies Act 2013",
    "CPA": "Consumer Protection Act 2019",
    "CONSUMER PROTECTION ACT": "Consumer Protection Act 2019",
    "ACA": "Arbitration and Conciliation Act 1996",
    "ARBITRATION ACT": "Arbitration and Conciliation Act 1996",
    "ARBITRATION AND CONCILIATION ACT": "Arbitration and Conciliation Act 1996",
    "TPA": "Transfer of Property Act 1882",
    "TRANSFER OF PROPERTY ACT": "Transfer of Property Act 1882",
    "LA": "Limitation Act 1963",
    "LIMITATION ACT": "Limitation Act 1963",
    "SRA": "Specific Relief Act 1963",
    "SPECIFIC RELIEF ACT": "Specific Relief Act 1963",
    "PWDVA": "Protection of Women from Domestic Violence Act 2005",
    "PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE ACT": "Protection of Women from Domestic Violence Act 2005",
    "POCSO": "Protection of Children from Sexual Offences Act 2012",
    "POCSO ACT": "Protection of Children from Sexual Offences Act 2012",
    "PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT": "Protection of Children from Sexual Offences Act 2012",
    "IT ACT": "Information Technology Act 2000",
    "INFORMATION TECHNOLOGY ACT": "Information Technology Act 2000",
}

# Words a reader would use for each act in an answer. Short codes are matched
# as whole words, so "BNS" never matches inside "BNSS".
ACT_ALIASES: Dict[str, List[str]] = {
    "Indian Penal Code 1860": ["indian penal code", "penal code", "ipc"],
    "Bharatiya Nyaya Sanhita 2023": ["bharatiya nyaya sanhita", "nyaya sanhita", "bns"],
    "Code of Criminal Procedure 1973": ["code of criminal procedure", "criminal procedure code", "crpc", "cr.p.c", "cr. p.c."],
    "Bharatiya Nagarik Suraksha Sanhita 2023": ["bharatiya nagarik suraksha sanhita", "nagarik suraksha sanhita", "bnss"],
    "Indian Evidence Act 1872": ["indian evidence act", "evidence act", "iea"],
    "Bharatiya Sakshya Adhiniyam 2023": ["bharatiya sakshya adhiniyam", "sakshya adhiniyam", "bsa"],
    "Negotiable Instruments Act 1881": ["negotiable instruments act", "ni act", "n.i. act"],
    "Code of Civil Procedure 1908": ["code of civil procedure", "civil procedure code", "cpc"],
    "Hindu Marriage Act 1955": ["hindu marriage act", "hma"],
    "Companies Act 2013": ["companies act"],
    "Consumer Protection Act 2019": ["consumer protection act"],
    "Arbitration and Conciliation Act 1996": ["arbitration and conciliation act", "arbitration act"],
    "Transfer of Property Act 1882": ["transfer of property act", "tpa"],
    "Limitation Act 1963": ["limitation act"],
    "Specific Relief Act 1963": ["specific relief act"],
    "Protection of Women from Domestic Violence Act 2005": ["domestic violence act", "pwdva"],
    "Protection of Children from Sexual Offences Act 2012": ["protection of children from sexual offences", "pocso"],
    "Information Technology Act 2000": ["information technology act", "it act"],
    "Constitution of India": ["constitution"],
}

# Characters allowed between an act name and a section number for the two to
# count as one citation ("Section 302 of the Indian Penal Code", "IPC s. 302").
PROXIMITY_CHARS = 40
GENERIC_PARTIES = ("state of", "state", "union of india", "union", "attorney general",
                   "government of", "commissioner", "the state")

Citation = Tuple[str, str]


def _s(value) -> str:
    """Text of a cell, with NaN and None as the empty string."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def canonical_act(name: str) -> str:
    """Canonical act name for an abbreviation or full name, matched exactly.

    Exact lookup, then lookup with a trailing year removed. Unknown names come
    back unchanged. No prefix matching, which mapped "BNSS 2023" to the BNS.
    """
    raw = re.sub(r"\s+", " ", _s(name)).rstrip(",").strip()
    if not raw:
        return ""
    key = raw.upper()
    if key in CANONICAL_ACTS:
        return CANONICAL_ACTS[key]
    no_year = re.sub(r"\s+\d{4}$", "", key)
    if no_year in CANONICAL_ACTS:
        return CANONICAL_ACTS[no_year]
    if no_year.startswith("CONSTITUTION"):
        return "Constitution of India"
    return raw


def base_section(section: str) -> str:
    """Section number at section level, lower-cased: 'Section 310(3)' -> '310'."""
    text = re.sub(r"^(section|sec\.?|ss?\.|art\.|article)\s*", "", _s(section), flags=re.I)
    text = re.sub(r"\.0$", "", text)
    return re.sub(r"\(.*$", "", text).replace(" ", "").lower()


def _expand_range(start: str, end: str) -> List[str]:
    """'289 to 300' -> 289..300; '376A to 376E' -> 376A..376E."""
    ma, mb = re.fullmatch(r"(\d+)([A-Z]?)", start), re.fullmatch(r"(\d+)([A-Z]?)", end)
    if not (ma and mb):
        return [start, end]
    if ma.group(1) == mb.group(1) and ma.group(2) and mb.group(2):
        return [ma.group(1) + chr(c) for c in range(ord(ma.group(2)), ord(mb.group(2)) + 1)]
    if not ma.group(2) and not mb.group(2) and int(ma.group(1)) <= int(mb.group(1)):
        return [str(n) for n in range(int(ma.group(1)), int(mb.group(1)) + 1)]
    return [start, end]


def parse_citations(text: str, default_act: str = "") -> Set[Citation]:
    """Turn 'IPC 403; BNS 314, 315' into {(canonical act, base section), ...}.

    A segment with no act ('s.18A') uses default_act. A segment that names an
    act but no section yields nothing, since answers are scored per section.
    """
    out: Set[Citation] = set()
    for seg in _s(text).split(";"):
        seg = re.sub(r"\(definition\)|\(related offence.*?\)|\(monetary penalty\)|proviso|Part [IVX]+",
                     "", seg).strip()
        if not seg:
            continue
        # The first number that is not a year starts the section list, so
        # "Companies Act 2013 s.448" splits into the act and section 448.
        first = next((m for m in re.finditer(r"\d+[A-Z]*", seg)
                      if not re.fullmatch(r"(18|19|20)\d\d", m.group())), None)
        if first is None:
            continue
        act_part = re.sub(r"(\bArt\.|\bss?\.)\s*$", "", seg[:first.start()]).strip()
        sec_part = seg[first.start():].replace("of the same Act", "")
        act = default_act if (not act_part or "same act" in seg.lower()) else canonical_act(act_part)
        for start, end in re.findall(r"(\d+[A-Z]*(?:\([0-9a-zA-Z]+\))*)(?:\s+to\s+(\d+[A-Z]*))?", sec_part):
            for sec in (_expand_range(start, end) if end else [start]):
                if base_section(sec):
                    out.add((act, base_section(sec)))
    return out


def _act_patterns(act: str) -> List[str]:
    aliases = ACT_ALIASES.get(act)
    if aliases is None:
        bare = re.sub(r"\s*\(.*?\)\s*", " ", re.sub(r"\s+\d{4}$", "", act)).strip().lower()
        aliases = [bare] if bare else []
    return [r"(?<![a-z])" + re.escape(a) + r"(?![a-z])" for a in aliases]


def act_cited(text: str, act: str) -> bool:
    """True when the text names the act by any of its usual names."""
    low = _s(text).lower()
    return any(re.search(p, low) for p in _act_patterns(act))


def statute_cited(text: str, act: str, section: str) -> bool:
    """True when the text cites this section of this act.

    The section number must appear within PROXIMITY_CHARS of a name for the
    act, in either order, so "Section 302 of the IPC", "IPC 302" and
    "[Section 302, Indian Penal Code 1860]" all count, while a bare 302
    elsewhere in the answer does not.
    """
    low = _s(text).lower()
    sec = re.escape(base_section(section))
    if not sec:
        return False
    sec_re = re.compile(r"(?<![0-9a-z])" + sec + r"(?![0-9a-z])")
    for pattern in _act_patterns(act):
        for m in re.finditer(pattern, low):
            window = low[max(0, m.start() - PROXIMITY_CHARS): m.end() + PROXIMITY_CHARS]
            if sec_re.search(window):
                return True
    return False


def _party_name(case: str) -> str:
    """The distinctive party name of a case: 'Arnesh Kumar v. State of Bihar' -> 'arnesh kumar'."""
    head = re.split(r"\(\d{4}\)|\bAIR\b|\(\w+ HC|\(\d{4}", _s(case))[0]
    parties = re.split(r"\s+(?:v\.?|vs\.?|versus)\s+", head, flags=re.I)
    names = [re.sub(r"[^a-z ]", " ", p.lower()).strip() for p in parties]
    names = [" ".join(n.split()) for n in names if n.strip()]
    for name in names:
        if not name.startswith(GENERIC_PARTIES):
            return name
    return names[0] if names else ""


def _reporter_cite(case: str) -> str:
    """Reporter citation of a case, normalised: '(2014) 8 SCC 273' -> '8 scc 273'."""
    m = re.search(r"(\d+\s+SCC\s+\d+|AIR\s+\d{4}\s+SC\s+\d+|\d{4}\s+Supp\s*\(\d\)\s*SCC\s+\d+)", _s(case), re.I)
    return re.sub(r"\s+", " ", m.group(1)).lower() if m else ""


def case_cited(text: str, case: str) -> bool:
    """True when the text names the case's distinctive party or its reporter citation."""
    low = re.sub(r"\s+", " ", _s(text).lower())
    party = _party_name(case)
    if party and len(party) >= 5 and re.search(r"(?<![a-z])" + re.escape(party) + r"(?![a-z])",
                                                re.sub(r"[^a-z0-9 ]", " ", low)):
        return True
    cite = _reporter_cite(case)
    return bool(cite) and cite in low


def is_qa_entry(metadata: dict) -> bool:
    """True for a Q&A dataset entry stored in the case_law collection, in either index format."""
    meta = metadata or {}
    return meta.get("doc_type") == "qa_pair" or _s(meta.get("citation")).startswith("VIBER")


def _json_list(value) -> list:
    text = _s(value)
    return json.loads(text) if text else []


def row_targets(gt: dict) -> Tuple[str, List[Citation], List[Citation], List[str]]:
    """(target type, primary citations, all acceptable citations, key cases) for a row.

    Rows from build_ground_truth carry explicit targets. Older ground-truth
    files fall back to correct_act/correct_section, and a row with neither is
    type "NONE", which every metric must leave out.
    """
    ttype = _s(gt.get("target_type"))
    if ttype:
        primary = [tuple(x) for x in _json_list(gt.get("primary_citations"))]
        acceptable = [tuple(x) for x in _json_list(gt.get("acceptable_citations"))]
        return ttype, primary, acceptable, _json_list(gt.get("key_cases"))
    act, sec = canonical_act(gt.get("correct_act")), base_section(gt.get("correct_section"))
    if act and sec:
        return "S", [(act, sec)], [(act, sec)], []
    return "NONE", [], [], []


def match_answer(text: str, gt: dict) -> Optional[float]:
    """Score one answer text against a row: 1.0, 0.5 (right act, wrong section), 0.0, or None.

    None means the row has no citation target and must not be scored.
    Statute rows score 1.0 when any acceptable citation is cited. Case rows
    score 1.0 when any key case is named, and have no partial credit.
    """
    ttype, primary, acceptable, cases = row_targets(gt)
    if ttype == "C":
        return 1.0 if any(case_cited(text, c) for c in cases) else 0.0 if cases else None
    if ttype != "S" or not acceptable:
        return None
    if any(statute_cited(text, act, sec) for act, sec in acceptable):
        return 1.0
    if any(act_cited(text, act) for act, _ in primary):
        return 0.5
    return 0.0


def build_ground_truth(key_path: str, ground_truth_path: str,
                       apply_section_lookup_fixes: bool = False) -> pd.DataFrame:
    """Ground-truth table for the metrics engine, with targets from the answer key.

    Section Lookup rows keep the original file's act and section (the key's
    sheet for them was not reviewed) and get an empty answer summary, so the
    completeness metric compares against the statute text instead of the
    template sentence in the original file. All other rows take targets from
    the key's "Draft key" sheet plus CORRECTIONS.

    Raises ValueError if a key row's query does not match the ground-truth row.
    """
    gt = pd.read_excel(ground_truth_path, sheet_name=0, dtype={"correct_section": str})
    key = pd.read_excel(key_path, sheet_name="Draft key", dtype=str).set_index("Query ID")
    rows = []
    for _, row in gt.iterrows():
        rec = row.to_dict()
        qid = rec["query_id"]
        if qid in key.index:
            k = key.loc[qid]
            if re.sub(r"\s+", " ", _s(k["Query"]).lower()) != re.sub(r"\s+", " ", _s(rec["query_text"]).lower()):
                raise ValueError(f"{qid}: key query does not match the ground-truth query")
            fix = CORRECTIONS.get(qid, {})
            ttype = fix.get("type", _s(k["Type"]))
            default_act = canonical_act(k["Draft: primary act"])
            primary: Set[Citation] = set()
            acceptable: Set[Citation] = set()
            cases: List[str] = []
            if ttype == "S":
                primary = parse_citations(
                    fix.get("primary", f'{_s(k["Draft: primary act"])} {_s(k["Draft: primary section"])}'),
                    default_act)
                acceptable = primary | parse_citations(fix.get("also", _s(k["Draft: also acceptable"])), default_act)
                if not primary:
                    ttype = "O"
            elif ttype == "C":
                cases = [c.strip() for c in _s(k["Draft: key cases"]).split(";") if c.strip()]
            first = sorted(primary)[0] if primary else ("", "")
            rec.update(
                target_type=ttype,
                primary_citations=json.dumps(sorted(primary)),
                acceptable_citations=json.dumps(sorted(acceptable)),
                key_cases=json.dumps(cases),
                correct_act=first[0],
                correct_section=first[1],
                correct_citation=(f"{first[0]} Section {first[1]}" if first[0] else (cases[0] if cases else "")),
                correct_answer_summary=_s(k["Draft: answer note"]),
                target_source="answer key" + (" (advocate correction)" if fix else ""),
            )
        else:
            act_raw = SECTION_LOOKUP_FIXES.get(qid, rec.get("correct_act")) if apply_section_lookup_fixes \
                else rec.get("correct_act")
            act, sec = canonical_act(act_raw), base_section(rec.get("correct_section"))
            cites = [(act, sec)] if act and sec else []
            rec.update(
                target_type="S" if cites else "NONE",
                primary_citations=json.dumps(cites),
                acceptable_citations=json.dumps(cites),
                key_cases=json.dumps([]),
                correct_act=act,
                correct_section=sec,
                correct_citation=f"{act} Section {sec}" if cites else "",
                correct_answer_summary="",
                target_source="original ground truth (Section Lookup)",
            )
        rows.append(rec)
    out = pd.DataFrame(rows)
    out["query"] = out["query_text"]
    return out


def scored_rows(frame: pd.DataFrame) -> Iterable[int]:
    """Positions of rows that have a citation target."""
    return [i for i, r in enumerate(frame.to_dict("records")) if row_targets(r)[0] in ("S", "C")]


def write_ground_truth(frame: pd.DataFrame, out_path: str) -> None:
    """Save the table in the layout run_evaluation.load_ground_truth reads.

    The 'query' column is dropped because the loader renames query_text to
    query, and a second column of that name would break the frame.
    """
    frame.drop(columns=["query"], errors="ignore").to_excel(
        out_path, sheet_name="Ground Truth Dataset", index=False)


def main() -> None:
    """Build the ground-truth workbook from the answer key."""
    import argparse
    from collections import Counter

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--key", required=True, help="answer key workbook (sheet 'Draft key')")
    ap.add_argument("--ground-truth", default="evaluation/ground_truth_verified_393_ready.xlsx")
    ap.add_argument("--out", default="evaluation/ground_truth_lexeval_key_393.xlsx")
    ap.add_argument("--section-lookup-fixes", action="store_true",
                    help="apply the three BNSS act fixes the key flags but the advocate did not decide")
    args = ap.parse_args()
    frame = build_ground_truth(args.key, args.ground_truth, args.section_lookup_fixes)
    write_ground_truth(frame, args.out)
    print(f"wrote {args.out}: {len(frame)} rows, target types {dict(Counter(frame['target_type']))}")


if __name__ == "__main__":
    main()
