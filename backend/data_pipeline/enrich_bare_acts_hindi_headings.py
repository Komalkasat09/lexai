"""Backfill Hindi heading aliases for existing bare_acts Chroma collection."""

from pathlib import Path
import chromadb

try:
    from data_pipeline.hindi_heading_utils import (
        derive_hindi_heading,
        build_embedding_text_with_headings,
    )
except ModuleNotFoundError:
    from hindi_heading_utils import (
        derive_hindi_heading,
        build_embedding_text_with_headings,
    )


def main() -> None:
    backend_root = Path(__file__).resolve().parent.parent
    env_path = Path(
        __import__("os").environ.get("LEXAI_CHROMA_PATH", "")
    ) if __import__("os").environ.get("LEXAI_CHROMA_PATH") else None

    candidates = []
    if env_path:
        candidates.append(env_path)
    candidates.extend([
        backend_root / "legal_research_db",
        backend_root / "chroma_legal_db",
        backend_root / "chroma_db",
        Path.cwd() / "legal_research_db",
        Path.cwd() / "chroma_legal_db",
        Path.cwd() / "chroma_db",
    ])

    best_path = None
    best_count = -1
    for path in candidates:
        try:
            client = chromadb.PersistentClient(path=str(path))
            col = client.get_collection("bare_acts")
            count = col.count()
            if count > best_count:
                best_count = count
                best_path = path
        except Exception:
            continue

    if best_path is None:
        raise RuntimeError("Could not find a Chroma DB path with bare_acts collection")

    print(f"Using Chroma path: {best_path} (bare_acts={best_count})")
    client = chromadb.PersistentClient(path=str(best_path))
    collection = client.get_collection("bare_acts")

    data = collection.get(include=["documents", "metadatas"])
    ids = data.get("ids", [])
    docs = data.get("documents", [])
    metas = data.get("metadatas", [])

    total = len(ids)
    print(f"Found {total} bare_acts documents")

    batch_ids = []
    batch_docs = []
    batch_metas = []
    updated = 0

    for i, doc_id in enumerate(ids):
        metadata = dict(metas[i] or {})
        original_doc = docs[i] or ""

        section_title = (
            metadata.get("section_title")
            or metadata.get("heading_en")
            or f"Section {metadata.get('section_number', '')}".strip()
        )
        heading_hi = metadata.get("heading_hi") or derive_hindi_heading(section_title)

        new_doc = build_embedding_text_with_headings(
            act_name=str(metadata.get("act_name", "")),
            section_number=str(metadata.get("section_number", "")),
            heading_en=str(section_title),
            heading_hi=str(heading_hi),
            body_preview=original_doc[:1000],
        )

        changed = False
        if metadata.get("heading_en") != section_title:
            metadata["heading_en"] = section_title
            changed = True
        if metadata.get("heading_hi") != heading_hi:
            metadata["heading_hi"] = heading_hi
            changed = True
        if original_doc != new_doc:
            changed = True

        if changed:
            updated += 1
            batch_ids.append(doc_id)
            batch_docs.append(new_doc)
            batch_metas.append(metadata)

        if len(batch_ids) >= 200:
            collection.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
            print(f"Upserted {len(batch_ids)} records at index {i + 1}")
            batch_ids, batch_docs, batch_metas = [], [], []

    if batch_ids:
        collection.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
        print(f"Upserted final {len(batch_ids)} records")

    print(f"Completed. Updated records: {updated}/{total}")


if __name__ == "__main__":
    main()
