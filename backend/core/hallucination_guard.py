"""
Hallucination Guard Module
Validates bare act citations before they are included in LLM responses.
Prevents hallucinated legal references.
"""
# NOTE: This module is not used in the evaluation pipeline.
# Retained for future integration. See metrics_engine.py
# for the canonical hallucination detection implementation.

import re
from typing import Dict, List, Tuple, Optional
from core.chroma_setup import ChromaDBManager


class HallucinationGuard:
    """Guards against hallucinated bare act citations."""
    
    def __init__(self, chroma_manager: ChromaDBManager):
        """
        Initialize hallucination guard.
        
        Args:
            chroma_manager: ChromaDB manager instance for validation
        """
        self.chroma_manager = chroma_manager
        
        # Cache valid sections for faster lookups
        self._valid_sections_cache = None
        self._build_valid_sections_cache()
    
    def _build_valid_sections_cache(self):
        """Build cache of all valid section references."""
        all_sections = self.chroma_manager.list_all_sections()
        self._valid_sections_cache = {
            (section['section'], section['act']): True
            for section in all_sections
        }
        print(f"✓ Cached {len(self._valid_sections_cache)} valid section references")
    
    def validate_citation(self, section: str, act: str) -> bool:
        """
        Validate if a citation exists in ChromaDB.
        
        Args:
            section: Section reference (e.g., "Section 73")
            act: Act name (e.g., "Indian Contract Act 1872")
            
        Returns:
            True if citation is valid, False otherwise
        """
        # Check cache first
        if (section, act) in self._valid_sections_cache:
            return True
        
        # If not in cache, check ChromaDB directly
        result = self.chroma_manager.get_section_by_reference(section, act)
        
        if result:
            # Add to cache
            self._valid_sections_cache[(section, act)] = True
            return True
        
        return False
    
    def extract_citations_from_text(self, text: str) -> List[Dict]:
        """
        Extract bare act citations from text using regex.
        
        Args:
            text: Text that may contain citations
            
        Returns:
            List of extracted citations with their positions
        """
        citations = []
        
        # Pattern 1: "Section X of Act Name"
        # Example: "Section 73 of Indian Contract Act 1872"
        pattern1 = r'Section\s+(\d+[A-Za-z]?)\s+of\s+([^.,;\n]+(?:Act|Code)\s+\d{4})'
        
        # Pattern 2: "Act Name, Section X"
        # Example: "Indian Contract Act 1872, Section 73"
        pattern2 = r'([^.,;\n]+(?:Act|Code)\s+\d{4}),?\s+Section\s+(\d+[A-Za-z]?)'
        
        # Find all matches with pattern 1
        for match in re.finditer(pattern1, text, re.IGNORECASE):
            section_num = match.group(1)
            act_name = match.group(2).strip()
            
            citations.append({
                'section': f"Section {section_num}",
                'act': act_name,
                'full_text': match.group(0),
                'start': match.start(),
                'end': match.end()
            })
        
        # Find all matches with pattern 2
        for match in re.finditer(pattern2, text, re.IGNORECASE):
            act_name = match.group(1).strip()
            section_num = match.group(2)
            
            citations.append({
                'section': f"Section {section_num}",
                'act': act_name,
                'full_text': match.group(0),
                'start': match.start(),
                'end': match.end()
            })
        
        # Sort by position and remove duplicates
        citations = sorted(citations, key=lambda x: x['start'])
        unique_citations = []
        seen = set()
        
        for citation in citations:
            key = (citation['section'], citation['act'])
            if key not in seen:
                unique_citations.append(citation)
                seen.add(key)
        
        return unique_citations
    
    def validate_and_filter_text(
        self, 
        text: str, 
        remove_invalid: bool = True,
        replacement_text: str = "[citation removed - not verified]"
    ) -> Tuple[str, List[Dict]]:
        """
        Validate all citations in text and optionally remove invalid ones.
        
        Args:
            text: Text containing potential citations
            remove_invalid: If True, remove invalid citations from text
            replacement_text: Text to replace invalid citations with
            
        Returns:
            Tuple of (filtered_text, validation_report)
        """
        citations = self.extract_citations_from_text(text)
        
        if not citations:
            return text, []
        
        validation_report = []
        filtered_text = text
        
        # Process citations in reverse order to maintain positions
        for citation in reversed(citations):
            is_valid = self.validate_citation(citation['section'], citation['act'])
            
            validation_report.insert(0, {
                'section': citation['section'],
                'act': citation['act'],
                'full_text': citation['full_text'],
                'is_valid': is_valid
            })
            
            # Remove invalid citation if requested
            if not is_valid and remove_invalid:
                filtered_text = (
                    filtered_text[:citation['start']] +
                    replacement_text +
                    filtered_text[citation['end']:]
                )
        
        return filtered_text, validation_report
    
    def validate_llm_response(
        self,
        response: Dict,
        citation_fields: List[str] = None
    ) -> Tuple[Dict, Dict]:
        """
        Validate an entire LLM response JSON for hallucinated citations.
        
        Args:
            response: LLM response dictionary
            citation_fields: List of field paths that may contain citations
                           (e.g., ['risks', 'suggested_revisions'])
            
        Returns:
            Tuple of (validated_response, validation_summary)
        """
        if citation_fields is None:
            # Default fields to check
            citation_fields = ['risks', 'suggested_revisions', 'overview']
        
        validated_response = response.copy()
        validation_summary = {
            'total_citations_found': 0,
            'valid_citations': 0,
            'invalid_citations': 0,
            'invalid_details': []
        }
        
        def process_value(value):
            """Recursively process values in response."""
            if isinstance(value, str):
                filtered_text, report = self.validate_and_filter_text(value)
                
                if report:
                    validation_summary['total_citations_found'] += len(report)
                    for item in report:
                        if item['is_valid']:
                            validation_summary['valid_citations'] += 1
                        else:
                            validation_summary['invalid_citations'] += 1
                            validation_summary['invalid_details'].append({
                                'section': item['section'],
                                'act': item['act'],
                                'found_in': item['full_text']
                            })
                
                return filtered_text
            
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            
            elif isinstance(value, list):
                return [process_value(item) for item in value]
            
            return value
        
        # Process each field
        for field in citation_fields:
            if field in validated_response:
                validated_response[field] = process_value(validated_response[field])
        
        return validated_response, validation_summary
    
    def get_valid_sections_list(self) -> List[str]:
        """
        Get formatted list of all valid sections.
        Useful for including in LLM prompts.
        
        Returns:
            List of formatted section references
        """
        sections = []
        for (section, act), _ in self._valid_sections_cache.items():
            sections.append(f"{section} of {act}")
        return sorted(sections)
    
    def create_validation_prompt_snippet(self) -> str:
        """
        Create a prompt snippet listing valid citations.
        To be included in LLM prompts.
        
        Returns:
            Formatted prompt text
        """
        valid_sections = self.get_valid_sections_list()
        
        prompt = "IMPORTANT - VALID BARE ACT CITATIONS ONLY:\n"
        prompt += "You may ONLY cite the following bare act sections. "
        prompt += "Never invent or reference any other sections:\n\n"
        
        # Group by act
        by_act = {}
        for section_str in valid_sections:
            # Extract act name
            if " of " in section_str:
                section, act = section_str.split(" of ", 1)
                if act not in by_act:
                    by_act[act] = []
                by_act[act].append(section)
        
        for act, sections in sorted(by_act.items()):
            prompt += f"• {act}: {', '.join(sections)}\n"
        
        prompt += "\nIf uncertain about a citation, omit it entirely.\n"
        
        return prompt


# Test function
if __name__ == "__main__":
    from core.chroma_setup import initialize_chroma_db
    
    print("\n" + "="*80)
    print("HALLUCINATION GUARD TEST")
    print("="*80 + "\n")
    
    # Initialize ChromaDB and guard
    chroma_manager = initialize_chroma_db()
    guard = HallucinationGuard(chroma_manager)
    
    # Test 1: Validate known good citation
    print("Test 1: Validate known good citation\n")
    is_valid = guard.validate_citation("Section 73", "Indian Contract Act 1872")
    print(f"Section 73 of Indian Contract Act 1872: {'✓ Valid' if is_valid else '✗ Invalid'}\n")
    
    # Test 2: Validate known bad citation
    print("Test 2: Validate known bad citation\n")
    is_valid = guard.validate_citation("Section 999", "Indian Contract Act 1872")
    print(f"Section 999 of Indian Contract Act 1872: {'✓ Valid' if is_valid else '✗ Invalid'}\n")
    
    # Test 3: Extract citations from text
    print("="*80)
    print("Test 3: Extract citations from text\n")
    
    test_text = """
    This clause violates Section 73 of Indian Contract Act 1872 which deals with 
    compensation. It also references Section 999 of Indian Contract Act 1872 
    (which doesn't exist) and Section 7 of Arbitration and Conciliation Act 1996.
    """
    
    citations = guard.extract_citations_from_text(test_text)
    print(f"Found {len(citations)} citations:\n")
    for citation in citations:
        print(f"  - {citation['section']} of {citation['act']}")
        is_valid = guard.validate_citation(citation['section'], citation['act'])
        print(f"    Status: {'✓ Valid' if is_valid else '✗ Invalid'}\n")
    
    # Test 4: Filter invalid citations
    print("="*80)
    print("Test 4: Filter invalid citations from text\n")
    
    print("Original text:")
    print(test_text)
    
    filtered_text, report = guard.validate_and_filter_text(test_text)
    
    print("\nFiltered text:")
    print(filtered_text)
    
    print("\nValidation report:")
    for item in report:
        status = "✓ Valid" if item['is_valid'] else "✗ Invalid (removed)"
        print(f"  - {item['section']} of {item['act']}: {status}")
    
    # Test 5: Validate LLM response
    print("\n" + "="*80)
    print("Test 5: Validate LLM response JSON\n")
    
    mock_llm_response = {
        "risks": [
            {
                "clause": "Indemnity",
                "risk_level": "high",
                "explanation": "Violates Section 73 of Indian Contract Act 1872 and Section 999 of Indian Contract Act 1872"
            }
        ],
        "suggested_revisions": [
            {
                "original": "Party A shall indemnify...",
                "revised": "As per Section 7 of Arbitration and Conciliation Act 1996..."
            }
        ]
    }
    
    validated_response, summary = guard.validate_llm_response(
        mock_llm_response,
        citation_fields=['risks', 'suggested_revisions']
    )
    
    print("Validation Summary:")
    print(f"  Total citations found: {summary['total_citations_found']}")
    print(f"  Valid citations: {summary['valid_citations']}")
    print(f"  Invalid citations: {summary['invalid_citations']}")
    
    if summary['invalid_details']:
        print("\n  Invalid citations removed:")
        for detail in summary['invalid_details']:
            print(f"    - {detail['section']} of {detail['act']}")
    
    # Test 6: Get validation prompt snippet
    print("\n" + "="*80)
    print("Test 6: Validation prompt snippet for LLM\n")
    
    prompt_snippet = guard.create_validation_prompt_snippet()
    print(prompt_snippet)
    
    print("\n✓ Hallucination guard test complete!")
