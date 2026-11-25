# System details for the rerun

Repository: `~/legal-website`, branch `komal/clean-index-and-scoring` (not pushed).
The main run started at commit `82b373d`; no commit after it changes system code
(`backend/llm`, `backend/retrieval`, `backend/database`, `backend/evaluation/baselines.py`,
`backend/evaluation/run_evaluation.py`), only scoring and run scripts.

## Run configuration

| Setting | Value |
|---|---|
| Model | `openai/gpt-oss-120b` on Groq (Llama-3.3-70B, used in the paper, has been retired) |
| Temperature | 0 |
| Output budget | 4,096 tokens, identical for all three systems |
| Regime | forced-answer (no system may refuse) |
| Queries | all 393; 378 have a citation target (14 open, 1 rejected) |
| Index | `backend/legal_research_db_v2` |
| Embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, the same model for the index and the queries |
| Transition classifier | **not used**: its trained model is not in this copy, and the logs record "Learned transition classifier unavailable" for every query. Transition handling is the hand-written map only (see `transition_map/`). |

## Index (v2)

2,604 statute sections from 11 acts, plus 12,800 Q&A pairs:

| Act | Sections |
|---|---|
| Indian Penal Code 1860 | 570 |
| Bharatiya Nagarik Suraksha Sanhita 2023 | 531 |
| Code of Criminal Procedure 1973 | 444 |
| Bharatiya Nyaya Sanhita 2023 | 350 (8 of 358 missing in the source PDF extraction) |
| Indian Evidence Act 1872 | 175 |
| Bharatiya Sakshya Adhiniyam 2023 | 170 |
| Negotiable Instruments Act 1881 | 153 |
| Consumer Protection Act 2019 | 107 |
| Protection of Women from Domestic Violence Act 2005 | 37 |
| Hindu Marriage Act 1955 | 35 |
| Limitation Act 1963 | 32 |

**Left out because the stored text was a different document:**
- "Companies Act 2013" was the Income-tax Act 1961.
- "IT Act 2000" was a copy of IPC sections.
- "Arbitration Act 1996" was the 1927 Geneva Convention.
- "CPC" and "TPA" were paragraphs from court judgments.

**Case law:** no judgment corpus. The 12,800 entries are Q&A pairs from `viber1/indian-law-dataset`, labelled "Legal Q&A reference (not a judgment)" so they cannot be cited as cases. The seven placeholder cases (e.g. "State of Maharashtra v. Rajesh Kumar, AIR 2019 SC 1234") and one unlabelled fragment are removed: the v2 index has 0 `source: demo` entries and 0 `SAMPLE` ids, and no system cited a placeholder case in the run. The paper's "13,000+ case-law documents" should be rewritten accordingly.

**Amendments and overruling map:** empty. The only stored amendment (IPC 420 by the Criminal Law (Amendment) Act 2013) is not a real amendment.

Full composition: `index_manifest.json`.

## Defects found and fixed (commit hashes)

**In LexAI**

| Commit | Defect |
|---|---|
| `92b17e4` | The model never saw retrieved text: the prompt builder read `text`, the retriever stores `document`, so every section and case reached the model as "No text available" (all 1,033 chunks in the paper's run; 115 answers said the text was missing). Transition notes and amendment fields were read from keys that are never set. |
| `df6d252` | 35 entries of the IPC->BNS / CrPC->BNSS map pointed at the wrong section (e.g. IPC 403 -> BNS 316 instead of 314; CrPC appeals off by about 13), corrected from the section texts (`scripts/audit_transition_maps.py`). In the forced-answer regime the retriever still discarded all low-confidence results and gave the model an empty context. |
| `cae5a04` | The middleware named the replacing BNS/BNSS section but never fetched its text. Now fetched (switch: `use_transition_expansion`). |
| `a361329`, `505636d` | The index searched by the paper's run held 59 statute sections; the larger index mislabelled five acts; 14 CrPC sections (incl. 482) held schedule rows. |
| (`a361329`) | Index vectors were made with `all-MiniLM-L6-v2` while queries were embedded with the multilingual model, so dense retrieval compared vectors from two different models. |

**In the evaluation**

| Commit | Defect |
|---|---|
| `1bbd068` | 204 rows without a target scored 1.0 in CAR, counted correct in CCS, and as correct abstentions in AP; act lookup mapped "BNSS" to the BNS; the P@K category check never matched the benchmark's category names. |
| `e06bf1e` | LexAI generated with 2,048 output tokens, the baselines with 1,024. |
| `128d9ca`, `32db2f6` | API errors and empty answers were saved as answers (151 SimpleRAG answers in the paper's run were API error messages). |
| `c30729e` | Collections opened without naming the embedding model could fall back to Chroma's default. |
| `2bf9725`, `97c52f3` | Citation matching missed initials ("K.S. Puttaswamy"), markdown tables and long act names. |
| `7c437df` | The hallucination rate called any citation outside the index a hallucination, so retrieval-only citations scored near zero by construction and placeholder cases passed. Replaced by a citation-validity check applied identically to all systems. |

**Tests:** `backend/tests/test_answer_key_scoring.py`, `test_rerun_fixes.py`, `test_citation_validity.py` (all pass). The 13 other failing tests in `backend/tests/` failed before these changes too.
