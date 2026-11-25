# LexEval-India rerun: review package

Prepared 25 Nov 2026 for rewriting the LexAI paper. Every number here comes from files under `~/legal-website` on branch `komal/clean-index-and-scoring`.

## Headline (primary result first)

All 393 queries, of which 378 are scored. Model: gpt-oss-120b. Answer key reviewed by an advocate (see `review_record.md` for the gaps).

| | LexAI | NoRAG | SimpleRAG |
|---|---|---|---|
| Fully correct, full benchmark (rule A) | 82.5% (78.8–86.2) | 83.1% (79.1–86.8) | 75.7% (71.4–79.9) |

- **LexAI vs NoRAG:** a tie. −0.5 points, discordant 27/29, p=0.89.
- **LexAI vs SimpleRAG:** +6.9 points, discordant 36/10, p=0.0002.

Sensitivity analyses: `scoring_sensitivity.md`.
- **Transition questions:** LexAI leads under both rules.
- **Statute questions:** LexAI leads under rule A only.
- **Case law:** LexAI loses.
- **Source of the transition lead:** the hand-written map (`transition_map/README.md`).

## Contents

| Path | What it is |
|---|---|
| `results/scores.json` | Per-system scores, bootstrap CIs, paired tests, citation validity, LexAI P@K |
| `results/scores_per_query.csv` | Verdict per query and system (rule A, full benchmark) |
| `results/scores_nontrivial_per_query.csv` | Verdict per query on non-echo rows |
| `results/sensitivity_report.json`, `results/sensitivity_per_query.csv` | The fixed analysis plan's output: every claim under rules A and B, with the map split |
| `results/run_config.json` | Model, token budget, index, regime |
| `results/ablations/` | The two LexAI ablations (replacement fetching off; transition middleware off) on the 90 transition and punishment queries; summary at the end of this README |
| `prompts.md` | The three system prompts and how each request is built |
| `system_details.md` | Run settings, index composition, every defect fixed with its commit hash |
| `index_manifest.json` | Exact index composition |
| `transition_map/` | The map, its provenance and git dates, its overlap with the benchmark, and the held-out test |
| `scoring_sensitivity.md` | Scoring rules, results table, answer lengths, citation validity |
| `review_record.md` | Who reviewed the key, what is still unreviewed, what to ask the advocate |

## Things the paper must change

- **Model:** gpt-oss-120b, not Llama-3.3-70B (retired), with a 4,096-token budget for every system.
- **Transition classifier:** not part of the tested system. Transition handling was the hand-written map. The classifier's training pool included the benchmark's 50 transition queries (`backend/transition_classifier/data/paper_protocol_metadata.json`).
- **Case law:** no judgment corpus. The 12,800 entries are Q&A pairs.
- **Index:** 2,604 sections from 11 acts. Five mislabelled acts were removed.
- **Old metrics:** the paper's CAR, HR and P@K came from scoring with the defects listed in `system_details.md`, so none of the old numbers stand.

## Ablations (added 26 Nov, 00:12)

LexAI variants on the 90 transition and punishment queries (86 scored), compared with full LexAI on the same queries under the fixed analysis plan. Paired discordant counts: full-only / variant-only, with the exact McNemar p.

| Variant | Transition, rule A | Transition, rule B | Punishment, rule A | Punishment, rule B |
|---|---|---|---|---|
| Full LexAI | 76.1 | 56.5 | 75.0 | 32.5 |
| No replacement fetching | 76.1 (0/0, p=1.0) | 56.5 (5/5, p=1.0) | 77.5 (1/2, p=1.0) | 27.5 (4/2, p=0.69) |
| No transition middleware (map off) | 58.7 (8/0, p=0.008) | 39.1 (12/4, p=0.077) | 60.0 (7/1, p=0.070) | 35.0 (2/3, p=1.0) |

**Reading:**
- **The map produces the transition advantage.** Removing it lowers transition accuracy by about 17 points: significant under rule A, the same direction under rule B.
- **Replacement fetching, added during debugging, has no measurable effect,** so the headline results do not depend on it.
- **Without the map, LexAI is still at 58.7 on transition rows,** against NoRAG 47.8 in the main run. That comparison is descriptive only; it is not a paired test in the plan.

Files: `results/ablations/` (answers, run configs, `sensitivity_report_with_ablations.json`).
