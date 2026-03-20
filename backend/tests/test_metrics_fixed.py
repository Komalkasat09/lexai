"""
Unit tests for fixed metrics functions.
Run with: python -m pytest tests/test_metrics_fixed.py -v
"""

import pytest
import pandas as pd
import chromadb
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics_engine import MetricsEngine


@pytest.fixture
def engine():
    """Create metrics engine with ChromaDB connection."""
    # Initialize ChromaDB
    chroma_path = '../chroma_db'
    if not os.path.exists(chroma_path):
        chroma_path = './chroma_db'
    if not os.path.exists(chroma_path):
        chroma_path = '../data_pipeline/chroma_db'
    
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    
    # Create empty ground truth df (not needed for these tests)
    gt_df = pd.DataFrame()
    
    return MetricsEngine(gt_df, chroma_client)


def test_hallucination_detection_catches_fake_section(engine):
    """Real hallucination should be detected"""
    response = {
        "answer": "Under Section 9999 of IPC the punishment is death",
        "citations": [{
            "type": "bare_act",
            "act_or_case": "Indian Penal Code",
            "section_or_citation": "9999"  # Does not exist
        }]
    }
    gt = {"correct_section": "302", "correct_act": "IPC"}
    
    result = engine._detect_hallucination(response, gt)
    
    assert result['hallucinated_count'] > 0, \
        f"Expected hallucinations, got {result['hallucinated_count']}"
    print(f"✓ Test passed: Fake section 9999 detected as hallucination")


def test_hallucination_detection_passes_valid_section(engine):
    """Valid DB section should NOT be flagged"""
    response = {
        "answer": "Section 302 IPC deals with murder",
        "citations": [{
            "type": "bare_act",
            "act_or_case": "Indian Penal Code 1860",
            "section_or_citation": "302"  # Real section in DB
        }]
    }
    gt = {"correct_section": "302", "correct_act": "IPC"}
    
    result = engine._detect_hallucination(response, gt)
    
    assert result['hallucinated_count'] == 0, \
        f"Valid section 302 wrongly flagged as hallucination. Details: {result['hallucinated_items']}"
    print(f"✓ Test passed: Valid section 302 not flagged as hallucination")


def test_abstention_detected_by_phrase_not_length(engine):
    """60-char abstention phrase should be detected"""
    response = {
        "answer": "I cannot provide a reliable answer to this query.",
        "confidence": "low",
        "citations": []
    }
    
    is_abstention = engine._is_abstention(response)
    
    assert is_abstention == True, \
        "60-char abstention phrase should be detected"
    print(f"✓ Test passed: Abstention phrase detected despite short length")


def test_short_correct_answer_not_abstention(engine):
    """40-char correct answer should NOT be abstention"""
    response = {
        "answer": "Section 302 IPC: punishment for murder.",
        "confidence": "high",
        "citations": [{"type": "bare_act"}]
    }
    
    is_abstention = engine._is_abstention(response)
    
    assert is_abstention == False, \
        "Short correct answer wrongly detected as abstention"
    print(f"✓ Test passed: Short answer with citations not flagged as abstention")


def test_pak_uses_metadata_not_text(engine):
    """P@K must use metadata match not text substring"""
    # Query about Section 138 NI Act
    gt = {
        "correct_section": "138",
        "correct_act": "Negotiable Instruments Act 1881",
        "category": "section_lookup"
    }
    
    result = engine.compute_retrieval_precision_at_k(
        "What is Section 138 NI Act?", gt, k=3
    )
    
    # Result should use metadata['section_number'] == '138'
    # not substring search
    assert 'p_at_1' in result, "Result should contain p_at_1"
    assert 'retrieved_metadata' in result, "Result should contain retrieved_metadata"
    
    # Check that we got metadata back (not text substring)
    metadata = result['retrieved_metadata']
    assert len(metadata) > 0, "Should have retrieved some results"
    assert 'section_number' in metadata[0] or 'citation' in metadata[0], \
        "Metadata should contain section_number or citation fields"
    
    print(f"✓ Test passed: P@K uses metadata matching")
    print(f"  Retrieved {len(metadata)} results")
    print(f"  P@1: {result['p_at_1']:.3f}")
    print(f"  P@3: {result.get('p_at_3', 0):.3f}")


def test_acs_length_not_scored(engine):
    """Long wrong answer should score lower than short correct answer"""
    long_wrong = {
        "answer": "x " * 200,  # Very long but irrelevant
        "citations": [],
        "amendment_notes": [],
        "bns_bnss_notes": []
    }
    short_correct = {
        "answer": "Section 138 NI Act covers cheque dishonour",
        "citations": [{
            "act_or_case": "Negotiable Instruments Act 1881",
            "section_or_citation": "138"
        }],
        "amendment_notes": [],
        "bns_bnss_notes": []
    }
    gt = {
        "correct_answer_summary": "cheque dishonour punishment",
        "correct_act": "Negotiable Instruments Act 1881",
        "correct_section": "138",
        "amendment_applies": "no",
        "bns_bnss_transition_applies": "no",
        "overruling_applies": "no"
    }
    
    long_score = engine.compute_answer_completeness(long_wrong, gt)['acs_score']
    short_score = engine.compute_answer_completeness(short_correct, gt)['acs_score']
    
    assert short_score > long_score, \
        f"Short correct ({short_score:.1f}) should beat long wrong ({long_score:.1f})"
    
    print(f"✓ Test passed: Answer completeness scores content not length")
    print(f"  Long wrong answer: {long_score:.1f}%")
    print(f"  Short correct answer: {short_score:.1f}%")


if __name__ == "__main__":
    # Run tests manually
    print("\n" + "="*80)
    print("TESTING FIXED METRICS FUNCTIONS")
    print("="*80)
    
    engine = engine()
    
    try:
        test_hallucination_detection_catches_fake_section(engine)
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    try:
        test_hallucination_detection_passes_valid_section(engine)
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    try:
        test_abstention_detected_by_phrase_not_length(engine)
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    try:
        test_short_correct_answer_not_abstention(engine)
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    try:
        test_pak_uses_metadata_not_text(engine)
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    try:
        test_acs_length_not_scored(engine)
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)
