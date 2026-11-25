# Scoring rules and sensitivity

## Fixed analysis plan

Committed as `8cc0006` at 23:31:31 on 25 Nov 2026, before any ablation result was read (the first ablation had 67 of 90 answers saved); `backend/scripts/sensitivity_report.py`. Every claim is reported under both rules:

- **Rule A, any acceptable citation:** the answer cites any acceptable target. On "non-echo" rows, targets already written in the question do not count.
- **Rule B, first new citation:** the first section the answer cites that is not already in the question is an acceptable target. Statute rows only.

**"Non-echo" rows** are the 231 of 378 scored queries whose question does not already contain an acceptable answer. In the other 147, such as "Explain Section 166 IPC", every system scores by repeating the question. This rule was first used in an independent re-scoring earlier on 25 Nov, before this rerun existed.

Primary result: rule A on the full benchmark, reported first. The rest are sensitivity analyses.

## Results (LexAI vs each baseline; paired discordant counts and exact McNemar p)

| Claim | Rule | n | LexAI % | NoRAG % | SimpleRAG % | vs NoRAG (LexAI-only/NoRAG-only) | vs SimpleRAG |
|---|---|---|---|---|---|---|---|
| overall (full benchmark) | A any acceptable | 378 | 82.5 | 83.1 | 75.7 | 27/29, p=0.8939 | 36/10, p=0.0002 |
| overall (non-echo rows) | A any acceptable | 231 | 63.2 | 57.6 | 44.2 | 46/33, p=0.1766 | 55/11, p=0.0 |
| statute rows (non-echo) | A any acceptable | 163 | 74.8 | 58.3 | 50.9 | 44/17, p=0.0007 | 46/7, p=0.0 |
| statute rows (non-echo) | B first new citation | 163 | 41.1 | 37.4 | 34.4 | 39/33, p=0.556 | 35/24, p=0.1925 |
| case-law rows (non-echo) | A any acceptable | 68 | 35.3 | 55.9 | 27.9 | 2/16, p=0.0013 | 9/4, p=0.2668 |
| IPC to BNS transition (non-echo) | A any acceptable | 46 | 76.1 | 47.8 | 45.7 | 14/1, p=0.001 | 15/1, p=0.0005 |
| IPC to BNS transition (non-echo) | B first new citation | 46 | 56.5 | 28.3 | 32.6 | 18/5, p=0.0106 | 16/5, p=0.0266 |

Bonferroni threshold for the three category claims (statute, case law, transition): 0.0167.

**Reading:**
- **Statute rows:** the lead holds under rule A (p=0.0007) but not under rule B (p=0.56). Part of it comes from LexAI citing more sections per answer.
- **Transition:** the lead holds under both rules.
- **Case law:** LexAI loses.

## Answer length and number of citations

| | LexAI | NoRAG | SimpleRAG |
|---|---|---|---|
| Median answer length (characters) | 2,364 | 4,202 | 1,026 |
| Median sections cited per answer | 3 (mean 3.3) | 1 (mean 1.8) | 1 (mean 1.4) |

NoRAG writes the longest answers, but LexAI cites the most sections. Any credit for listing several sections therefore goes mostly to LexAI; rule B controls for it.

## Primary-target-only check (answer text, statute rows)

| | LexAI | NoRAG | SimpleRAG |
|---|---|---|---|
| All statute rows (300) | 82.0 | 70.7 | 67.3 |
| Non-echo statute rows (149) | 63.8 | 43.0 | 35.6 (LexAI vs NoRAG 46/15, p=0.0001) |

## Citation validity (replaces the old hallucination rate)

A section beyond the last section of its act (e.g. "BNS 420"; the BNS ends at 358), or a known placeholder case, counts as invented. Unverifiable citations are not counted.

| | LexAI | NoRAG | SimpleRAG |
|---|---|---|---|
| Sections checked | 1292 | 711 | 544 |
| Invented sections | 21 | 7 | 12 |
| Per 100 sections cited | 1.63 | 0.98 | 2.21 |
| Placeholder cases cited | 0 | 0 | 0 |

LexAI's invented sections are mostly BNSS numbers given under the BNS label (e.g. "BNS 480/483" for bail). Examples are in `results/scores.json` under `citation_validity.examples`.

## Not comparable across systems

`CAR_retrieved` (structured citations): LexAI's list is built by code from retrieval, the baselines' by a regex over their answer, and the prompts differ (see `prompts.md`). Do not use the 54% vs 29% figure as a verifiability claim.
