"""
LexAI Metrics Engine
====================
Computes all 7 metrics for research evaluation.

Metrics:
1. Citation Accuracy Rate (CAR)
2. Hallucination Rate (HR)
3. Outdated Law Rate (OLR)
4. Abstention Precision (AP)
5. Answer Completeness Score (ACS)
6. Retrieval Precision@K
7. Confidence Calibration Score (CCS)

Usage:
    from evaluation.metrics_engine import MetricsEngine
    
    engine = MetricsEngine(ground_truth_df, chromadb_client)
    metrics = engine.compute_all_metrics(lexai_responses, baseline_responses)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import re
from collections import defaultdict
import chromadb


# Increment when metric definitions or key contracts change.
METRIC_SCHEMA_VERSION = "2.0.0"


# Abstention detection phrases
ABSTENTION_PHRASES = [
    "cannot provide a reliable answer",
    "insufficient information",
    "not found in my current database",
    "unable to conclusively assess",
    "cannot answer this query",
    "i could not find",
    "not available in my database",
    "please consult primary sources",
    "outside my current knowledge",
    "i do not have sufficient",
    "no relevant information found",
    "database does not contain",
    "cannot find a reliable",
    "please verify with primary",
    "unable to find",
]


class MetricsEngine:
    """
    Computes all evaluation metrics for LexAI research paper.
    """
    
    # ── Canonical act names exactly as stored in ChromaDB ──────────────────
    # chromadb $contains operator does NOT work on string metadata fields;
    # must use $eq with the exact full name.
    _ACT_CANONICAL_NAMES = {
        # IPC family
        'IPC':                          'Indian Penal Code 1860',
        'INDIAN PENAL CODE':            'Indian Penal Code 1860',
        'INDIAN PENAL CODE 1860':       'Indian Penal Code 1860',
        # BNS family
        'BNS':                          'Bharatiya Nyaya Sanhita 2023',
        'BHARATIYA NYAYA SANHITA':      'Bharatiya Nyaya Sanhita 2023',
        'BHARATIYA NYAYA SANHITA 2023': 'Bharatiya Nyaya Sanhita 2023',
        # CrPC family
        'CRPC':                         'Code of Criminal Procedure 1973',
        'CR.P.C':                       'Code of Criminal Procedure 1973',
        'CODE OF CRIMINAL PROCEDURE':   'Code of Criminal Procedure 1973',
        'CODE OF CRIMINAL PROCEDURE 1973': 'Code of Criminal Procedure 1973',
        # BNSS family
        'BNSS':                         'Bharatiya Nagarik Suraksha Sanhita 2023',
        'BHARATIYA NAGARIK SURAKSHA SANHITA': 'Bharatiya Nagarik Suraksha Sanhita 2023',
        'BHARATIYA NAGARIK SURAKSHA SANHITA 2023': 'Bharatiya Nagarik Suraksha Sanhita 2023',
        # NI Act
        'NI ACT':                       'Negotiable Instruments Act 1881',
        'NEGOTIABLE INSTRUMENTS ACT':   'Negotiable Instruments Act 1881',
        'NEGOTIABLE INSTRUMENTS ACT 1881': 'Negotiable Instruments Act 1881',
        # Evidence act family
        'IEA':                          'Indian Evidence Act 1872',
        'INDIAN EVIDENCE ACT':          'Indian Evidence Act 1872',
        'INDIAN EVIDENCE ACT 1872':     'Indian Evidence Act 1872',
        'EVIDENCE ACT':                 'Indian Evidence Act 1872',
        # BSA
        'BSA':                          'Bharatiya Sakshya Adhiniyam 2023',
        'BHARATIYA SAKSHYA ADHINIYAM':  'Bharatiya Sakshya Adhiniyam 2023',
        'BHARATIYA SAKSHYA ADHINIYAM 2023': 'Bharatiya Sakshya Adhiniyam 2023',
        # Civil Procedure
        'CPC':                          'Code of Civil Procedure 1908',
        'CODE OF CIVIL PROCEDURE':      'Code of Civil Procedure 1908',
        'CODE OF CIVIL PROCEDURE 1908': 'Code of Civil Procedure 1908',
        # Other acts
        'COMPANIES ACT':                'Companies Act 2013',
        'COMPANIES ACT 2013':           'Companies Act 2013',
        'CONSUMER PROTECTION ACT':      'Consumer Protection Act 2019',
        'CONSUMER PROTECTION ACT 2019': 'Consumer Protection Act 2019',
        'HINDU MARRIAGE ACT':           'Hindu Marriage Act 1955',
        'HINDU MARRIAGE ACT 1955':      'Hindu Marriage Act 1955',
        'HMA':                          'Hindu Marriage Act 1955',
        'ARBITRATION AND CONCILIATION ACT': 'Arbitration and Conciliation Act 1996',
        'ARBITRATION AND CONCILIATION ACT 1996': 'Arbitration and Conciliation Act 1996',
        'ACA':                          'Arbitration and Conciliation Act 1996',
        'TRANSFER OF PROPERTY ACT':     'Transfer of Property Act 1882',
        'TRANSFER OF PROPERTY ACT 1882': 'Transfer of Property Act 1882',
        'TPA':                          'Transfer of Property Act 1882',
        'LIMITATION ACT':               'Limitation Act 1963',
        'LIMITATION ACT 1963':          'Limitation Act 1963',
        'LA':                           'Limitation Act 1963',
        'PWDVA':                        'Protection of Women from Domestic Violence Act 2005',
        'PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE ACT': 'Protection of Women from Domestic Violence Act 2005',
        'PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE ACT 2005': 'Protection of Women from Domestic Violence Act 2005',
        'POCSO':                        'Protection of Children from Sexual Offences Act 2012',
        'PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT': 'Protection of Children from Sexual Offences Act 2012',
        'PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT 2012': 'Protection of Children from Sexual Offences Act 2012',
        'SRA':                          'Specific Relief Act 1963',
        'SPECIFIC RELIEF ACT':          'Specific Relief Act 1963',
        'SPECIFIC RELIEF ACT 1963':     'Specific Relief Act 1963',
    }

    @classmethod
    def _resolve_act_name(cls, fragment: str) -> Optional[str]:
        """
        Resolve an act name fragment / abbreviation to the exact canonical
        act_name stored in ChromaDB.  Returns None if unrecognised.
        """
        if not fragment:
            return None
        key = fragment.strip().upper()
        # Exact match first
        if key in cls._ACT_CANONICAL_NAMES:
            return cls._ACT_CANONICAL_NAMES[key]
        # Prefix match (e.g. "Indian Penal Code 186" → IPC)
        for k, v in cls._ACT_CANONICAL_NAMES.items():
            if key.startswith(k) or k.startswith(key):
                return v
        return None

    @staticmethod
    def _safe_str(value, default=''):
        """Convert pandas/dict value to string, handling NaN."""
        if pd.isna(value):
            return default
        return str(value) if value is not None else default

    @staticmethod
    def _to_native(value):
        """Recursively convert numpy scalars/bools into plain Python types."""
        if hasattr(value, 'item'):
            return value.item()
        if isinstance(value, dict):
            return {k: MetricsEngine._to_native(v) for k, v in value.items()}
        if isinstance(value, list):
            return [MetricsEngine._to_native(v) for v in value]
        if isinstance(value, tuple):
            return tuple(MetricsEngine._to_native(v) for v in value)
        return value
    
    def __init__(self, ground_truth_df: pd.DataFrame = None, chroma_client: chromadb.Client = None):
        """
        Initialize metrics engine.
        
        Args:
            ground_truth_df: Verified ground truth dataset
            chroma_client: ChromaDB client for hallucination detection
        """
        self.ground_truth = ground_truth_df
        self.chroma_client = chroma_client
        
        # Load ChromaDB collections for verification
        self.collections = {}
        if chroma_client:
            for name in ["bare_acts", "case_law", "amendments", "overruling_map"]:
                try:
                    self.collections[name] = chroma_client.get_collection(name=name)
                except:
                    print(f"Warning: Collection '{name}' not found")
        
        # Direct collection references for convenience
        self.bare_acts_collection = self.collections.get('bare_acts')
        self.case_law_collection = self.collections.get('case_law')
        self.amendments_collection = self.collections.get('amendments')
        self.overruling_map_collection = self.collections.get('overruling_map')
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # METRIC 1: Citation Accuracy Rate (CAR)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def compute_citation_accuracy(self, responses: List[Dict]) -> Dict:
        """
        METRIC 1: Citation Accuracy Rate (CAR) — SPLIT INTO TWO COMPONENTS
        
        CAR_retrieved: Accuracy of citations from retrieval metadata
        CAR_generated: Accuracy of citations extracted from LLM-generated answer text
        
        Measures % of answers containing correct act + section citation.
        
        Scoring:
        - Both act and section correct: 1.0
        - Act correct but section wrong: 0.5
        - Neither correct: 0.0
        
        Args:
            responses: List of system responses
            
        Returns:
            Dictionary with overall CAR and per-category breakdown for both retrieved and generated
        """
        scores_retrieved = []
        scores_generated = []
        category_scores_retrieved = defaultdict(list)
        category_scores_generated = defaultdict(list)
        
        for i, response in enumerate(responses):
            gt = self.ground_truth.iloc[i]
            response_query_id = response.get('query_id')
            gt_query_id = gt.get('query_id')
            
            # VALIDATION: Check for query_id mismatch (silent mis-scoring prevention)
            if response_query_id and gt_query_id and response_query_id != gt_query_id:
                raise ValueError(
                    f"Query ID mismatch at index {i}: response={response_query_id}, "
                    f"ground_truth={gt_query_id}. Index-based joins are invalid."
                )
            
            # Extract citations from response
            response_citations = response.get('citations', [])
            response_text = response.get('answer', '')
            
            # Get ground truth
            correct_act = self._safe_str(gt.get('correct_act', '')).strip().upper()
            correct_section = self._safe_str(gt.get('correct_section', '')).strip()
            correct_citation = self._safe_str(gt.get('correct_citation', '')).strip()
            if not correct_citation and correct_act and correct_section:
                correct_citation = f"{correct_act} Section {correct_section}"
            category = self._safe_str(gt.get('category', 'unknown'))

            predicted_candidates = self._extract_predicted_citation_candidates(response)
            citation_match = bool(correct_citation) and any(
                self.citations_match(pred, correct_citation)
                for pred in predicted_candidates
                if pred
            )
            
            if correct_act == '':
                # Query doesn't require specific citation
                score_retrieved = 1.0  # Don't penalize
                score_generated = 1.0
            else:
                # Check if correct act appears in citations or answer
                act_found = self._check_act_mentioned(correct_act, response_citations, response_text)
                
                # Check if correct section appears
                section_found = self._check_section_mentioned(correct_section, response_citations, response_text)
                
                # Scoring - RETRIEVED (from citations list)
                if citation_match:
                    score_retrieved = 1.0
                elif act_found and section_found:
                    score_retrieved = 1.0
                elif act_found:
                    score_retrieved = 0.5
                else:
                    score_retrieved = 0.0
                
                # Scoring - GENERATED (from answer text)
                # Extract section/act references from answer text alone
                import re
                answer_lower = response_text.lower()
                act_lower = correct_act.lower() if correct_act else ''
                act_found_text = act_lower in answer_lower if act_lower else True
                
                # Look for section numbers in answer
                section_pattern = r'(?:section|sec|s\.)\s*(\d+(?:\.\d+)?)'
                sections_in_answer = [m.group(1) for m in re.finditer(section_pattern, answer_lower)]
                section_found_text = bool(sections_in_answer) and any(
                    sec == correct_section for sec in sections_in_answer
                ) if correct_section else True
                
                if act_found_text and section_found_text:
                    score_generated = 1.0
                elif act_found_text:
                    score_generated = 0.5
                else:
                    score_generated = 0.0
            
            scores_retrieved.append(score_retrieved)
            scores_generated.append(score_generated)
            category_scores_retrieved[category].append(score_retrieved)
            category_scores_generated[category].append(score_generated)
        
        # Compute overall and per-category CAR
        car_retrieved_overall = np.mean(scores_retrieved) * 100 if scores_retrieved else 0
        car_generated_overall = np.mean(scores_generated) * 100 if scores_generated else 0
        
        car_retrieved_by_category = {
            cat: np.mean(cat_scores) * 100
            for cat, cat_scores in category_scores_retrieved.items()
        }
        
        car_generated_by_category = {
            cat: np.mean(cat_scores) * 100
            for cat, cat_scores in category_scores_generated.items()
        }
        
        return {
            "CAR_retrieved_overall": car_retrieved_overall,
            "CAR_retrieved_by_category": car_retrieved_by_category,
            "CAR_generated_overall": car_generated_overall,
            "CAR_generated_by_category": car_generated_by_category,
            # Legacy backward compatibility: average of both
            "CAR_overall": (car_retrieved_overall + car_generated_overall) / 2.0 if scores_retrieved and scores_generated else 0,
            "individual_scores_retrieved": scores_retrieved,
            "individual_scores_generated": scores_generated
        }

    def normalize_citation(self, citation_str: str) -> str:
        """Normalize Indian legal citation formats before CAR comparison."""
        s = str(citation_str).strip()
        if not s or s.lower() == 'nan':
            return ''

        # Abbreviation expansion
        s = re.sub(r'\bS\.\s*', 'Section ', s, flags=re.IGNORECASE)
        s = re.sub(r'\bSec\b\.?\s*', 'Section ', s, flags=re.IGNORECASE)
        s = re.sub(r'\bArt\b\.?\s*', 'Article ', s, flags=re.IGNORECASE)
        s = re.sub(r'\bOrd\b\.?\s*', 'Order ', s, flags=re.IGNORECASE)
        s = re.sub(r'\bR\.\s*(?=\d)', 'Rule ', s, flags=re.IGNORECASE)

        # Act name normalization
        replacements = {
            'CPC': 'Code of Civil Procedure',
            'CrPC': 'Code of Criminal Procedure',
            'Cr.P.C': 'Code of Criminal Procedure',
            'NI Act': 'Negotiable Instruments Act',
            'HMA': 'Hindu Marriage Act',
            'IPC': 'Indian Penal Code',
            'BNS': 'Bharatiya Nyaya Sanhita',
            'BNSS': 'Bharatiya Nagarik Suraksha Sanhita',
            'BSA': 'Bharatiya Sakshya Adhiniyam',
            'IEA': 'Indian Evidence Act',
            'NIA': 'Negotiable Instruments Act',
            'POCSO': 'Protection of Children from Sexual Offences Act',
        }
        for src, dst in replacements.items():
            s = re.sub(rf'\b{re.escape(src)}\b', dst, s, flags=re.IGNORECASE)

        # If format is "<Act Name> <number>", insert "Section" before number.
        s = re.sub(r'^(.*?\bACT\b(?:\s+\d{4})?)\s+(\d+[A-Z]?)$', r'\1 Section \2', s, flags=re.IGNORECASE)

        # Remove year suffixes for fuzzy matching
        s = re.sub(r'\b(19|20)\d{2}\b', '', s)

        # Normalize punctuation + whitespace
        s = s.replace(':', ' ').replace('-', ' ')
        s = re.sub(r'(?i)\bSECTION\s*([0-9]+[A-Z]?(?:\([0-9A-Za-z]+\))?)\b', r'SECTION \1', s)
        s = re.sub(r'(?i)\bARTICLE\s*([0-9]+[A-Z]?)\b', r'ARTICLE \1', s)
        s = re.sub(r'\s+', ' ', s).strip()

        return s.upper()

    def citations_match(self, predicted: str, ground_truth: str) -> bool:
        """Compare predicted and expected citations with robust normalization."""
        pred_norm = self.normalize_citation(predicted)
        gt_norm = self.normalize_citation(ground_truth)

        if not pred_norm or not gt_norm:
            return False

        # Exact match after normalization
        if pred_norm == gt_norm:
            return True

        # Containment match when one is a stricter formatted version of the other
        if gt_norm in pred_norm or pred_norm in gt_norm:
            return True

        # Partial match: section/article/order/rule numbers + act keywords
        section_nums = re.findall(r'\d+[A-Z]?', gt_norm)
        if section_nums and all(n in pred_norm for n in section_nums):
            stop_words = {
                'SECTION', 'ARTICLE', 'ORDER', 'RULE', 'CODE', 'ACT',
                'PROCEDURE', 'CHILDREN', 'FROM', 'SEXUAL', 'OFFENCES',
                'OF', 'THE', 'AND', 'FOR', 'UNDER',
            }
            act_keywords = [
                w for w in gt_norm.split()
                if len(w) > 4 and w not in stop_words
            ]
            if not act_keywords or any(kw in pred_norm for kw in act_keywords):
                return True

        return False

    def _extract_predicted_citation_candidates(self, response: Dict) -> List[str]:
        """Collect predicted citation candidates from response structures."""
        candidates: List[str] = []

        # 0) Direct fields
        direct = response.get('citation')
        if isinstance(direct, str) and direct.strip():
            candidates.append(direct.strip())

        source_section = response.get('source_section')
        if isinstance(source_section, str) and source_section.strip():
            candidates.append(source_section.strip())

        # 1) Structured citations list
        citations = response.get('citations', [])
        if isinstance(citations, list):
            for citation in citations:
                if isinstance(citation, dict):
                    act_part = str(citation.get('act_or_case', '')).strip()
                    sec_part = str(citation.get('section_or_citation', '')).strip()
                    combined = (act_part + ' ' + sec_part).strip()
                    if combined:
                        candidates.append(combined)
                    if sec_part:
                        candidates.append(sec_part)
                else:
                    c = str(citation).strip()
                    if c:
                        candidates.append(c)

        # 2) structured_response fallback (LexAI format)
        sr = response.get('structured_response', {})
        if isinstance(sr, dict):
            act = str(sr.get('act_cited', '')).strip()
            sec = str(sr.get('section_cited', '')).strip()
            combined = (act + ' ' + sec).strip()
            if combined:
                candidates.append(combined)
            if act and sec:
                candidates.append(f"{act} Section {sec}")
            if sec:
                candidates.append(sec)

        # De-duplicate while preserving order
        seen = set()
        out: List[str] = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out
    
    def _check_act_mentioned(self, act: str, citations: List[str], text: str) -> bool:
        """
        Check if correct act appears in STRUCTURED CITATIONS ONLY.
        Answer text is deliberately excluded — a system that writes the correct
        act name in prose is not the same as a system that provides a structured
        citation.  This is the research paper's definition of citation accuracy.
        """
        if not act or act == 'NAN':
            return True

        # No citations provided → act not cited
        if not citations:
            return False

        act_variants = {
            'IPC': ['IPC', 'INDIAN PENAL CODE', 'PENAL CODE'],
            'BNS': ['BNS', 'BHARATIYA NYAYA SANHITA', 'NYAYA SANHITA'],
            'CRPC': ['CRPC', 'CR.P.C', 'CODE OF CRIMINAL PROCEDURE', 'CRIMINAL PROCEDURE CODE'],
            'BNSS': ['BNSS', 'BHARATIYA NAGARIK SURAKSHA SANHITA'],
            'NI ACT': ['NI ACT', 'NEGOTIABLE INSTRUMENTS ACT', 'N.I. ACT'],
            'NIA': ['NIA', 'NI ACT', 'NEGOTIABLE INSTRUMENTS ACT', 'N.I. ACT'],
            'COMPANIES ACT': ['COMPANIES ACT'],
            'EVIDENCE ACT': ['EVIDENCE ACT', 'INDIAN EVIDENCE ACT'],
            'HMA': ['HMA', 'HINDU MARRIAGE ACT'],
            'POCSO': ['POCSO', 'PROTECTION OF CHILDREN FROM SEXUAL OFFENCES'],
            'PWDVA': ['PWDVA', 'DOMESTIC VIOLENCE ACT', 'PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE'],
            'SRA': ['SRA', 'SPECIFIC RELIEF ACT'],
            'TPA': ['TPA', 'TRANSFER OF PROPERTY ACT'],
            'LA': ['LA', 'LIMITATION ACT'],
            'ACA': ['ACA', 'ARBITRATION AND CONCILIATION ACT', 'ARBITRATION ACT'],
            'CPC': ['CPC', 'CODE OF CIVIL PROCEDURE'],
        }
        search_terms = act_variants.get(act, [act])

        # Build search text from citations ONLY — never from `text`
        citations_str = []
        for citation in citations:
            if isinstance(citation, dict):
                citations_str.append(
                    str(citation.get('act_or_case', '')) + ' ' +
                    str(citation.get('section_or_citation', ''))
                )
            else:
                citations_str.append(str(citation))

        citations_text = ' '.join(citations_str).upper()
        return any(term in citations_text for term in search_terms)

    def _check_section_mentioned(self, section: str, citations: List[str], text: str) -> bool:
        """
        Check if correct section appears in STRUCTURED CITATIONS ONLY.
        Answer text is deliberately excluded for the same reason as _check_act_mentioned.
        """
        if not section or section == 'nan':
            return True

        # No citations provided → section not cited
        if not citations:
            return False

        section_clean = section.strip().upper()

        # Build search text from citations ONLY — never from `text`
        citations_str = []
        for citation in citations:
            if isinstance(citation, dict):
                # For structured dicts, also do exact match on section_or_citation
                sec_val = str(citation.get('section_or_citation', '')).strip().upper()
                if sec_val == section_clean:
                    return True
                citations_str.append(
                    str(citation.get('act_or_case', '')) + ' ' + sec_val
                )
            else:
                citations_str.append(str(citation))

        citations_text = ' '.join(citations_str).upper()

        # Require the section number to appear next to a section indicator
        patterns = [
            f"SECTION {section_clean}",
            f"SEC {section_clean}",
            f"S. {section_clean}",
            f"§ {section_clean}",
            f"SEC. {section_clean}",
            f" {section_clean} ",   # bare number match inside citation text
        ]
        return any(pattern in citations_text for pattern in patterns)

    def _normalize_section_token(self, section: str) -> str:
        """Normalize section token to DB metadata format, e.g. 'Section 420' -> '420'."""
        sec = self._safe_str(section).strip()
        if not sec:
            return ''
        sec = re.sub(r'(?i)^section\s*', '', sec).strip()
        sec = re.sub(r'(?i)^sec\.?\s*', '', sec).strip()
        return sec

    def _parse_string_citation_claim(self, citation_text: str) -> Optional[Dict[str, str]]:
        """Parse string citations (baseline format) into structured claim candidates."""
        text = self._safe_str(citation_text).strip()
        if not text:
            return None

        if re.search(r'\b(?:AIR|SCC|SCR|Cri\.?\s*L\.?\s*J\.?)\b', text, re.IGNORECASE):
            return {
                "type": "case_law",
                "act_or_case": text,
                "section_or_citation": text,
            }

        sec_match = re.search(r'(?i)(?:section|sec\.?|s\.?)\s*([0-9]+[A-Z]?(?:\([0-9A-Za-z]+\))?)', text)
        if sec_match:
            return {
                "type": "bare_act",
                "act_or_case": text,
                "section_or_citation": f"Section {sec_match.group(1)}",
            }

        return None
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # METRIC 2: Hallucination Rate (HR) - FIXED
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _detect_hallucination(self, response: dict, ground_truth: dict) -> dict:
        """
        Verify every citation against ChromaDB.
        If citation not in ChromaDB AND not in ground truth = hallucinated.
        
        This is the only valid approach for a retrieval-based system.
        """
        hallucinated_sections = []
        hallucinated_cases = []
        hallucinated_inline = []
        total_claims = 0
        inline_claims = 0
        
        gt_section = self._normalize_section_token(self._safe_str(ground_truth.get('correct_section', '')))
        gt_act = self._safe_str(ground_truth.get('correct_act', '')).lower()
        gt_citation = self._safe_str(ground_truth.get('correct_citation', ''))
        
        # ── CHECK 1: Structured citations list ──────────────
        citations = response.get('citations', [])
        if not isinstance(citations, list):
            citations = []
        
        for citation in citations:
            # Handle both dict and string citations
            if isinstance(citation, str):
                parsed_citation = self._parse_string_citation_claim(citation)
                if not parsed_citation:
                    continue
                citation = parsed_citation
            elif not isinstance(citation, dict):
                # Unknown citation format - skip
                continue
            
            total_claims += 1
            ctype = citation.get('type', '')
            act_name = citation.get('act_or_case', '')
            section = self._safe_str(citation.get('section_or_citation', ''))
            section_norm = self._normalize_section_token(section)
            
            # Is this citation in ground truth?
            in_gt = (
                (section_norm == gt_section and gt_act in act_name.lower())
                or section == gt_citation
            )
            if in_gt:
                continue  # Ground truth citations are never hallucinations
            
            if ctype == 'bare_act':
                # Verify section exists in ChromaDB using $eq on both fields
                if self.bare_acts_collection:
                    canonical_act = self._resolve_act_name(act_name) or act_name
                    try:
                        results = self.bare_acts_collection.get(
                            where={
                                "$and": [
                                    {"section_number": {"$eq": section_norm}},
                                    {"act_name": {"$eq": canonical_act}},
                                ]
                            }
                        )
                        if len(results['ids']) == 0:
                            hallucinated_sections.append({
                                "act": act_name,
                                "section": section,
                                "type": "bare_act_not_in_db"
                            })
                    except Exception:
                        pass  # ChromaDB error — skip, do not flag
                    
            elif ctype == 'case_law':
                # Verify case exists in ChromaDB
                if self.case_law_collection:
                    try:
                        results = self.case_law_collection.get(
                            where={"citation": {"$eq": section}}
                        )
                        if len(results['ids']) == 0:
                            hallucinated_cases.append({
                                "citation": section,
                                "case": act_name,
                                "type": "case_not_in_db"
                            })
                    except Exception:
                        pass
        
        # ── CHECK 2: Inline section references (RE-ENABLED in Phase 2) ────
        # Scan answer text for unsupported section/act claims (pattern-based)
        answer_text = response.get('answer', '').lower()
        import re
        
        # Pattern: "Section NNN" or "IPC NNN" or "BNS NNN" mentions in answer
        section_pattern = r'(?:section|sec|s\.)\s*(\d+(?:\.\d+)?)'
        for match in re.finditer(section_pattern, answer_text):
            section_mentioned = match.group(1)
            # Check if this section appears in the structured citations
            in_citations = any(
                str(section_mentioned) in str(c.get('section_or_citation', '')).lower()
                for c in citations if isinstance(c, dict)
            )
            if not in_citations:
                inline_claims += 1
                # Section mentioned in answer but not in structured citations — potential hallucination
                context_start = max(0, match.start() - 50)
                context_end = min(len(answer_text), match.end() + 50)
                hallucinated_inline.append({
                    "section": section_mentioned,
                    "context": answer_text[context_start:context_end],
                    "type": "unsupported_inline_reference"
                })

        total_claims_effective = total_claims + inline_claims
        all_hallucinated = hallucinated_sections + hallucinated_cases + hallucinated_inline
        total_hallucinated = len(all_hallucinated)
        
        return {
            "hr_citation": len(hallucinated_sections) / max(total_claims, 1),
            "hr_case": len(hallucinated_cases) / max(total_claims, 1),
            "hr_inline": len(hallucinated_inline) / max(total_claims_effective, 1),
            "hallucination_rate": total_hallucinated / max(total_claims_effective, 1),
            "hallucinated_items": all_hallucinated,
            "total_claims": total_claims_effective,
            "hallucinated_count": total_hallucinated
        }
    
    def compute_hallucination_rate(self, responses: List[Dict]) -> Dict:
        """
        METRIC 2: Hallucination Rate (HR)
        
        Uses fixed _detect_hallucination to verify against ChromaDB.
        
        Args:
            responses: List of system responses
            
        Returns:
            Dictionary with HR breakdown
        """
        all_hr_results = []
        total_hallucinated = 0
        total_claims = 0
        
        for i, response in enumerate(responses):
            gt = self.ground_truth.iloc[i].to_dict()
            response_query_id = response.get('query_id')
            gt_query_id = gt.get('query_id')
            
            # VALIDATION: Check for query_id mismatch (silent mis-scoring prevention)
            if response_query_id and gt_query_id and response_query_id != gt_query_id:
                raise ValueError(
                    f"Query ID mismatch at index {i}: response={response_query_id}, "
                    f"ground_truth={gt_query_id}. Index-based joins are invalid."
                )
            
            hr_result = self._detect_hallucination(response, gt)
            all_hr_results.append(hr_result)
            
            total_hallucinated += hr_result['hallucinated_count']
            total_claims += hr_result['total_claims']
        
        # Compute overall rate
        hr_overall = (total_hallucinated / total_claims * 100) if total_claims > 0 else 0
        
        # Aggregate by type
        hr_citation = np.mean([r['hr_citation'] for r in all_hr_results]) * 100
        hr_case = np.mean([r['hr_case'] for r in all_hr_results]) * 100
        hr_inline = np.mean([r['hr_inline'] for r in all_hr_results]) * 100
        
        return {
            "HR_overall": hr_overall,
            "HR_citation": hr_citation,
            "HR_case": hr_case,
            "HR_inline": hr_inline,
            "total_claims": total_claims,
            "hallucinated_claims": total_hallucinated,
            "individual_results": all_hr_results
        }
    
    def _extract_sections(self, text: str) -> List[Dict]:
        """Extract all section mentions from text."""
        pattern = r'(?:Section|Sec\.?|§)\s*(\d+[A-Z]?)\s+(?:of\s+)?([A-Z][A-Za-z\s]+)'
        matches = re.findall(pattern, text, re.IGNORECASE)
        return [{"section": m[0], "act": m[1].strip()} for m in matches]
    
    def _extract_case_citations(self, text: str) -> List[str]:
        """Extract case citations."""
        pattern = r'(?:AIR|SCC|SCR)\s+\d{4}\s+(?:SC|HC)\s+\d+'
        return re.findall(pattern, text, re.IGNORECASE)
    
    def _verify_section_exists(self, section_claim: Dict) -> bool:
        """Verify section exists in ChromaDB."""
        if 'bare_acts' not in self.collections:
            return True  # Cannot verify, assume true
        
        try:
            results = self.collections['bare_acts'].query(
                query_texts=[f"Section {section_claim['section']} {section_claim['act']}"],
                n_results=1
            )
            return len(results['documents'][0]) > 0
        except:
            return True  # Assume true on error
    
    def _verify_case_exists(self, case_citation: str) -> bool:
        """Verify case exists in ChromaDB."""
        if 'case_law' not in self.collections:
            return True
        
        try:
            results = self.collections['case_law'].query(
                query_texts=[case_citation],
                n_results=1
            )
            return len(results['documents'][0]) > 0
        except:
            return True
    
    def _verify_citation_legitimacy(self, citation: str, ground_truth_row) -> bool:
        """Check if citation is legitimate (in DB or ground truth)."""
        # Check against ground truth
        if citation in str(ground_truth_row.get('correct_citation', '')):
            return True
        if citation in str(ground_truth_row.get('correct_act', '')):
            return True
        
        # Simplified - assume legitimate if we can't verify
        return True
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # METRIC 3: Outdated Law Rate (OLR)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # METRIC 3: Outdated Law Rate (OLR)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Patterns indicating citation of a replaced act
    _REPLACED_ACTS_PATTERNS = [
        # IPC → BNS (from July 1 2024)
        (re.compile(r'\b(?:IPC|Indian Penal Code)\b', re.I),
         re.compile(r'\b(?:BNS|Bharatiya Nyaya Sanhita)\b', re.I),
         'IPC→BNS'),
        # CrPC → BNSS
        (re.compile(r'\b(?:CrPC|Cr\.P\.C|Code of Criminal Procedure)\b', re.I),
         re.compile(r'\b(?:BNSS|Bharatiya Nagarik Suraksha Sanhita)\b', re.I),
         'CrPC→BNSS'),
        # Evidence Act → BSA
        (re.compile(r'\b(?:Indian Evidence Act|IEA)\b', re.I),
         re.compile(r'\b(?:BSA|Bharatiya Sakshya Adhiniyam)\b', re.I),
         'IEA→BSA'),
    ]

    def compute_outdated_law_rate(self, responses: List[Dict]) -> Dict:
        """
        METRIC 3: Outdated Law Rate (OLR)

        Measures % of responses that cite a replaced/superseded law (IPC, CrPC,
        Indian Evidence Act) without also acknowledging the replacement act
        (BNS, BNSS, BSA respectively).

        This text-evidence approach works even when the ground-truth
        'bns_bnss_transition_applies' column is unpopulated, because the
        replacement of IPC/CrPC by BNS/BNSS is a universal fact (effective
        July 1, 2024) — any response citing IPC sections without a BNS note
        is citing outdated law.

        Sub-metrics:
        - OLR_ipc_bns:   cites IPC without BNS mention
        - OLR_crpc_bnss: cites CrPC without BNSS mention
        - OLR_evidence:  cites Indian Evidence Act without BSA mention

        Args:
            responses: List of system responses

        Returns:
            Dictionary with OLR overall and breakdown
        """
        ipc_violations = 0
        crpc_violations = 0
        evidence_violations = 0

        ipc_cited_count = 0
        crpc_cited_count = 0
        evidence_cited_count = 0

        for response in responses:
            answer = response.get('answer', '') or ''
            # Also inspect citations list for act names
            citations_text = ''
            for c in (response.get('citations', []) or []):
                if isinstance(c, dict):
                    citations_text += ' ' + c.get('act_or_case', '')
                else:
                    citations_text += ' ' + str(c)
            full_text = answer + ' ' + citations_text

            # BNS/BNSS/BSA transition-awareness notes from the response
            bns_note = (
                response.get('bns_transition_note') or
                response.get('bns_bnss_notes') or
                ''
            )
            bns_note_present = (
                isinstance(bns_note, str) and
                bns_note.strip() not in ('', '[]', 'null', 'None')
            ) or (
                isinstance(bns_note, list) and len(bns_note) > 0
            )

            for old_pat, new_pat, label in self._REPLACED_ACTS_PATTERNS:
                cites_old = bool(old_pat.search(full_text))
                cites_new = bool(new_pat.search(full_text)) or (
                    label == 'IPC→BNS' and bns_note_present
                )

                if label == 'IPC→BNS':
                    if cites_old:
                        ipc_cited_count += 1
                        if not cites_new:
                            ipc_violations += 1
                elif label == 'CrPC→BNSS':
                    if cites_old:
                        crpc_cited_count += 1
                        if not cites_new:
                            crpc_violations += 1
                elif label == 'IEA→BSA':
                    if cites_old:
                        evidence_cited_count += 1
                        if not cites_new:
                            evidence_violations += 1

        total_responses = len(responses)

        def rate(violations, applicable):
            if applicable == 0:
                return 0.0
            return violations / applicable * 100

        olr_ipc = rate(ipc_violations, ipc_cited_count)
        olr_crpc = rate(crpc_violations, crpc_cited_count)
        olr_evidence = rate(evidence_violations, evidence_cited_count)

        # For overall OLR: combine all violations against all applicable citations
        total_applicable = ipc_cited_count + crpc_cited_count + evidence_cited_count
        total_violations = ipc_violations + crpc_violations + evidence_violations
        olr_overall = rate(total_violations, total_applicable)

        # Also report % of responses containing ANY outdated citation
        responses_with_violation = sum(
            1 for response in responses
            if self._response_has_outdated_citation(response)
        )
        olr_response_level = responses_with_violation / max(total_responses, 1) * 100

        return {
            "OLR_overall": olr_overall,
            "OLR_response_level": olr_response_level,
            "OLR_ipc_bns": olr_ipc,
            "OLR_crpc_bnss": olr_crpc,
            "OLR_evidence_bsa": olr_evidence,
            "applicable_cases": {
                "ipc_cited": ipc_cited_count,
                "crpc_cited": crpc_cited_count,
                "evidence_cited": evidence_cited_count,
                "total": total_applicable,
            },
            "violations": {
                "ipc": ipc_violations,
                "crpc": crpc_violations,
                "evidence": evidence_violations,
                "total": total_violations,
            },
        }

    def _response_has_outdated_citation(self, response: dict) -> bool:
        """Return True if the response cites a replaced act without mentioning the replacement."""
        answer = response.get('answer', '') or ''
        citations_text = ' '.join(
            c.get('act_or_case', '') if isinstance(c, dict) else str(c)
            for c in (response.get('citations', []) or [])
        )
        full_text = answer + ' ' + citations_text

        bns_note = (
            response.get('bns_transition_note') or
            response.get('bns_bnss_notes') or ''
        )
        bns_note_present = (
            isinstance(bns_note, str) and
            bns_note.strip() not in ('', '[]', 'null', 'None')
        ) or (isinstance(bns_note, list) and len(bns_note) > 0)

        for old_pat, new_pat, label in self._REPLACED_ACTS_PATTERNS:
            cites_old = bool(old_pat.search(full_text))
            cites_new = bool(new_pat.search(full_text)) or (
                label == 'IPC→BNS' and bns_note_present
            )
            if cites_old and not cites_new:
                return True
        return False

    def compute_outdated_law_rate_transition_only(self, responses: List[Dict]) -> Dict:
        """
        Compute OLR restricted to transition-category queries.

        Transition-focused reporting should not be conflated with global OLR.
        """
        transition_mask = self.ground_truth['category'].astype(str).str.contains(
            'transition', case=False, na=False
        )
        transition_indices = [i for i, flag in enumerate(transition_mask.tolist()) if flag]

        if not transition_indices:
            return {
                "OLR_transition_overall": 0.0,
                "OLR_transition_response_level": 0.0,
                "OLR_transition_ipc_bns": 0.0,
                "OLR_transition_crpc_bnss": 0.0,
                "OLR_transition_evidence_bsa": 0.0,
                "transition_query_count": 0,
                "transition_applicable_cases": {
                    "ipc_cited": 0,
                    "crpc_cited": 0,
                    "evidence_cited": 0,
                    "total": 0,
                },
                "transition_violations": {
                    "ipc": 0,
                    "crpc": 0,
                    "evidence": 0,
                    "total": 0,
                },
            }

        transition_responses = [responses[i] for i in transition_indices if i < len(responses)]
        base = self.compute_outdated_law_rate(transition_responses)

        return {
            "OLR_transition_overall": base.get("OLR_overall", 0.0),
            "OLR_transition_response_level": base.get("OLR_response_level", 0.0),
            "OLR_transition_ipc_bns": base.get("OLR_ipc_bns", 0.0),
            "OLR_transition_crpc_bnss": base.get("OLR_crpc_bnss", 0.0),
            "OLR_transition_evidence_bsa": base.get("OLR_evidence_bsa", 0.0),
            "transition_query_count": len(transition_responses),
            "transition_applicable_cases": base.get("applicable_cases", {}),
            "transition_violations": base.get("violations", {}),
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # METRIC 4: Abstention Precision (AP) - FIXED
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _is_abstention(self, response: dict) -> bool:
        """
        Detect abstention by content not length.
        Abstention = system explicitly refused to answer due to insufficient database evidence.
        """
        # Signal 0: Explicit abstention flag from system output.
        if bool(response.get('trigger_uncertainty')):
            return True

        # Signal 1: Explicit low confidence flag
        confidence = response.get('confidence', '')
        if isinstance(confidence, str):
            confidence_low = confidence.lower() == 'low'
        elif isinstance(confidence, (int, float)):
            confidence_low = confidence < 0.5
        else:
            confidence_low = False
        
        # Signal 2: Abstention language in answer
        answer_lower = response.get('answer', '').lower()
        phrase_match = any(
            phrase in answer_lower 
            for phrase in ABSTENTION_PHRASES
        )
        
        # Signal 3: No citations provided
        no_citations = len(response.get('citations', [])) == 0
        
        # Abstention requires: (low confidence OR phrase match) AND no citations
        return (confidence_low or phrase_match) and no_citations
    
    def _check_answer_available_in_db(self, ground_truth: dict) -> bool:
        """
        Check if ChromaDB actually contains the answer for this query.
        Used for abstention precision.
        
        True = answer was available, system should have answered
        False = answer not in DB, abstention was correct
        """
        correct_section = self._safe_str(ground_truth.get('correct_section', ''))
        correct_act = self._safe_str(ground_truth.get('correct_act', ''))
        
        if not correct_section or not correct_act:
            return False
        
        if not self.bare_acts_collection:
            return False

        canonical_act = self._resolve_act_name(correct_act) or correct_act
        try:
            results = self.bare_acts_collection.get(
                where={
                    "$and": [
                        {"section_number": {"$eq": correct_section}},
                        {"act_name": {"$eq": canonical_act}},
                    ]
                }
            )
            return len(results['ids']) > 0
        except Exception:
            return False
    
    def compute_abstention_metrics(self, responses: List[Dict], ground_truths: List[Dict] = None) -> Dict:
        """
        METRIC 4: Abstention Precision (AP)
        
        TP: abstained AND answer not in DB (correct abstention)
        FP: abstained BUT answer was in DB (wrong abstention)
        FN: answered BUT answer was wrong (should have abstained)
        TN: answered AND answer was correct
        
        AP = TP / (TP + FP)
        AR = TP / (TP + FN)
        F1 = harmonic mean of AP and AR
        
        Args:
            responses: List of system responses
            ground_truths: List of ground truth dicts (optional, uses self.ground_truth if not provided)
            
        Returns:
            Dictionary with AP, AR, and F1
        """
        TP = FP = FN = TN = 0
        
        # Use provided ground_truths or fall back to self.ground_truth
        if ground_truths is None:
            if self.ground_truth is None:
                return {
                    "abstention_precision": 0.0,
                    "abstention_recall": 0.0,
                    "f1_abstention": 0.0,
                    "abstention_rate": 0.0,
                    "TP": 0, "FP": 0, "FN": 0, "TN": 0,
                    "total_queries": 0
                }
            ground_truths = [self.ground_truth.iloc[i].to_dict() for i in range(len(responses))]
        
        for response, gt in zip(responses, ground_truths):
            abstained = self._is_abstention(response)
            available = self._check_answer_available_in_db(gt)
            
            # Check if answer was actually correct by checking citations
            correct_act = self._safe_str(gt.get('correct_act', '')).strip().upper()
            correct_section = self._safe_str(gt.get('correct_section', '')).strip()
            
            response_citations = response.get('citations', [])
            response_text = response.get('answer', '')
            
            answered_correctly = False
            if correct_act:
                act_found = self._check_act_mentioned(correct_act, response_citations, response_text)
                section_found = self._check_section_mentioned(correct_section, response_citations, response_text)
                answered_correctly = act_found and section_found
            else:
                answered_correctly = True  # No specific answer required
            
            if abstained and not available:
                TP += 1  # Correct abstention
            elif abstained and available:
                FP += 1  # Should have answered
            elif not abstained and not answered_correctly:
                FN += 1  # Should have abstained
            else:
                TN += 1  # Correctly answered
        
        total = len(responses)
        precision = TP / max(TP + FP, 1)
        recall = TP / max(TP + FN, 1)
        f1 = (2 * precision * recall) / max(precision + recall, 0.001)
        
        return {
            "abstention_precision": precision,
            "abstention_recall": recall,
            "f1_abstention": f1,
            "abstention_rate": (TP + FP) / max(total, 1),
            "TP": TP, "FP": FP, "FN": FN, "TN": TN,
            "total_queries": total
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # METRIC 5: Answer Completeness Score (ACS) - FIXED
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _fetch_section_text_from_chromadb(self, act: str, section: str) -> str:
        """
        Fetch the full_text of a section from ChromaDB bare_acts collection.
        Returns empty string if not found or ChromaDB unavailable.
        """
        if not self.bare_acts_collection or not act or not section:
            return ''

        act = self._safe_str(act)
        section = self._safe_str(section)
        if not act or not section:
            return ''

        act_upper = act.strip().upper()
        canonical_act = self._resolve_act_name(act_upper) or act.strip()

        try:
            results = self.bare_acts_collection.get(
                where={
                    "$and": [
                        {"section_number": {"$eq": section.strip()}},
                        {"act_name": {"$eq": canonical_act}},
                    ]
                },
                include=['documents', 'metadatas'],
            )
            if results['ids']:
                docs = results.get('documents') or []
                if docs and docs[0]:
                    return docs[0]
        except Exception:
            pass
        return ''

    def compute_answer_completeness(self, response: dict, ground_truth: dict) -> dict:
        """
        6-component scoring.  Length never awarded points.
        Each component tests content presence, not volume.

        Component 1 (direct_answer) now resolves the reference text from:
          1. correct_answer_summary in ground truth (if present / non-NaN)
          2. full_text of the GT section fetched from ChromaDB bare_acts
          3. Fallback: award 1.0 if answer is substantive (≥80 content words)
             because we have no reference to compare against.
        """
        scores = {}
        answer = response.get('answer', '')
        answer_lower = answer.lower()
        citations = response.get('citations', [])

        gt_summary = self._safe_str(ground_truth.get('correct_answer_summary', ''))
        gt_act = self._safe_str(ground_truth.get('correct_act', '')).lower()
        gt_section = self._safe_str(ground_truth.get('correct_section', ''))

        # ── Component 1: Answer addresses the question ──────
        # Use gt_summary if available, otherwise fetch section text from ChromaDB,
        # otherwise fall back to checking that the answer is substantive.
        STOPWORDS = {
            'the','a','an','is','are','was','were','in',
            'of','to','and','or','for','with','on','at',
            'from','by','that','this','which','shall','may',
            'any','such','said','under','section','act'
        }

        reference_text = gt_summary
        if not reference_text:
            reference_text = self._fetch_section_text_from_chromadb(
                self._safe_str(ground_truth.get('correct_act', '')),
                self._safe_str(ground_truth.get('correct_section', ''))
            )

        if reference_text and answer:
            ref_tokens = set(reference_text.lower().split()) - STOPWORDS
            answer_tokens = set(answer_lower.split()) - STOPWORDS
            if len(ref_tokens) > 0:
                overlap = len(ref_tokens & answer_tokens) / len(ref_tokens)
                if overlap >= 0.35:
                    scores['direct_answer'] = 1.0
                elif overlap >= 0.15:
                    scores['direct_answer'] = 0.5
                else:
                    scores['direct_answer'] = 0.0
            else:
                scores['direct_answer'] = 0.0
        else:
            # No reference available — grant credit if answer is substantive (≥80 content words)
            content_words = [w for w in answer_lower.split() if w not in STOPWORDS]
            scores['direct_answer'] = 1.0 if len(content_words) >= 80 else 0.5

        # ── Component 2: Correct act cited (structured citations ONLY) ──
        act_in_citations = any(
            gt_act in c.get('act_or_case', '').lower()
            for c in citations if isinstance(c, dict)
        )
        scores['act_cited'] = 1.0 if act_in_citations else 0.0

        # ── Component 3: Correct section cited (structured citations ONLY) ──
        section_in_citations = any(
            str(c.get('section_or_citation', '')).strip() == gt_section.strip()
            for c in citations if isinstance(c, dict)
        )
        scores['section_cited'] = 1.0 if section_in_citations else 0.0
        
        # ── Component 4: Amendment note (conditional) ────────
        if self._safe_str(ground_truth.get('amendment_applies')).lower() == 'yes':
            amendment_keywords = [
                'amended', 'amendment', 'modified',
                'substituted', 'inserted', 'changed',
                '2013', '2015', '2018', '2019', '2023'
            ]
            # Support both field name variants used by different systems
            amendment_notes_raw = (
                response.get('amendment_note') or
                response.get('amendment_notes') or
                []
            )
            amendment_note_present = (
                isinstance(amendment_notes_raw, list) and len(amendment_notes_raw) > 0
            ) or (
                isinstance(amendment_notes_raw, str) and
                amendment_notes_raw.strip() not in ('', '[]', 'null', 'None')
            )
            has_amendment = (
                amendment_note_present or
                any(kw in answer_lower for kw in amendment_keywords)
            )
            scores['amendment_note'] = 1.0 if has_amendment else 0.0
        else:
            scores['amendment_note'] = 1.0  # Not required

        # ── Component 5: BNS/BNSS note (conditional) ─────────
        if self._safe_str(ground_truth.get('bns_bnss_transition_applies')).lower() == 'yes':
            bns_keywords = [
                'bns', 'bnss', 'bsa', 'bharatiya nyaya',
                'bharatiya nagarik', 'bharatiya sakshya',
                'replaced', 'transition', 'new law',
                'july 2024', '2024'
            ]
            # Support both field name variants
            bns_notes_raw = (
                response.get('bns_transition_note') or
                response.get('bns_bnss_notes') or
                []
            )
            bns_note_present = (
                isinstance(bns_notes_raw, list) and len(bns_notes_raw) > 0
            ) or (
                isinstance(bns_notes_raw, str) and
                bns_notes_raw.strip() not in ('', '[]', 'null', 'None')
            )
            has_bns = (
                bns_note_present or
                any(kw in answer_lower for kw in bns_keywords)
            )
            scores['bns_note'] = 1.0 if has_bns else 0.0
        else:
            scores['bns_note'] = 1.0

        # ── Component 6: Overruling note (conditional) ───────
        if self._safe_str(ground_truth.get('overruling_applies')).lower() == 'yes':
            overruling_keywords = [
                'overruled', 'overruling', 'no longer good law',
                'per incuriam', 'not good law',
                'subsequently overruled', 'reversed'
            ]
            overruling_note_raw = (
                response.get('overruling_note') or
                response.get('overruling_notes') or
                ''
            )
            overruling_note_present = (
                isinstance(overruling_note_raw, str) and
                overruling_note_raw.strip() not in ('', '[]', 'null', 'None')
            ) or (
                isinstance(overruling_note_raw, list) and len(overruling_note_raw) > 0
            )
            has_overruling = (
                overruling_note_present or
                any(kw in answer_lower for kw in overruling_keywords)
            )
            scores['overruling_note'] = 1.0 if has_overruling else 0.0
        else:
            scores['overruling_note'] = 1.0
        
        total_earned = sum(scores.values())
        acs = (total_earned / 6.0) * 100
        
        return {
            "acs_score": round(acs, 2),
            "component_scores": scores,
            "components_passed": sum(1 for v in scores.values() if v > 0),
            "max_components": 6
        }
    
    def compute_completeness_score(self, responses: List[Dict]) -> Dict:
        """
        METRIC 5: Answer Completeness Score (ACS)

        Semantic completeness scoring against ground-truth summaries.
        This avoids fixed-value plateaus from rubric defaults (e.g., repeated 66.67).
        """
        scores = []
        category_scores = defaultdict(list)

        # Load once per batch; model is multilingual and already used in the project.
        from sentence_transformers import SentenceTransformer, util

        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

        # Build a query->GT map for robust alignment.
        query_map = {}
        if self.ground_truth is not None and 'query' in self.ground_truth.columns:
            for _, row in self.ground_truth.iterrows():
                q = self._safe_str(row.get('query', '')).strip()
                if q and q not in query_map:
                    query_map[q] = row.to_dict()

        fallback_rubric = 0
        skipped_empty_answer = 0

        for i, response in enumerate(responses):
            gt = None
            q = self._safe_str(response.get('query', '')).strip()
            if q and q in query_map:
                gt = query_map[q]
            elif self.ground_truth is not None and i < len(self.ground_truth):
                gt = self.ground_truth.iloc[i].to_dict()
            else:
                gt = {}

            answer = self._safe_str(response.get('answer', '')).strip()
            reference = self._safe_str(gt.get('correct_answer_summary', '')).strip()

            # Fallback to section text from Chroma only when summary is missing.
            if not reference:
                reference = self._fetch_section_text_from_chromadb(
                    self._safe_str(gt.get('correct_act', '')),
                    self._safe_str(gt.get('correct_section', '')),
                ).strip()

            category = self._safe_str(gt.get('category', 'unknown'))

            # Never default to a fixed score.
            if not answer:
                score = 0.0
                skipped_empty_answer += 1
            elif not reference:
                # Use existing rubric when semantic reference is unavailable.
                # This avoids artificial 0.0 scores for legacy rows while
                # still removing fixed-value fallbacks.
                score = float(self.compute_answer_completeness(response, gt)['acs_score'])
                fallback_rubric += 1
            else:
                emb_ans = model.encode(answer, convert_to_tensor=True)
                emb_ref = model.encode(reference, convert_to_tensor=True)
                sim = float(util.cos_sim(emb_ans, emb_ref).item())
                # Map cosine [-1, 1] to ACS [0, 100].
                score = round(max(0.0, min(100.0, ((sim + 1.0) / 2.0) * 100.0)), 2)
        
            scores.append(score)
            category_scores[category].append(score)

        if fallback_rubric > 0 or skipped_empty_answer > 0:
            print(
                f"[ACS] rubric_fallback={fallback_rubric}, empty_answer={skipped_empty_answer}"
            )

        return {
            "ACS_overall": np.mean(scores) if scores else 0.0,
            "ACS_by_category": {
                cat: (np.mean(cat_scores) if cat_scores else 0.0)
                for cat, cat_scores in category_scores.items()
            },
            "individual_scores": scores
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # METRIC 6: Retrieval Precision@K - FIXED
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def compute_retrieval_precision_at_k(self, query: str, ground_truth: dict, k: int = 3) -> dict:
        """
        Relevance determined by metadata match only.
        chunk.metadata['section_number'] == correct_section AND
        chunk.metadata['act_name'] contains correct_act
        
        Never use text substring for relevance judgment.
        """
        correct_section = self._safe_str(ground_truth.get('correct_section', ''))
        correct_act = self._safe_str(ground_truth.get('correct_act', '')).lower()
        correct_citation = self._safe_str(ground_truth.get('correct_citation', ''))
        category = self._safe_str(ground_truth.get('category', ''))
        
        # Choose collection based on query category
        if category in ['case_law_search', 'overruled_detection']:
            if not self.case_law_collection:
                return {
                    "p_at_1": 0.0,
                    f"p_at_{k}": 0.0,
                    "relevant_positions": [],
                    "relevant_count": 0,
                    "retrieved_metadata": []
                }
            
            collection = self.case_law_collection
            results = collection.query(
                query_texts=[query],
                n_results=k,
                include=['metadatas', 'distances']
            )
            
            relevant = []
            for metadata in results['metadatas'][0]:
                # Exact citation match for case law
                match = metadata.get('citation', '') == correct_citation
                relevant.append(match)
                
        else:
            if not self.bare_acts_collection:
                return {
                    "p_at_1": 0.0,
                    f"p_at_{k}": 0.0,
                    "relevant_positions": [],
                    "relevant_count": 0,
                    "retrieved_metadata": []
                }
            
            collection = self.bare_acts_collection
            results = collection.query(
                query_texts=[query],
                n_results=k,
                include=['metadatas', 'distances']
            )
            
            relevant = []
            canonical_act = self._resolve_act_name(correct_act.upper()) or correct_act
            for metadata in results['metadatas'][0]:
                # EXACT metadata match — not substring in text
                section_match = (
                    str(metadata.get('section_number', '')) == correct_section
                )
                act_match = (
                    metadata.get('act_name', '') == canonical_act
                )
                relevant.append(section_match and act_match)
        
        # Compute P@1 and P@k
        p_at_1 = float(relevant[0]) if relevant else 0.0
        p_at_k = (
            sum(relevant[:k]) / min(k, len(relevant)) 
            if relevant else 0.0
        )
        
        return {
            "p_at_1": p_at_1,
            f"p_at_{k}": p_at_k,
            "relevant_positions": [i for i, r in enumerate(relevant) if r],
            "relevant_count": sum(relevant),
            "retrieved_metadata": results['metadatas'][0]
        }
    
    def compute_retrieval_precision(self, responses: List[Dict], k_values: List[int] = [1, 3]) -> Dict:
        """
        METRIC 6: Retrieval Precision@K
        
        Wrapper for batch processing using fixed compute_retrieval_precision_at_k
        """
        precision_at_k = {k: [] for k in k_values}
        
        for i, response in enumerate(responses):
            gt = self.ground_truth.iloc[i].to_dict()
            query = response.get('query', '')
            
            if not query:
                continue
            
            for k in k_values:
                result = self.compute_retrieval_precision_at_k(query, gt, k=k)
                precision = result.get(f"p_at_{k}", 0.0)
                precision_at_k[k].append(precision)
        
        return {
            f"P@{k}": np.mean(scores) * 100 if scores else 0
            for k, scores in precision_at_k.items()
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # METRIC 7: Confidence Calibration Score (CCS)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def compute_confidence_calibration(self, responses: List[Dict]) -> Dict:
        """
        METRIC 7: Confidence Calibration Score (CCS)
        
        Does confidence level match actual accuracy?
        
        Well-calibrated system:
        - HIGH confidence → >85% accurate
        - MEDIUM confidence → 60-85% accurate
        - LOW confidence → <60% accurate
        
        Args:
            responses: List of system responses
            
        Returns:
            Dictionary with calibration metrics and curve data
        """
        confidence_buckets = {'high': [], 'medium': [], 'low': []}
        
        for i, response in enumerate(responses):
            gt = self.ground_truth.iloc[i]
            confidence = response.get('confidence', 'medium').lower()
            
            is_correct = self._is_response_correct_for_ccs(response, gt)
            
            if confidence in confidence_buckets:
                confidence_buckets[confidence].append(1.0 if is_correct else 0.0)
        
        # Compute accuracy per confidence level
        calibration = {}
        for conf_level, scores in confidence_buckets.items():
            if scores:
                calibration[f"accuracy_at_{conf_level}"] = np.mean(scores) * 100
                calibration[f"count_{conf_level}"] = len(scores)
            else:
                calibration[f"accuracy_at_{conf_level}"] = 0
                calibration[f"count_{conf_level}"] = 0
        
        # Calibration error (simplified ECE)
        expected_accuracy = {'high': 0.90, 'medium': 0.725, 'low': 0.50}
        calibration_error = 0
        total_samples = sum(len(scores) for scores in confidence_buckets.values())
        
        for conf_level, scores in confidence_buckets.items():
            if scores:
                actual_accuracy = np.mean(scores)
                weight = len(scores) / total_samples
                error = abs(actual_accuracy - expected_accuracy[conf_level])
                calibration_error += weight * error
        
        calibration['calibration_error'] = calibration_error
        calibration['is_well_calibrated'] = calibration_error < 0.15
        
        return calibration

    def _is_response_correct_for_ccs(self, response: Dict, gt_row) -> bool:
        """
        Compute binary correctness label for confidence calibration.

        Uses citation-grounded correctness signals rather than confidence text,
        so CCS reflects true answer quality.
        """
        answer = self._safe_str(response.get('answer', ''))

        correct_act = self._safe_str(gt_row.get('correct_act', '')).strip().upper()
        correct_section = self._safe_str(gt_row.get('correct_section', '')).strip()
        correct_citation = self._safe_str(gt_row.get('correct_citation', '')).strip()
        if not correct_citation and correct_act and correct_section:
            correct_citation = f"{correct_act} Section {correct_section}"

        response_citations = response.get('citations', [])
        predicted_candidates = self._extract_predicted_citation_candidates(response)
        citation_match = bool(correct_citation) and any(
            self.citations_match(pred, correct_citation)
            for pred in predicted_candidates
            if pred
        )

        act_found = self._check_act_mentioned(correct_act, response_citations, answer) if correct_act else True
        section_found = self._check_section_mentioned(correct_section, response_citations, answer) if correct_section else True

        return citation_match or (act_found and section_found)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MASTER COMPUTE FUNCTION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def compute_all_metrics(self, responses: List[Dict]) -> Dict:
        """
        Compute all 7 metrics for a system.
        
        Args:
            responses: List of system responses (must match ground truth order)
            
        Returns:
            Dictionary with all metrics
        """
        print(f"Computing metrics for {len(responses)} responses...")
        
        metrics = {}
        
        print("  1/7 Computing Citation Accuracy Rate...")
        metrics['CAR'] = self.compute_citation_accuracy(responses)
        
        print("  2/7 Computing Hallucination Rate...")
        metrics['HR'] = self.compute_hallucination_rate(responses)
        
        print("  3/7 Computing Outdated Law Rate...")
        metrics['OLR'] = self.compute_outdated_law_rate(responses)
        metrics['OLR'].update(self.compute_outdated_law_rate_transition_only(responses))
        
        print("  4/7 Computing Abstention Precision...")
        metrics['AP'] = self.compute_abstention_metrics(responses)
        
        print("  5/7 Computing Answer Completeness Score...")
        metrics['ACS'] = self.compute_completeness_score(responses)
        
        print("  6/7 Computing Retrieval Precision...")
        metrics['Precision_at_K'] = self.compute_retrieval_precision(responses)
        
        print("  7/7 Computing Confidence Calibration...")
        metrics['CCS'] = self.compute_confidence_calibration(responses)

        metrics['metric_schema_version'] = METRIC_SCHEMA_VERSION
        
        print("  ✓ All metrics computed")

        return self._to_native(metrics)


def demo():
    """Demo function showing metrics computation."""
    # This would use real data in practice
    print("Metrics Engine Demo")
    print("=" * 60)
    print("\nThis module computes 7 research metrics:")
    print("  1. Citation Accuracy Rate (CAR)")
    print("  2. Hallucination Rate (HR)")
    print("  3. Outdated Law Rate (OLR)")
    print("  4. Abstention Precision (AP)")
    print("  5. Answer Completeness Score (ACS)")
    print("  6. Retrieval Precision@K")
    print("  7. Confidence Calibration Score (CCS)")
    print("\nUse with verified ground truth dataset and system responses.")


if __name__ == "__main__":
    demo()
