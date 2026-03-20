# LexAI: Complete Reproducibility Guide

This document provides step-by-step instructions to reproduce all results from the paper **"LexAI: A Hybrid RAG System for Indian Legal Retrieval with Specialized Middleware and Confidence-Based Answering"**.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Environment Setup](#environment-setup)
3. [Database Construction](#database-construction)
4. [Evaluation Pipeline](#evaluation-pipeline)
5. [Baseline Systems](#baseline-systems)
6. [Ablation Studies](#ablation-studies)
7. [Statistical Analysis & Figures](#statistical-analysis--figures)
8. [Expected Results](#expected-results)
9. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Hardware
- **CPU**: 4+ cores recommended
- **RAM**: 16 GB minimum, 32 GB recommended
- **Storage**: 10 GB free space (5 GB for database + models, 5 GB for results)
- **GPU**: Not required (but Groq API used for LLM inference)

### Software
- **OS**: macOS, Linux, or Windows (tested on macOS)
- **Python**: 3.10 or 3.11
- **API Keys Required**:
  - Groq API key (for LLaMA 3.1 70B inference)
  - HuggingFace account (for reranker models, free)

### Estimated Runtime
- Database construction: ~10 minutes
- Full evaluation (293 queries × 3 systems): ~8 hours
- Threshold ablation (50 queries × 6 threshold pairs): ~2 hours
- BNS middleware ablation (50 queries × 2 settings): ~1 hour
- **Total**: ~12-14 hours

---

## Environment Setup

### Step 1: Clone Repository
```bash
cd /path/to/your/workspace
# Repository assumed to be at: legal-website/backend
cd legal-website/backend
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

**Critical packages** (versions must match exactly):
- `chromadb==0.5.0`
- `sentence-transformers==2.2.2`
- `groq==0.9.0`
- `pandas==2.0.3`
- `openpyxl==3.1.2`
- `matplotlib==3.7.2`
- `scipy==1.11.1`

### Step 4: Configure API Keys
Create a `.env` file in `backend/` with:
```bash
GROQ_API_KEY=your_groq_api_key_here
```

Get your Groq API key from: https://console.groq.com/keys

### Step 5: Verify Installation
```bash
python -c "import chromadb; import sentence_transformers; import groq; print('✓ All dependencies installed')"
```

---

## Database Construction

### Step 1: Prepare Source Documents

Ensure these directories exist with legal data:
```
backend/
├── bare_acts/          # 2,408 sections from Indian Bare Acts
├── case_law/           # 43 landmark judgment PDFs
├── amendments_data/    # 50 amendment records (CSV/JSON)
└── overruling_map/     # 30 overruling relationships (CSV)
```

### Step 2: Build ChromaDB Vector Database
```bash
cd backend
python build_chroma_db.py
```

**Expected output**:
```
Building ChromaDB database...
- Bare Acts: 2,408 sections indexed
- Case Law: 43 judgments indexed
- Amendments: 50 records indexed
- Overruling Map: 30 relationships indexed
✓ Database saved to: chroma_db/
```

**Embedding Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions)

### Step 3: Verify Database
```bash
python -c "
import chromadb
client = chromadb.PersistentClient(path='chroma_db')
print('Collections:', [c.name for c in client.list_collections()])
for col in client.list_collections():
    print(f'{col.name}: {col.count()} documents')
"
```

**Expected output**:
```
Collections: ['bare_acts', 'case_law', 'amendments', 'overruling_map']
bare_acts: 2408 documents
case_law: 43 documents
amendments: 50 documents
overruling_map: 30 documents
```

---

## Evaluation Pipeline

### Step 1: Prepare Ground Truth
The ground truth file contains 293 manually annotated queries:
```
backend/evaluation/ground_truth_verified.xlsx
```

**Columns**:
- `Query`: Legal question
- `Category`: Query type (7 categories)
- `Ground_Truth_Citations`: List of relevant sections/cases
- `Expected_Confidence`: HIGH/MEDIUM/LOW

### Step 2: Run LexAI Full Evaluation (Baseline 293)
```bash
cd backend/evaluation
python run_evaluation.py
```

**Parameters** (hardcoded in script):
- Similarity threshold: 0.73
- Confidence low threshold: 0.25
- Confidence high threshold: 0.73
- Reranker: `cross-encoder/ms-marco-MiniLM-L-12-v2`
- LLM: `llama-3.1-70b-versatile` (via Groq)
- Random seed: 42

**Output**:
- `evaluation/results/checkpoints/lexai_responses.json`: All 293 responses
- Runtime: ~5-6 hours (due to API rate limits)

### Step 2B: Run Cross-Domain Expansion Evaluation (393 total)

Run the expanded benchmark that includes Civil, Corporate, and Family domains:

```bash
cd backend/evaluation
python run_cross_domain_eval_393.py
```

**Output**:
- `evaluation/results/checkpoints/lexai_responses_393.json`: All 393 responses (reuses baseline where available)
- `evaluation/results/table5_cross_domain_summary.json`: Domain-wise CAR/ACS summary
- `evaluation/results/table5_cross_domain.md`: Table V markdown export

This step updates the evaluation scope from a criminal-law-only benchmark to a general Indian legal research benchmark across multiple domains.

### Step 3: Recompute Metrics
```bash
python recompute_metrics.py
```

**Output**:
- `evaluation/results/recomputed_metrics.csv`: Per-query metrics (CAR, HR, ACS, OLR)

### Step 4: Hindi Query Evaluation (LexEval-India Subset)

Generate Hindi subset:
```bash
python /tmp/build_hindi_subset.py
```

Run Hindi LexAI responses (fresh run, no resume):
```bash
python /tmp/run_hindi_eval.py
```

Compute Hindi metrics with empty-response handling:
```bash
python /tmp/fix_hindi_summary.py
```

Artifacts:
- `evaluation/hindi_queries.xlsx`
- `evaluation/evaluation/results/checkpoints/lexai_hindi_responses.json`
- `evaluation/evaluation/results/checkpoints/lexai_hindi_empty_responses.json`
- `evaluation/evaluation/results/hindi_eval_summary.json`

### Table IV: English + Hindi Evaluation

| Language | Queries | CAR | ACS |
|---|---:|---:|---:|
| English | 293 | 69.62% | 63.77 |
| Hindi | 40 | 42.50% | 63.13 |
| **Overall** | **333** | **66.37%** | **63.69** |

Note: Empty Hindi responses are logged at `evaluation/evaluation/results/checkpoints/lexai_hindi_empty_responses.json` and excluded from Hindi CAR/ACS. In this run, empty responses = 0.

Updated paper sentence:

"LexAI supports multilingual queries through paraphrase-multilingual-MiniLM-L12-v2
embeddings, evaluated on Hindi legal queries with 42.50% CAR on a 40-query Hindi
subset of LexEval-India."

---

## Baseline Systems

### Baseline 1: SimpleRAG
```bash
python run_baselines.py --system simple_rag
```

**Differences from LexAI**:
- No BNS/BNSS middleware
- No overruling detection
- No confidence-based uncertainty handling
- Answers every query (no "UNCERTAIN" responses)

**Output**:
- `evaluation/results/checkpoints/simple_rag_responses.json`
- `evaluation/results/simple_rag_metrics.csv`
- Runtime: ~2 hours

### Baseline 2: NoRAG
```bash
python run_baselines.py --system no_rag
```

**Configuration**:
- LLM only (no retrieval)
- Same LLM as LexAI (LLaMA 3.1 70B)
- Tests LLM's inherent legal knowledge

**Output**:
- `evaluation/results/checkpoints/no_rag_responses.json`
- `evaluation/results/no_rag_metrics.csv`
- Runtime: ~1 hour

---

## Ablation Studies

### Ablation 1: Threshold Sensitivity
Tests 6 different similarity threshold pairs:
```bash
python threshold_ablation.py
```

**Threshold pairs tested**:
| Pair | Similarity | Conf Low | Conf High |
|------|-----------|----------|-----------|
| 1    | 0.65      | 0.20     | 0.65      |
| 2    | 0.70      | 0.25     | 0.70      |
| 3    | **0.73**  | **0.25** | **0.73**  | ← Default
| 4    | 0.75      | 0.30     | 0.75      |
| 5    | 0.78      | 0.35     | 0.78      |
| 6    | 0.80      | 0.40     | 0.80      |

**50 queries** × 6 pairs = 300 evaluations

**Output**:
- `evaluation/results/threshold_ablation_results.json`
- `evaluation/results/figures/threshold_ablation.png` (300 DPI)
- Runtime: ~3 hours

**Goal**: Demonstrate robustness — performance should degrade gracefully, with 0.73 as optimal.

### Ablation 2: BNS Middleware Contribution
Tests impact of BNS/BNSS transition middleware:
```bash
python bns_ablation.py
```

**Configurations**:
- **Middleware ON**: Full LexAI system
- **Middleware OFF**: Disable BNS/BNSS translation layer

**Test set**: 50 IPC→BNS transition queries

**Metric**: Outdated Law Rate (OLR)
- Measures how often system returns outdated IPC sections instead of new BNS equivalents

**Output**:
- `evaluation/results/bns_ablation_results.json`
- `evaluation/results/figures/bns_middleware_ablation.png` (300 DPI)
- Runtime: ~1 hour

**Expected**: OLR significantly higher with middleware OFF (proves middleware value).

---

## Statistical Analysis & Figures

### Step 1: Generate All Figures
```bash
python results_dashboard.py
```

**Output** (5 figures, all 300 DPI):
1. `figures/main_comparison.png`: 4 metrics × 3 systems, with error bars
2. `figures/category_breakdown.png`: CAR by query category
3. `figures/calibration.png`: Confidence calibration analysis
4. `figures/threshold_ablation.png`: Threshold sensitivity (from ablation)
5. `figures/bns_middleware_ablation.png`: Middleware contribution (from ablation)

**All figures include**:
- Bootstrap 95% confidence intervals
- Significance markers (* p<0.05, ** p<0.01, *** p<0.001)
- Publication-quality formatting

### Step 2: Generate Table 1 Statistics
```bash
python statistical_analysis.py
```

**Output**:
- `results/paper_table1.csv`: Complete statistics (mean ± CI, p-values, effect sizes)
- `results/paper_table1_latex.txt`: Ready-to-paste LaTeX code

**Statistical tests performed**:
- Paired t-tests (LexAI vs each baseline)
- Cohen's d effect sizes
- Bootstrap confidence intervals (10,000 iterations)

**Random seeds**:
- All analyses use `random_seed=42` for reproducibility
- Bootstrap CIs, train/test splits, etc. all seeded

---

## Expected Results

Fill in this table after running all experiments:

### Table 1: Main Results

| Metric | LexAI | SimpleRAG | NoRAG | p (vs SimpleRAG) | p (vs NoRAG) |
|--------|-------|-----------|-------|------------------|--------------|
| CAR ↑  |       |           |       |                  |              |
| HR ↓   |       |           |       |                  |              |
| ACS ↑  |       |           |       |                  |              |
| OLR ↓  |       |           |       |                  |              |

### Threshold Ablation

| Threshold | CAR   | HR    | ACS   | OLR   |
|-----------|-------|-------|-------|-------|
| 0.65      |       |       |       |       |
| 0.70      |       |       |       |       |
| **0.73**  |       |       |       |       |
| 0.75      |       |       |       |       |
| 0.78      |       |       |       |       |
| 0.80      |       |       |       |       |

### BNS Middleware Ablation

| Configuration   | OLR   | IPC→BNS Accuracy |
|-----------------|-------|------------------|
| Middleware ON   |       |                  |
| Middleware OFF  |       |                  |

---

## Troubleshooting

### Issue: ChromaDB Version Mismatch
**Error**: `AttributeError: 'Collection' object has no attribute 'get'`

**Solution**:
```bash
pip uninstall chromadb
pip install chromadb==0.5.0
```

### Issue: Groq API Rate Limit
**Error**: `RateLimitError: You have exceeded your rate limit`

**Solution**:
- Free tier: 30 requests/minute
- Evaluation script has built-in rate limiting (2 sec delay)
- If still failing, increase delay in `legal_llm.py` line 487: `time.sleep(3)`

### Issue: Out of Memory
**Error**: `MemoryError` during embedding

**Solution**:
- Process documents in smaller batches
- Reduce batch size in `build_chroma_db.py` (default: 100)
- Close other applications

### Issue: Missing Ground Truth
**Error**: `FileNotFoundError: ground_truth_verified.xlsx`

**Solution**:
```bash
# Ensure file exists at correct path
ls backend/evaluation/ground_truth_verified.xlsx

# If missing, check if it's named differently:
ls backend/evaluation/*.xlsx
```

### Issue: Inconsistent Metrics
**Error**: Metrics differ from paper

**Possible causes**:
1. **Wrong database**: Check `ls -l chroma_db/chroma.sqlite3` creation date
2. **Wrong thresholds**: Verify in `run_evaluation.py` that default = 0.73/0.25/0.73
3. **API changes**: Groq may update models; verify `llama-3.1-70b-versatile` still available
4. **Random seed**: Ensure all scripts use `seed=42`

---

## Citation

If you use this code or data, please cite:

```bibtex
@article{lexai2024,
  title={LexAI: A Hybrid RAG System for Indian Legal Retrieval with Specialized Middleware and Confidence-Based Answering},
  author={[Your Name]},
  journal={[Journal Name]},
  year={2024}
}
```

---

## Contact

For questions about reproducibility:
- **Email**: [your-email]
- **GitHub Issues**: [repo-url]/issues

---

## Version Information

- **Code Version**: 1.0 (February 2024)
- **Database Version**: Created February 23, 2026
- **Python**: 3.10.12
- **ChromaDB**: 0.5.0
- **Sentence Transformers**: 2.2.2
- **Groq API**: 0.9.0

**Last updated**: February 23, 2026
