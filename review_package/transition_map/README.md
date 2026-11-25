# The IPC->BNS / CrPC->BNSS map

`transition_map.json` is the map LexAI used in the rerun (`IPC_BNS_MAP`, 110 entries; `CRPC_BNSS_MAP`, 68 entries, in `backend/retrieval/smart_retriever.py`). It is LexAI's only transition mechanism in the rerun: the learned classifier was not available.

## Provenance

- **Written:** 22 Feb 2026, commit `c7a8de3` ("complete backend for rag") in the earlier repository (`~/Desktop/legal-website`, remote `legal-website`).
- **Benchmark file first committed:** 24 Feb 2026 (`ground_truth_verified.xlsx`, commit `6123462`, same repository), two days later by the same project. The map cannot be shown to be independent of the benchmark.
- **Corrected:** 25 Nov 2026, commit `df6d252`. 35 entries changed, each because the section texts show the correct target (closest-text similarity at least 0.5, mapped section at most 0.2; `backend/scripts/audit_transition_maps.py` reproduces the check). The answer key was not used. IPC 396 -> BNS 311 is probably wrong (BNS 310(3)), but its text evidence was just under the bar, so it was left unchanged.

## Overlap with the benchmark

- 46 of the 110 IPC entries are an acceptable target somewhere in the benchmark.
- The 50 IPC-to-BNS transition queries name 23 distinct IPC/CrPC sections; 16 are in the map.
- Transition queries by map coverage of the section they name: {'no section named': 27, 'in map': 16, 'not in map': 7}.

| Section named in a transition query | In the map? |
|---|---|
| IPC 109 | no |
| IPC 120B | no |
| IPC 141 | yes -> BNS 189 |
| IPC 147 | yes -> BNS 191 |
| IPC 201 | no |
| IPC 279 | no |
| IPC 302 | yes -> BNS 103 |
| IPC 304B | yes -> BNS 80 |
| IPC 307 | yes -> BNS 109 |
| IPC 323 | yes -> BNS 115 |
| IPC 325 | yes -> BNS 121 |
| IPC 34 | no |
| IPC 354 | yes -> BNS 74 |
| IPC 366 | yes -> BNS 87 |
| IPC 376 | yes -> BNS 64 |
| IPC 377 | no |
| IPC 406 | yes -> BNS 316 |
| IPC 411 | no |
| IPC 420 | yes -> BNS 318 |
| IPC 498A | yes -> BNS 85 |
| IPC 506 | yes -> BNS 351 |
| IPC 509 | yes -> BNS 79 |
| IPC 511 | yes -> BNS 62 |

## Held-out test: does LexAI lead where the map cannot help?

Transition queries whose target is not already in the question (non-echo), split by whether the IPC/CrPC section the query names is in the map. Rule A = any acceptable citation; rule B = first new citation correct. "Only" = paired discordant counts (LexAI right and NoRAG wrong / the reverse); exact McNemar p.

| Group | Rule | n | LexAI % | NoRAG % | SimpleRAG % | LexAI-only / NoRAG-only | p (vs NoRAG) |
|---|---|---|---|---|---|---|---|
| in map | A | 16 | 62.5 | 0.0 | 6.2 | 10 / 0 | 0.002 |
| in map | B | 16 | 56.2 | 0.0 | 6.2 | 9 / 0 | 0.0039 |
| not in map | A | 6 | 50.0 | 16.7 | 0.0 | 2 / 0 | 0.5 |
| not in map | B | 6 | 33.3 | 0.0 | 0.0 | 2 / 0 | 0.5 |
| no section named | A | 24 | 91.7 | 87.5 | 83.3 | 2 / 1 | 1.0 |
| no section named | B | 24 | 62.5 | 54.2 | 58.3 | 7 / 5 | 0.7744 |

**Reading:**
- **In map:** the lead is large. NoRAG answers none of these 16 correctly; gpt-oss does not reliably know the 2023 BNS numbering.
- **Not in map:** only 6 queries. LexAI is ahead 2 to 0, which is too few to conclude anything.
- **No section named:** no real difference.

**Conclusion:** LexAI's transition advantage comes from the map. The paper should present the map as the mechanism and disclose its overlap with the benchmark.
