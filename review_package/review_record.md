# Answer-key review record

Key file: `LexEval_draft_key_with_reviewer_notes (1).xlsx` (in the author's Downloads folder; not in the repository). The ground truth the scripts use is built from it by `backend/evaluation/answer_key.py`, and each row records its source in `target_source`.

| Part | Rows | Status |
|---|---|---|
| Draft key, non-Section-Lookup categories | 250 | Reviewed by **the reviewing advocate** (name held by the authors): 222 accepted, 27 corrected, 1 rejected. **Review date: not yet recorded.** The "Reviewed by / date" column in the file is empty. |
| Advocate corrections | 27 | Free-text corrections translated into targets by hand in `answer_key.CORRECTIONS`. 7 of them make a row open (no single citation) and are excluded from scoring. |
| Rows accepted with an open question | 6 (Q064, Q076, Q172, Q248, Q269, Q284) | Answers supplied on 25 Nov. Three change a scored target (Q064, Q076, Q269) and are labelled "answer to an open question, pending advocate confirmation". The wording suggests an AI assistant wrote them. **They need the advocate's sign-off.** |
| Section Lookup | 143 | **Not reviewed.** Targets come from the original ground-truth file: the section named in the question, checked by the authors. The key flags 4 rows (Q030: 156(3) recorded as 156; Q032, Q033, Q034: BNSS recorded as BNS). They are scored as recorded. `answer_key.py --section-lookup-fixes` builds the alternative. |
| Excluded from scoring | 15 | 14 open (no single citation), 1 rejected (Q216). |

## Still to obtain from the advocate

1. The review date.
2. Sign-off on Q064, Q076 and Q269. Two points within them are flagged:
   - Is BNS 344 the right equivalent of IPC 477A?
   - The BNSS s.2(1) clause letters for cognizable and bailable offences (Q269, Q270) need confirming.
3. A decision on Q030, Q032, Q033 and Q034.

Until then the paper should say: "the 250-row key was reviewed by a practising advocate [name to be added by the authors]; three rows completed afterwards are pending confirmation; the 143 Section Lookup targets are taken from the query text and checked by the authors."
