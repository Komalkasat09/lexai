# Legal Research API - Backend

Production-ready FastAPI server for legal document research and contract analysis.

## Quick Start

### One Command to Run

```bash
python app.py
```

The server will start at **http://localhost:8000**

### Options

```bash
python app.py --port 8080              # Custom port
python app.py --load-data              # Load production data first
python app.py --host 0.0.0.0 --port 80 # Production config
```

## 📚 API Endpoints

- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/api/health
- **Contract Analysis**: POST http://localhost:8000/api/analyze
- **Legal Research**: POST http://localhost:8000/api/research

## 📁 Project Structure

```
backend/
├── app.py                  # 🎯 Single entry point - START HERE
├── setup.sh                # Setup script
│
├── api/                    # FastAPI routes
├── llm/                    # Legal LLM (Groq/Mixtral)
├── retrieval/              # Smart RAG retriever
├── database/               # ChromaDB setup
├── intelligence/           # Analytics & feedback
├── data_pipeline/          # Web scrapers & loaders
├── evaluation/             # Research evaluation framework
│
├── core/                   # Contract analysis modules (legacy)
├── legacy/                 # Old entry points (deprecated)
├── demos/                  # Demo scripts
├── tests/                  # Test suites
├── scripts/                # Utility scripts
├── docs/                   # Documentation
└── data/                   # Data files and samples
```

## 🔧 Environment Setup

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment** (`.env`):
   ```
   GROQ_API_KEY=your_key_here
   ENVIRONMENT=development
   HOST=0.0.0.0
   PORT=8000
   ```

## 📦 Load Production Data

```bash
# Option 1: Load during startup
python app.py --load-data

# Option 2: Load manually
python scripts/production_data_loader.py
```

See `scripts/PRODUCTION_DATA_GUIDE.py` for details.

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python tests/test_api.py
```

## 📊 Evaluation Framework

For baseline research paper evaluation with 293 criminal-law queries:

```bash
cd evaluation
python run_evaluation.py
```

Generates publication-ready LaTeX tables and PNG figures.

For cross-domain expansion (Civil + Corporate + Family) with 393 total queries:

```bash
cd evaluation
python run_cross_domain_eval_393.py
```

This expanded benchmark evaluates LexAI as a general Indian legal research system across multiple legal domains.

## 🗄️ Database

- **Location**: `./legal_research_db/`
- **Type**: ChromaDB (vector database)
- **Current**: 67 documents (59 bare acts + 7 case law + 1 amendment)
- **HuggingFace Dataset**: 24,607 Indian law Q&A available

## 🛠️ Useful Scripts

```bash
# Check database status
python scripts/check_db_status.py

# Debug retriever
python scripts/debug_retriever.py

# Populate production DB
python scripts/populate_production_db.py
```

## 📖 Documentation

See `docs/` folder:
- `QUICKSTART.md` - Getting started guide
- `INTELLIGENCE_LAYER.md` - Analytics system
- `PRODUCTION_DEPLOYMENT.md` - Deploy to production
- `SYSTEM_STATUS.md` - Complete system overview

## 🔗 Frontend Integration

Frontend expects backend at: **http://localhost:8000**

Configure in `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📝 License

See LICENSE file for details.

## 🆕 Recent Fixes (Feb 2026)

- Added documentation note to `core/hallucination_guard.py` clarifying dead code status.
- Updated IPC regex in `retrieval/smart_retriever.py` for precise section extraction.
- Refactored `explain_section()` and `summarize_judgment()` in `llm/legal_llm.py` to accept pre-retrieved context, avoiding redundant retrieval.
- Clarified CAR coverage log line in `evaluation/recompute_fixed.py` to document numerator/denominator.

## 📄 Complete Summary

See `COMPLETE_SUMMARY.md` for a full backend summary, including directory structure, features, quick start, evaluation/testing, frontend integration, documentation, license, and changelog.

## 🗒️ Changelog

See `CHANGELOG_SUMMARY.md` for a full git history and backend changes.
