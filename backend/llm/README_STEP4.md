# Step 4: Legal LLM Layer - Documentation

## Overview
Production-grade LLM integration for the legal research assistant, combining **SmartRetriever** (Step 3) with **Groq's LLM** to generate accurate, citation-aware legal answers.

## Key Features

### 1. **Deterministic LLM Responses**
```python
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.0  # Fully deterministic
GROQ_SEED = 42          # Consistent seed
```
- Same query = same answer (critical for legal reliability)
- No randomness in legal interpretations
- Reproducible results for verification

### 2. **Strict Legal System Prompt**
9 critical rules enforced:
- ✅ Only use information from provided context (no hallucination)
- ✅ Always cite sources (every legal statement has reference)
- ✅ Acknowledge limitations (if context insufficient)
- ✅ Warn about BNS/BNSS transitions (IPC/CrPC → new laws)
- ✅ Flag uncertainties (LOW/MEDIUM confidence warnings)
- ✅ Never fabricate information
- ✅ Preserve legal language (precise terminology)
- ✅ Check dates (mention year of cases/amendments)
- ✅ Note overruling (don't rely on overruled cases)

### 3. **Confidence-Based Response Filtering**
```python
if confidence == "LOW":
    return "I cannot provide a reliable answer..."
    # Prevents hallucinations by refusing to answer
```

### 4. **BNS/BNSS Transition Handling**
- Automatically warns when IPC/CrPC sections are replaced
- Example: "IPC 420 → BNS 318" with change description
- Critical for 2023 law transition compliance

## File Structure

```
backend/
├── llm/
│   ├── __init__.py           # Package initialization
│   └── legal_llm.py          # Main LLM class (560 lines)
├── demo_legal_llm.py         # Comprehensive demo
└── verify_legal_llm.py       # Structure verification
```

## Class: `LegalLLM`

### Main Functions

#### 1. `answer_legal_question(query, include_reasoning=True)`
**Purpose**: Primary legal Q&A function

**Process**:
1. Retrieve context using SmartRetriever
2. Check confidence (trigger uncertainty if LOW)
3. Format context for LLM
4. Generate answer with strict prompt
5. Return structured response with citations

**Returns**:
```python
{
    "answer": str,              # LLM-generated answer
    "confidence": str,          # HIGH/MEDIUM/LOW
    "trigger_uncertainty": bool, # Show warning?
    "sources": {
        "bare_acts": List[Dict],
        "case_laws": List[Dict],
        "amendments": List[Dict]
    },
    "warnings": List[str],      # BNS/BNSS, overruling
    "query_type": str,          # section_lookup, case_search, etc.
    "stats": Dict               # Retrieval statistics
}
```

**Example**:
```python
legal_llm = LegalLLM(db_path="./legal_research_db")
result = legal_llm.answer_legal_question("What is Section 420 IPC?")

print(result['answer'])
# "Section 420 of the Indian Penal Code 1860 deals with 
#  'Cheating and dishonestly inducing delivery of property'..."
```

#### 2. `explain_section(act_name, section_number)`
**Purpose**: Detailed explanation of a specific legal section

**Features**:
- Covers purpose, scope, key elements
- Lists punishments/consequences
- Includes case law interpretations
- Shows recent amendments
- BNS/BNSS transition notes

**Example**:
```python
result = legal_llm.explain_section("Indian Penal Code 1860", "302")
```

#### 3. `summarize_judgment(citation)`
**Purpose**: Summarize a legal judgment by citation

**Covers**:
- Case name and citation
- Court and year
- Facts (brief)
- Legal issues
- Judgment/Held
- Legal principles established
- Overruling status

**Example**:
```python
result = legal_llm.summarize_judgment("AIR 2020 SC 1234")
```

#### 4. `compare_sections(old_section, new_section)`
**Purpose**: Compare IPC/CrPC with BNS/BNSS sections

**Example**:
```python
result = legal_llm.compare_sections("IPC 420", "BNS 318")
```

#### 5. `get_legal_opinion(facts, legal_issue)`
**Purpose**: Research opinion based on facts and issue

**⚠️ WARNING**: Includes disclaimer - NOT formal legal advice

**Example**:
```python
result = legal_llm.get_legal_opinion(
    facts="Party A promised to marry Party B but later refused...",
    legal_issue="Can this be prosecuted as rape under IPC 376?"
)
```

### Internal Functions

#### `_format_retrieval_context(retrieval_result)`
Converts SmartRetriever output into structured context for LLM:
- Bare acts with BNS/BNSS notes
- Case law with overruling warnings
- Amendments with effective dates
- Retrieval statistics

#### `_call_groq_llm(user_prompt, system_prompt, context)`
Calls Groq API with deterministic settings:
- Temperature = 0.0
- Seed = 42
- Max tokens = 2048

## Usage

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Set Groq API key
export GROQ_API_KEY='your-api-key-here'
```

Get API key from: https://console.groq.com/keys

### Basic Usage

```python
from llm.legal_llm import LegalLLM

# Initialize
legal_llm = LegalLLM(db_path="./legal_research_db")

# Ask a question
result = legal_llm.answer_legal_question(
    "What is the punishment for cheating under IPC?"
)

# Check confidence
if result['confidence'] == 'HIGH':
    print(result['answer'])
else:
    print("Low confidence - verify with primary sources")
```

### Running Demos

**1. Structure Verification** (no API key needed):
```bash
python verify_legal_llm.py
```
Checks imports, configuration, class structure.

**2. Full Demo** (requires API key):
```bash
export GROQ_API_KEY='your-key'
python demo_legal_llm.py
```
Tests:
- Section lookup queries
- Legal questions with case law
- Punishment queries
- explain_section() function

## Integration with Smart Retriever

```
User Query
    ↓
SmartRetriever.retrieve(query)
    ↓
7-Step Pipeline:
  1. Query Classification
  2. Parallel Retrieval (bare_acts + case_law)
  3. Confidence Scoring
  4. Overruling Check
  5. Amendment Check
  6. BNS/BNSS Middleware
  7. Enriched Context
    ↓
LegalLLM._format_retrieval_context()
    ↓
Groq LLM (temp=0.0, seed=42)
    ↓
Structured Answer with Citations
```

## Response Examples

### HIGH Confidence Response
```python
{
    "answer": "Section 420 of the Indian Penal Code 1860 addresses 'Cheating and dishonestly inducing delivery of property'. According to the provision, whoever cheats and thereby dishonestly induces the person deceived to deliver any property shall be punished with imprisonment up to seven years and fine.\n\nThe Supreme Court in State of Maharashtra v. Rajesh Kumar (AIR 2019 SC 1234) held that for establishing the offense, the prosecution must prove: (1) deception, (2) fraudulent inducement from inception, and (3) delivery of property.\n\n⚠️ Note: IPC Section 420 has been replaced by BNS Section 318 (substantially same provisions).",
    
    "confidence": "HIGH",
    "trigger_uncertainty": false,
    "warnings": [
        "⚠️ This answer references IPC sections replaced by BNS (2023)"
    ],
    "sources": {
        "bare_acts": [{"act_name": "IPC 1860", "section_number": "420", ...}],
        "case_laws": [{"case_name": "State v. Rajesh Kumar", ...}]
    }
}
```

### LOW Confidence Response (Triggers Uncertainty)
```python
{
    "answer": "I cannot provide a reliable answer based on the current database. The retrieved information has low confidence. Please consult primary sources or a qualified lawyer.",
    
    "confidence": "LOW",
    "trigger_uncertainty": true,
    "warnings": ["⚠️ Insufficient reliable information in database"],
    "sources": {"bare_acts": [], "case_laws": [], "amendments": []}
}
```

## Testing Results

```
✓ Testing imports...
  ✓ Imported LegalLLM class
  ✓ Imported system prompt
  ✓ Imported configuration constants

✓ Testing configuration...
  Model: llama-3.3-70b-versatile
  Temperature: 0.0
  Seed: 42
  System Prompt Length: 1404 characters

✓ Checking system prompt rules...
  ✓ Contains rule: 'Only use information from the provided context'
  ✓ Contains rule: 'Always cite sources'
  ✓ Contains rule: 'Acknowledge limitations'
  ✓ Contains rule: 'Never fabricate'
  ✓ Contains rule: 'BNS/BNSS'

✓ Testing LegalLLM class structure...
  ✓ Method exists: __init__()
  ✓ Method exists: answer_legal_question()
  ✓ Method exists: explain_section()
  ✓ Method exists: summarize_judgment()
  ✓ Method exists: compare_sections()
  ✓ Method exists: get_legal_opinion()
```

## Production Considerations

### 1. **Error Handling**
- Groq API failures return user-friendly error messages
- Falls back gracefully on network issues
- Logs errors for debugging

### 2. **Rate Limiting**
- Monitor Groq API rate limits
- Implement retry logic if needed
- Cache common queries (future enhancement)

### 3. **Cost Management**
- Temperature=0.0 reduces token variance
- Max tokens=2048 controls costs
- Efficient context formatting

### 4. **Legal Accuracy**
- System prompt enforces strict citation rules
- Confidence filtering prevents unreliable answers
- BNS/BNSS warnings ensure compliance

## Next Steps

**Step 5**: Create FastAPI endpoints ([legal_research.py](../api/legal_research.py))
- Expose LegalLLM functions as REST API
- Add authentication/authorization
- Implement request logging

**Step 6**: Web scraping ([playwright_scraper.py](../data_pipeline/playwright_scraper.py))
- IndianKanoon, Supreme Court, E-Courts
- Respectful scraping with rate limiting

**Step 7**: Scheduling ([scheduler.py](../data_pipeline/scheduler.py))
- Nightly scraping jobs
- Weekly gazette monitoring
- Database updates

**Step 8**: Intelligence layer ([intelligence/](../intelligence/))
- Query logging
- Feedback handling
- Performance analytics

---

**Status**: ✅ Complete and verified  
**File**: [llm/legal_llm.py](legal_llm.py) (560 lines)  
**Dependencies**: SmartRetriever (Step 3), Groq API  
**Ready for**: FastAPI integration (Step 5)
