"""
Quick test of hybrid retrieval with the migrated database
"""
import sys
import os
sys.path.append('/Users/komalkasat09/Desktop/legal-website/backend')

from database.chroma_setup import LegalResearchDB
from retrieval.smart_retriever import SmartRetriever

def test_hybrid_retrieval():
    """Test hybrid retrieval on migrated database."""
    
    print("\n" + "="*80)
    print("HYBRID RETRIEVAL TEST - Migrated Database")
    print("="*80)
    
    # Initialize database from data_pipeline directory
    db_path = "/Users/komalkasat09/Desktop/legal-website/backend/data_pipeline/chroma_db"
    print(f"\nDatabase: {db_path}")
    
    db = LegalResearchDB(persist_directory=db_path)
    
    # Show stats
    print(f"\n📊 Database Stats:")
    print(f"  Bare Acts: {db.bare_acts_collection.count()} sections")
    print(f"  Case Law: {db.case_law_collection.count()} documents")
    print(f"  Amendments: {db.amendments_collection.count()}")
    print(f"  Overrulings: {db.overruling_map_collection.count()}")
    
    # Initialize SmartRetriever with hybrid=True
    print(f"\n🚀 Initializing SmartRetriever with hybrid retrieval...")
    retriever = SmartRetriever(db, use_hybrid=True)
    
    # Test queries
    test_queries = [
        "Section 138 Negotiable Instruments Act",
        "punishment for rape under BNS",
        "Section 420 IPC cheating"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")
        
        result = retriever.retrieve(query)
        
        print(f"\n📋 Query Type: {result['query_type']}")
        print(f"🎯 Confidence: {result.get('confidence_level', 'N/A')}")
        print(f"\n📚 Bare Acts Retrieved: {len(result['bare_acts'])}")
        
        for i, act in enumerate(result['bare_acts'][:3], 1):
            meta = act['metadata']
            conf = act.get('confidence_score', 0)
            print(f"  {i}. {meta.get('act_name', 'N/A')} Section {meta.get('section_number', 'N/A')}")
            print(f"     Confidence: {conf:.3f}")
            if 'bns_transition' in act:
                print(f"     ⚠️  {act['bns_transition']['note'][:80]}...")
        
        print(f"\n⚖️  Case Law Retrieved: {len(result.get('case_laws', []))}")
        for i, case in enumerate(result.get('case_laws', [])[:2], 1):
            meta = case.get('metadata', {})
            conf = case.get('confidence_score', 0)
            print(f"  {i}. {meta.get('case_name', 'N/A')[:50]}")
            print(f"     Citation: {meta.get('citation', 'N/A')}")
            print(f"     Confidence: {conf:.3f}")
            if case.get('is_overruled'):
                print(f"     {case.get('warning', '')}")
    
    print(f"\n{'='*80}")
    print("✅ HYBRID RETRIEVAL TEST COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    test_hybrid_retrieval()
