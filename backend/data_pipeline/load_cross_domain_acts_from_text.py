"""
Load cross-domain bare acts from plain-text section files into ChromaDB.

Source folder:
  backend/data/cross_domain_acts/*.txt

Format per file:
  ACT_NAME: <full act name>
  SHORT_NAME: <short code>

  [SECTION <num>] <title>
  <body line 1>
  <body line 2>

This loader follows the same section-level chunking approach used for criminal acts:
one section -> one document with metadata + embedding_text.
"""

from __future__ import annotations

import re
from pathlib import Path
import chromadb


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "cross_domain_acts"
CHROMA_PATH = ROOT / "chroma_db"
COLLECTION_NAME = "bare_acts"


def parse_act_file(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")

    act_match = re.search(r"^ACT_NAME:\s*(.+)$", raw, re.MULTILINE)
    short_match = re.search(r"^SHORT_NAME:\s*(.+)$", raw, re.MULTILINE)
    if not act_match or not short_match:
        raise ValueError(f"Missing ACT_NAME/SHORT_NAME header in {path}")

    act_name = act_match.group(1).strip()
    short_name = short_match.group(1).strip()

    pattern = re.compile(
        r"\[SECTION\s+([0-9A-Za-z]+)\]\s*(.+?)\n(.*?)(?=\n\[SECTION\s+[0-9A-Za-z]+\]|\Z)",
        re.DOTALL,
    )

    sections = []
    for m in pattern.finditer(raw):
        sec = m.group(1).strip()
        title = m.group(2).strip()
        body = " ".join(line.strip() for line in m.group(3).strip().splitlines() if line.strip())
        full_text = f"Section {sec} {title}. {body}".strip()

        sections.append(
            {
                "id": f"{short_name}_{sec}",
                "act_name": act_name,
                "short_name": short_name,
                "section_number": sec,
                "section_title": title,
                "full_text": full_text,
                "source": f"plain_text:{path.name}",
                "priority": "HIGH",
                "embedding_text": f"{act_name} Section {sec}. {title}. {body}",
            }
        )

    return sections


def load_into_chroma(section_docs: list[dict]):
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        col = client.get_collection(COLLECTION_NAME)
    except Exception:
        col = client.create_collection(COLLECTION_NAME)

    ids = [d["id"] for d in section_docs]
    docs = [d["embedding_text"] for d in section_docs]
    metas = [
        {
            k: v
            for k, v in d.items()
            if k != "embedding_text" and isinstance(v, (str, int, float, bool)) and v is not None
        }
        for d in section_docs
    ]

    col.upsert(ids=ids, documents=docs, metadatas=metas)


def main():
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Source directory not found: {SOURCE_DIR}")

    files = sorted(SOURCE_DIR.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt source files found in {SOURCE_DIR}")

    all_sections = []
    for fp in files:
        parsed = parse_act_file(fp)
        all_sections.extend(parsed)
        print(f"[parse] {fp.name}: {len(parsed)} sections")

    load_into_chroma(all_sections)
    print(f"[load] upserted {len(all_sections)} sections into {COLLECTION_NAME} at {CHROMA_PATH}")


if __name__ == "__main__":
    main()
