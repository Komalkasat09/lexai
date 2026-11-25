"""Build a clean Chroma index for the LexAI rerun, in a new directory.

The index the 393-query run used held 59 statute sections, and the larger
legal_research_db holds several acts whose text is not the act on the label.
This script builds a fresh index from the sources that check out, embedded
with the model the retriever queries with. It never modifies an existing
index: it refuses to write into a directory that already exists.

Run from backend/ with the backend virtualenv:

    python scripts/build_clean_index.py --dry-run
    python scripts/build_clean_index.py --out legal_research_db_clean

Statute sources (bare_acts)
    legal_research_db (repo root)   IPC, CrPC, Indian Evidence Act, HMA,
                                    Limitation Act, Consumer Protection Act,
                                    NI Act
    Desktop backup bare_acts/*.json BNS, BNSS, BSA, the DV Act, and the IPC and
                                    NI Act sections missing from the above
    Left out, because the stored text is a different document:
        "Companies Act 2013"  is the Income-tax Act 1961
        "IT Act 2000"         is a copy of IPC sections
        "Arbitration Act"     is the 1927 Geneva Convention
        "CPC", "TPA"          are paragraphs from court judgments

Case-law source (case_law)
    The 12,800 viber1/indian-law-dataset Q&A pairs, relabelled as Q&A so the
    pipeline cannot cite them as judgments. The seven placeholder cases
    (e.g. "State of Maharashtra v. Rajesh Kumar, AIR 2019 SC 1234") and one
    unlabelled fragment are dropped.

amendments and overruling_map are created empty: the only stored amendment
(IPC 420 by the Criminal Law (Amendment) Act 2013) is not a real amendment.
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "data_pipeline"))

from hindi_heading_utils import build_embedding_text_with_headings, derive_hindi_heading  # noqa: E402

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
HOME_INDEX = BACKEND.parent / "legal_research_db"
DESKTOP = Path.home() / "Desktop/legal-website/backend"
BACKUP_ACTS = DESKTOP / "data_pipeline/data/backup/bare_acts"
CASE_LAW_INDEX = DESKTOP / "legal_research_db"

HOME_ACTS_KEPT = {
    "Indian Penal Code 1860",
    "Code of Criminal Procedure 1973",
    "Indian Evidence Act 1872",
    "Hindu Marriage Act 1955",
    "Limitation Act 1963",
    "Consumer Protection Act 2019",
    "Negotiable Instruments Act 1881",
}
HOME_ACTS_DROPPED = {
    "Companies Act 2013": "text is the Income-tax Act 1961",
    "Information Technology Act 2000": "text is a copy of IPC sections",
    "Arbitration and Conciliation Act 1996": "text is the 1927 Geneva Convention",
    "Code of Civil Procedure 1908": "text is paragraphs from a tax tribunal order",
    "Transfer of Property Act 1882": "text is paragraphs from a writ judgment",
}
# Backup files added whole, or only for sections the home index lacks.
BACKUP_WHOLE = ["BNS.json", "BNSS.json", "BSA.json", "PWDVA.json"]
BACKUP_FILL = ["IPC.json", "NIA.json"]
REPLACED_BY = {
    "Indian Penal Code 1860": "Bharatiya Nyaya Sanhita 2023",
    "Code of Criminal Procedure 1973": "Bharatiya Nagarik Suraksha Sanhita 2023",
    "Indian Evidence Act 1872": "Bharatiya Sakshya Adhiniyam 2023",
}
QA_CASE_NAME = "Legal Q&A reference (not a judgment)"
SCHEDULE_ROW = re.compile(r"^\s*(The (owner|person)\b|Sedition\s+Imprisonment\b)")


def clean_pdf_text(text):
    """Drop the repeated first line the 2023-code PDF extraction left in.

    '103. (1) Whoever commits...\\n(1) Whoever commits...' keeps only the first.
    """
    lines = text.split("\n")
    if len(lines) > 1:
        first = re.sub(r"^\d+[A-Z]*\.\s*", "", lines[0]).strip()
        if first and lines[1].strip() == first:
            del lines[1]
    return "\n".join(lines).strip()


def str_meta(meta):
    """Chroma accepts only str/int/float/bool values; drop None and stringify the rest."""
    out = {}
    for k, v in meta.items():
        if v is None or v == "":
            continue
        out[k] = v if isinstance(v, (str, int, float, bool)) else json.dumps(v)
    return out


def is_schedule_row(text):
    """True for text copied from a Code's tables rather than a section.

    CrPC entries such as 482 hold rows of the compounding table ("The person
    to whom loss or injury is caused by such use. Counterfeiting a ...") or the
    First Schedule ("Sedition Imprisonment for life ..."), stored under the
    section number of the IPC offence they describe.
    """
    return bool(SCHEDULE_ROW.match(text or ""))


def load_home_sections(client):
    col = client.get_collection("bare_acts")
    got = col.get(include=["documents", "metadatas"])
    rows = []
    for doc_id, doc, meta in zip(got["ids"], got["documents"], got["metadatas"]):
        if meta.get("act_name") in HOME_ACTS_KEPT:
            rows.append(dict(id=doc_id, document=doc, metadata=dict(meta)))
    return rows


def repair_schedule_rows(rows):
    """Replace section entries holding schedule text with the genuine section, or drop them.

    The genuine text comes from the backup JSON for the same act and section,
    taking the first entry that is not itself a schedule row. A section with no
    genuine text (CrPC has no section 124A or 491-508) is dropped.

    Returns:
        (kept rows, {"replaced": [...], "dropped": [...]}) with "<act> <section>" labels.
    """
    backup = {}
    for name in ("CrPC.json", "IPC.json", "IEA.json", "NIA.json"):
        for section in json.loads((BACKUP_ACTS / name).read_text(encoding="utf-8")).get("sections") or []:
            if not is_schedule_row(section.get("full_text")):
                backup.setdefault((section["act_name"], str(section["section_number"])), section)
    kept, report = [], {"replaced": [], "dropped": []}
    for row in rows:
        meta = row["metadata"]
        if not is_schedule_row(meta.get("full_text")):
            kept.append(row)
            continue
        key = (meta["act_name"], str(meta["section_number"]))
        label = f"{key[0]} {key[1]}"
        if key in backup:
            fixed = backup_row(backup[key], "IPC.json")  # IPC/CrPC backups start with a real heading
            fixed["id"] = fixed["metadata"]["id"] = row["id"]
            kept.append(fixed)
            report["replaced"].append(label)
        else:
            report["dropped"].append(label)
    return kept, report


def backup_row(section, source_file):
    act = section["act_name"]
    sec = str(section["section_number"])
    text = clean_pdf_text(section.get("full_text") or "")
    heading_en = ""
    if source_file in BACKUP_FILL:
        # IPC and NI Act backups start with a real marginal heading ("Dacoity with murder.—").
        heading_en = text.split("\n", 1)[0].strip()
    heading_hi = derive_hindi_heading(heading_en)
    replaced_by = REPLACED_BY.get(act, "")
    meta = dict(
        id=section.get("id") or f"{section.get('short_name')}_{sec}",
        act_name=act,
        short_name=section.get("short_name"),
        section_number=sec,
        section_title=heading_en or (section.get("section_title") or "")[:200],
        heading_en=heading_en,
        heading_hi=heading_hi,
        full_text=text,
        punishment=section.get("punishment"),
        priority=section.get("priority"),
        source=section.get("source") or f"backup/{source_file}",
        is_replaced=str(bool(replaced_by)),
        replaced_by_act=replaced_by,
    )
    doc = build_embedding_text_with_headings(act, sec, heading_en, heading_hi, text)
    return dict(id=meta["id"], document=doc, metadata=str_meta(meta))


def load_backup_sections(have):
    """Sections from the backup JSONs, skipping (act, section) pairs already in `have`."""
    rows, skipped = [], Counter()
    for name in BACKUP_WHOLE + BACKUP_FILL:
        data = json.loads((BACKUP_ACTS / name).read_text(encoding="utf-8"))
        sections = data.get("sections") or []
        if name == "PWDVA.json":
            # The first four entries are the Bill's statement of objects, not sections.
            sections = sections[4:]
        for section in sections:
            key = (section["act_name"], str(section["section_number"]))
            if is_schedule_row(section.get("full_text")):
                skipped[f"{name} schedule rows"] += 1
                continue
            if key in have:
                skipped[name] += 1
                continue
            have.add(key)
            rows.append(backup_row(section, name))
    return rows, skipped


def load_case_law(client):
    col = client.get_collection("case_law")
    got = col.get(include=["documents", "metadatas"])
    rows, dropped = [], []
    for doc_id, doc, meta in zip(got["ids"], got["documents"], got["metadatas"]):
        meta = dict(meta or {})
        if meta.get("source") != "huggingface" or not str(meta.get("citation", "")).startswith("VIBER"):
            dropped.append((doc_id, meta.get("case_name"), meta.get("citation")))
            continue
        qa_id = meta.pop("citation")
        for k in ("case_name", "court", "year"):
            meta.pop(k, None)
        meta.update(case_name=QA_CASE_NAME, doc_type="qa_pair", qa_id=qa_id,
                    dataset="viber1/indian-law-dataset", is_overruled=False)
        rows.append(dict(id=doc_id, document=doc, metadata=str_meta(meta)))
    return rows, dropped


def add_rows(collection, rows, model, batch_size=256):
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        docs = [r["document"] for r in batch]
        collection.add(ids=[r["id"] for r in batch], documents=docs,
                       metadatas=[r["metadata"] for r in batch],
                       embeddings=model.encode(docs, show_progress_bar=False).tolist())
        print(f"  {collection.name}: {min(i + batch_size, len(rows))}/{len(rows)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=BACKEND / "legal_research_db_clean")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--manifest", type=Path, default=None,
                    help="where to write the composition report (default: <out>_manifest.json)")
    args = ap.parse_args()

    import chromadb

    # Opening a Chroma directory writes to it (lock rows, segment flushes), so
    # the sources are read from throwaway copies and never touched.
    scratch = Path(tempfile.mkdtemp(prefix="lexai_index_sources_"))
    home_copy = scratch / "home"
    case_copy = scratch / "case_law"
    shutil.copytree(HOME_INDEX, home_copy)
    shutil.copytree(CASE_LAW_INDEX, case_copy)

    home = chromadb.PersistentClient(path=str(home_copy))
    home_rows, schedule_report = repair_schedule_rows(load_home_sections(home))
    have = {(r["metadata"]["act_name"], str(r["metadata"]["section_number"])) for r in home_rows}
    backup_rows, skipped = load_backup_sections(have)
    statute = home_rows + backup_rows
    ids = Counter(r["id"] for r in statute)
    dupes = [i for i, n in ids.items() if n > 1]
    if dupes:
        raise SystemExit(f"duplicate ids in statute rows: {dupes[:10]}")

    case_rows, dropped = load_case_law(chromadb.PersistentClient(path=str(case_copy)))

    manifest = {
        "embedding_model": MODEL_NAME,
        "bare_acts_total": len(statute),
        "bare_acts_by_act": dict(sorted(Counter(r["metadata"]["act_name"] for r in statute).items())),
        "from_home_index": len(home_rows),
        "from_backup": len(backup_rows),
        "backup_sections_already_in_home_index": dict(skipped),
        "acts_left_out": HOME_ACTS_DROPPED,
        "schedule_rows_repaired": schedule_report,
        "case_law_total": len(case_rows),
        "case_law_dropped": [dict(id=i, case_name=n, citation=c) for i, n, c in dropped],
        "amendments_total": 0,
        "overruling_map_total": 0,
    }
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    if args.dry_run:
        return

    if args.out.exists():
        raise SystemExit(f"{args.out} already exists; choose a new --out so nothing is overwritten")
    manifest_path = args.manifest or args.out.with_name(args.out.name + "_manifest.json")

    from database.chroma_setup import LegalResearchDB
    from sentence_transformers import SentenceTransformer

    db = LegalResearchDB(persist_directory=str(args.out))
    model = SentenceTransformer(MODEL_NAME)
    add_rows(db.bare_acts_collection, statute, model)
    add_rows(db.case_law_collection, case_rows, model)
    manifest["built_counts"] = {c.name: c.count() for c in db.client.list_collections()}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nbuilt", args.out, manifest["built_counts"])
    print("wrote", manifest_path)


if __name__ == "__main__":
    main()
