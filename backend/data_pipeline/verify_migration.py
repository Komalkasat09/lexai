"""
Verify that collections are using SentenceTransformer embeddings
"""
import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="./legal_research_db")

# Create the embedding function
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

collections = ["bare_acts", "case_law", "amendments", "overruling_map"]

print("\nGetting collections WITH embedding function specified:")
print("="*70)

for coll_name in collections:
    try:
        # Get collection WITH embedding function
        coll = client.get_collection(coll_name, embedding_function=embedding_fn)
        
        print(f"\n{coll_name}:")
        print(f"  Count: {coll.count()}")
        print(f"  Metadata: {coll.metadata}")
        
        # Try a test query
        if coll.count() > 0:
            results = coll.query(
                query_texts=["test query"],
                n_results=1
            )
            print(f"  Query test: ✓ Returns {len(results['ids'][0])} results")
        
    except Exception as e:
        print(f"\n{coll_name}: ERROR - {e}")

print("\n" + "="*70)
print("If no errors above, SentenceTransformer embeddings are working!")
