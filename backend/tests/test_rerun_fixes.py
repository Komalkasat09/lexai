"""Tests for the rerun fixes: the forced-answer regime keeps low-confidence
context, failed API calls are never saved as answers, and schedule rows are
recognised when building the index."""

import os
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BACKEND)
sys.path.append(os.path.join(BACKEND, "scripts"))

from retrieval.smart_retriever import SmartRetriever  # noqa: E402
import rerun_eval  # noqa: E402
from build_clean_index import clean_pdf_text, is_schedule_row, str_meta  # noqa: E402


class StubDB:
    """Returns fixed results whose confidence scores are all below the thresholds."""

    def __init__(self, score):
        self.score = score

    def _raw(self, prefix, meta):
        return {"ids": [[f"{prefix}_1", f"{prefix}_2"]], "documents": [["text one", "text two"]],
                "metadatas": [[meta, meta]], "distances": [[self.score, self.score]]}

    def query_bare_acts(self, query_text, n_results, act_filter=None):
        return self._raw("BA", {"act_name": "Hindu Marriage Act 1955", "section_number": "13B"})

    def query_case_law(self, **kwargs):
        return self._raw("CL", {"case_name": "Legal Q&A reference (not a judgment)"})

    def check_if_overruled(self, citation):
        return None

    def get_amendments_for_section(self, act_name, section_number):
        return {"ids": [], "metadatas": [], "documents": []}


def _retriever(score):
    retriever = SmartRetriever.__new__(SmartRetriever)
    retriever.db = StubDB(score)
    retriever.use_query_routing = False
    retriever.use_hybrid = False
    retriever.hybrid_retrievers = {}
    retriever.use_bns_middleware = False
    retriever.confidence_high = 0.75
    retriever.confidence_medium = 0.60
    retriever.logged = []
    retriever.log_unanswered_query = lambda **kw: retriever.logged.append(kw)
    return retriever


def test_all_low_confidence_abstains_by_default():
    retriever = _retriever(0.3)
    result = retriever.retrieve("divorce by mutual consent")
    assert result["trigger_uncertainty"] is True
    assert result["bare_acts"] == [] and result["case_laws"] == []
    assert len(retriever.logged) == 1


def test_all_low_confidence_kept_when_asked_and_labelled_low():
    retriever = _retriever(0.3)
    result = retriever.retrieve("divorce by mutual consent", keep_low_confidence=True)
    assert result["trigger_uncertainty"] is True
    assert [r["id"] for r in result["bare_acts"]] == ["BA_1", "BA_2"]
    assert {r["confidence_level"] for r in result["bare_acts"] + result["case_laws"]} == {"LOW"}
    assert result["confidence_level"] == "LOW"
    assert retriever.logged == []


def test_confident_results_unaffected_by_flag():
    plain = _retriever(0.9).retrieve("divorce by mutual consent")
    kept = _retriever(0.9).retrieve("divorce by mutual consent", keep_low_confidence=True)
    assert plain["trigger_uncertainty"] is False and kept["trigger_uncertainty"] is False
    assert [r["id"] for r in plain["bare_acts"]] == [r["id"] for r in kept["bare_acts"]] == ["BA_1", "BA_2"]


# --- run wrapper -------------------------------------------------------------

@pytest.mark.parametrize("response, expected", [
    ({"answer": "Error: All 16 API keys failed: rate limit"}, True),
    ({"answer": "ERROR: timeout", "confidence": "ERROR"}, True),
    ({"answer": "fine", "error": "boom"}, True),
    ({"answer": "[PLACEHOLDER: LexAI response to ...]"}, True),
    ({"answer": "Section 302 IPC prescribes death. Errors in the FIR do not matter."}, False),
    ({"answer": "The error of law in this judgment was corrected on appeal."}, False),
    ({"answer": "Errors in the investigation do not vitiate the trial (Section 465 CrPC)."}, False),
])
def test_is_error_response(response, expected):
    assert rerun_eval.is_error_response(response) is expected


def test_answer_with_retry_retries_then_returns_real_answer(monkeypatch):
    monkeypatch.setattr(rerun_eval.time, "sleep", lambda s: None)
    replies = iter([{"answer": "Error: rate limit"}, {"answer": "Error: rate limit"}, {"answer": "Section 13B HMA"}])
    assert rerun_eval.answer_with_retry(lambda: next(replies), "Q1", "NoRAG") == {"answer": "Section 13B HMA"}


def test_answer_with_retry_gives_up_without_returning_the_error(monkeypatch):
    monkeypatch.setattr(rerun_eval.time, "sleep", lambda s: None)
    calls = []
    result = rerun_eval.answer_with_retry(lambda: calls.append(1) or {"answer": "Error: down"}, "Q1", "LexAI")
    assert result is None
    assert len(calls) == len(rerun_eval.RETRY_WAITS_S) + 1


# --- index build helpers --------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("The person to whom loss or injury is caused by such use.  Counterfeiting a ...", True),
    ("The owner of the property stolen.  Dishonest misappropriation of property.", True),
    ("Sedition  Imprisonment for life and fine, or imprisonment for 3 years", True),
    ("Sedition.—\nWhoever, by words, either spoken or written ...", False),
    ("Saving of inherent powers of High Court. - Nothing in this Code ...", False),
    ("", False),
])
def test_is_schedule_row(text, expected):
    assert is_schedule_row(text) is expected


def test_clean_pdf_text_drops_repeated_first_line_only():
    assert clean_pdf_text("103. (1) Whoever commits murder\n(1) Whoever commits murder\nshall be punished") == \
        "103. (1) Whoever commits murder\nshall be punished"
    assert clean_pdf_text("Short title.\nThis Act may be called") == "Short title.\nThis Act may be called"


def test_str_meta_drops_empty_and_stringifies_structures():
    assert str_meta({"a": None, "b": "", "c": 3, "d": ["x"], "e": True}) == {"c": 3, "d": '["x"]', "e": True}
