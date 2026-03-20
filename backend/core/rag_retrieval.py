"""
RAG Retrieval Module
Handles retrieval of relevant bare act sections for contract clauses.
"""

from typing import List, Dict
from core.chroma_setup import ChromaDBManager


class RAGRetriever:
    """Retrieves relevant bare act sections for contract clauses using RAG."""
    
    def __init__(self, chroma_manager: ChromaDBManager):
        """
        Initialize RAG retriever.
        
        Args:
            chroma_manager: ChromaDB manager instance
        """
        self.chroma_manager = chroma_manager
    
    def retrieve_for_clause(
        self, 
        clause_text: str, 
        clause_heading: str = None,
        n_results: int = 2
    ) -> List[Dict]:
        """
        Retrieve relevant bare act sections for a single clause.
        
        Args:
            clause_text: The text content of the clause
            clause_heading: Optional heading to enhance retrieval
            n_results: Number of sections to retrieve (default: 2)
            
        Returns:
            List of relevant bare act sections
        """
        # Combine heading and text for better retrieval
        query_text = clause_text
        if clause_heading:
            query_text = f"{clause_heading}: {clause_text}"
        
        # Query ChromaDB
        results = self.chroma_manager.query_similar_sections(
            query_text=query_text,
            n_results=n_results
        )
        
        return results
    
    def retrieve_for_multiple_clauses(
        self,
        clauses: List[Dict],
        n_results_per_clause: int = 2
    ) -> Dict[int, List[Dict]]:
        """
        Retrieve relevant sections for multiple clauses.
        
        Args:
            clauses: List of clause dictionaries with 'heading' and 'content' keys
            n_results_per_clause: Number of sections per clause
            
        Returns:
            Dictionary mapping clause index to list of relevant sections
        """
        results_map = {}
        
        for idx, clause in enumerate(clauses):
            clause_text = clause.get('content', '')
            clause_heading = clause.get('heading', '')
            
            results = self.retrieve_for_clause(
                clause_text=clause_text,
                clause_heading=clause_heading,
                n_results=n_results_per_clause
            )
            
            results_map[idx] = results
        
        return results_map
    
    def retrieve_for_risk_assessment(
        self,
        clauses: List[Dict],
        risk_threshold: float = 0.7
    ) -> Dict[int, List[Dict]]:
        """
        Retrieve sections specifically for risk assessment.
        Focuses on high-relevance matches.
        
        Args:
            clauses: List of clause dictionaries
            risk_threshold: Similarity threshold for inclusion
            
        Returns:
            Dictionary mapping clause index to highly relevant sections
        """
        results_map = {}
        
        for idx, clause in enumerate(clauses):
            clause_text = clause.get('content', '')
            clause_heading = clause.get('heading', '')
            
            # Retrieve more results initially
            all_results = self.retrieve_for_clause(
                clause_text=clause_text,
                clause_heading=clause_heading,
                n_results=3
            )
            
            # Filter by distance/similarity
            # Lower distance = higher similarity
            # Keeping results with distance < risk_threshold
            filtered_results = [
                r for r in all_results 
                if r.get('distance') is not None and r['distance'] < risk_threshold
            ]
            
            # If no high-quality matches, take top 2 anyway
            if not filtered_results and all_results:
                filtered_results = all_results[:2]
            
            results_map[idx] = filtered_results
        
        return results_map
    
    def get_context_for_prompt(
        self,
        clause: Dict,
        sections: List[Dict]
    ) -> str:
        """
        Format retrieved sections as context for LLM prompt.
        
        Args:
            clause: Clause dictionary
            sections: List of retrieved sections
            
        Returns:
            Formatted context string for LLM
        """
        if not sections:
            return "No directly relevant bare act sections found for this clause."
        
        context_parts = ["Relevant bare act sections:\n"]
        
        for i, section in enumerate(sections, 1):
            context_parts.append(
                f"\n{i}. {section['section']} of {section['act']}:\n"
                f"{section['text']}\n"
            )
        
        return "\n".join(context_parts)
    
    def get_all_available_sections(self) -> List[Dict]:
        """
        Get list of all available sections in ChromaDB.
        Useful for validation and debugging.
        
        Returns:
            List of all section references
        """
        return self.chroma_manager.list_all_sections()


# Test function
if __name__ == "__main__":
    from core.chroma_setup import initialize_chroma_db
    
    print("\n" + "="*80)
    print("RAG RETRIEVAL TEST")
    print("="*80 + "\n")
    
    # Initialize ChromaDB and retriever
    chroma_manager = initialize_chroma_db()
    retriever = RAGRetriever(chroma_manager)
    
    # Test 1: Single clause retrieval
    print("Test 1: Retrieve for indemnity clause\n")
    
    test_clause = {
        "heading": "Indemnity",
        "content": "Party A shall indemnify and hold harmless Party B from all claims, damages, losses, and expenses arising from any breach of this Agreement."
    }
    
    results = retriever.retrieve_for_clause(
        clause_text=test_clause['content'],
        clause_heading=test_clause['heading'],
        n_results=2
    )
    
    print(f"Retrieved {len(results)} sections:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['section']} - {result['act']}")
        print(f"   Relevance score: {1 - result['distance']:.2f}")
        print(f"   Text preview: {result['text'][:150]}...\n")
    
    # Test 2: Context formatting
    print("="*80)
    print("Test 2: Format context for LLM prompt\n")
    
    context = retriever.get_context_for_prompt(test_clause, results)
    print(context)
    
    # Test 3: Multiple clauses
    print("\n" + "="*80)
    print("Test 3: Retrieve for multiple clauses\n")
    
    test_clauses = [
        {
            "heading": "Termination",
            "content": "Either party may terminate this agreement by providing 30 days written notice."
        },
        {
            "heading": "Dispute Resolution",
            "content": "Any disputes arising out of this agreement shall be resolved through arbitration in accordance with applicable laws."
        }
    ]
    
    multi_results = retriever.retrieve_for_multiple_clauses(test_clauses, n_results_per_clause=2)
    
    for idx, sections in multi_results.items():
        print(f"Clause {idx + 1}: {test_clauses[idx]['heading']}")
        print(f"  Retrieved {len(sections)} sections:")
        for section in sections:
            print(f"    - {section['section']} ({section['act']})")
        print()
    
    # Test 4: List all available sections
    print("="*80)
    print("Test 4: All available sections\n")
    
    all_sections = retriever.get_all_available_sections()
    print(f"Total sections in database: {len(all_sections)}\n")
    
    by_act = {}
    for section in all_sections:
        act = section['act']
        if act not in by_act:
            by_act[act] = []
        by_act[act].append(section['section'])
    
    for act, sections in by_act.items():
        print(f"{act}:")
        for section in sections:
            print(f"  - {section}")
        print()
    
    print("✓ RAG retrieval test complete!")
