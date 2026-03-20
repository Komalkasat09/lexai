"""
Check what embedding function the collections are using
"""
import chromadb

client = chromadb.PersistentClient(path="./legal_research_db")

collections = ["bare_acts", "case_law", "amendments", "overruling_map"]

for coll_name in collections:
    try:
        coll = client.get_collection(coll_name)
        metadata = coll.metadata
        print(f"\n{coll_name}:")
        print(f"  Count: {coll.count()}")
        print(f"  Metadata: {metadata}")
        
        # Try to get embedding function info
        if hasattr(coll, '_embedding_function'):
            print(f"  Embedding function: {type(coll._embedding_function).__name__}")
            if hasattr(coll._embedding_function, 'model_name'):
                print(f"  Model: {coll._embedding_function.model_name}")
        
    except Exception as e:
        print(f"\n{coll_name}: ERROR - {e}")
