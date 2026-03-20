# Contract Review Assistant - Backend

AI-powered contract review assistant for Indian commercial lawyers.

## Current Status: Phase 1 - Document Extraction & Clause Segmentation

This implementation covers the foundational document processing pipeline:
- ✅ PDF and DOCX file upload
- ✅ Text extraction with typed-document validation
- ✅ Smart clause segmentation using heading detection
- ✅ FastAPI REST endpoints
- ⏳ LLM integration (Groq) - Not implemented yet
- ⏳ RAG with ChromaDB - Not implemented yet
- ⏳ Risk assessment - Not implemented yet
- ⏳ Bare Act cross-references - Not implemented yet

## Installation

### Prerequisites
- Python 3.9 or higher
- pip package manager

### Setup

1. **Create a virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Create environment file**:
```bash
cp .env.example .env
```

## Running the Application

### Option 1: Start the API Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Option 2: Run the Test Pipeline

Test the extraction and segmentation with a sample contract:

```bash
python test_pipeline.py
```

Test with your own PDF or DOCX file:

```bash
python test_pipeline.py path/to/your/contract.pdf
```

## API Endpoints

### `POST /api/upload-contract`

Upload and process a contract document.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: file (PDF or DOCX)

**Response:**
```json
{
  "success": true,
  "filename": "contract.pdf",
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
      "content": "...",
      "level": 1,
      "start_line": 10
    }
  ]
}
```

### `GET /api/supported-formats`

Get list of supported document formats.

### `GET /health`

Health check endpoint.

## Project Structure

```
backend/
├── main.py                  # FastAPI application
├── document_extractor.py    # PDF/DOCX text extraction
├── clause_segmenter.py      # Clause segmentation logic
├── test_pipeline.py         # Test script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## How It Works

### 1. Document Extraction (`document_extractor.py`)

- Supports PDF (via PyMuPDF) and DOCX (via python-docx)
- Validates that documents are typed (not scanned)
- Extracts metadata (page count, author, etc.)
- Cleans extracted text (removes excessive whitespace, page numbers)

### 2. Clause Segmentation (`clause_segmenter.py`)

Uses multiple pattern-matching strategies to detect clause headings:

- **Numbered headings**: `1. DEFINITIONS`, `1.1 Payment Terms`
- **Article/Section format**: `Article 1: Definitions`, `Section 2.1: Payment`
- **Roman numerals**: `I. Definitions`, `II. Payment Terms`
- **All-caps headings**: `DEFINITIONS`, `PAYMENT TERMS`

Each clause includes:
- Clause number
- Heading text
- Full content
- Hierarchy level (1 for main, 2 for sub-sections)
- Starting line number

### 3. FastAPI Endpoint (`main.py`)

- Accepts file uploads
- Validates file type and size (max 10 MB)
- Processes document through extraction → segmentation pipeline
- Returns structured JSON response

## Supported Document Types

✅ **Supported:**
- Typed PDF documents
- DOCX (Word 2007+) documents
- Commercial contracts, NDAs, service agreements, vendor agreements

❌ **Not Supported:**
- Scanned PDF documents (OCR not implemented)
- Handwritten documents
- Legacy .doc format (Word 97-2003)
- Images or other formats

## Testing

### Manual Testing with cURL

```bash
curl -X POST "http://localhost:8000/api/upload-contract" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@contract.pdf"
```

### Using the Interactive API Docs

1. Start the server: `python main.py`
2. Open http://localhost:8000/docs
3. Try the `/api/upload-contract` endpoint
4. Upload a test contract and view the response

## Next Steps (Not Yet Implemented)

The following features are planned but not yet built:

1. **Groq LLM Integration**
   - Multi-step prompt pipeline
   - Contract type identification
   - Clause classification
   - Risk assessment

2. **RAG with ChromaDB**
   - Vector database for Bare Acts
   - Semantic search for relevant sections
   - Indian Contract Act 1872
   - Arbitration and Conciliation Act 1996
   - Companies Act 2013

3. **Advanced Analysis**
   - Missing clause detection
   - Improvement suggestions
   - Bare Act cross-references with validation

4. **Output Generation**
   - Structured JSON reports
   - Risk flagging (🟢🟡🔴)
   - Copy-paste ready clause revisions

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Future: Groq API key (not used yet)
# GROQ_API_KEY=your_groq_api_key_here

# Future: ChromaDB settings (not used yet)
# CHROMA_PERSIST_DIR=./chroma_db
```

## Dependencies

- **FastAPI**: Modern web framework for building APIs
- **PyMuPDF (fitz)**: PDF text extraction
- **python-docx**: DOCX file processing
- **uvicorn**: ASGI server for FastAPI
- **python-multipart**: File upload support

## Troubleshooting

### "Document appears to be scanned"
→ Only typed PDFs are supported. If your PDF is scanned, you'll need OCR preprocessing.

### "Failed to extract text"
→ Ensure the file is not corrupted and is a valid PDF/DOCX file.

### "Unsupported file format"
→ Only .pdf and .docx files are accepted.

## License

Proprietary - For internal use only

## Contact

For questions or issues, contact the development team.
