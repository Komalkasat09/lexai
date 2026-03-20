# 🤖 RAG + Groq LLM Integration - Complete Setup Guide

## What Was Built

A complete AI-powered contract analysis pipeline with:
- ✅ **ChromaDB RAG System** - Vector database with 12 bare act sections
- ✅ **Groq LLM Integration** - 5-step prompt pipeline for contract analysis
- ✅ **Hallucination Guard** - Validates all bare act citations
- ✅ **Complete Orchestration** - End-to-end analysis pipeline
- ✅ **FastAPI Endpoints** - Updated with full analysis capabilities

---

## 📦 New Dependencies Installed

Update your environment:
```bash
pip install groq chromadb
```

Or reinstall all dependencies:
```bash
pip install -r requirements.txt
```

---

## 🔧 Setup Instructions

### Step 1: Get Groq API Key

1. Visit [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign up/login (free account available)
3. Create a new API key
4. Copy the key (starts with `gsk_...`)

### Step 2: Configure Environment

Create `.env` file in the backend directory:
```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:
```bash
GROQ_API_KEY=gsk_your_actual_api_key_here
```

### Step 3: Initialize ChromaDB

The vector database will initialize automatically on first run, but you can test it:
```bash
python chroma_setup.py
```

Expected output:
```
✓ Created new collection 'bare_acts'
✓ Loaded 12 bare act sections into ChromaDB
```

---

## 🏗️ Architecture Overview

### New Modules Created

1. **[chroma_setup.py](chroma_setup.py)** - ChromaDB initialization
   - Loads 12 bare act sections (Indian Contract Act, Arbitration Act, Companies Act)
   - Provides vector similarity search
   - Validates citations

2. **[rag_retrieval.py](rag_retrieval.py)** - RAG retrieval layer
   - Retrieves top 2 relevant bare acts per clause
   - Formats context for LLM prompts
   - Supports batch retrieval

3. **[hallucination_guard.py](hallucination_guard.py)** - Citation validation
   - Extracts citations from LLM responses using regex
   - Validates against ChromaDB
   - Removes invalid citations automatically

4. **[groq_prompts.py](groq_prompts.py)** - 5 Groq LLM functions
   - `identify_contract()` - Extract contract metadata
   - `classify_clauses()` - Classify clause types
   - `assess_risk()` - Risk assessment with RAG context
   - `detect_missing()` - Find missing clauses
   - `suggest_revisions()` - Generate improved clause text

5. **[orchestrator.py](orchestrator.py)** - Pipeline orchestration
   - Coordinates all 5 LLM calls in sequence
   - Integrates RAG retrieval
   - Applies hallucination guard
   - Merges all outputs into final JSON

6. **[main.py](main.py)** - Updated FastAPI endpoints
   - `/api/analyze-contract` - Full AI analysis (NEW)
   - `/api/upload-contract` - Basic extraction only
   - `/health` - Shows AI capabilities status

---

## 🚀 API Endpoints

### Full AI Analysis (NEW)
```bash
POST /api/analyze-contract
```

Upload a contract and get complete analysis:
```json
{
  "success": true,
  "filename": "contract.pdf",
  "analysis": {
    "overview": {
      "contract_type": "Service Agreement",
      "party_a": "TechCorp Solutions Pvt Ltd",
      "party_b": "Global Enterprises Ltd",
      "governing_law": "Laws of India",
      "jurisdiction": "Bangalore",
      "effective_date": "January 15, 2024",
      "duration": "12 months"
    },
    "clauses": [
      {
        "clause_number": "1",
        "heading": "PAYMENT TERMS",
        "content": "...",
        "type": "Payment Terms"
      }
    ],
    "risks": [
      {
        "clause_number": 1,
        "clause_heading": "Indemnity",
        "risk_level": "high",
        "explanation": "Violates Section 73 of Indian Contract Act 1872..."
      }
    ],
    "missing_clauses": [
      {
        "clause_type": "Data Protection",
        "importance": "critical",
        "reason": "Required for handling personal data under law"
      }
    ],
    "suggested_revisions": [
      {
        "clause_number": 1,
        "clause_heading": "Indemnity",
        "original_issue": "Unlimited liability exposure",
        "revised_clause": "Party A shall indemnify...",
        "key_changes": "Added liability cap as per Section 74..."
      }
    ],
    "metadata": {
      "total_clauses": 10,
      "high_risk_count": 2,
      "missing_clauses_count": 1,
      "revisions_suggested": 2
    }
  }
}
```

### Basic Extraction Only
```bash
POST /api/upload-contract
```

Returns only extracted clauses without AI analysis (doesn't require API key).

### Health Check
```bash
GET /health
```

Shows system status:
```json
{
  "status": "healthy",
  "extraction_enabled": true,
  "segmentation_enabled": true,
  "llm_enabled": true,
  "rag_enabled": true,
  "groq_api_configured": true
}
```

---

## 🧪 Testing the Pipeline

### Test Individual Components

1. **Test ChromaDB Setup:**
```bash
python chroma_setup.py
```

2. **Test RAG Retrieval:**
```bash
python rag_retrieval.py
```

3. **Test Hallucination Guard:**
```bash
python hallucination_guard.py
```

4. **Test Groq Integration:**
```bash
python groq_prompts.py
```

5. **Test Full Orchestration:**
```bash
python orchestrator.py
```

### Test API Endpoint

1. **Start the server:**
```bash
python main.py
```

2. **Test with cURL:**
```bash
curl -X POST "http://localhost:8000/api/analyze-contract" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_contract.pdf"
```

3. **Or use the interactive docs:**
   - Visit http://localhost:8000/docs
   - Try the `/api/analyze-contract` endpoint
   - Upload a test contract

---

## 📊 Bare Acts in ChromaDB

The system includes these sections:

### Indian Contract Act 1872
- Section 10 - What agreements are contracts
- Section 23 - Lawful consideration and objects
- Section 27 - Agreement in restraint of trade
- Section 28 - Agreements in restraint of legal proceedings
- Section 73 - Compensation for breach
- Section 74 - Compensation where penalty stipulated

### Arbitration and Conciliation Act 1996
- Section 7 - Arbitration agreement
- Section 8 - Power to refer parties to arbitration
- Section 11 - Appointment of arbitrators

### Companies Act 2013
- Section 2 - Definitions
- Section 179 - Powers of Board
- Section 184 - Disclosure of interest by director

---

## 🛡️ Hallucination Guard Features

The system prevents hallucinated citations through:

1. **Automatic Citation Extraction** - Regex patterns detect citations
2. **ChromaDB Validation** - Each citation checked against database
3. **Automatic Removal** - Invalid citations stripped from responses
4. **Prompt Injection** - LLM receives list of valid sections only

Example validation:
```python
from hallucination_guard import HallucinationGuard

guard = HallucinationGuard(chroma_manager)

# Validate citation
is_valid = guard.validate_citation("Section 73", "Indian Contract Act 1872")
# Returns: True

is_valid = guard.validate_citation("Section 999", "Indian Contract Act 1872")
# Returns: False (section doesn't exist)
```

---

## 🔄 Pipeline Flow

```
1. Upload Contract (PDF/DOCX)
        ↓
2. Extract Text → Segment Clauses
        ↓
3. [LLM Call 1] Identify Contract Overview
        ↓
4. [LLM Call 2] Classify Clauses
        ↓
5. [RAG] Retrieve Relevant Bare Acts
        ↓
6. [LLM Call 3] Assess Risk (with RAG context)
        ↓
7. [LLM Call 4] Detect Missing Clauses
        ↓
8. [LLM Call 5] Suggest Revisions (high-risk only)
        ↓
9. [Hallucination Guard] Validate Citations
        ↓
10. Return Complete Analysis JSON
```

---

## ⚙️ Configuration Options

### Groq Model Settings

Edit [groq_prompts.py](groq_prompts.py#L20-L21):
```python
GROQ_MODEL = "llama-3.3-70b-versatile"  # Latest Groq model (Feb 2026)
GROQ_TEMPERATURE = 0.1                   # Low temperature for consistency
```

**Note:** Previous model `llama3-70b-8192` was decommissioned in Feb 2026.

### Hallucination Guard

Enable/disable in orchestrator:
```python
orchestrator = ContractAnalysisOrchestrator(
    enable_hallucination_guard=True  # Set to False to disable
)
```

### RAG Retrieval Count

Adjust number of sections retrieved per clause:
```python
# In rag_retrieval.py
retriever.retrieve_for_clause(
    clause_text=text,
    n_results=2  # Change to retrieve more/fewer sections
)
```

---

## 🐛 Troubleshooting

### "Groq API key not configured"
- Check `.env` file exists in backend directory
- Verify `GROQ_API_KEY` is set correctly
- Restart server after updating `.env`

### "ChromaDB collection not found"
- Run `python chroma_setup.py` to initialize
- Check `chroma_db/` directory was created
- Try resetting: `ChromaDBManager().reset_collection()`

### "Module not found" errors
- Run `pip install -r requirements.txt`
- Ensure virtual environment is activated
- Check Python version (3.9+ required)

### Slow API responses
- First request initializes ChromaDB (slow)
- Subsequent requests are much faster
- Groq API calls take 2-5 seconds each

---

## 📝 Output Format

The `/api/analyze-contract` endpoint returns this structure:

```json
{
  "success": true,
  "filename": "contract.pdf",
  "document_metadata": {
    "format": "PDF",
    "page_count": 10,
    "total_characters": 15000,
    "total_clauses": 12
  },
  "analysis": {
    "overview": { ... },
    "clauses": [ ... ],
    "risks": [ ... ],
    "missing_clauses": [ ... ],
    "suggested_revisions": [ ... ],
    "metadata": {
      "total_clauses": 12,
      "high_risk_count": 2,
      "missing_clauses_count": 1,
      "revisions_suggested": 2,
      "hallucination_guard_enabled": true
    }
  }
}
```

---

## 🔮 Next Steps

To expand the system:

1. **Add More Bare Acts** - Edit `BARE_ACTS_DATA` in [chroma_setup.py](chroma_setup.py#L11)
2. **Customize Risk Levels** - Modify prompts in [groq_prompts.py](groq_prompts.py)
3. **Add Clause Types** - Update classification list in `classify_clauses()`
4. **Adjust RAG Threshold** - Tune `risk_threshold` in orchestrator
5. **Frontend Integration** - Connect Next.js to `/api/analyze-contract`

---

## 📚 Module Reference

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| chroma_setup.py | ChromaDB initialization | `initialize_chroma_db()` |
| rag_retrieval.py | Vector similarity search | `retrieve_for_clause()` |
| hallucination_guard.py | Citation validation | `validate_citation()` |
| groq_prompts.py | LLM prompt functions | 5 analysis functions |
| orchestrator.py | Pipeline coordination | `orchestrate_analysis()` |
| main.py | FastAPI endpoints | `/api/analyze-contract` |

---

**🎉 Your AI-powered contract review assistant is ready!**

Start the server: `python main.py`  
Visit API docs: http://localhost:8000/docs
