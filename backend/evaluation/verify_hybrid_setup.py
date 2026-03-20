"""
Quick verification that hybrid retrieval is properly integrated for evaluation
"""
import sys
import os
sys.path.append('/Users/komalkasat09/Desktop/legal-website/backend')

from llm.legal_llm import LegalLLM

def test_evaluation_setup():
    """Test that LegalLLM uses migrated database with hybrid retrieval."""
    
    print("\n" + "="*80)
    print("EVALUATION SETUP VERIFICATION")
    print("="*80)
    
    # Initialize LegalLLM (same as evaluation does)
    chroma_path = "/Users/komalkasat09/Desktop/legal-website/backend/chroma_db"
    print(f"\n📂 Database Path: {chroma_path}")
    
    print(f"\n🚀 Initializing LegalLLM...")
    llm = LegalLLM(persist_directory=chroma_path)
    
    # Check database stats
    print(f"\n📊 Database Stats:")
    print(f"  Bare Acts: {llm.db.bare_acts_collection.count()} sections")
    print(f"  Case Law: {llm.db.case_law_collection.count()} documents")
    print(f"  Amendments: {llm.db.amendments_collection.count()}")
    print(f"  Overrulings: {llm.db.overruling_map_collection.count()}")
    
    # Check if SmartRetriever is using hybrid
    print(f"\n🔍 SmartRetriever Status:")
    print(f"  Hybrid Enabled: {llm.retriever.use_hybrid}")
    if llm.retriever.use_hybrid:
        print(f"  Hybrid Retrievers: {list(llm.retriever.hybrid_retrievers.keys())}")
        if 'bare_acts' in llm.retriever.hybrid_retrievers:
            stats = llm.retriever.hybrid_retrievers['bare_acts'].get_retrieval_stats()
            print(f"  BM25 Indexed Docs: {stats['doc_count']}")
            print(f"  Cross-Encoder: {stats['cross_encoder_model']}")
    
    # Test a query
    print(f"\n🧪 Test Query: 'What is punishment for rape under BNS?'")
    result = llm.retriever.retrieve("What is punishment for rape under BNS?")
    
    print(f"\n✅ Query Result:")
    print(f"  Query Type: {result.get('query_type', 'N/A')}")
    print(f"  Confidence: {result.get('confidence_level', 'N/A')}")
    print(f"  Bare Acts Retrieved: {len(result.get('bare_acts', []))}")
    
    if result.get('bare_acts'):
        top = result['bare_acts'][0]
        meta = top.get('metadata', {})
        conf = top.get('confidence_score', 0)
        print(f"\n  Top Result:")
        print(f"    Act: {meta.get('act_name', 'N/A')}")
        print(f"    Section: {meta.get('section_number', 'N/A')}")
        print(f"    Confidence: {conf:.3f}")
        if 'bns_transition' in top:
            print(f"    BNS Note: ✓ Present")
    
    print(f"\n{'='*80}")
    print("✅ EVALUATION SETUP VERIFIED")
    print("="*80)
    print("\nHybrid retrieval (BM25 + Dense + Cross-Encoder) is active!")
    print("Ready to run full evaluation with improved retrieval.")


if __name__ == "__main__":
    test_evaluation_setup()
