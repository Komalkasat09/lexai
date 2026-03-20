"""
STEP 5: LEGAL RESEARCH API
===========================
Production-grade FastAPI endpoints for legal research assistant.

This module provides REST API endpoints for:
- Legal Q&A (answer_legal_question)
- Section explanations
- Judgment summaries
- Section comparisons (IPC/CrPC → BNS/BNSS)
- Legal opinions

Features:
- Pydantic models for request/response validation
- Error handling with proper HTTP status codes
- CORS configuration for frontend integration
- Logging for monitoring
- Health check endpoint

Author: Legal Research System
Date: February 2026
"""

import os
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import LegalLLM from Step 4
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.legal_llm import LegalLLM

# Import Intelligence Layer (Step 8)
from intelligence.query_logger import QueryLogger, QueryLog, ResponseLog
from intelligence.analytics import AnalyticsEngine
from intelligence.feedback import FeedbackCollector

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================
app = FastAPI(
    title="Legal Research Assistant API",
    description="Production-grade API for Indian legal research with LLM-powered Q&A",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ============================================================================
# CORS CONFIGURATION
# ============================================================================
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# GLOBAL STATE
# ============================================================================
legal_llm: Optional[LegalLLM] = None
query_logger: Optional[QueryLogger] = None
analytics_engine: Optional[AnalyticsEngine] = None
feedback_collector: Optional[FeedbackCollector] = None

# ============================================================================
# PYDANTIC MODELS (Request/Response)
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    timestamp: str
    database: str = "connected"
    llm: str = "connected"

class LegalQuestionRequest(BaseModel):
    """Request model for legal Q&A"""
    query: str = Field(..., min_length=10, max_length=1000, description="Legal question to ask")
    include_reasoning: bool = Field(True, description="Include legal reasoning in response")
    
    @validator('query')
    def query_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Query cannot be empty")
        return v.strip()

class SectionExplanationRequest(BaseModel):
    """Request model for section explanation"""
    act_name: str = Field(..., description="Name of the Act (e.g., 'Indian Penal Code 1860')")
    section_number: str = Field(..., description="Section number (e.g., '420')")
    
    @validator('act_name', 'section_number')
    def field_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()

class JudgmentSummaryRequest(BaseModel):
    """Request model for judgment summary"""
    citation: str = Field(..., description="Case citation (e.g., 'AIR 2020 SC 1234')")
    
    @validator('citation')
    def citation_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Citation cannot be empty")
        return v.strip()

class SectionComparisonRequest(BaseModel):
    """Request model for section comparison"""
    old_section: str = Field(..., description="Old section (e.g., 'IPC 420')")
    new_section: str = Field(..., description="New section (e.g., 'BNS 318')")
    
    @validator('old_section', 'new_section')
    def section_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Section cannot be empty")
        return v.strip()

class LegalOpinionRequest(BaseModel):
    """Request model for legal opinion"""
    facts: str = Field(..., min_length=20, max_length=2000, description="Brief facts of the case")
    legal_issue: str = Field(..., min_length=10, max_length=500, description="Legal issue to address")
    
    @validator('facts', 'legal_issue')
    def field_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()

class FeedbackRequest(BaseModel):
    """Request model for user feedback"""
    query_id: int = Field(..., description="ID of the query being rated")
    response_id: int = Field(..., description="ID of the response being rated")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 (poor) to 5 (excellent)")
    helpful: bool = Field(..., description="Was the response helpful?")
    accurate: bool = Field(..., description="Was the response accurate?")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional feedback comment")

class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""
    success: bool
    message: str
    feedback_id: Optional[int] = None
    timestamp: str

class AnalyticsDashboardResponse(BaseModel):
    """Response model for analytics dashboard"""
    success: bool
    dashboard_data: Dict[str, Any]
    timestamp: str

class SourceDocument(BaseModel):
    """Model for source documents in response"""
    type: str  # "bare_act", "case_law", "amendment"
    text: str
    metadata: Dict[str, Any]
    confidence_score: Optional[float] = None
    bns_bnss_note: Optional[str] = None
    is_overruled: Optional[bool] = None
    warning: Optional[str] = None

class LegalResponse(BaseModel):
    """Unified response model for all legal queries"""
    success: bool
    answer: str
    confidence: str  # HIGH/MEDIUM/LOW
    trigger_uncertainty: bool
    query_type: str
    warnings: List[str]
    sources: Dict[str, List[Dict[str, Any]]]
    stats: Dict[str, int]
    timestamp: str

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: str

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_request_metadata(req: Request) -> tuple:
    """Extract session_id, ip_address, user_agent from request"""
    client_host = req.client.host if req.client else "unknown"
    user_agent = req.headers.get("user-agent", "unknown")
    session_id = req.headers.get("x-session-id", None)
    return session_id, client_host, user_agent

def log_query_and_response(query_text: str, query_type: str, result: dict, 
                           response_time_ms: int, req: Request) -> None:
    """Helper function to log query and response to intelligence layer"""
    if not query_logger:
        return
    
    # Extract metadata
    session_id, client_host, user_agent = extract_request_metadata(req)
    
    # Log query
    query_log = QueryLog(
        query_text=query_text,
        query_type=query_type,
        user_id=None,  # Add user auth later if needed
        session_id=session_id,
        ip_address=client_host,
        user_agent=user_agent
    )
    query_id = query_logger.log_query(query_log)
    
    # Log response
    if query_id:
        response_log = ResponseLog(
            query_id=query_id,
            answer=result['answer'],
            confidence=result['confidence'],
            sources_count=len(result.get('sources', {})),
            response_time_ms=response_time_ms,
            warnings=result.get('warnings', []),
            trigger_uncertainty=result.get('trigger_uncertainty', False)
        )
        query_logger.log_response(response_log)

# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize LegalLLM and Intelligence Layer on startup"""
    global legal_llm, query_logger, analytics_engine, feedback_collector
    try:
        logger.info("Initializing Legal Research API...")
        
        # Initialize LegalLLM
        legal_llm = LegalLLM(persist_directory="./legal_research_db")
        logger.info("✅ Legal LLM initialized")
        
        # Initialize Intelligence Layer
        query_logger = QueryLogger(db_path="./intelligence.db")
        analytics_engine = AnalyticsEngine(query_logger)
        feedback_collector = FeedbackCollector(query_logger)
        logger.info("✅ Intelligence Layer initialized")
        
        logger.info("✅ Legal Research API fully initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Legal Research API: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Legal Research API...")

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail or "An error occurred",
            timestamp=datetime.now().isoformat()
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if os.getenv("DEBUG") == "true" else None,
            timestamp=datetime.now().isoformat()
        ).dict()
    )

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Legal Research Assistant API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/health"
    }

@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status of the API, database, and LLM connection
    """
    try:
        # Check if LegalLLM is initialized
        if legal_llm is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LegalLLM not initialized"
            )
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            database="connected",
            llm="connected"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

@app.post("/api/legal/question", response_model=LegalResponse, tags=["Legal Research"])
async def answer_legal_question(request: LegalQuestionRequest, req: Request):
    """
    Answer a legal question using retrieval + LLM.
    
    This is the main endpoint for legal Q&A. It:
    1. Retrieves relevant legal context (bare acts, case law, amendments)
    2. Uses LLM to generate citation-aware answer
    3. Returns structured response with confidence level and warnings
    
    Args:
        request: LegalQuestionRequest with query and options
        req: FastAPI Request object for extracting metadata
    
    Returns:
        LegalResponse with answer, sources, confidence, and warnings
    
    Example:
        ```json
        {
            "query": "What is the punishment for cheating under IPC?",
            "include_reasoning": true
        }
        ```
    """
    try:
        if legal_llm is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LegalLLM not initialized"
            )
        
        logger.info(f"Processing legal question: {request.query[:100]}...")
        
        # Time the response
        start_time = time.time()
        
        # Call LegalLLM
        result = legal_llm.answer_legal_question(
            query=request.query,
            include_reasoning=request.include_reasoning
        )
        
        # Calculate response time and log
        response_time_ms = int((time.time() - start_time) * 1000)
        log_query_and_response(
            query_text=request.query,
            query_type="general_question",
            result=result,
            response_time_ms=response_time_ms,
            req=req
        )
        
        # Return structured response
        return LegalResponse(
            success=True,
            answer=result['answer'],
            confidence=result['confidence'],
            trigger_uncertainty=result['trigger_uncertainty'],
            query_type=result['query_type'],
            warnings=result['warnings'],
            sources=result['sources'],
            stats=result['stats'],
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error processing legal question: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/legal/section/explain", response_model=LegalResponse, tags=["Legal Research"])
async def explain_section(request: SectionExplanationRequest, req: Request):
    """
    Provide detailed explanation of a specific legal section.
    
    Covers:
    - Purpose and scope of the section
    - Key elements/ingredients
    - Punishments/consequences (if applicable)
    - Important case law interpretations
    - Recent amendments
    - BNS/BNSS transition notes
    
    Args:
        request: SectionExplanationRequest with act name and section number
        req: FastAPI Request object for extracting metadata
    
    Returns:
        LegalResponse with detailed section explanation
    
    Example:
        ```json
        {
            "act_name": "Indian Penal Code 1860",
            "section_number": "420"
        }
        ```
    """
    try:
        if legal_llm is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LegalLLM not initialized"
            )
        
        logger.info(f"Explaining {request.act_name} Section {request.section_number}")
        
        # Time the response
        start_time = time.time()
        
        # Call LegalLLM
        result = legal_llm.explain_section(
            act_name=request.act_name,
            section_number=request.section_number
        )
        
        # Calculate response time and log
        response_time_ms = int((time.time() - start_time) * 1000)
        query_text = f"Explain {request.act_name} Section {request.section_number}"
        log_query_and_response(
            query_text=query_text,
            query_type="section_explanation",
            result=result,
            response_time_ms=response_time_ms,
            req=req
        )
        
        return LegalResponse(
            success=True,
            answer=result['answer'],
            confidence=result['confidence'],
            trigger_uncertainty=result['trigger_uncertainty'],
            query_type=result['query_type'],
            warnings=result['warnings'],
            sources=result['sources'],
            stats=result['stats'],
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error explaining section: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/legal/judgment/summarize", response_model=LegalResponse, tags=["Legal Research"])
async def summarize_judgment(request: JudgmentSummaryRequest, req: Request):
    """
    Summarize a legal judgment by citation.
    
    Covers:
    - Case name and citation
    - Court and year
    - Facts (brief)
    - Legal issues
    - Judgment/Held
    - Legal principles established
    - Overruling status
    
    Args:
        request: JudgmentSummaryRequest with citation
    
    Returns:
        LegalResponse with judgment summary
    
    Example:
        ```json
        {
            "citation": "AIR 2020 SC 1234"
        }
        ```
    """
    try:
        if legal_llm is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LegalLLM not initialized"
            )
        
        logger.info(f"Summarizing judgment: {request.citation}")
        
        # Time the response
        start_time = time.time()
        
        # Call LegalLLM
        result = legal_llm.summarize_judgment(citation=request.citation)
        
        # Calculate response time and log
        response_time_ms = int((time.time() - start_time) * 1000)
        query_text = f"Summarize judgment: {request.citation}"
        log_query_and_response(
            query_text=query_text,
            query_type="judgment_summary",
            result=result,
            response_time_ms=response_time_ms,
            req=req
        )
        
        return LegalResponse(
            success=True,
            answer=result['answer'],
            confidence=result['confidence'],
            trigger_uncertainty=result['trigger_uncertainty'],
            query_type=result['query_type'],
            warnings=result['warnings'],
            sources=result['sources'],
            stats=result['stats'],
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error summarizing judgment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/legal/section/compare", response_model=LegalResponse, tags=["Legal Research"])
async def compare_sections(request: SectionComparisonRequest, req: Request):
    """
    Compare IPC/CrPC section with new BNS/BNSS section.
    
    Useful for understanding the 2023 legal code transition.
    
    Args:
        request: SectionComparisonRequest with old and new sections
    
    Returns:
        LegalResponse with comparison analysis
    
    Example:
        ```json
        {
            "old_section": "IPC 420",
            "new_section": "BNS 318"
        }
        ```
    """
    try:
        if legal_llm is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LegalLLM not initialized"
            )
        
        logger.info(f"Comparing {request.old_section} with {request.new_section}")
        
        # Time the response
        start_time = time.time()
        
        # Call LegalLLM
        result = legal_llm.compare_sections(
            old_section=request.old_section,
            new_section=request.new_section
        )
        
        # Calculate response time and log
        response_time_ms = int((time.time() - start_time) * 1000)
        query_text = f"Compare {request.old_section} with {request.new_section}"
        log_query_and_response(
            query_text=query_text,
            query_type="section_comparison",
            result=result,
            response_time_ms=response_time_ms,
            req=req
        )
        
        return LegalResponse(
            success=True,
            answer=result['answer'],
            confidence=result['confidence'],
            trigger_uncertainty=result['trigger_uncertainty'],
            query_type=result['query_type'],
            warnings=result['warnings'],
            sources=result['sources'],
            stats=result['stats'],
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error comparing sections: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/api/legal/opinion", response_model=LegalResponse, tags=["Legal Research"])
async def get_legal_opinion(request: LegalOpinionRequest, req: Request):
    """
    Generate legal opinion based on facts and issue.
    
    ⚠️ WARNING: This is for research assistance only, NOT formal legal advice.
    
    Args:
        request: LegalOpinionRequest with facts and legal issue
    
    Returns:
        LegalResponse with legal opinion (includes disclaimer)
    
    Example:
        ```json
        {
            "facts": "Party A promised to marry Party B but later refused...",
            "legal_issue": "Can this be prosecuted as rape under IPC 376?"
        }
        ```
    """
    try:
        if legal_llm is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LegalLLM not initialized"
            )
        
        logger.info(f"Generating legal opinion for: {request.legal_issue[:100]}...")
        
        # Time the response
        start_time = time.time()
        
        # Call LegalLLM
        result = legal_llm.get_legal_opinion(
            facts=request.facts,
            legal_issue=request.legal_issue
        )
        
        # Calculate response time and log
        response_time_ms = int((time.time() - start_time) * 1000)
        query_text = f"Facts: {request.facts[:100]}... Issue: {request.legal_issue}"
        log_query_and_response(
            query_text=query_text,
            query_type="legal_opinion",
            result=result,
            response_time_ms=response_time_ms,
            req=req
        )
        
        return LegalResponse(
            success=True,
            answer=result['answer'],
            confidence=result['confidence'],
            trigger_uncertainty=result['trigger_uncertainty'],
            query_type=result['query_type'],
            warnings=result['warnings'],
            sources=result['sources'],
            stats=result['stats'],
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error generating legal opinion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# INTELLIGENCE LAYER ENDPOINTS
# ============================================================================

@app.post("/api/feedback", response_model=FeedbackResponse, tags=["Intelligence"])
async def submit_feedback(request: FeedbackRequest):
    """
    Submit user feedback for a query/response pair.
    
    This helps improve the system by collecting user ratings and comments.
    
    Args:
        request: FeedbackRequest with rating, helpfulness, accuracy, and optional comment
    
    Returns:
        FeedbackResponse confirming feedback submission
    
    Example:
        ```json
        {
            "query_id": 123,
            "response_id": 456,
            "rating": 4,
            "helpful": true,
            "accurate": true,
            "comment": "Great explanation of IPC 420!"
        }
        ```
    """
    try:
        if feedback_collector is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Feedback system not initialized"
            )
        
        logger.info(f"Receiving feedback for query {request.query_id}, rating: {request.rating}")
        
        # Submit feedback
        feedback_id = feedback_collector.submit_feedback(
            query_id=request.query_id,
            response_id=request.response_id,
            rating=request.rating,
            helpful=request.helpful,
            accurate=request.accurate,
            comment=request.comment
        )
        
        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully",
            feedback_id=feedback_id,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/analytics/dashboard", response_model=AnalyticsDashboardResponse, tags=["Intelligence"])
async def get_analytics_dashboard():
    """
    Get analytics dashboard data.
    
    Provides comprehensive statistics about:
    - Query volume (today, week, all-time)
    - Response times
    - Confidence distribution
    - User feedback metrics
    - Query type distribution
    - Session statistics
    
    Returns:
        AnalyticsDashboardResponse with dashboard statistics
    
    Example response:
        ```json
        {
            "success": true,
            "dashboard_data": {
                "today": {"queries": 45, "sessions": 12, "avg_response_time_ms": 1234},
                "this_week": {"queries": 312, "sessions": 87, "avg_response_time_ms": 1156},
                "all_time": {"queries": 5678, "sessions": 1234, "avg_response_time_ms": 1298},
                "confidence_distribution": {"HIGH": 3456, "MEDIUM": 1890, "LOW": 332},
                "query_type_distribution": {...},
                "avg_user_rating": 4.2
            }
        }
        ```
    """
    try:
        if analytics_engine is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analytics system not initialized"
            )
        
        logger.info("Fetching analytics dashboard data")
        
        # Get dashboard stats
        dashboard_data = analytics_engine.get_dashboard_stats()
        
        return AnalyticsDashboardResponse(
            success=True,
            dashboard_data=dashboard_data,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error fetching analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# MAIN (for development server)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    PORT = int(os.getenv("PORT", 8000))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    print("=" * 80)
    print("LEGAL RESEARCH API - DEVELOPMENT SERVER")
    print("=" * 80)
    print(f"Starting server on {HOST}:{PORT}")
    print(f"API Docs: http://localhost:{PORT}/api/docs")
    print(f"Health Check: http://localhost:{PORT}/api/health")
    print("=" * 80)
    
    uvicorn.run(
        "legal_research:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info"
    )
