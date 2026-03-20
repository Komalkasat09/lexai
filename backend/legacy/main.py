"""
FastAPI Backend for AI-Powered Contract Review Assistant
Main API endpoints for document upload and processing.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, List
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.document_extractor import DocumentExtractor
from core.clause_segmenter import ClauseSegmenter
from core.orchestrator import ContractAnalysisOrchestrator

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Contract Review Assistant API",
    description="AI-powered contract analysis for Indian commercial lawyers",
    version="1.0.0"
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Initialize orchestrator (lazy loading)
_orchestrator = None


def get_orchestrator() -> ContractAnalysisOrchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ContractAnalysisOrchestrator()
    return _orchestrator


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Contract Review Assistant API",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    # Check if Groq API key is set
    groq_enabled = bool(os.environ.get("GROQ_API_KEY"))
    
    return {
        "status": "healthy",
        "extraction_enabled": True,
        "segmentation_enabled": True,
        "llm_enabled": groq_enabled,
        "rag_enabled": True,
        "groq_api_configured": groq_enabled
    }


@app.post("/api/analyze-contract")
async def analyze_contract(file: UploadFile = File(...)):
    """
    Full contract analysis endpoint with AI-powered insights.
    
    This endpoint performs:
    1. Document extraction and clause segmentation
    2. Contract overview identification
    3. Clause classification
    4. Risk assessment with RAG-retrieved bare act sections
    5. Missing clause detection
    6. Improvement suggestions for high-risk clauses
    
    Args:
        file: Uploaded contract file (PDF or DOCX)
        
    Returns:
        Complete analysis JSON with all sections
        
    Raises:
        HTTPException: If processing fails or API key not configured
    """
    # Check if Groq API key is configured
    if not os.environ.get("GROQ_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Groq API key not configured. Please set GROQ_API_KEY environment variable."
        )
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed."
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB."
        )
    
    # Save to temporary file for processing
    temp_file = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Step 1: Extract text from document
        try:
            extractor = DocumentExtractor()
            extracted_text, metadata = extractor.extract(temp_file_path, file_extension)
            cleaned_text = extractor.clean_text(extracted_text)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Text extraction failed: {str(e)}"
            )
        
        # Step 2: Segment into clauses
        try:
            segmenter = ClauseSegmenter()
            clauses = segmenter.segment(cleaned_text)
            clauses_dict = segmenter.get_clauses_as_dict()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Clause segmentation failed: {str(e)}"
            )
        
        # Step 3: Run full AI analysis pipeline
        try:
            orchestrator = get_orchestrator()
            analysis_result = orchestrator.orchestrate_analysis(
                clauses=clauses_dict,
                full_text=cleaned_text
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"AI analysis failed: {str(e)}"
            )
        
        # Prepare final response
        response_data = {
            "success": True,
            "filename": file.filename,
            "document_metadata": {
                **metadata,
                "total_characters": len(cleaned_text),
                "total_clauses": len(clauses_dict),
            },
            "analysis": analysis_result
        }
        
        return JSONResponse(content=response_data, status_code=200)
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@app.post("/api/upload-contract")
async def upload_contract(file: UploadFile = File(...)) -> JSONResponse:
    """
    Basic upload endpoint - extracts and segments only (no AI analysis).
    
    This endpoint:
    1. Validates file type (PDF or DOCX only)
    2. Extracts text from the document
    3. Segments the contract into clauses
    4. Returns structured clause data
    
    For full AI analysis, use /api/analyze-contract instead.
    
    Args:
        file: Uploaded contract file
        
    Returns:
        JSON response with extracted clauses and metadata
        
    Raises:
        HTTPException: If file validation or processing fails
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed."
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB."
        )
    
    # Save to temporary file for processing
    temp_file = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Step 1: Extract text from document
        try:
            extractor = DocumentExtractor()
            extracted_text, metadata = extractor.extract(temp_file_path, file_extension)
            cleaned_text = extractor.clean_text(extracted_text)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Text extraction failed: {str(e)}"
            )
        
        # Step 2: Segment into clauses
        try:
            segmenter = ClauseSegmenter()
            clauses = segmenter.segment(cleaned_text)
            clauses_dict = segmenter.get_clauses_as_dict()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Clause segmentation failed: {str(e)}"
            )
        
        # Prepare response
        response_data = {
            "success": True,
            "filename": file.filename,
            "metadata": {
                **metadata,
                "total_characters": len(cleaned_text),
                "total_clauses": len(clauses),
            },
            "clauses": clauses_dict,
            "message": f"Successfully extracted {len(clauses)} clauses from {file.filename}. Use /api/analyze-contract for full AI analysis."
        }
        
        return JSONResponse(content=response_data, status_code=200)
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@app.get("/api/supported-formats")
async def get_supported_formats():
    """Get list of supported document formats."""
    return {
        "formats": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "notes": [
            "Only typed documents are supported",
            "Scanned or handwritten documents will be rejected",
            "Legacy .doc format is not supported - please use .docx"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("CONTRACT REVIEW ASSISTANT API")
    print("=" * 80)
    print(f"Starting server on http://localhost:8000")
    print(f"API documentation: http://localhost:8000/docs")
    print(f"Allowed file types: {', '.join(ALLOWED_EXTENSIONS)}")
    print("=" * 80)
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
