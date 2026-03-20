# 🎯 Backend + Frontend Integration Guide

## ✅ CLEAN STRUCTURE COMPLETE

The backend has been fully reorganized with a clean, production-ready structure.

---

## 🚀 ONE COMMAND TO RUN EVERYTHING

### Backend (Terminal 1)

```bash
cd backend
python app.py
```

**Server starts at**: http://localhost:8000  
**API Docs**: http://localhost:8000/api/docs

### Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

**Frontend starts at**: http://localhost:3000

That's it! The frontend automatically connects to the backend.

---

## 📁 NEW CLEAN STRUCTURE

### Before (Messy  ❌)
```
backend/
├── demo_legal_llm.py
├── demo_smart_retriever.py
├── demo_realtime_scraping.py
├── test_api.py
├── test_intelligence.py
├── test_legal_db_setup.py
├── test_pipeline.py
├── test_scraper.py
├── verify_legal_llm.py
├── verify_system.py
├── populate_production_db.py
├── production_data_loader.py
├── check_db_status.py
├── debug_retriever.py
├── COMPLETE.md
├── INSTALLATION_FIX.md
├── INTELLIGENCE_LAYER.md
├── PRODUCTION_DEPLOYMENT.md
├── QUICKSTART.md
├── RAG_GROQ_SETUP.md
├── README.md
├── SYSTEM_STATUS.md
├── PRODUCTION_DATA_GUIDE.py
├── start_api.py (old entry)
├── main.py (confusing)
├── api/
├── llm/
├── retrieval/
...
```

### After (Clean ✅)
```
backend/
├── app.py                  # 🎯 SINGLE ENTRY POINT - START HERE!
├── README.md               # Quick start guide
│
├── api/                    # FastAPI routes
├── llm/                    # Legal LLM
├── retrieval/              # Smart retriever
├── database/               # ChromaDB
├── intelligence/           # Analytics
├── data_pipeline/          # Scrapers & loaders
├── evaluation/             # Research framework
│
├── demos/                  # All demo scripts
│   ├── demo_legal_llm.py
│   ├── demo_smart_retriever.py
│   └── demo_realtime_scraping.py
│
├── tests/                  # All test files
│   ├── test_api.py
│   ├── test_intelligence.py
│   ├── test_legal_db_setup.py
│   ├── test_pipeline.py
│   ├── test_scraper.py
│   ├── verify_legal_llm.py
│   └── verify_system.py
│
├── scripts/                # Utility scripts
│   ├── production_data_loader.py
│   ├── populate_production_db.py
│   ├── check_db_status.py
│   ├── debug_retriever.py
│   └── PRODUCTION_DATA_GUIDE.py
│
└── docs/                   # All documentation
    ├── README.md
    ├── QUICKSTART.md
    ├── INTELLIGENCE_LAYER.md
    ├── PRODUCTION_DEPLOYMENT.md
    ├── COMPLETE.md
    ├── INSTALLATION_FIX.md
    ├── RAG_GROQ_SETUP.md
    └── SYSTEM_STATUS.md
```

---

## 🔧 Backend Commands

### Start Server (Standard)
```bash
python app.py
```

### Start Server (Custom Port)
```bash
python app.py --port 8080
```

### Load Production Data + Start Server
```bash
python app.py --load-data
```

### Production Config
```bash
python app.py --host 0.0.0.0 --port 80
```

---

## 📊 Database & Data Loading

### Check Database Status
```bash
python scripts/check_db_status.py
```

### Load Full Production Data
```bash
python scripts/production_data_loader.py --full
```

### Quick Test (100 docs)
```bash
python scripts/production_data_loader.py --quick
```

### Populate Manually
```bash
python scripts/populate_production_db.py
```

---

## 🧪 Testing

### Run All Tests
```bash
python -m pytest tests/
```

### Run Individual Tests
```bash
python tests/test_api.py
python tests/test_intelligence.py
```

### Verify System
```bash
python tests/verify_system.py
```

---

## 🎮 Demos

### Demo Legal LLM
```bash
python demos/demo_legal_llm.py
```

### Demo Smart Retriever
```bash
python demos/demo_smart_retriever.py
```

### Demo Real-time Scraping
```bash
python demos/demo_realtime_scraping.py
```

---

## 📈 Research Evaluation

### Run Full Baseline Evaluation (293 criminal-law queries)
```bash
cd evaluation
python run_evaluation.py
```

**Outputs**:
- LaTeX tables (3 files)
- PNG figures (5 files)
- Statistical test results
- Complete evaluation report

### Run Cross-Domain Evaluation (393 total queries)
```bash
cd evaluation
python run_cross_domain_eval_393.py
```

This run expands evaluation beyond criminal law into Civil, Corporate, and Family law, supporting a general Indian legal research system claim.

---

## 🌐 Frontend Configuration

The frontend is **already configured** to use the backend at http://localhost:8000.

### Configuration File
`frontend/lib/api.ts`:
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

### Override (Optional)
Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8080
```

---

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze-contract` | POST | Analyze legal contract |
| `/api/research` | POST | Legal research query |
| `/api/health` | GET | Health check |
| `/api/docs` | GET | API documentation |

---

## 📝 Project Status

### ✅ COMPLETED
- Clean folder structure
- Single entry point (`app.py`)
- Organized tests, demos, scripts, docs
- Working frontend integration
- Evaluation framework (8-part pipeline)
- Database with 67 documents (59 real bare acts)
- HuggingFace loader fixed (24,607 docs available)

### 🔄 READY TO USE
- Production data loading
- Real-time web scraping
- Auto-updater scheduler
- Intelligence analytics
- Contract analysis API

### 📊 METRICS
- **Bare Acts**: 59 authentic IPC/BNS/CrPC/BNSS sections
- **Case Law**: 7 documents (demo - can load 24,607+ from HuggingFace)
- **Retrieval**: 8 docs per query (3 bare acts + 5 case law)
- **Evaluation**: 393-query cross-domain benchmark ready for research paper (293 baseline + 100 cross-domain)

---

## 🎯 Common Workflows

### 1. Development
```bash
# Terminal 1: Backend
cd backend
python app.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

### 2. Load Data + Test
```bash
# Load data
cd backend
python scripts/production_data_loader.py --full

# Start with data
python app.py

# Test in another terminal
curl http://localhost:8000/api/health
```

### 3. Research Evaluation
```bash
# Ensure data loaded
cd backend
python scripts/check_db_status.py

# Run evaluation
cd evaluation
python run_evaluation.py

# Check outputs
ls *.tex *.png
```

---

## 📚 Documentation

All documentation moved to `docs/`:

- **QUICKSTART.md**: Getting started guide
- **INTELLIGENCE_LAYER.md**: Analytics system details
- **PRODUCTION_DEPLOYMENT.md**: Deploy to production
- **SYSTEM_STATUS.md**: Complete system overview
- **INSTALLATION_FIX.md**: Installation troubleshooting

---

## 🎉 SUCCESS!

**Before**: Messy structure, scattered files, confusing entry points  
**After**: Clean organization, single command, production-ready

**To start everything**:
```bash
# Backend
cd backend && python app.py

# Frontend (new terminal)
cd frontend && npm run dev
```

Visit: http://localhost:3000 🚀
