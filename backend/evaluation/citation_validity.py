"""Checks whether the sections and cases an answer cites actually exist.

Works only on the answer text, so every system is judged the same way. A
section beyond the last section of its act (e.g. "BNS 420"; the BNS ends at
358) is invented. Citing one of the placeholder cases that were in the old
index is invented too. Anything else that cannot be checked is reported as
unverified rather than counted either way.
"""
import re
from typing import Dict, List, Tuple

try:
    from evaluation.answer_key import ACT_ALIASES, _normalise
except ImportError:  # run from inside evaluation/
    from answer_key import ACT_ALIASES, _normalise

# Highest section number of each act whose full text is in the index. Section
# numbers with letter suffixes (376AB, 65B) are checked on their numeric part.
LAST_SECTION: Dict[str, int] = {
    "Indian Penal Code 1860": 511,
    "Code of Criminal Procedure 1973": 484,
    "Indian Evidence Act 1872": 167,
    "Bharatiya Nyaya Sanhita 2023": 358,
    "Bharatiya Nagarik Suraksha Sanhita 2023": 531,
    "Bharatiya Sakshya Adhiniyam 2023": 170,
    "Negotiable Instruments Act 1881": 148,
    "Hindu Marriage Act 1955": 30,
    "Limitation Act 1963": 32,
    "Consumer Protection Act 2019": 107,
    "Protection of Women from Domestic Violence Act 2005": 37,
}

# Placeholder cases that sat in the old case_law collection; none is a real judgment.
PLACEHOLDER_CASES: Tuple[str, ...] = (
    "air 2019 sc 1234", "air 2020 sc 5678", "2020 scc 456", "2018 scc 234",
    "air 2021 sc 789", "2022 scc 567",
    "state of maharashtra v rajesh kumar", "vijay singh v state of nct delhi",
    "priya sharma v union of india", "state of kerala v anil kumar",
    "ramesh technology ltd v commissioner of income tax", "union of india v delhi green solutions",
)

_SECTION = r"(\d{1,4})([a-z]{0,2})"
_MARKER = r"(?:section|sections|sec|secs|s|ss|u s)"


def _alias_regex(act: str) -> str:
    aliases = sorted({_normalise(a) for a in ACT_ALIASES.get(act, [])}, key=len, reverse=True)
    return "(?:" + "|".join(re.escape(a) for a in aliases if a) + ")"


def extract_section_claims(text: str) -> List[Tuple[str, str]]:
    """(act, section) pairs the text cites for the acts in LAST_SECTION.

    Only tight forms count, so a number is not attributed to an act merely
    because both appear in the same paragraph:
    "<act> [section] N", "section N [of the] <act>", "N <act>".
    """
    low = _normalise(text)
    claims = set()
    # An act name followed by its own section number starts the next citation
    # ("bnss section 404 bsa section 37"), so it cannot close the previous one.
    # A bare year after the act ("Indian Penal Code, 1860") does not start one.
    year = r"(?:18|19|20)\d\d(?![0-9])"
    starts_next = rf"(?! (?:{_MARKER} )?(?!{year})\d)(?! {year} (?:{_MARKER} )?\d)"
    for act in LAST_SECTION:
        alias = _alias_regex(act)
        patterns = [
            rf"(?<![a-z0-9]){alias} (?:(?:18|19|20)\d\d )?(?:{_MARKER} )?{_SECTION}(?![0-9a-z])",
            rf"(?<![a-z0-9]){_MARKER} {_SECTION}(?: \d{{1,2}}| [a-z])*(?: of)?(?: the)? {alias}(?![a-z0-9]){starts_next}",
            rf"(?<![a-z0-9]){_SECTION} {alias}(?![a-z0-9]){starts_next}",
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, low):
                number, suffix = m.group(1), m.group(2)
                if 1800 <= int(number) <= 2099 and not suffix:
                    continue  # a year ("IPC 1860"), not a section
                claims.add((act, number + suffix))
    return sorted(claims)


def check_answer(text: str) -> Dict[str, object]:
    """Section and case citations in an answer, split into valid, invented and unverified.

    Args:
        text: The answer text.

    Returns:
        {"section_claims": n, "invented_sections": [...], "placeholder_cases": [...],
         "invented": n} where invented = invented sections + placeholder cases.
    """
    sections = extract_section_claims(text)
    invented_sections = [f"{act} s.{sec}" for act, sec in sections
                         if int(re.match(r"\d+", sec).group()) > LAST_SECTION[act]]
    low = _normalise(text)
    placeholders = [p for p in PLACEHOLDER_CASES if re.search(rf"(?<![a-z0-9]){re.escape(p)}(?![a-z0-9])", low)]
    return {
        "section_claims": len(sections),
        "invented_sections": invented_sections,
        "placeholder_cases": placeholders,
        "invented": len(invented_sections) + len(placeholders),
    }
