"""
Clause Segmentation Module
Splits contract text into logical clauses/sections using heading detection and regex.
Works BEFORE any LLM processing - pure rule-based extraction.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class Clause:
    """Represents a single clause in a contract."""
    clause_number: str  # e.g., "1", "1.1", "2.3.1"
    heading: str        # e.g., "DEFINITIONS", "Payment Terms"
    content: str        # Full text of the clause
    level: int          # Hierarchy level (1 for main, 2 for sub, etc.)
    start_line: int     # Line number where clause starts
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class ClauseSegmenter:
    """Segments contract text into structured clauses."""
    
    # Common heading patterns in legal contracts
    # Pattern 1: Numbered headings (1. DEFINITIONS, 1.1 Payment Terms)
    NUMBERED_HEADING_PATTERN = r'^(\d+(?:\.\d+)*)\.\s+([A-Z][A-Z\s]+|[A-Z][a-zA-Z\s\-]+)$'
    
    # Pattern 2: All-caps headings (DEFINITIONS, PAYMENT TERMS)
    CAPS_HEADING_PATTERN = r'^([A-Z][A-Z\s]{2,}):?$'
    
    # Pattern 3: Roman numerals (I. Definitions, II. Payment Terms)
    ROMAN_HEADING_PATTERN = r'^([IVXLCDM]+)\.\s+([A-Z][A-Za-z\s\-]+)$'
    
    # Pattern 4: Article/Section prefix (Article 1: Definitions, Section 2.1: Payment)
    ARTICLE_PATTERN = r'^((?:Article|Section|Clause)\s+\d+(?:\.\d+)*):?\s+([A-Z][A-Za-z\s\-]+)$'
    
    def __init__(self):
        """Initialize the clause segmenter."""
        self.clauses: List[Clause] = []
    
    def segment(self, text: str) -> List[Clause]:
        """
        Main segmentation method - splits contract into clauses.
        
        Args:
            text: Full contract text
            
        Returns:
            List of Clause objects
        """
        lines = text.split('\n')
        self.clauses = []
        
        current_clause_number = ""
        current_heading = ""
        current_content = []
        current_level = 0
        clause_start_line = 0
        
        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                if current_content:
                    current_content.append("")  # Preserve paragraph breaks
                continue
            
            # Try to match heading patterns
            heading_match = self._detect_heading(line)
            
            if heading_match:
                # Save previous clause if exists
                if current_heading:
                    self._save_clause(
                        current_clause_number,
                        current_heading,
                        current_content,
                        current_level,
                        clause_start_line
                    )
                
                # Start new clause
                current_clause_number = heading_match['number']
                current_heading = heading_match['title']
                current_level = heading_match['level']
                current_content = []
                clause_start_line = line_num
            else:
                # Add to current clause content
                current_content.append(line)
        
        # Save the last clause
        if current_heading:
            self._save_clause(
                current_clause_number,
                current_heading,
                current_content,
                current_level,
                clause_start_line
            )
        
        # If no structured clauses found, treat entire document as one clause
        if not self.clauses:
            self.clauses.append(Clause(
                clause_number="1",
                heading="FULL CONTRACT",
                content=text,
                level=1,
                start_line=1
            ))
        
        return self.clauses
    
    def _detect_heading(self, line: str) -> Optional[Dict[str, any]]:
        """
        Detect if a line is a heading and extract its components.
        
        Args:
            line: Single line of text
            
        Returns:
            Dict with 'number', 'title', and 'level' if heading detected, else None
        """
        # Pattern 1: Numbered headings (1. DEFINITIONS, 1.1 Payment Terms)
        match = re.match(self.NUMBERED_HEADING_PATTERN, line)
        if match:
            number = match.group(1)
            title = match.group(2).strip()
            level = number.count('.') + 1
            return {'number': number, 'title': title, 'level': level}
        
        # Pattern 2: Article/Section prefix
        match = re.match(self.ARTICLE_PATTERN, line, re.IGNORECASE)
        if match:
            number = match.group(1)
            title = match.group(2).strip()
            # Extract numeric level from "Article 1.2.3" -> level 3
            number_parts = re.findall(r'\d+', number)
            level = len(number_parts)
            return {'number': number, 'title': title, 'level': level}
        
        # Pattern 3: Roman numerals
        match = re.match(self.ROMAN_HEADING_PATTERN, line)
        if match:
            number = match.group(1)
            title = match.group(2).strip()
            return {'number': number, 'title': title, 'level': 1}
        
        # Pattern 4: All-caps headings (only if 3+ chars and followed by content)
        match = re.match(self.CAPS_HEADING_PATTERN, line)
        if match:
            title = match.group(1).strip()
            # Auto-generate number for unnumbered headings
            current_max = self._get_max_clause_number()
            number = str(current_max + 1)
            return {'number': number, 'title': title, 'level': 1}
        
        return None
    
    def _get_max_clause_number(self) -> int:
        """Get the highest clause number assigned so far."""
        if not self.clauses:
            return 0
        
        max_num = 0
        for clause in self.clauses:
            # Extract first number from clause_number
            match = re.match(r'(\d+)', clause.clause_number)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)
        
        return max_num
    
    def _save_clause(
        self,
        clause_number: str,
        heading: str,
        content_lines: List[str],
        level: int,
        start_line: int
    ):
        """
        Save a clause to the internal list.
        
        Args:
            clause_number: Clause identifier
            heading: Clause heading/title
            content_lines: List of content lines
            level: Hierarchy level
            start_line: Starting line number
        """
        # Join content and clean up
        content = '\n'.join(content_lines).strip()
        
        # Only save if there's actual content
        if content:
            self.clauses.append(Clause(
                clause_number=clause_number,
                heading=heading,
                content=content,
                level=level,
                start_line=start_line
            ))
    
    def get_clauses_as_dict(self) -> List[dict]:
        """
        Get all clauses as a list of dictionaries.
        
        Returns:
            List of clause dictionaries
        """
        return [clause.to_dict() for clause in self.clauses]
    
    def get_clause_count(self) -> int:
        """Get total number of clauses."""
        return len(self.clauses)
    
    def get_clauses_by_level(self, level: int) -> List[Clause]:
        """
        Get all clauses at a specific hierarchy level.
        
        Args:
            level: Hierarchy level (1, 2, 3, etc.)
            
        Returns:
            List of clauses at that level
        """
        return [clause for clause in self.clauses if clause.level == level]
    
    def search_clauses(self, keyword: str, case_sensitive: bool = False) -> List[Clause]:
        """
        Search for clauses containing a specific keyword.
        
        Args:
            keyword: Search term
            case_sensitive: Whether search should be case-sensitive
            
        Returns:
            List of matching clauses
        """
        matching_clauses = []
        
        for clause in self.clauses:
            search_in = clause.heading + " " + clause.content
            
            if case_sensitive:
                if keyword in search_in:
                    matching_clauses.append(clause)
            else:
                if keyword.lower() in search_in.lower():
                    matching_clauses.append(clause)
        
        return matching_clauses
    
    def print_structure(self):
        """Print the clause structure in a readable format."""
        print(f"\n{'='*80}")
        print(f"CONTRACT STRUCTURE - {len(self.clauses)} clauses found")
        print(f"{'='*80}\n")
        
        for clause in self.clauses:
            indent = "  " * (clause.level - 1)
            print(f"{indent}[{clause.clause_number}] {clause.heading}")
            print(f"{indent}    Lines: {clause.start_line}+")
            print(f"{indent}    Content preview: {clause.content[:100]}...")
            print()
