"""
Migrate ChromaDB collections from DefaultEmbeddingFunction to SentenceTransformer
This is required for hybrid retrieval (BM25 + Dense + Cross-Encoder) to work properly.

Steps:
1. Export all data from existing collections
2. Delete old collections  
3. Recreate with SentenceTransformerEmbeddingFunction
4. Reload all data

WARNING: This will temporarily delete collections. Ensure you have backups!
"""

import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from datetime import datetime
import json
import os
from tqdm import tqdm

def export_collection(client, collection_name: str, backup_dir: str):
    """Export all data from a collection to JSON."""
    print(f"\n📤 Exporting {collection_name}...")
    
    try:
        collection = client.get_collection(collection_name)
        
        # Get all documents
        results = collection.get()
        
        data = {
            "ids": results['ids'],
            "documents": results['documents'],
            "metadatas": results['metadatas'],
            "count": len(results['ids'])
        }
        
        # Save to JSON
        filepath = os.path.join(backup_dir, f"{collection_name}_backup.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Exported {data['count']} documents to {filepath}")
        return data['count']
    
    except Exception as e:
        print(f"  ✗ Failed to export {collection_name}: {e}")
        return 0


def recreate_collection_with_sentence_transformer(client, collection_name: str):
    """Recreate collection with SentenceTransformerEmbeddingFunction."""
    print(f"\n🔄 Recreating {collection_name} with sentence-transformers...")
    
    # Delete old collection
    try:
        client.delete_collection(collection_name)
        print(f"  ✓ Deleted old collection")
    except Exception as e:
        print(f"  ⚠️  Collection doesn't exist or couldn't be deleted: {e}")
    
    # Create new collection with SentenceTransformer
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={
            "description": f"Legal {collection_name} with SentenceTransformer embeddings",
            "created_at": datetime.now().isoformat(),
            "embedding_function": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        }
    )
    
    print(f"  ✓ Created new collection with SentenceTransformer")
    return collection


def reload_collection_data(collection, backup_filepath: str, batch_size: int = 100):
    """Reload data into collection from backup."""
    print(f"\n📥 Reloading data from {backup_filepath}...")
    
    with open(backup_filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    ids = data['ids']
    documents = data['documents']
    metadatas = data['metadatas']
    total = data['count']
    
    print(f"  Found {total} documents to reload")
    
    # Reload in batches
    for i in tqdm(range(0, total, batch_size), desc=f"  Loading batches"):
        batch_ids = ids[i:i+batch_size]
        batch_docs = documents[i:i+batch_size]
        batch_meta = metadatas[i:i+batch_size]
        
        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_meta
        )
    
    final_count = collection.count()
    print(f"  ✓ Reloaded {final_count} documents")
    
    if final_count != total:
        print(f"  ⚠️  Warning: Expected {total} but got {final_count}")


def migrate_database(persist_directory: str = "./chroma_db", backup_dir: str = "./data/backup/migration"):
    """
    Main migration function.
    
    Args:
persist_directory: Path to ChromaDB database
        backup_dir: Directory for backups
    """
    print("\n" + "="*80)
    print("CHROMADB MIGRATION: DEFAULT → SENTENCE-TRANSFORMERS")
    print("="*80)
    print(f"\nDatabase: {persist_directory}")
    print(f"Backups: {backup_dir}")
    
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    # Initialize ChromaDB client
    client = chromadb.PersistentClient(
        path=persist_directory,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=False
        )
    )
    
    collections_to_migrate = ["bare_acts", "case_law", "amendments", "overruling_map"]
    
    # PHASE 1: Export all collections
    print("\n" + "="*80)
    print("PHASE 1: EXPORTING COLLECTIONS")
    print("="*80)
    
    exported_counts = {}
    for coll_name in collections_to_migrate:
        count = export_collection(client, coll_name, backup_dir)
        exported_counts[coll_name] = count
    
    print(f"\n✓ Total exported: {sum(exported_counts.values())} documents")
    
    # PHASE 2: Recreate collections with SentenceTransformer
    print("\n" + "="*80)
    print("PHASE 2: RECREATING COLLECTIONS")
    print("="*80)
    
    new_collections = {}
    for coll_name in collections_to_migrate:
        new_collections[coll_name] = recreate_collection_with_sentence_transformer(client, coll_name)
    
    print(f"\n✓ Recreated {len(new_collections)} collections")
    
    # PHASE 3: Reload data
    print("\n" + "="*80)
    print("PHASE 3: RELOADING DATA")
    print("="*80)
    
    for coll_name in collections_to_migrate:
        backup_file = os.path.join(backup_dir, f"{coll_name}_backup.json")
        reload_collection_data(new_collections[coll_name], backup_file)
    
    # PHASE 4: Verification
    print("\n" + "="*80)
    print("PHASE 4: VERIFICATION")
    print("="*80)
    
    all_good = True
    for coll_name in collections_to_migrate:
        collection = client.get_collection(coll_name)
        final_count = collection.count()
        expected = exported_counts[coll_name]
        
        status = "✓" if final_count == expected else "✗"
        print(f"{status} {coll_name}: {final_count}/{expected} documents")
        
        if final_count != expected:
            all_good = False
        
        # Check embedding function
        if hasattr(collection, '_embedding_function'):
            emb_type = type(collection._embedding_function).__name__
            print(f"   Embedding: {emb_type}")
    
    # Final summary
    print("\n" + "="*80)
    if all_good:
        print("✅ MIGRATION SUCCESSFUL")
        print("="*80)
        print("\nAll collections migrated to SentenceTransformer embeddings!")
        print("Hybrid retrieval (BM25 + Dense + Cross-Encoder) is now enabled.")
        print("\nNext steps:")
        print("  1. Test hybrid retrieval: python test_hybrid_retrieval.py")
        print("  2. Run evaluation: cd ../evaluation && python run_evaluation.py")
    else:
        print("⚠️  MIGRATION COMPLETED WITH WARNINGS")
        print("="*80)
        print("\nSome collections have count mismatches. Check backup files.")
        print(f"Backups located at: {backup_dir}")


if __name__ == "__main__":
    import sys
    
    print("\n⚠️  WARNING: This will recreate all ChromaDB collections!")
    print("   Backups will be created first, but proceed with caution.")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--confirm":
        migrate_database()
    else:
        print("\nTo proceed, run:")
        print("  python migrate_embeddings.py --confirm")
