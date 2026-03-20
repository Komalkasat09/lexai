# 🚀 Quick Start Guide

## What We Built

Phase 1 of your AI-powered contract review assistant is complete! Here's what's ready:

### ✅ Completed Features

1. **Document Extraction Module** (`document_extractor.py`)
   - Extracts text from PDF files using PyMuPDF
   - Extracts text from DOCX files using python-docx
   - Validates documents are typed (rejects scanned PDFs)
   - Cleans and normalizes extracted text
   - Extracts metadata (page count, author, etc.)

2. **Clause Segmentation Module** (`clause_segmenter.py`)
   - Intelligently splits contracts into logical clauses
   - Detects multiple heading formats:
     - Numbered: `1. DEFINITIONS`, `1.1 Payment Terms`
     - Article/Section: `Article 1: Definitions`
     - Roman numerals: `I. Definitions`
     - All-caps: `DEFINITIONS`
   - Outputs structured clause objects with:
     - Clause number
     - Heading text
     - Full content
     - Hierarchy level
     - Start line number
   - Search functionality to find clauses by keyword

3. **FastAPI REST API** (`main.py`)
   - POST `/api/upload-contract` - Upload and process contracts
   - GET `/health` - Health check
   - GET `/api/supported-formats` - Get supported file types
   - Automatic API documentation at `/docs`
   - CORS configured for Next.js frontend

4. **Test Pipeline** (`test_pipeline.py`)
   - Includes sample contract for testing
   - Tests extraction and segmentation
   - Shows detailed clause structure
   - Can test with your own PDF/DOCX files

## 📦 Installation

### Option 1: Automatic Setup (Recommended)

```bash
cd backend
./setup.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Create .env file
- Run the test pipeline

### Option 2: Manual Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Run test
python test_pipeline.py
```

## 🧪 Testing the Pipeline

### Test with Sample Contract

```bash
python test_pipeline.py
```

This runs through a complete sample contract and shows:
- Clause extraction
- Segmentation results
- Search functionality
- JSON export format
- Statistics

### Test with Your Own File

```bash
python test_pipeline.py /path/to/your/contract.pdf
```

## 🚀 Running the API Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the server
python main.py
```

The server will start on: http://localhost:8000

- **API Docs**: http://localhost:8000/docs (interactive testing interface)
- **Health Check**: http://localhost:8000/health

### Test API with cURL

```bash
curl -X POST "http://localhost:8000/api/upload-contract" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_contract.pdf"
```

## 📂 File Structure

```
backend/
├── main.py                    # FastAPI application with endpoints
├── document_extractor.py      # PDF/DOCX text extraction
├── clause_segmenter.py        # Smart clause segmentation
├── test_pipeline.py           # Test script with sample contract
├── requirements.txt           # Python dependencies
├── setup.sh                   # Automatic setup script
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
└── README.md                 # Full documentation
```

## 🔄 How the Pipeline Works

```
1. Upload PDF/DOCX
        ↓
2. Extract Text (document_extractor.py)
   - Validate file type
   - Extract text from document
   - Reject scanned documents
   - Clean and normalize text
        ↓
3. Segment Clauses (clause_segmenter.py)
   - Detect headings using regex patterns
   - Split into logical sections
   - Assign clause numbers and levels
   - Create structured clause objects
        ↓
4. Return JSON Response
   {
     "clauses": [
       {
         "clause_number": "1",
         "heading": "DEFINITIONS",
         "content": "...",
         "level": 1,
         "start_line": 10
       }
     ]
   }
```

## 📝 Example Output

When you upload a contract, you get:

```json
{
  "success": true,
  "filename": "service_agreement.pdf",
  "metadata": {
    "format": "PDF",
    "page_count": 10,
    "total_characters": 15234,
    "total_clauses": 25
  },
  "clauses": [
    {
      "clause_number": "1",
      "heading": "DEFINITIONS",
      "content": "For the purposes of this Agreement...",
      "level": 1,
      "start_line": 42
    },
    {
      "clause_number": "1.1",
      "heading": "Confidential Information",
      "content": "\"Confidential Information\" means...",
      "level": 2,
      "start_line": 45
    }
  ]
}
```

## ⚠️ Important Notes

### Supported Documents
✅ Typed PDF files
✅ DOCX files (Word 2007+)

❌ Scanned PDFs (no OCR yet)
❌ Handwritten documents
❌ Legacy .doc files

### File Size Limit
Maximum: 10 MB per file

## 🔮 Next Steps (Not Yet Implemented)

Ready to add these features next:

1. **Groq LLM Integration**
   - Set up Groq API client
   - Implement 5-step prompt pipeline
   - Contract type identification
   - Clause classification

2. **ChromaDB RAG**
   - Set up vector database
   - Index Bare Acts (Indian Contract Act, etc.)
   - Semantic search for relevant sections

3. **Advanced Analysis**
   - Risk assessment (🟢🟡🔴)
   - Missing clause detection
   - Improvement suggestions
   - Bare Act cross-references

## 🐛 Troubleshooting

### Dependencies Not Installing

Make sure you're using Python 3.9+:
```bash
python3 --version
```

### "Command not found: python"

Use `python3` instead:
```bash
python3 main.py
python3 test_pipeline.py
```

### "Document appears to be scanned"

Only typed PDFs are supported. Scanned documents need OCR preprocessing (not implemented yet).

## 💡 Tips

1. **Interactive API Testing**: Use http://localhost:8000/docs for a web interface to test endpoints

2. **View Sample Contract**: Look at the sample contract in `test_pipeline.py` to understand the expected format

3. **Debug Output**: Run `test_pipeline.py` to see detailed clause structure before testing API

4. **JSON Export**: All clauses have `.to_dict()` method for easy JSON serialization

## 📞 Need Help?

- Check [README.md](README.md) for detailed documentation
- Review code comments in each module
- Test with the sample contract first
- Use the interactive API docs at `/docs`

---

**You're all set!** 🎉 Run `./setup.sh` to get started.
