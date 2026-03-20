"""
Reindex ChromaDB collections using multilingual embeddings.

Creates new collections with `_ml` suffix by default:
  - bare_acts_ml
  - case_law_ml
  - amendments_ml
  - overruling_map_ml

The script is idempotent via upsert and supports custom DB paths.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_COLLECTIONS = ["bare_acts", "case_law", "amendments", "overruling_map"]


def reindex_collection(
    collection_name: str,
    client: chromadb.PersistentClient,
    model: SentenceTransformer,
    suffix: str = "_ml",
    batch_size: int = 100,
) -> None:
    """Re-embed one collection into `<collection_name><suffix>`."""
    source = client.get_collection(collection_name)
    target_name = f"{collection_name}{suffix}"
    target = client.get_or_create_collection(target_name)

    total = source.count()
    print(f"Reindexing {collection_name} -> {target_name}: {total} documents")

    for offset in range(0, total, batch_size):
        batch = source.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas"],
        )
        ids = batch.get("ids", [])
        docs = batch.get("documents", [])
        metadatas = batch.get("metadatas", [])

        if not ids:
            continue

        embeddings = model.encode(docs, show_progress_bar=False).tolist()

        target.upsert(
            ids=ids,
            documents=docs,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        if ((offset // batch_size) % 10) == 0:
            print(f"  Progress: {min(offset + batch_size, total)}/{total}")

    print(f"  Done: {target.count()} documents indexed in {target_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reindex ChromaDB with multilingual embeddings")
    parser.add_argument(
        "--db-path",
        default="./legal_research_db",
        help="Path to Chroma persistent DB (default: ./legal_research_db)",
    )
    parser.add_argument(
        "--collections",
        nargs="*",
        default=DEFAULT_COLLECTIONS,
        help="Collections to reindex",
    )
    parser.add_argument(
        "--suffix",
        default="_ml",
        help="Suffix for new multilingual collections (default: _ml)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for read/encode/upsert (default: 100)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = str(Path(args.db_path).resolve())
    print(f"Using DB path: {db_path}")
    print(f"Embedding model: {MODEL_NAME}")

    client = chromadb.PersistentClient(
        path=db_path,
        settings=Settings(anonymized_telemetry=False, allow_reset=False),
    )

    model = SentenceTransformer(MODEL_NAME)

    existing = {
        c.name if hasattr(c, 'name') else str(c)
        for c in client.list_collections()
    }
    requested: List[str] = list(args.collections)
    for name in requested:
        if name not in existing:
            print(f"Skipping missing collection: {name}")
            continue
        reindex_collection(
            collection_name=name,
            client=client,
            model=model,
            suffix=args.suffix,
            batch_size=args.batch_size,
        )

    print("\nAll requested collections processed.")
    print(f"Use collections with suffix `{args.suffix}` in retrieval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
