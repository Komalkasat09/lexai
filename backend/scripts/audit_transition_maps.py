"""Check the IPC->BNS and CrPC->BNSS maps against the texts of the sections.

For every entry, compares the old section's text with every section of the
new code (TF-IDF cosine) and reports entries whose mapped section is not
among the three closest texts. An entry is called a clear error when the
closest text scores at least --strong and the mapped one at most --weak;
those are the entries corrected in retrieval/smart_retriever.py.

Run from backend/ against a built index:

    python scripts/audit_transition_maps.py --index legal_research_db_clean
"""
import argparse
import re
import sys
from pathlib import Path

import chromadb
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from retrieval.smart_retriever import CRPC_BNSS_MAP, IPC_BNS_MAP  # noqa: E402

PAIRS = [
    ("Indian Penal Code 1860", "Bharatiya Nyaya Sanhita 2023", IPC_BNS_MAP, "bns"),
    ("Code of Criminal Procedure 1973", "Bharatiya Nagarik Suraksha Sanhita 2023", CRPC_BNSS_MAP, "bnss"),
]


def section_texts(collection, act):
    """{section number: first 600 characters of its text} for one act."""
    got = collection.get(where={"act_name": act}, include=["metadatas"])
    return {m["section_number"]: re.sub(r"^\d+[A-Z]*\.\s*", "", m.get("full_text", ""))[:600]
            for m in got["metadatas"]}


def audit(collection, src_act, dst_act, mapping, key, strong, weak):
    """Print the audit for one map; return the clear errors as (old, mapped, best)."""
    src, dst = section_texts(collection, src_act), section_texts(collection, dst_act)
    dst_keys = list(dst)
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    vec.fit(list(src.values()) + list(dst.values()))
    dst_matrix = vec.transform([dst[k] for k in dst_keys])
    confirmed, flagged, clear, unchecked = 0, [], [], 0
    for old, info in mapping.items():
        target = str(info[key]).split("(")[0].strip()
        if old not in src or target not in dst:
            unchecked += 1
            continue
        sims = (vec.transform([src[old]]) @ dst_matrix.T).toarray()[0]
        order = np.argsort(-sims)
        best = dst_keys[order[0]]
        if target in [dst_keys[i] for i in order[:3]]:
            confirmed += 1
            continue
        mapped_sim, best_sim = float(sims[dst_keys.index(target)]), float(sims[order[0]])
        flagged.append((old, target, best, mapped_sim, best_sim))
        if best_sim >= strong and mapped_sim <= weak:
            clear.append((old, target, best))
    print(f"\n{src_act} -> {dst_act}: {len(mapping)} entries, {confirmed} confirmed, "
          f"{len(flagged)} flagged ({len(clear)} clear errors), {unchecked} not checkable")
    for old, target, best, mapped_sim, best_sim in flagged:
        mark = "CLEAR" if (old, target, best) in clear else "check"
        print(f"  [{mark}] {old} -> {target} (sim {mapped_sim:.2f}); closest text {best} (sim {best_sim:.2f})")
    return clear


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=str(BACKEND / "legal_research_db_clean"))
    ap.add_argument("--strong", type=float, default=0.5)
    ap.add_argument("--weak", type=float, default=0.2)
    args = ap.parse_args()
    collection = chromadb.PersistentClient(path=args.index).get_collection("bare_acts")
    clear = [c for pair in PAIRS for c in audit(collection, *pair, args.strong, args.weak)]
    print(f"\n{len(clear)} clear errors")
    sys.exit(1 if clear else 0)


if __name__ == "__main__":
    main()
