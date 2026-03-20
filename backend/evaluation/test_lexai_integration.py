"""
Quick test to verify LexAI integration in evaluation framework.
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_evaluation import EvaluationRunner

def test_lexai_integration():
    """Test LexAI integration with a few sample queries."""
    print("=" * 60)
    print("LexAI Integration Test")
    print("=" * 60)
    
    # Sample queries
    test_queries = [
        "What is Section 420 IPC?",
        "What is the punishment for murder?",
        "Has Section 377 been struck down?"
    ]
    
    # Initialize evaluation runner
    runner = EvaluationRunner()
    
    # Run LexAI on test queries
    print("\nRunning LexAI on test queries...")
    responses = runner.run_lexai(test_queries)
    
    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    for i, (query, response) in enumerate(zip(test_queries, responses), 1):
        print(f"\n[Query {i}]: {query}")
        print(f"[Confidence]: {response.get('confidence', 'N/A')}")
        print(f"[Answer]: {response.get('answer', 'N/A')[:200]}...")
        
        # Show structured response
        struct = response.get('structured_response', {})
        if struct.get('act_cited'):
            print(f"[Cited Act]: {struct['act_cited']}")
        if struct.get('section_cited'):
            print(f"[Cited Section]: {struct['section_cited']}")
        
        # Show warnings
        warnings = response.get('warnings', [])
        if warnings:
            print(f"[Warnings]: {', '.join(warnings)}")
        
        print("-" * 60)
    
    print("\n✅ LexAI integration test complete!")
    print(f"   Processed {len(responses)} queries successfully")

if __name__ == "__main__":
    test_lexai_integration()
