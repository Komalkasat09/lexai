"""Tests for the citation-validity check that replaces the old hallucination rate."""

import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.citation_validity import check_answer, extract_section_claims  # noqa: E402

IPC = "Indian Penal Code 1860"
BNS = "Bharatiya Nyaya Sanhita 2023"
BNSS = "Bharatiya Nagarik Suraksha Sanhita 2023"
BSA = "Bharatiya Sakshya Adhiniyam 2023"


@pytest.mark.parametrize("text, expected", [
    ("Section 302 of the Indian Penal Code, 1860", [(IPC, "302")]),
    ("IPC 302 is now BNS 103(1)", [(BNS, "103"), (IPC, "302")]),
    ("under **Sec. 438 CrPC**", [("Code of Criminal Procedure 1973", "438")]),
    ("BNS 2023 sec 309(4) covers robbery", [(BNS, "309")]),
    ("BNSS s. 482(4)", [(BNSS, "482")]),
    ("Indian Penal Code 1860 governs", []),
    ("bnss section 404, bsa section 37", [(BNSS, "404"), (BSA, "37")]),
    ("ipc sec 390 bns 2023 sec 309", [(BNS, "309"), (IPC, "390")]),
    ("IPC 376AB", [(IPC, "376ab")]),
])
def test_extract_section_claims(text, expected):
    assert extract_section_claims(text) == sorted(expected)


def test_section_beyond_the_last_section_is_invented():
    result = check_answer("Cheating is punished under BNS Section 420 and BNSS 482.")
    assert result["invented_sections"] == [f"{BNS} s.420"]
    assert result["invented"] == 1
    assert result["section_claims"] == 2


def test_last_section_itself_is_valid():
    assert check_answer("BNS 358 repeals the IPC")["invented"] == 0
    assert check_answer("BNS 359")["invented"] == 1


def test_placeholder_cases_count_as_invented():
    result = check_answer("See State of Maharashtra v. Rajesh Kumar, AIR 2019 SC 1234.")
    assert set(result["placeholder_cases"]) == {"state of maharashtra v rajesh kumar", "air 2019 sc 1234"}
    assert result["invented"] == 2


def test_real_case_and_unknown_acts_are_not_flagged():
    result = check_answer("Arnesh Kumar v. State of Bihar (2014) 8 SCC 273; Companies Act s. 448")
    assert result["invented"] == 0
