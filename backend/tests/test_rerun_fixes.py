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


class StubCollection:
    """bare_acts collection holding a fixed set of (act, section) -> text."""

    def __init__(self, sections):
        self.sections = sections
        self.calls = 0

    def get(self, where, include=None):
        self.calls += 1
        act = where["$and"][0]["act_name"]["$eq"]
        sec = where["$and"][1]["section_number"]["$eq"]
        if (act, sec) not in self.sections:
            return {"ids": [], "documents": [], "metadatas": []}
        return {"ids": [f"{act}_{sec}"], "documents": [self.sections[(act, sec)]],
                "metadatas": [{"act_name": act, "section_number": sec}]}


BNS_ACT = "Bharatiya Nyaya Sanhita 2023"


def _ipc_result(section, replaced_by):
    return {"id": f"IPC_{section}", "document": "...", "confidence_level": "HIGH", "confidence_score": 0.8,
            "metadata": {"act_name": "Indian Penal Code 1860", "section_number": section},
            "bns_transition": {"original": f"IPC Section {section}", "replaced_by": replaced_by}}


def test_replacement_sections_are_fetched_once_with_source_confidence():
    retriever = _retriever(0.9)
    retriever.db.bare_acts_collection = StubCollection({(BNS_ACT, "64"): "64. Whoever commits rape ..."})
    already = {"id": "BNS_103", "metadata": {"act_name": BNS_ACT, "section_number": "103"}}
    results = [_ipc_result("376", "BNS Section 64"), _ipc_result("376A", "BNS Section 64"),
               _ipc_result("302", "BNS Section 103"), _ipc_result("311", "Removed in BNS"), already]
    added = retriever._fetch_replacement_sections(results)
    assert [(a["metadata"]["section_number"], a["replaces"], a["confidence_level"]) for a in added] == \
        [("64", "IPC Section 376", "HIGH")]
    assert added[0]["document"] == "64. Whoever commits rape ..."


def test_replacement_missing_from_index_adds_nothing():
    retriever = _retriever(0.9)
    retriever.db.bare_acts_collection = StubCollection({})
    assert retriever._fetch_replacement_sections([_ipc_result("376", "BNS Section 64")]) == []


def test_replacement_respects_limit():
    retriever = _retriever(0.9)
    retriever.db.bare_acts_collection = StubCollection({(BNS_ACT, str(n)): "x" for n in range(1, 10)})
    results = [_ipc_result(str(300 + n), f"BNS Section {n}") for n in range(1, 10)]
    assert len(retriever._fetch_replacement_sections(results, limit=3)) == 3


# --- LLM context ---------------------------------------------------------------

def test_llm_context_carries_section_text_transition_note_and_amendment():
    from llm.legal_llm import LegalLLM

    retrieval = {
        "query_type": "section_lookup", "confidence_level": "HIGH", "has_bns_bnss_notes": True,
        "bare_acts": [{
            "document": "Indian Penal Code 1860 Section 302 Punishment for murder.— Whoever commits murder",
            "metadata": {"act_name": "Indian Penal Code 1860", "section_number": "302"},
            "confidence_score": 0.9,
            "bns_transition": {"note": "IPC Section 302 has been replaced by BNS Section 103."},
        }],
        "case_laws": [{
            "document": "Question: What is bail? Answer: Release pending trial.",
            "metadata": {"case_name": "Legal Q&A reference (not a judgment)"},
            "confidence_score": 0.7,
            "ipc_sections_mentioned": ["IPC 420 → BNS 318"],
        }],
        "amendments": [{"document": "Old text ... New text ...",
                        "metadata": {"amendment_act": "Example (Amendment) Act 2018", "amendment_year": 2018,
                                     "act_name": "Indian Penal Code 1860", "section_number": "376"}}],
        "stats": {},
    }
    context = LegalLLM._format_retrieval_context(None, retrieval)
    assert "Whoever commits murder" in context
    assert "Release pending trial." in context
    assert "No text available" not in context
    assert "TRANSITION: IPC Section 302 has been replaced by BNS Section 103." in context
    assert "IPC 420 → BNS 318" in context
    assert "Amendment: Example (Amendment) Act 2018" in context and "Old text ... New text ..." in context


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
