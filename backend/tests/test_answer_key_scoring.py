"""Tests for answer-key scoring: no free marks for rows without a target,
exact act lookup, and the citation-matching rules the metrics share."""

import json
import os
import sys

import pandas as pd
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.answer_key import (  # noqa: E402
    base_section,
    canonical_act,
    case_cited,
    is_qa_entry,
    match_answer,
    parse_citations,
    row_targets,
    statute_cited,
)
from evaluation.metrics_engine import MetricsEngine  # noqa: E402

IPC = "Indian Penal Code 1860"
BNS = "Bharatiya Nyaya Sanhita 2023"
BNSS = "Bharatiya Nagarik Suraksha Sanhita 2023"


def statute_row(primary, also=(), category="Punishment Queries"):
    acceptable = sorted(set(primary) | set(also))
    return {
        "query_id": "Q1", "category": category, "target_type": "S",
        "primary_citations": json.dumps(sorted(primary)),
        "acceptable_citations": json.dumps(acceptable),
        "key_cases": "[]",
    }


def case_row(cases):
    return {"query_id": "Q2", "category": "Case Law Search", "target_type": "C",
            "primary_citations": "[]", "acceptable_citations": "[]",
            "key_cases": json.dumps(cases)}


OPEN_ROW = {"query_id": "Q3", "category": "Amendment Specific", "target_type": "O",
            "primary_citations": "[]", "acceptable_citations": "[]", "key_cases": "[]"}
LEGACY_EMPTY_ROW = {"query_id": "Q4", "category": "Case Law Search", "correct_act": float("nan"),
                    "correct_section": float("nan"), "correct_citation": "Section nan, nan"}


# --- act lookup -------------------------------------------------------------

@pytest.mark.parametrize("name, expected", [
    ("BNSS", BNSS),
    ("BNSS 2023", BNSS),
    ("BNS", BNS),
    ("IPC", IPC),
    ("Evidence Act", "Indian Evidence Act 1872"),
    ("Constitution of India", "Constitution of India"),
    ("Juvenile Justice (Care and Protection of Children) Act 2015",
     "Juvenile Justice (Care and Protection of Children) Act 2015"),
])
def test_canonical_act_is_exact(name, expected):
    assert canonical_act(name) == expected


@pytest.mark.parametrize("fragment, expected", [
    ("BNSS 2023", BNSS),
    ("BNS 2023", BNS),
    ("Indian Penal Code 186", IPC),
    ("CRPC", "Code of Criminal Procedure 1973"),
])
def test_engine_resolve_act_prefers_longest_prefix(fragment, expected):
    assert MetricsEngine._resolve_act_name(fragment) == expected


# --- parsing the key --------------------------------------------------------

def test_parse_citations_handles_ranges_years_and_bare_sections():
    assert parse_citations("BNSS ss.289 to 291; CrPC 265A to 265C") == {
        (BNSS, "289"), (BNSS, "290"), (BNSS, "291"),
        ("Code of Criminal Procedure 1973", "265a"),
        ("Code of Criminal Procedure 1973", "265b"),
        ("Code of Criminal Procedure 1973", "265c"),
    }
    assert parse_citations("Companies Act 2013 s.448") == {("Companies Act 2013", "448")}
    assert parse_citations("s.18A", default_act="SC/ST Act") == {("SC/ST Act", "18a")}
    assert parse_citations("Amendment Acts of 2015, 2017, 2019") == set()


def test_base_section_strips_subsections_and_prefixes():
    assert base_section("Section 310(3)") == "310"
    assert base_section("498A") == "498a"
    assert base_section("2(1)(c)") == "2"
    assert base_section("420.0") == "420"


# --- matching ---------------------------------------------------------------

@pytest.mark.parametrize("text, act, section, expected", [
    ("Section 302 of the Indian Penal Code prescribes death", IPC, "302", True),
    ("[Section 420, Indian Penal Code 1860]", IPC, "420", True),
    ("Section 103(1) BNS", BNS, "103", True),
    ("BNSS 482 replaces CrPC 438", BNS, "482", False),
    ("BNSS 482 replaces CrPC 438", BNSS, "482", True),
    ("Section 1030 BNS", BNS, "103", False),
    ("The IPC applies. " + "word " * 40 + "there were 302 cases", IPC, "302", False),
    ("**Section 166 – “Public servant disobeying law, with intent to cause injury to any person”** "
     "*Indian Penal Code, 1860*", IPC, "166", True),
    ("| **Possession** | **Sec. 21** – Punishment for possession | NDPS Act, 1985 |",
     "NDPS Act 1985", "21", True),
    ("Cr.P.C. s. 438 allows anticipatory bail", "Code of Criminal Procedure 1973", "438", True),
])
def test_statute_cited(text, act, section, expected):
    assert statute_cited(text, act, section) is expected


@pytest.mark.parametrize("text, expected", [
    ("In Arnesh Kumar v. State of Bihar the court held", True),
    ("see (2014) 8 SCC 273", True),
    ("The State of Bihar argued otherwise", False),
    ("", False),
])
def test_case_cited(text, expected):
    assert case_cited(text, "Arnesh Kumar v. State of Bihar (2014) 8 SCC 273") is expected


@pytest.mark.parametrize("text, expected", [
    ("| **Justice K.S. Puttaswamy (Retd.) vs Union of India & Ors.** | (2017) 4 SCC 1 |", True),
    ("The nine-judge bench in (2017) 10 SCC 1 held privacy fundamental", True),
    ("Union of India argued that privacy is not fundamental", False),
    ("see (2017) 10 SCC 15", False),
])
def test_case_cited_handles_initials_markdown_and_exact_reporter(text, expected):
    assert case_cited(text, "K.S. Puttaswamy v. Union of India (2017) 10 SCC 1") is expected


def test_match_answer_scores_full_partial_and_zero():
    row = statute_row([(IPC, "302")], also=[(BNS, "103")])
    assert match_answer("Under Section 302 IPC ...", row) == 1.0
    assert match_answer("BNS Section 103 now governs murder", row) == 1.0
    assert match_answer("The IPC punishes murder under Section 300", row) == 0.5
    assert match_answer("Murder is punishable with death.", row) == 0.0


def test_match_answer_case_rows_have_no_partial_credit():
    row = case_row(["Kedar Nath Singh v. State of Bihar AIR 1962 SC 955"])
    assert match_answer("Kedar Nath Singh upheld section 124A", row) == 1.0
    assert match_answer("Section 124A IPC deals with sedition", row) == 0.0


@pytest.mark.parametrize("metadata, expected", [
    ({"citation": "VIBER_000001", "case_name": "Who decided Kesavananda Bharati v. State of Kerala?"}, True),
    ({"doc_type": "qa_pair", "case_name": "Legal Q&A reference (not a judgment)"}, True),
    ({"citation": "(1973) 4 SCC 225", "case_name": "Kesavananda Bharati v. State of Kerala"}, False),
    ({}, False),
])
def test_is_qa_entry(metadata, expected):
    assert is_qa_entry(metadata) is expected


def test_rows_without_target_are_not_scored():
    assert match_answer("anything at all", OPEN_ROW) is None
    assert row_targets(LEGACY_EMPTY_ROW)[0] == "NONE"
    assert match_answer("Section nan, nan", LEGACY_EMPTY_ROW) is None


def test_legacy_rows_fall_back_to_act_and_section():
    row = {"correct_act": "CRPC", "correct_section": "438"}
    assert row_targets(row)[0] == "S"
    assert match_answer("Section 438 CrPC provides anticipatory bail", row) == 1.0


# --- metrics engine: no free marks -----------------------------------------

def _engine(rows):
    engine = MetricsEngine(pd.DataFrame(rows), None)
    engine.bare_acts_collection = None
    engine.case_law_collection = None
    return engine


def _response(answer, citations=()):
    return {"answer": answer, "citations": list(citations), "confidence": "high"}


def test_car_excludes_rows_without_target_instead_of_scoring_them_correct():
    rows = [statute_row([(IPC, "302")]), OPEN_ROW, LEGACY_EMPTY_ROW]
    responses = [_response("No idea."), _response("No idea."), _response("No idea.")]
    car = _engine(rows).compute_citation_accuracy(responses)
    assert car["n_scored"] == 1
    assert car["n_excluded_no_target"] == 2
    assert car["CAR_generated_overall"] == 0.0
    assert car["CAR_retrieved_overall"] == 0.0


def test_car_uses_structured_citations_and_answer_text_separately():
    rows = [statute_row([(IPC, "302")])]
    cited = _response("Murder is punishable with death.",
                      [{"act_or_case": "IPC", "section_or_citation": "Section 302"}])
    car = _engine(rows).compute_citation_accuracy([cited])
    assert car["CAR_retrieved_overall"] == 100.0
    assert car["CAR_generated_overall"] == 0.0


def test_ccs_skips_rows_without_target():
    rows = [statute_row([(IPC, "302")]), OPEN_ROW]
    responses = [_response("Section 302 IPC"), _response("No idea.")]
    ccs = _engine(rows).compute_confidence_calibration(responses)
    assert ccs["count_high"] == 1
    assert ccs["accuracy_at_high"] == 100.0


def test_abstention_on_row_without_target_is_not_a_correct_abstention():
    rows = [OPEN_ROW, statute_row([(IPC, "302")])]
    refusal = {"answer": "I could not find this.", "citations": [], "confidence": "low"}
    ap = _engine(rows).compute_abstention_metrics([refusal, _response("Section 302 IPC")])
    assert ap["n_excluded_no_target"] == 1
    assert ap["TP"] == 0
    assert ap["TN"] == 1
    assert ap["total_queries"] == 1
