# LexAI Evaluation: Reproducibility & Methodology

## Overview

**Framework**: Rigorous evaluation of LexAI on Indian legal QA  
**Phases**: 4 (Schema & Dashboard), 5 (Ablation Credibility), 6 (Reproducibility)  
**Date**: March 18, 2026  
**Metrics**: 7 (CAR, HR, OLR, AP, ACS, P@K, CCS)  
**Dataset**: 393 verified ground truth queries across 7 legal categories  

## Key Findings

| Metric | LexAI | SimpleRAG | NoRAG |
|---|---|---|---|
| **CAR** (accuracy) | - | - | - |
| **HR** (hallucination) | - | - | - |
| **OLR** (outdated law) | - | - | - |
| **ACS** (completeness) | - | - | - |

### Phase 5: Threshold Tuning
- **Holdout Split**: 50 queries (stratified by category)
- **Pairs Tested**: 6 threshold pairs from (0.90, 0.75) to (0.65, 0.50)
- **Optimal**: HIGH=0.75, MEDIUM=0.60 (objective_score=0.4422)
- **Applied**: Updated smart_retriever.py and legal_llm.py

### Phase 5: BNS Middleware
- **Dataset**: 50 IPC→BNS transition queries
- **OLR Reduction**: 6.25% → 5.88% (0.37 pp absolute, 5.88% relative)
- **P-value**: n/a (insufficient variance in matched pairs)
- **Transition Accuracy**: 100% on answered queries

## Reproduction

### Environment Setup
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### One-Command Reproduction
```bash
# Regenerate paper tables from canonical complete_results + checkpoints
python scripts/regenerate_paper_artifacts.py

# Regenerate figures (fail-fast schema validation + provenance sidecars)
python evaluation/results_dashboard.py
```

### Required Files
✅ Ground truth: `evaluation/ground_truth_verified_393_ready.xlsx`  
✅ Responses: `evaluation/results/checkpoints/lexai_responses.json`  
✅ Baselines: `evaluation/results/checkpoints/baseline_responses.json`  
✅ Checkpoints: 6 threshold ablation JSON files  

### Output Artifacts
- `paper_table_*.csv` - Tables for manuscript
- `figures/*.png` - Publication-quality figures (300 DPI)
- `*.provenance.json` - Figure input tracking

## Dataset

### Ground Truth (393 queries)
- **Lawyer-verified**: All correctness labels verified by legal expert
- **Categories**: 7 legal domains
  1. Section Lookup (e.g., "Show me Section 27 of Evidence Act")
  2. Punishment Query (e.g., "Punishment for murder in BNS?")
  3. Amendment Query (e.g., "How did Section 498A change?")
  4. IPC→BNS Transition (e.g., "BNS equivalent of IPC 307?")
  5. Case Law Search (e.g., "Find cases on dowry harassment")
  6. Overruled Detection (e.g., "Is this case still valid?")
  7. Complex Interpretation (e.g., "Difference between murder & culpable homicide")
- **Split**: 343 main evaluation + 50 holdout (for threshold tuning)

### Knowledge Base (ChromaDB)
- Bare Acts: 100 (IPC, BNS, CrPC, BNSS, Evidence Act)
- Case Law: ~12,800 documents
- Amendments: ~500 IPC→BNS mapping records
- Retrieval: Hybrid semantic + BM25, reranked with cross-encoder

## Evaluation Metrics (7 Total)

1. **Citation Accuracy Rate (CAR)**: % responses with correct citations
2. **Hallucination Rate (HR)**: % responses with false claims
3. **Outdated Law Rate (OLR)**: % citing superseded pre-2023 law
4. **Abstention Precision (AP)**: % "cannot answer" justified
5. **Answer Completeness Score (ACS)**: Mean answer length
6. **Precision@K (P@K)**: % relevant documents in top-k
7. **Confidence Calibration Score (CCS)**: Rank correlation (confidence vs. correctness)

## Known Limitations

### Data Quality
- 393 queries may not fully represent all legal inquiry types
- Lawyer-verified by single annotator (potential systematic bias)
- Ground truth cut March 2026; newer amendments not captured
- Some categories have smaller n (50-60 queries)

### Methods
- Threshold tuning on 50-query holdout (generalization risk)
- BNS ablation p-values unreliable (n=14 conditional pairs)
- CCS operationalized as rank correlation (may hide persistent bias)
- Abstention judgment heuristic-based, not ground truth

### System Design
- ChromaDB retrieval may have systematic gaps (not audited)
- LLM generates false citations despite retrieval grounding
- Amendment/overruling database may be incomplete

### Infrastructure
- Groq API quota limits (100K tokens/day) affects full re-runs
- Checkpoint system required for reproducibility (API costs)
- Floating-point precision differences possible between environments

## Files

### Paper Tables
- `paper_table_01_threshold_ablation.csv`
- `paper_table_02_bns_ablation_attrition.csv`
- `paper_table_02b_bns_ablation_metrics.csv`
- `paper_table_03_system_comparison.csv`

### Figures (300 DPI)
- `figures/main_comparison.png` - System × Metric bar chart
- `figures/category_breakdown.png` - Per-category performance
- `figures/calibration.png` - Confidence calibration curve
- `figures/*.provenance.json` - Figure lineage (×3)

### Data
- `evaluation/results/checkpoints/lexai_responses.json` - 393 LexAI responses
- `evaluation/results/checkpoints/baseline_responses.json` - Baseline responses

### Provenance
- `dashboard_data_provenance.json` - Data pipeline tracking

---

For additional details on threat-to-validity and methodology, see THREAT_TO_VALIDITY.md
