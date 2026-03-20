"""
Core Contract Analysis Modules

Legacy modules from the original contract review system.
These are used by the legacy/main.py entry point for contract analysis.
"""

from core.chroma_setup import ChromaDBManager, initialize_chroma_db
from core.document_extractor import DocumentExtractor
from core.clause_segmenter import ClauseSegmenter
from core.orchestrator import ContractAnalysisOrchestrator
from core.rag_retrieval import RAGRetriever
from core.hallucination_guard import HallucinationGuard

__all__ = [
    'ChromaDBManager',
    'initialize_chroma_db',
    'DocumentExtractor',
    'ClauseSegmenter',
    'ContractAnalysisOrchestrator',
    'RAGRetriever',
    'HallucinationGuard',
    'groq_prompts',
]
