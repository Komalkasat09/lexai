"""
ChromaDB Setup for Legal Research System
Creates and manages 4 separate collections for comprehensive legal research:
1. bare_acts - Indian legal statutes and sections
2. case_law - Court judgments and precedents
3. amendments - Legislative amendments to acts
4. overruling_map - Tracks which judgments have been overruled

Each collection has a specific schema optimized for legal research.
"""

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
import os
import json
from datetime import datetime


class LegalResearchDB:
    """
    Manages all ChromaDB collections for the legal research system.
    Provides unified interface for initializing, querying, and maintaining collections.
    """
    
    def __init__(self, persist_directory: str = "./legal_research_db"):
        """
        Initialize ChromaDB client and prepare all collections.
        
        Args:
            persist_directory: Directory where ChromaDB will persist data
        """
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB persistent client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )
        
        # Use sentence-transformers for embedding generation
        # This model is optimized for semantic similarity in legal text
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        # Initialize all collections
        self.bare_acts_collection = None
        self.case_law_collection = None
        self.amendments_collection = None
        self.overruling_map_collection = None
        
        print("🔧 Initializing Legal Research Database...")
        self._create_all_collections()
        print("✅ All collections initialized successfully")
    
    
    def _create_all_collections(self):
        """Create or retrieve all 4 collections with proper schemas."""
        
        # ========================================================================
        # COLLECTION 1: BARE ACTS
        # Stores Indian legal statutes, sections, and their metadata
        # ========================================================================
        self.bare_acts_collection = self.client.get_or_create_collection(
            name="bare_acts",
            embedding_function=self.embedding_function,
            metadata={
                "description": "Indian legal statutes and act sections",
                "created_at": datetime.now().isoformat()
            }
        )
        print("✓ Initialized 'bare_acts' collection")
        
        # ========================================================================
        # COLLECTION 2: CASE LAW
        # Stores court judgments, precedents, and their analysis
        # ========================================================================
        self.case_law_collection = self.client.get_or_create_collection(
            name="case_law",
            embedding_function=self.embedding_function,
            metadata={
                "description": "Court judgments and legal precedents",
                "created_at": datetime.now().isoformat()
            }
        )
        print("✓ Initialized 'case_law' collection")
        
        # ========================================================================
        # COLLECTION 3: AMENDMENTS
        # Tracks legislative amendments to acts over time
        # ========================================================================
        self.amendments_collection = self.client.get_or_create_collection(
            name="amendments",
            embedding_function=self.embedding_function,
            metadata={
                "description": "Legislative amendments to Indian acts",
                "created_at": datetime.now().isoformat()
            }
        )
        print("✓ Initialized 'amendments' collection")
        
        # ========================================================================
        # COLLECTION 4: OVERRULING MAP
        # Tracks which judgments have been overruled by subsequent decisions
        # ========================================================================
        self.overruling_map_collection = self.client.get_or_create_collection(
            name="overruling_map",
            embedding_function=self.embedding_function,
            metadata={
                "description": "Mapping of overruled judgments",
                "created_at": datetime.now().isoformat()
            }
        )
        print("✓ Initialized 'overruling_map' collection")
    
    
    # ============================================================================
    # BARE ACTS OPERATIONS
    # ============================================================================
    
    def add_bare_act_section(
        self,
        section_id: str,
        act_name: str,
        section_number: str,
        section_title: str,
        full_text: str,
        simplified_text: Optional[str] = None,
        punishment: Optional[str] = None,
        is_replaced: bool = False,
        replaced_by_act: Optional[str] = None,
        replaced_by_section: Optional[str] = None,
        replacement_changes: Optional[str] = None,
        last_verified_date: Optional[str] = None,
        amendment_ids: Optional[List[str]] = None
    ) -> None:
        """
        Add a bare act section to the database.
        
        Schema per document:
        {
          "id": "IPC_420",
          "act_name": "Indian Penal Code 1860",
          "section_number": "420",
          "section_title": "Cheating and dishonestly inducing delivery of property",
          "full_text": "...",
          "simplified_text": "...",
          "punishment": "...",
          "is_replaced": true,
          "replaced_by_act": "Bharatiya Nyaya Sanhita 2023",
          "replaced_by_section": "318",
          "replacement_changes": "substantially same with minor wording changes",
          "last_verified_date": "2024-01-01",
          "amendment_ids": ["AMEND_001", "AMEND_002"]
        }
        """
        metadata = {
            "act_name": act_name,
            "section_number": section_number,
            "section_title": section_title,
            "is_replaced": str(is_replaced),  # ChromaDB stores as strings
            "last_verified_date": last_verified_date or datetime.now().strftime("%Y-%m-%d")
        }
        
        # Add optional fields only if provided
        if simplified_text:
            metadata["simplified_text"] = simplified_text
        if punishment:
            metadata["punishment"] = punishment
        if is_replaced and replaced_by_act:
            metadata["replaced_by_act"] = replaced_by_act
            metadata["replaced_by_section"] = replaced_by_section or ""
            metadata["replacement_changes"] = replacement_changes or ""
        if amendment_ids:
            metadata["amendment_ids"] = json.dumps(amendment_ids)
        
        # The full text is embedded for semantic search
        self.bare_acts_collection.add(
            ids=[section_id],
            documents=[full_text],
            metadatas=[metadata]
        )
    
    
    def query_bare_acts(
        self,
        query_text: str,
        n_results: int = 3,
        act_filter: Optional[str] = None
    ) -> Dict:
        """
        Query bare acts collection using semantic similarity.
        
        Args:
            query_text: Natural language query
            n_results: Number of results to return
            act_filter: Optional filter to restrict to specific act
            
        Returns:
            Dictionary with ids, documents, metadatas, distances
        """
        where_filter = None
        if act_filter:
            where_filter = {"act_name": act_filter}
        
        return self.bare_acts_collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter
        )
    
    
    # ============================================================================
    # CASE LAW OPERATIONS
    # ============================================================================
    
    def add_case_law(
        self,
        case_id: str,
        case_name: str,
        citation: str,
        court: str,
        year: str,
        chunk_text: str,
        chunk_number: int = 1,
        total_chunks: int = 1,
        judges: Optional[List[str]] = None,
        acts_referred: Optional[List[str]] = None,
        sections_referred: Optional[List[str]] = None,
        facts_summary: Optional[str] = None,
        issues: Optional[str] = None,
        held: Optional[str] = None,
        legal_principle: Optional[str] = None,
        is_overruled: bool = False,
        overruled_by_citation: Optional[str] = None,
        overruled_year: Optional[str] = None,
        overrules_citations: Optional[List[str]] = None,
        source: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> None:
        """
        Add a case law document (or chunk) to the database.
        
        Schema per document:
        {
          "id": "SC_2019_1234_chunk_1",
          "case_name": "...",
          "citation": "AIR 2019 SC 1234",
          "court": "Supreme Court",
          "year": "2019",
          "judges": ["Justice X", "Justice Y"],
          "acts_referred": ["IPC", "CrPC"],
          "sections_referred": ["420", "34"],
          "facts_summary": "...",
          "issues": "...",
          "held": "...",
          "legal_principle": "...",
          "chunk_text": "...",
          "chunk_number": 1,
          "total_chunks": 5,
          "is_overruled": false,
          "overruled_by_citation": null,
          "overruled_year": null,
          "overrules_citations": [],
          "source": "indiankanoon",
          "source_url": "..."
        }
        """
        metadata = {
            "case_name": case_name,
            "citation": citation,
            "court": court,
            "year": year,
            "chunk_number": str(chunk_number),
            "total_chunks": str(total_chunks),
            "is_overruled": str(is_overruled)
        }
        
        # Add optional list fields as JSON
        if judges:
            metadata["judges"] = json.dumps(judges)
        if acts_referred:
            metadata["acts_referred"] = json.dumps(acts_referred)
        if sections_referred:
            metadata["sections_referred"] = json.dumps(sections_referred)
        if overrules_citations:
            metadata["overrules_citations"] = json.dumps(overrules_citations)
        
        # Add optional string fields
        if facts_summary:
            metadata["facts_summary"] = facts_summary
        if issues:
            metadata["issues"] = issues
        if held:
            metadata["held"] = held
        if legal_principle:
            metadata["legal_principle"] = legal_principle
        if is_overruled and overruled_by_citation:
            metadata["overruled_by_citation"] = overruled_by_citation
            metadata["overruled_year"] = overruled_year or ""
        if source:
            metadata["source"] = source
        if source_url:
            metadata["source_url"] = source_url
        
        # The chunk text is embedded for semantic search
        self.case_law_collection.add(
            ids=[case_id],
            documents=[chunk_text],
            metadatas=[metadata]
        )
    
    
    def query_case_law(
        self,
        query_text: str,
        n_results: int = 5,
        court_filter: Optional[str] = None,
        year_from: Optional[str] = None,
        year_to: Optional[str] = None
    ) -> Dict:
        """
        Query case law collection using semantic similarity.
        
        Args:
            query_text: Natural language query
            n_results: Number of results to return
            court_filter: Optional filter for specific court
            year_from: Optional year range start
            year_to: Optional year range end
            
        Returns:
            Dictionary with ids, documents, metadatas, distances
        """
        where_filter = {}
        
        if court_filter:
            where_filter["court"] = court_filter
        
        # Note: ChromaDB doesn't support range queries easily
        # For year filtering, we'll retrieve more results and filter in Python
        
        results = self.case_law_collection.query(
            query_texts=[query_text],
            n_results=n_results * 2 if (year_from or year_to) else n_results,
            where=where_filter if where_filter else None
        )
        
        # Post-process for year filtering if needed
        if year_from or year_to:
            filtered_results = {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
            
            for i, metadata in enumerate(results["metadatas"][0]):
                year = int(metadata.get("year", "0"))
                
                if year_from and year < int(year_from):
                    continue
                if year_to and year > int(year_to):
                    continue
                
                if len(filtered_results["ids"][0]) >= n_results:
                    break
                
                filtered_results["ids"][0].append(results["ids"][0][i])
                filtered_results["documents"][0].append(results["documents"][0][i])
                filtered_results["metadatas"][0].append(results["metadatas"][0][i])
                filtered_results["distances"][0].append(results["distances"][0][i])
            
            return filtered_results
        
        return results
    
    
    def check_if_case_exists(self, citation: str) -> bool:
        """
        Check if a case with given citation already exists in database.
        Used for deduplication during data loading.
        
        Args:
            citation: Case citation to check
            
        Returns:
            True if exists, False otherwise
        """
        try:
            results = self.case_law_collection.get(
                where={"citation": citation},
                limit=1
            )
            return len(results["ids"]) > 0
        except Exception:
            return False
    
    
    # ============================================================================
    # AMENDMENTS OPERATIONS
    # ============================================================================
    
    def add_amendment(
        self,
        amendment_id: str,
        act_name: str,
        section_number: str,
        amendment_year: str,
        amendment_act: str,
        old_text: str,
        new_text: str,
        effective_date: str,
        impact_summary: str,
        gazette_reference: Optional[str] = None
    ) -> None:
        """
        Add an amendment record to the database.
        
        Schema per document:
        {
          "id": "AMEND_001",
          "act_name": "...",
          "section_number": "...",
          "amendment_year": "2023",
          "amendment_act": "...",
          "old_text": "...",
          "new_text": "...",
          "effective_date": "...",
          "impact_summary": "...",
          "gazette_reference": "..."
        }
        """
        metadata = {
            "act_name": act_name,
            "section_number": section_number,
            "amendment_year": amendment_year,
            "amendment_act": amendment_act,
            "effective_date": effective_date,
            "impact_summary": impact_summary
        }
        
        if gazette_reference:
            metadata["gazette_reference"] = gazette_reference
        
        # Embed the combined old and new text for similarity search
        combined_text = f"Old text: {old_text}\n\nNew text: {new_text}\n\nImpact: {impact_summary}"
        
        self.amendments_collection.add(
            ids=[amendment_id],
            documents=[combined_text],
            metadatas=[metadata]
        )
    
    
    def get_amendments_for_section(self, act_name: str, section_number: str) -> Dict:
        """
        Retrieve all amendments for a specific act section.
        
        Args:
            act_name: Name of the act
            section_number: Section number
            
        Returns:
            Dictionary with amendment records
        """
        try:
            results = self.amendments_collection.get(
                where={
                    "act_name": act_name,
                    "section_number": section_number
                }
            )
            return results
        except Exception:
            return {"ids": [], "documents": [], "metadatas": []}
    
    
    # ============================================================================
    # OVERRULING MAP OPERATIONS
    # ============================================================================
    
    def add_overruling_record(
        self,
        overruling_id: str,
        overruled_citation: str,
        overruled_by_citation: str,
        overruled_by_case: str,
        overruling_year: str,
        reason_summary: str
    ) -> None:
        """
        Add an overruling record to track judgment validity.
        
        Schema per document:
        {
          "id": "OVER_001",
          "overruled_citation": "AIR 2010 SC 1234",
          "overruled_by_citation": "AIR 2019 SC 5678",
          "overruled_by_case": "...",
          "overruling_year": "2019",
          "reason_summary": "..."
        }
        """
        metadata = {
            "overruled_citation": overruled_citation,
            "overruled_by_citation": overruled_by_citation,
            "overruled_by_case": overruled_by_case,
            "overruling_year": overruling_year
        }
        
        self.overruling_map_collection.add(
            ids=[overruling_id],
            documents=[reason_summary],
            metadatas=[metadata]
        )
    
    
    def check_if_overruled(self, citation: str) -> Optional[Dict]:
        """
        Check if a judgment has been overruled.
        
        Args:
            citation: Citation to check
            
        Returns:
            Overruling details if overruled, None otherwise
        """
        try:
            results = self.overruling_map_collection.get(
                where={"overruled_citation": citation},
                limit=1
            )
            
            if len(results["ids"]) > 0:
                return {
                    "is_overruled": True,
                    "overruled_by": results["metadatas"][0]["overruled_by_citation"],
                    "overruling_case": results["metadatas"][0]["overruled_by_case"],
                    "year": results["metadatas"][0]["overruling_year"],
                    "reason": results["documents"][0]
                }
            return None
        except Exception:
            return None
    
    
    # ============================================================================
    # UTILITY OPERATIONS
    # ============================================================================
    
    def get_collection_stats(self) -> Dict:
        """
        Get statistics about all collections.
        
        Returns:
            Dictionary with count for each collection
        """
        return {
            "bare_acts": self.bare_acts_collection.count(),
            "case_law": self.case_law_collection.count(),
            "amendments": self.amendments_collection.count(),
            "overruling_map": self.overruling_map_collection.count(),
            "total": (
                self.bare_acts_collection.count() +
                self.case_law_collection.count() +
                self.amendments_collection.count() +
                self.overruling_map_collection.count()
            )
        }
    
    
    def reset_all_collections(self):
        """
        DANGER: Reset all collections. Use only for testing or complete rebuild.
        """
        print("⚠️  WARNING: Resetting all collections...")
        
        for collection_name in ["bare_acts", "case_law", "amendments", "overruling_map"]:
            try:
                self.client.delete_collection(name=collection_name)
                print(f"✓ Deleted '{collection_name}' collection")
            except Exception as e:
                print(f"✗ Could not delete '{collection_name}': {e}")
        
        # Recreate collections
        self._create_all_collections()
        print("✅ All collections reset and recreated")


# ============================================================================
# INITIALIZATION HELPER
# ============================================================================

def initialize_legal_db(persist_directory: str = "./chroma_legal_db") -> LegalResearchDB:
    """
    Initialize the legal research database.
    
    Args:
        persist_directory: Directory to persist ChromaDB data
        
    Returns:
        LegalResearchDB instance
    """
    return LegalResearchDB(persist_directory=persist_directory)


# ============================================================================
# QUICK TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("LEGAL RESEARCH DATABASE - INITIALIZATION TEST")
    print("="*80 + "\n")
    
    # Initialize database
    db = initialize_legal_db()
    
    # Show statistics
    stats = db.get_collection_stats()
    print("\n📊 Collection Statistics:")
    print(f"  • Bare Acts: {stats['bare_acts']}")
    print(f"  • Case Law: {stats['case_law']}")
    print(f"  • Amendments: {stats['amendments']}")
    print(f"  • Overruling Map: {stats['overruling_map']}")
    print(f"  • Total Documents: {stats['total']}")
    
    print("\n✅ Legal Research Database ready for use!")
    print("="*80 + "\n")
