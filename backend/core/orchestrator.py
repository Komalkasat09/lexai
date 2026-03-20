"""
Orchestrator Module
Coordinates the complete contract analysis pipeline.
Integrates RAG retrieval, Groq LLM calls, and hallucination guard.
"""

from typing import Dict, List
from core.chroma_setup import ChromaDBManager, initialize_chroma_db
from core.rag_retrieval import RAGRetriever
from core.hallucination_guard import HallucinationGuard
from core import groq_prompts


class ContractAnalysisOrchestrator:
    """Orchestrates the complete contract analysis pipeline."""
    
    def __init__(
        self,
        chroma_manager: ChromaDBManager = None,
        enable_hallucination_guard: bool = True
    ):
        """
        Initialize the orchestrator.
        
        Args:
            chroma_manager: ChromaDB manager (creates new one if None)
            enable_hallucination_guard: Enable/disable hallucination checking
        """
        # Initialize components
        if chroma_manager is None:
            self.chroma_manager = initialize_chroma_db()
        else:
            self.chroma_manager = chroma_manager
        
        self.rag_retriever = RAGRetriever(self.chroma_manager)
        self.hallucination_guard = HallucinationGuard(self.chroma_manager)
        self.enable_guard = enable_hallucination_guard
        
        # Get valid citations prompt for LLM
        self.valid_citations_prompt = self.hallucination_guard.create_validation_prompt_snippet()
        
        print("✓ Contract Analysis Orchestrator initialized")
    
    def orchestrate_analysis(
        self,
        clauses: List[Dict],
        full_text: str
    ) -> Dict:
        """
        Main orchestration function - runs complete analysis pipeline.
        
        Args:
            clauses: List of segmented clause objects from document_extractor
                    Each must have: clause_number, heading, content, level, start_line
            full_text: Complete contract text
            
        Returns:
            Complete analysis JSON with all sections merged
        """
        print("\n" + "="*80)
        print("STARTING CONTRACT ANALYSIS PIPELINE")
        print("="*80 + "\n")
        
        final_result = {}
        
        # ====================================================================
        # STEP 1: Identify Contract Overview
        # ====================================================================
        print("Step 1/5: Identifying contract overview...")
        
        try:
            overview_result = groq_prompts.identify_contract(
                full_text=full_text,
                valid_citations_prompt=self.valid_citations_prompt
            )
            
            # Apply hallucination guard
            if self.enable_guard:
                overview_result, summary = self.hallucination_guard.validate_llm_response(
                    overview_result,
                    citation_fields=['overview']
                )
                if summary['invalid_citations'] > 0:
                    print(f"  ⚠ Removed {summary['invalid_citations']} invalid citation(s) from overview")
            
            final_result.update(overview_result)
            print("  ✓ Contract overview identified")
        except Exception as e:
            print(f"  ✗ Error in overview identification: {e}")
            final_result['overview'] = {
                "error": "Failed to identify contract overview",
                "details": str(e)
            }
        
        # ====================================================================
        # STEP 2: Classify Clauses
        # ====================================================================
        print("\nStep 2/5: Classifying clauses...")
        
        try:
            classified_clauses = groq_prompts.classify_clauses(clauses)
            print(f"  ✓ Classified {len(classified_clauses)} clauses")
            
            # Show distribution
            types = {}
            for clause in classified_clauses:
                clause_type = clause.get('type', 'Other')
                types[clause_type] = types.get(clause_type, 0) + 1
            print(f"  Types found: {', '.join(f'{k}({v})' for k, v in types.items())}")
            
        except Exception as e:
            print(f"  ✗ Error in clause classification: {e}")
            classified_clauses = [{**c, 'type': 'Other'} for c in clauses]
        
        # ====================================================================
        # STEP 3: RAG Retrieval for Risk Assessment
        # ====================================================================
        print("\nStep 3/5: Retrieving relevant bare act sections...")
        
        try:
            # Retrieve relevant sections for each clause
            rag_context_map = self.rag_retriever.retrieve_for_risk_assessment(
                classified_clauses,
                risk_threshold=0.7
            )
            
            total_sections = sum(len(sections) for sections in rag_context_map.values())
            print(f"  ✓ Retrieved {total_sections} relevant bare act sections")
            
        except Exception as e:
            print(f"  ✗ Error in RAG retrieval: {e}")
            rag_context_map = {}
        
        # ====================================================================
        # STEP 4: Assess Risk
        # ====================================================================
        print("\nStep 4/5: Assessing clause risk levels...")
        
        try:
            risk_result = groq_prompts.assess_risk(
                classified_clauses=classified_clauses,
                rag_context_map=rag_context_map,
                valid_citations_prompt=self.valid_citations_prompt
            )
            
            # Apply hallucination guard
            if self.enable_guard:
                risk_result, summary = self.hallucination_guard.validate_llm_response(
                    risk_result,
                    citation_fields=['risks']
                )
                if summary['invalid_citations'] > 0:
                    print(f"  ⚠ Removed {summary['invalid_citations']} invalid citation(s) from risk assessment")
            
            final_result.update(risk_result)
            
            # Count risk levels
            risk_counts = {'standard': 0, 'moderate': 0, 'high': 0, 'unknown': 0}
            for risk in risk_result.get('risks', []):
                level = risk.get('risk_level', 'unknown')
                risk_counts[level] = risk_counts.get(level, 0) + 1
            
            print(f"  ✓ Risk assessment complete:")
            print(f"    High: {risk_counts.get('high', 0)}, "
                  f"Moderate: {risk_counts.get('moderate', 0)}, "
                  f"Standard: {risk_counts.get('standard', 0)}")
            
        except Exception as e:
            print(f"  ✗ Error in risk assessment: {e}")
            final_result['risks'] = []
        
        # ====================================================================
        # STEP 5a: Detect Missing Clauses
        # ====================================================================
        print("\nStep 5a/6: Detecting missing clauses...")
        
        try:
            missing_result = groq_prompts.detect_missing(classified_clauses)
            final_result.update(missing_result)
            
            missing_count = len(missing_result.get('missing_clauses', []))
            if missing_count > 0:
                print(f"  ⚠ Found {missing_count} missing standard clause(s)")
            else:
                print(f"  ✓ All standard clauses present")
            
        except Exception as e:
            print(f"  ✗ Error in missing clause detection: {e}")
            final_result['missing_clauses'] = []
        
        # ====================================================================
        # STEP 5b: Suggest Revisions for High-Risk Clauses
        # ====================================================================
        print("\nStep 5b/6: Generating revision suggestions for high-risk clauses...")
        
        try:
            # Extract high-risk clauses with their original text
            high_risk_clauses = []
            risks = final_result.get('risks', [])
            
            for risk in risks:
                if risk.get('risk_level') == 'high':
                    # Find corresponding clause
                    clause_num = risk.get('clause_number', 0)
                    if 0 < clause_num <= len(classified_clauses):
                        original_clause = classified_clauses[clause_num - 1]
                        high_risk_clauses.append({
                            'clause_number': clause_num,
                            'clause_heading': risk.get('clause_heading', ''),
                            'original_text': original_clause.get('content', ''),
                            'explanation': risk.get('explanation', '')
                        })
            
            if high_risk_clauses:
                revision_result = groq_prompts.suggest_revisions(
                    high_risk_clauses=high_risk_clauses,
                    valid_citations_prompt=self.valid_citations_prompt
                )
                
                # Apply hallucination guard
                if self.enable_guard:
                    revision_result, summary = self.hallucination_guard.validate_llm_response(
                        revision_result,
                        citation_fields=['suggested_revisions']
                    )
                    if summary['invalid_citations'] > 0:
                        print(f"  ⚠ Removed {summary['invalid_citations']} invalid citation(s) from revisions")
                
                final_result.update(revision_result)
                print(f"  ✓ Generated {len(revision_result.get('suggested_revisions', []))} revision(s)")
            else:
                final_result['suggested_revisions'] = []
                print(f"  ✓ No high-risk clauses found, no revisions needed")
            
        except Exception as e:
            print(f"  ✗ Error in revision suggestions: {e}")
            final_result['suggested_revisions'] = []
        
        # ====================================================================
        # STEP 6: Add Classified Clauses to Output
        # ====================================================================
        print("\nStep 6/6: Finalizing output...")
        
        # Add classified clauses to final result
        final_result['clauses'] = classified_clauses
        
        # Add metadata
        final_result['metadata'] = {
            'total_clauses': len(classified_clauses),
            'high_risk_count': sum(
                1 for r in final_result.get('risks', [])
                if r.get('risk_level') == 'high'
            ),
            'missing_clauses_count': len(final_result.get('missing_clauses', [])),
            'revisions_suggested': len(final_result.get('suggested_revisions', [])),
            'hallucination_guard_enabled': self.enable_guard
        }
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        print(f"  Total clauses analyzed: {final_result['metadata']['total_clauses']}")
        print(f"  High-risk clauses: {final_result['metadata']['high_risk_count']}")
        print(f"  Missing clauses: {final_result['metadata']['missing_clauses_count']}")
        print(f"  Revisions suggested: {final_result['metadata']['revisions_suggested']}")
        print("="*80 + "\n")
        
        return final_result
    
    def analyze_contract_from_text(
        self,
        contract_text: str,
        pre_segmented_clauses: List[Dict] = None
    ) -> Dict:
        """
        Convenience method: analyze contract from raw text.
        Handles segmentation if not provided.
        
        Args:
            contract_text: Full contract text
            pre_segmented_clauses: Optional pre-segmented clauses
            
        Returns:
            Complete analysis result
        """
        if pre_segmented_clauses is None:
            # Import here to avoid circular dependency
            from core.clause_segmenter import ClauseSegmenter
            
            print("Segmenting contract...")
            segmenter = ClauseSegmenter()
            clauses = segmenter.segment(contract_text)
            clauses = segmenter.get_clauses_as_dict()
        else:
            clauses = pre_segmented_clauses
        
        return self.orchestrate_analysis(clauses, contract_text)


# Test function
if __name__ == "__main__":
    import os
    
    print("\n" + "="*80)
    print("ORCHESTRATOR TEST")
    print("="*80 + "\n")
    
    # Check environment
    if not os.environ.get("GROQ_API_KEY"):
        print("⚠ GROQ_API_KEY not set. Please set it in .env file.")
        print("Test will initialize components but skip LLM calls.\n")
    
    # Initialize orchestrator
    orchestrator = ContractAnalysisOrchestrator()
    
    # Sample test data
    sample_clauses = [
        {
            "clause_number": "1",
            "heading": "PAYMENT TERMS",
            "content": "Party B shall pay Party A Rs. 10,00,000 per month within 30 days of invoice.",
            "level": 1,
            "start_line": 10
        },
        {
            "clause_number": "2",
            "heading": "INDEMNITY",
            "content": "Party A shall indemnify Party B for all damages, claims, losses, and liabilities arising from any breach.",
            "level": 1,
            "start_line": 15
        }
    ]
    
    sample_contract = """
    SERVICE AGREEMENT
    
    This agreement entered on January 15, 2024 between TechCorp Solutions Pvt Ltd
    and Global Enterprises India Ltd.
    
    1. PAYMENT TERMS
    Party B shall pay Party A Rs. 10,00,000 per month within 30 days of invoice.
    
    2. INDEMNITY
    Party A shall indemnify Party B for all damages, claims, losses, and liabilities.
    
    Governed by laws of India. Jurisdiction: Bangalore.
    """
    
    if os.environ.get("GROQ_API_KEY"):
        print("Running full pipeline test with Groq API...\n")
        
        try:
            result = orchestrator.orchestrate_analysis(
                clauses=sample_clauses,
                full_text=sample_contract
            )
            
            print("\nResult structure:")
            print(f"  - overview: {bool(result.get('overview'))}")
            print(f"  - clauses: {len(result.get('clauses', []))} clauses")
            print(f"  - risks: {len(result.get('risks', []))} assessments")
            print(f"  - missing_clauses: {len(result.get('missing_clauses', []))}")
            print(f"  - suggested_revisions: {len(result.get('suggested_revisions', []))}")
            print(f"  - metadata: {bool(result.get('metadata'))}")
            
        except Exception as e:
            print(f"\n✗ Error during test: {e}")
    else:
        print("Skipping full pipeline test (no API key)")
        print("Components initialized successfully!")
    
    print("\n✓ Orchestrator module ready!")
