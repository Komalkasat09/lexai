"""Regression tests for metric fairness and normalization fixes."""

import os
import sys

import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics_engine import MetricsEngine


class FakeBareActsCollection:
    """Tiny in-memory stub that emulates Chroma get(where=...)."""

    def __init__(self, existing_pairs):
        self.existing_pairs = set(existing_pairs)

    def get(self, where=None, include=None):
        and_filters = where.get("$and", []) if isinstance(where, dict) else []
        sec = None
        act = None
        for item in and_filters:
            if "section_number" in item:
                sec = item["section_number"].get("$eq")
            if "act_name" in item:
                act = item["act_name"].get("$eq")
        if (act, sec) in self.existing_pairs:
            return {"ids": ["ok"]}
        return {"ids": []}


def _engine_with_fake_collection(existing_pairs):
    # ground_truth_df/chroma_client are not needed for these unit-level checks
    engine = MetricsEngine(pd.DataFrame(), None)
    engine.bare_acts_collection = FakeBareActsCollection(existing_pairs)
    engine.case_law_collection = None
    return engine


def test_hr_counts_string_citations_as_claims():
    engine = _engine_with_fake_collection(set())

    response = {
        "citations": [
            "the Indian Penal Code Section 420",
            "Section 302 of IPC",
        ]
    }
    gt = {"correct_section": "999", "correct_act": "IPC", "correct_citation": ""}

    hr = engine._detect_hallucination(response, gt)

    assert hr["total_claims"] == 2


def test_hr_section_normalization_avoids_false_positive():
    engine = _engine_with_fake_collection({("Indian Penal Code 1860", "304A")})

    response = {
        "citations": [
            {
                "type": "bare_act",
                "act_or_case": "IPC",
                "section_or_citation": "Section 304A",
            }
        ]
    }
    gt = {"correct_section": "999", "correct_act": "IPC", "correct_citation": ""}

    hr = engine._detect_hallucination(response, gt)

    assert hr["hallucinated_count"] == 0


def test_hr_string_citation_can_match_ground_truth():
    engine = _engine_with_fake_collection(set())

    response = {"citations": ["Indian Penal Code Section 420"]}
    gt = {"correct_section": "420", "correct_act": "IPC", "correct_citation": ""}

    hr = engine._detect_hallucination(response, gt)

    assert hr["hallucinated_count"] == 0
