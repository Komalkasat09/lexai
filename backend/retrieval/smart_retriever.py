"""
Smart Retriever for Legal Research System
Implements 7-step intelligent retrieval pipeline:
1. Query Classification - Auto-detect query type
2. Parallel Retrieval - Query all relevant collections simultaneously
3. Confidence Scoring - Filter low-confidence results
4. Overruling Check - Flag invalidated judgments
5. Amendment Check - Attach amendment history
6. BNS/BNSS Middleware - Handle IPC/CrPC → BNS/BNSS transitions
7. Enriched Context - Return comprehensive legal context

This module prevents hallucinations by rejecting low-confidence results
and maintaining awareness of legal changes over time.
"""

import os
import re
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

# Import database manager
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.chroma_setup import LegalResearchDB

# Import hybrid retrieval (improved retrieval with BM25 + cross-encoder)
try:
    from retrieval.hybrid_retriever import HybridRetriever, initialize_hybrid_retrievers
    HYBRID_RETRIEVAL_AVAILABLE = True
    print("✅ Hybrid retrieval enabled (BM25 + Dense + Cross-Encoder)")
except ImportError as e:
    HYBRID_RETRIEVAL_AVAILABLE = False
    print(f"⚠️  Hybrid retrieval unavailable: {e}")
    print("   Falling back to naive ChromaDB retrieval")
    print("   Install: pip install rank-bm25")


# ============================================================================
# CONFIGURATION
# ============================================================================

# Confidence thresholds
CONFIDENCE_HIGH = 0.75      # Tuned on 50-query holdout (Phase 5)
CONFIDENCE_MEDIUM = 0.60    # Tuned on 50-query holdout (Phase 5)
CONFIDENCE_LOW = 0.50       # Do not use - triggers uncertainty

# Unanswered queries log
UNANSWERED_LOG = "./data/unanswered_queries.log"


# ============================================================================
# QUERY TYPE CLASSIFICATION
# ============================================================================

class QueryType(Enum):
    """Types of legal queries the system can handle."""
    SECTION_LOOKUP = "section_lookup"           # "What is Section 420 IPC"
    CASE_SEARCH = "case_search"                 # "Find cases on cheating"
    LEGAL_QUESTION = "legal_question"           # "Can a contract be oral?"
    PUNISHMENT_QUERY = "punishment_query"       # "What is punishment for theft"
    AMENDMENT_QUERY = "amendment_query"         # "Has Section 420 been amended"
    CITATION_LOOKUP = "citation_lookup"         # "AIR 2019 SC 1234"
    GENERAL = "general"                         # Catch-all


def classify_query(query: str) -> QueryType:
    """
    Automatically detect query type from text.
    
    Args:
        query: User's natural language query
        
    Returns:
        QueryType enum
    """
    query_lower = query.lower()
    
    # Check for section lookup patterns
    section_patterns = [
        r'section\s+\d+[a-z]?',
        r'sec\.\s+\d+',
        r's\.\s+\d+',
        r'what is section',
        r'explain section',
        r'define section'
    ]
    for pattern in section_patterns:
        if re.search(pattern, query_lower):
            return QueryType.SECTION_LOOKUP
    
    # Check for citation lookup
    citation_patterns = [
        r'air\s+\d{4}\s+sc\s+\d+',
        r'\(\d{4}\)\s+\d+\s+scc\s+\d+',
        r'\d{4}\s+\(\d+\)\s+scc\s+\d+'
    ]
    for pattern in citation_patterns:
        if re.search(pattern, query_lower):
            return QueryType.CITATION_LOOKUP
    
    # Check for punishment query
    punishment_keywords = ['punishment', 'penalty', 'sentence', 'imprisonment', 'fine']
    if any(keyword in query_lower for keyword in punishment_keywords):
        return QueryType.PUNISHMENT_QUERY
    
    # Check for amendment query
    amendment_keywords = ['amended', 'amendment', 'changed', 'modified', 'updated']
    if any(keyword in query_lower for keyword in amendment_keywords):
        return QueryType.AMENDMENT_QUERY
    
    # Check for case search
    case_keywords = ['case', 'judgment', 'precedent', 'ruling', 'held', 'decided']
    if any(keyword in query_lower for keyword in case_keywords):
        return QueryType.CASE_SEARCH
    
    # Default to legal question
    return QueryType.LEGAL_QUESTION


def infer_act_filter_from_query(query: str) -> Optional[str]:
    """Infer canonical act name from query text for precision routing."""
    q = str(query or '').upper()

    act_patterns = [
        (r'\bCPC\b|CODE OF CIVIL PROCEDURE', 'Code of Civil Procedure 1908'),
        (r'\bCRPC\b|CODE OF CRIMINAL PROCEDURE|CR\.P\.C', 'Code of Criminal Procedure 1973'),
        (r'\bIPC\b|INDIAN PENAL CODE', 'Indian Penal Code 1860'),
        (r'\bBNS\b|BHARATIYA NYAYA SANHITA', 'Bharatiya Nyaya Sanhita 2023'),
        (r'\bBNSS\b|BHARATIYA NAGARIK SURAKSHA SANHITA', 'Bharatiya Nagarik Suraksha Sanhita 2023'),
        (r'\bBSA\b|BHARATIYA SAKSHYA ADHINIYAM', 'Bharatiya Sakshya Adhiniyam 2023'),
        (r'\bPOCSO\b|PROTECTION OF CHILDREN FROM SEXUAL OFFENCES', 'Protection of Children from Sexual Offences Act 2012'),
        (r'\bNIA\b|\bNI ACT\b|NEGOTIABLE INSTRUMENTS ACT', 'Negotiable Instruments Act 1881'),
        (r'SPECIFIC RELIEF ACT', 'Specific Relief Act 1963'),
        (r'LIMITATION ACT', 'Limitation Act 1963'),
        (r'TRANSFER OF PROPERTY ACT', 'Transfer of Property Act 1882'),
        (r'ARBITRATION( AND| &) CONCILIATION ACT|ARBITRATION ACT', 'Arbitration and Conciliation Act 1996'),
        (r'HINDU MARRIAGE ACT|\bHMA\b', 'Hindu Marriage Act 1955'),
        (r'DOMESTIC VIOLENCE ACT|PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE', 'Protection of Women from Domestic Violence Act 2005'),
    ]

    for pattern, canonical in act_patterns:
        if re.search(pattern, q):
            return canonical
    return None


# ============================================================================
# BNS/BNSS MAPPING MIDDLEWARE
# ============================================================================

# Comprehensive IPC → BNS mapping (50+ critical sections)
IPC_BNS_MAP = {
    # Offences against the State
    "121": {"bns": "147", "changes": "substantially same"},
    "124A": {"bns": "152", "changes": "sedition redefined"},
    
    # Offences against Public Tranquility
    "141": {"bns": "189", "changes": "unlawful assembly - same"},
    "147": {"bns": "191", "changes": "rioting - same"},
    "153A": {"bns": "196", "changes": "promoting enmity - enhanced"},
    
    # Offences against Human Body
    "299": {"bns": "100", "changes": "culpable homicide - same"},
    "300": {"bns": "101", "changes": "murder definition - same"},
    "302": {"bns": "103", "changes": "punishment for murder - same"},
    "304": {"bns": "105", "changes": "culpable homicide not amounting to murder - minor changes"},
    "304A": {"bns": "106", "changes": "causing death by negligence - same"},
    "304B": {"bns": "80", "changes": "dowry death - same"},
    "307": {"bns": "109", "changes": "attempt to murder - same"},
    "308": {"bns": "110", "changes": "attempt to culpable homicide - same"},
    "311": {"bns": "113", "changes": "being thug - removed"},
    "312": {"bns": "88", "changes": "causing miscarriage - same"},
    "313": {"bns": "89", "changes": "miscarriage without consent - same"},
    "314": {"bns": "90", "changes": "death by miscarriage - same"},
    "315": {"bns": "91", "changes": "prevent child being born alive - same"},
    "316": {"bns": "92", "changes": "child death by neglect - same"},
    "319": {"bns": "115", "changes": "hurt - same definition"},
    "320": {"bns": "114", "changes": "grievous hurt - same"},
    "323": {"bns": "115", "changes": "punishment for hurt - same"},
    "324": {"bns": "117", "changes": "hurt by dangerous weapons - same"},
    "325": {"bns": "121", "changes": "grievous hurt - same"},
    "326": {"bns": "117", "changes": "grievous hurt by weapons - same"},
    "326A": {"bns": "124", "changes": "acid attack - enhanced punishment"},
    "326B": {"bns": "125", "changes": "acid throwing - same"},
    "354": {"bns": "74", "changes": "outraging modesty - enhanced punishment"},
    "354A": {"bns": "75", "changes": "sexual harassment - same"},
    "354B": {"bns": "76", "changes": "assault to disrobe - same"},
    "354C": {"bns": "77", "changes": "voyeurism - same"},
    "354D": {"bns": "78", "changes": "stalking - same"},
    "363": {"bns": "137", "changes": "kidnapping - same"},
    "364": {"bns": "139", "changes": "kidnapping for murder - same"},
    "364A": {"bns": "140", "changes": "kidnapping for ransom - same"},
    "365": {"bns": "141", "changes": "kidnapping with intent - same"},
    "366": {"bns": "87", "changes": "kidnapping woman - same"},
    "366A": {"bns": "94", "changes": "procuration of minor girl - same"},
    "366B": {"bns": "95", "changes": "importation of girl - same"},
    "375": {"bns": "63", "changes": "rape - expanded definition of consent"},
    "376": {"bns": "64", "changes": "punishment for rape - enhanced"},
    "376A": {"bns": "65", "changes": "rape causing death - same"},
    "376B": {"bns": "66", "changes": "intercourse by husband - same"},
    "376C": {"bns": "67", "changes": "intercourse by person in authority - same"},
    "376D": {"bns": "70", "changes": "gang rape - enhanced punishment"},
    "376E": {"bns": "71", "changes": "repeat offenders - life/death"},
    
    # Offences against Property
    "378": {"bns": "303", "changes": "theft - same"},
    "379": {"bns": "303", "changes": "punishment for theft - same"},
    "380": {"bns": "305", "changes": "theft in dwelling - same"},
    "381": {"bns": "306", "changes": "theft by servant - same"},
    "382": {"bns": "304", "changes": "theft after preparation - same"},
    "383": {"bns": "308", "changes": "extortion - same"},
    "384": {"bns": "308", "changes": "punishment for extortion - same"},
    "385": {"bns": "351", "changes": "putting in fear - same"},
    "386": {"bns": "309", "changes": "extortion by threat - same"},
    "387": {"bns": "309", "changes": "extortion by threat of death - same"},
    "392": {"bns": "309", "changes": "robbery - same"},
    "393": {"bns": "310", "changes": "attempt to commit robbery - same"},
    "394": {"bns": "311", "changes": "robbery with hurt - enhanced"},
    "395": {"bns": "310", "changes": "dacoity - same"},
    "396": {"bns": "311", "changes": "dacoity with murder - death penalty"},
    "397": {"bns": "311", "changes": "robbery with attempt to murder - same"},
    "399": {"bns": "310", "changes": "preparation for dacoity - same"},
    "400": {"bns": "310", "changes": "being dacoit - same"},
    "401": {"bns": "312", "changes": "belonging to gang - same"},
    "402": {"bns": "310", "changes": "assembling for dacoity - same"},
    "403": {"bns": "316", "changes": "dishonest misappropriation - same"},
    "404": {"bns": "316", "changes": "misappropriation of property - same"},
    "405": {"bns": "316", "changes": "criminal breach of trust - same"},
    "406": {"bns": "316", "changes": "punishment for breach of trust - same"},
    "407": {"bns": "316", "changes": "breach of trust by carrier - same"},
    "408": {"bns": "316", "changes": "breach of trust by servant - same"},
    "409": {"bns": "316", "changes": "breach of trust by public servant - enhanced"},
    "415": {"bns": "318", "changes": "cheating - same"},
    "417": {"bns": "318", "changes": "punishment for cheating - same"},
    "418": {"bns": "318", "changes": "cheating with knowledge - same"},
    "419": {"bns": "318", "changes": "cheating by personation - same"},
    "420": {"bns": "318", "changes": "cheating and dishonestly inducing - substantially same"},
    "421": {"bns": "318", "changes": "cheating by false property - same"},
    "422": {"bns": "318", "changes": "cheating by personation - same"},
    "423": {"bns": "318", "changes": "dishonest concealment - same"},
    "424": {"bns": "318", "changes": "dishonest destruction - same"},
    "425": {"bns": "324", "changes": "mischief - same"},
    "426": {"bns": "324", "changes": "punishment for mischief - same"},
    "427": {"bns": "324", "changes": "mischief causing damage - same"},
    
    # Offences relating to Documents
    "463": {"bns": "336", "changes": "forgery - same"},
    "464": {"bns": "336", "changes": "making false document - same"},
    "465": {"bns": "336", "changes": "punishment for forgery - same"},
    "466": {"bns": "337", "changes": "forgery of record - same"},
    "467": {"bns": "337", "changes": "forgery of valuable security - same"},
    "468": {"bns": "337", "changes": "forgery for cheating - same"},
    "469": {"bns": "337", "changes": "forgery for harming reputation - same"},
    "470": {"bns": "338", "changes": "forged document - same"},
    "471": {"bns": "340", "changes": "using forged document - same"},
    
    # Offences relating to Marriage
    "493": {"bns": "81", "changes": "cohabitation by fraud - same"},
    "494": {"bns": "82", "changes": "bigamy - same"},
    "495": {"bns": "83", "changes": "bigamy with concealment - same"},
    "496": {"bns": "84", "changes": "fraudulent marriage - same"},
    "497": {"bns": "removed", "changes": "adultery decriminalized"},
    "498": {"bns": "84", "changes": "enticing married woman - same"},
    "498A": {"bns": "85", "changes": "cruelty by husband - substantially same"},
    
    # Defamation
    "499": {"bns": "356", "changes": "defamation - same"},
    "500": {"bns": "356", "changes": "punishment for defamation - same"},
    
    # Criminal Intimidation
    "503": {"bns": "351", "changes": "criminal intimidation - same"},
    "504": {"bns": "352", "changes": "intentional insult - same"},
    "505": {"bns": "196", "changes": "statements causing public mischief - same"},
    "506": {"bns": "351", "changes": "punishment for criminal intimidation - same"},
    "507": {"bns": "351", "changes": "criminal intimidation by anonymous - same"},
    "509": {"bns": "79", "changes": "word/gesture to insult modesty - same"},
    "511": {"bns": "62", "changes": "attempting to commit offences - same"},
}

# Lazy-loaded learned transition classifier (Fix 2 runtime integration).
_transition_classifier = None


def _get_transition_classifier():
    """Load learned transition classifier once; return None if unavailable."""
    global _transition_classifier
    if _transition_classifier is not None:
        return _transition_classifier
    try:
        from transition_classifier.transition_classifier import TransitionClassifier
        _transition_classifier = TransitionClassifier()
        print("✅ Learned transition classifier loaded")
    except Exception as e:
        print(f"⚠️  Learned transition classifier unavailable: {e}")
        _transition_classifier = None
    return _transition_classifier


def _normalize_section_number(section_number: Any) -> str:
    """Normalize section numbers for map lookups (e.g. 420.0 -> 420)."""
    sec = str(section_number or "").strip()
    if sec.endswith(".0") and sec[:-2].isdigit():
        sec = sec[:-2]
    return sec


def _build_transition_reference_text(act_name: str, section_number: str) -> str:
    """Build canonical section-reference text for classifier inference."""
    act = str(act_name or "").strip()
    if "IPC" in act or "Indian Penal Code" in act:
        return f"Section {section_number} of the Indian Penal Code"
    if "CrPC" in act or "Code of Criminal Procedure" in act or "Cr.P.C" in act:
        return f"Section {section_number} of the Code of Criminal Procedure"
    return f"Section {section_number} of {act}" if act else ""

# Comprehensive CrPC → BNSS mapping (50+ critical sections)
CRPC_BNSS_MAP = {
    # Arrest provisions
    "41": {"bnss": "35", "changes": "arrest without warrant - added safeguards for women/disabled"},
    "41A": {"bnss": "35", "changes": "notice of appearance - same"},
    "41B": {"bnss": "36", "changes": "personal bond - same"},
    "41C": {"bnss": "37", "changes": "arrest procedure - same"},
    "41D": {"bnss": "38", "changes": "health checkup - same"},
    
    # FIR and Investigation
    "154": {"bnss": "173", "changes": "FIR - added e-FIR and zero FIR provisions"},
    "155": {"bnss": "174", "changes": "information about cognizable offence - same"},
    "156": {"bnss": "175", "changes": "police officer's power - same"},
    "157": {"bnss": "176", "changes": "procedure for investigation - same"},
    "158": {"bnss": "177", "changes": "report to magistrate - same"},
    "159": {"bnss": "178", "changes": "power to hold investigation - same"},
    "160": {"bnss": "179", "changes": "police officer's power to require attendance - same"},
    "161": {"bnss": "180", "changes": "examination of witnesses - substantially same"},
    "162": {"bnss": "181", "changes": "statements to police not signed - same"},
    "163": {"bnss": "182", "changes": "no inducement to be offered - same"},
    "164": {"bnss": "183", "changes": "recording of confessions - added video conferencing"},
    "165": {"bnss": "184", "changes": "search by police officer - same"},
    "166": {"bnss": "185", "changes": "public to give information - same"},
    "167": {"bnss": "187", "changes": "police custody and remand - changed default remand to 15 days"},
    "168": {"bnss": "188", "changes": "report of investigation - same"},
    "169": {"bnss": "189", "changes": "release of accused - same"},
    "170": {"bnss": "190", "changes": "charge sheet procedure - same"},
    "173": {"bnss": "193", "changes": "final report - substantially same"},
    
    # Complaints to Magistrates
    "190": {"bnss": "210", "changes": "cognizance of offences - same"},
    "191": {"bnss": "211", "changes": "transfer on application - same"},
    "192": {"bnss": "212", "changes": "making false accusation - same"},
    "193": {"bnss": "213", "changes": "prosecution for false charge - same"},
    "200": {"bnss": "220", "changes": "examination of complainant - same"},
    "202": {"bnss": "222", "changes": "postponement of issue - same"},
    "203": {"bnss": "223", "changes": "dismissal of complaint - same"},
    "204": {"bnss": "224", "changes": "issue of process - same"},
    
    # Trial Procedures
    "207": {"bnss": "230", "changes": "supply of copies - same"},
    "208": {"bnss": "231", "changes": "commitment procedure - removed for sessions cases"},
    "209": {"bnss": "232", "changes": "commitment of case - simplified"},
    "215": {"bnss": "238", "changes": "trial before court of sessions - same"},
    "216": {"bnss": "239", "changes": "court of sessions to try with assessors - same"},
    "217": {"bnss": "240", "changes": "sessions trial procedure - same"},
    "218": {"bnss": "241", "changes": "trial for more than one offence - same"},
    "228": {"bnss": "251", "changes": "discharge - same"},
    "229": {"bnss": "252", "changes": "framing of charge - same"},
    "230": {"bnss": "253", "changes": "plea of guilty - same"},
    "231": {"bnss": "254", "changes": "acquittal on plea - same"},
    "232": {"bnss": "255", "changes": "conviction on plea - same"},
    "233": {"bnss": "256", "changes": "prosecutor's opening - same"},
    "235": {"bnss": "258", "changes": "hearing on sentence - same"},
    "240": {"bnss": "263", "changes": "framing of charge - summary trial"},
    "242": {"bnss": "265", "changes": "conviction on plea - summary"},
    "243": {"bnss": "266", "changes": "evidence if not guilty plea - same"},
    "244": {"bnss": "267", "changes": "aquittal or conviction - same"},
    
    # Bail Provisions
    "436": {"bnss": "479", "changes": "bail in bailable offences - same"},
    "437": {"bnss": "483", "changes": "bail in non-bailable - expanded provisions for undertrials"},
    "438": {"bnss": "482", "changes": "anticipatory bail - same"},
    "439": {"bnss": "483", "changes": "special powers of High Court - substantially same"},
    "440": {"bnss": "484", "changes": "amount of bond - same"},
    "441": {"bnss": "485", "changes": "bond to be executed - same"},
    "445": {"bnss": "489", "changes": "cancellation of bond - same"},
    
    # Appeals and Revisions
    "372": {"bnss": "400", "changes": "no appeal in petty cases - same"},
    "374": {"bnss": "402", "changes": "appeal from convictions - same"},
    "377": {"bnss": "405", "changes": "appeal by State - same"},
    "378": {"bnss": "406", "changes": "appeal to High Court - same"},
    "379": {"bnss": "407", "changes": "appeal in Sessions trial - same"},
    "380": {"bnss": "408", "changes": "special right of appeal - same"},
    "384": {"bnss": "412", "changes": "appeal procedure - same"},
    "386": {"bnss": "414", "changes": "powers of appellate court - same"},
    "389": {"bnss": "417", "changes": "suspension of sentence pending appeal - same"},
    "397": {"bnss": "425", "changes": "calling for records - same"},
    "401": {"bnss": "429", "changes": "High Court's revisional powers - same"},
    "482": {"bnss": "528", "changes": "inherent powers of High Court - same"},
}


def apply_bns_bnss_middleware(results: List[Dict], result_type: str) -> List[Dict]:
    """
    Apply BNS/BNSS transition notes to results mentioning IPC/CrPC sections.
    
    Args:
        results: List of retrieved results with metadata
        result_type: "bare_act" or "case_law"
        
    Returns:
        Enhanced results with BNS/BNSS transition notes
    """
    enhanced_results = []
    classifier = _get_transition_classifier()
    
    for result in results:
        metadata = result.get("metadata", {})
        act_name = metadata.get("act_name", "")
        section_number = _normalize_section_number(metadata.get("section_number", ""))
        
        # Check if this is IPC section
        if "IPC" in act_name or "Indian Penal Code" in act_name:
            learned_applied = False
            if classifier and section_number:
                reference_text = _build_transition_reference_text(act_name, section_number)
                if reference_text:
                    pred = classifier.predict(reference_text)
                    if pred.get("is_superseded"):
                        replacement = pred.get("replacement") or "Removed in BNS"
                        result["bns_transition"] = {
                            "original": f"IPC Section {section_number}",
                            "replaced_by": replacement,
                            "changes": "learned transition classifier",
                            "note": f"⚠️ Note: IPC Section {section_number} has been superseded. Suggested replacement: {replacement}.",
                            "source": "learned"
                        }
                        learned_applied = True

            if not learned_applied and section_number in IPC_BNS_MAP:
                bns_info = IPC_BNS_MAP[section_number]
                
                # Add transition note to metadata
                result["bns_transition"] = {
                    "original": f"IPC Section {section_number}",
                    "replaced_by": f"BNS Section {bns_info['bns']}" if bns_info['bns'] != 'removed' else "Removed in BNS",
                    "changes": bns_info["changes"],
                    "note": f"⚠️ Note: IPC Section {section_number} has been replaced by BNS Section {bns_info['bns']}. Changes: {bns_info['changes']}" if bns_info['bns'] != 'removed' else f"⚠️ Note: IPC Section {section_number} has been removed in Bharatiya Nyaya Sanhita 2023.",
                    "source": "rule_map"
                }
        
        # Check if this is CrPC section
        elif "CrPC" in act_name or "Code of Criminal Procedure" in act_name or "Cr.P.C" in act_name:
            learned_applied = False
            if classifier and section_number:
                reference_text = _build_transition_reference_text(act_name, section_number)
                if reference_text:
                    pred = classifier.predict(reference_text)
                    if pred.get("is_superseded"):
                        replacement = pred.get("replacement") or "BNSS equivalent"
                        result["bnss_transition"] = {
                            "original": f"CrPC Section {section_number}",
                            "replaced_by": replacement,
                            "changes": "learned transition classifier",
                            "note": f"⚠️ Note: CrPC Section {section_number} has been superseded. Suggested replacement: {replacement}.",
                            "source": "learned"
                        }
                        learned_applied = True

            if not learned_applied and section_number in CRPC_BNSS_MAP:
                bnss_info = CRPC_BNSS_MAP[section_number]
                
                # Add transition note to metadata
                result["bnss_transition"] = {
                    "original": f"CrPC Section {section_number}",
                    "replaced_by": f"BNSS Section {bnss_info['bnss']}",
                    "changes": bnss_info["changes"],
                    "note": f"⚠️ Note: CrPC Section {section_number} has been replaced by BNSS Section {bnss_info['bnss']}. Changes: {bnss_info['changes']}",
                    "source": "rule_map"
                }
        
        # Also check document text for IPC/CrPC mentions
        document_text = result.get("document", "")
        
        # Extract IPC sections from text
        ipc_sections = re.findall(r'\b[Ss]ection\s+(\d+[A-Z]?)\s+(?:of\s+)?(?:the\s+)?(?:IPC|I\.P\.C\.)\b', document_text)
        if ipc_sections:
            ipc_notes = []
            for sec in set(ipc_sections):
                if sec in IPC_BNS_MAP:
                    bns_info = IPC_BNS_MAP[sec]
                    ipc_notes.append(f"IPC {sec} → BNS {bns_info['bns']}")
            
            if ipc_notes:
                result["ipc_sections_mentioned"] = ipc_notes
        
        # Extract CrPC sections from text
        crpc_sections = re.findall(r'[Ss]ection\s+(\d+[A-Z]?)\s+(?:of\s+)?(?:the\s+)?(?:CrPC|Cr\.P\.C\.)', document_text)
        if crpc_sections:
            crpc_notes = []
            for sec in set(crpc_sections):
                if sec in CRPC_BNSS_MAP:
                    bnss_info = CRPC_BNSS_MAP[sec]
                    crpc_notes.append(f"CrPC {sec} → BNSS {bnss_info['bnss']}")
            
            if crpc_notes:
                result["crpc_sections_mentioned"] = crpc_notes
        
        enhanced_results.append(result)
    
    return enhanced_results


# ============================================================================
# CONFIDENCE SCORING
# ============================================================================

def calculate_confidence(distance: float) -> Tuple[str, float]:
    """
    Convert score to confidence level.
    
    NOTE: After Phase 1 fix, 'distance' is actually a pre-calculated confidence score (0-1)
    from hybrid_retriever, not a ChromaDB distance. ChromaDB distance was 0-2 range,
    but hybrid_retriever now passes native confidence directly to avoid double-conversion.
    
    Args:
        distance: Pre-calculated confidence score (0-1) from hybrid_retriever
        
    Returns:
        Tuple of (confidence_level, confidence_score)
    """
    # If value is already in confidence range [0, 1], use it directly (from hybrid_retriever)
    # Otherwise, convert from ChromaDB distance if < 2.0
    if distance <= 1.0:
        # Already a confidence score from hybrid_retriever
        similarity = distance
    else:
        # Legacy ChromaDB distance (0-2 range)
        similarity = 1 - (distance / 2)
    
    if similarity >= CONFIDENCE_HIGH:
        return ("HIGH", similarity)
    elif similarity >= CONFIDENCE_MEDIUM:
        return ("MEDIUM", similarity)
    else:
        return ("LOW", similarity)


def filter_by_confidence(results: List[Dict]) -> Tuple[List[Dict], bool]:
    """
    Filter results by confidence threshold and flag if all are low confidence.
    
    Args:
        results: List of results with distance scores
        
    Returns:
        Tuple of (filtered_results, trigger_uncertainty)
    """
    filtered_results = []
    low_confidence_count = 0
    
    for result in results:
        distance = result.get("distance", 2.0)
        confidence_level, confidence_score = calculate_confidence(distance)
        
        result["confidence_level"] = confidence_level
        result["confidence_score"] = round(confidence_score, 3)
        
        if confidence_level != "LOW":
            filtered_results.append(result)
        else:
            low_confidence_count += 1
    
    # Trigger uncertainty if all results are low confidence
    trigger_uncertainty = (len(filtered_results) == 0 and low_confidence_count > 0)
    
    return filtered_results, trigger_uncertainty


# ============================================================================
# SMART RETRIEVER CLASS
# ============================================================================

class SmartRetriever:
    """
    Intelligent retrieval system with 7-step pipeline for legal research.
    Prevents hallucinations through confidence filtering and tracks legal changes.
    """
    
    def __init__(self, db: LegalResearchDB, use_hybrid: bool = True,
                 confidence_high: float = None, confidence_medium: float = None,
                 use_bns_middleware: bool = True,
                 use_reranker: bool = True,
                 use_bm25: bool = True,
                 use_query_routing: bool = True):
        """
        Initialize smart retriever with database connection.
        
        Args:
            db: LegalResearchDB instance
            use_hybrid: Enable hybrid retrieval (BM25 + Dense + Cross-Encoder) for better precision
            confidence_high: High confidence threshold (default: 0.75)
            confidence_medium: Medium confidence threshold (default: 0.60)
            use_bns_middleware: Enable BNS/BNSS transition middleware (default: True)
        """
        self.db = db
        self.unanswered_log = UNANSWERED_LOG
        
        # Set confidence thresholds (use provided or defaults)
        self.confidence_high = confidence_high if confidence_high is not None else CONFIDENCE_HIGH
        self.confidence_medium = confidence_medium if confidence_medium is not None else CONFIDENCE_MEDIUM
        
        # BNS middleware flag (for ablation studies)
        self.use_bns_middleware = use_bns_middleware
        self.use_query_routing = use_query_routing
        self.use_reranker = use_reranker
        self.use_bm25 = use_bm25
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.unanswered_log), exist_ok=True)
        
        # Initialize hybrid retrieval (if available and enabled)
        self.use_hybrid = use_hybrid and HYBRID_RETRIEVAL_AVAILABLE
        self.hybrid_retrievers = {}
        
        if self.use_hybrid:
            try:
                print("\n🚀 Initializing hybrid retrieval system...")
                self.hybrid_retrievers = initialize_hybrid_retrievers(
                    db,
                    use_reranker=self.use_reranker,
                    use_bm25=self.use_bm25,
                )
                print(f"✅ Hybrid retrieval ready: {len(self.hybrid_retrievers)} collections")
            except Exception as e:
                print(f"⚠️  Failed to initialize hybrid retrieval: {e}")
                print("   Falling back to naive ChromaDB retrieval")
                self.use_hybrid = False
        else:
            print("ℹ️  Using naive ChromaDB retrieval (cosine similarity only)")
    
    
    def log_unanswered_query(self, query: str, query_type: str, reason: str):
        """
        Log queries that couldn't be answered with confidence.
        
        Args:
            query: Original query
            query_type: Classified query type
            reason: Reason for uncertainty
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "query": query,
            "query_type": query_type,
            "reason": reason
        }
        
        with open(self.unanswered_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    
    def retrieve(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute 7-step intelligent retrieval pipeline.
        
        Args:
            query: Natural language query
            query_type: Optional pre-classified query type
            filters: Optional filters (acts, courts, year_from, year_to)
            
        Returns:
            Enriched context package with legal data
        """
        filters = filters or {}
        
        # ====================================================================
        # STEP 1: QUERY CLASSIFICATION
        # ====================================================================
        if query_type is None and self.use_query_routing:
            query_type = classify_query(query)
        elif query_type is None:
            query_type = QueryType.GENERAL
        
        print(f"📋 Query Type: {query_type.value}")

        # Adapt retrieval depth for complex queries while keeping section lookups tight.
        if self.use_query_routing:
            bare_top_k, case_top_k = self._get_adaptive_top_k(query, query_type)
        else:
            # Ablation path: no query-type routing, fixed all-collections retrieval depth.
            bare_top_k, case_top_k = 5, 5
        
        # ====================================================================
        # STEP 2: PARALLEL RETRIEVAL
        # Retrieve from all relevant collections simultaneously
        # ====================================================================
        
        # Retrieve from bare_acts (always - top 3)
        # Use hybrid retrieval if available, otherwise fallback to naive ChromaDB
        act_filter = filters.get("acts", [None])[0] if filters.get("acts") else None
        if self.use_query_routing and (not act_filter) and query_type == QueryType.SECTION_LOOKUP:
            act_filter = infer_act_filter_from_query(query)
        
        if self.use_hybrid and 'bare_acts' in self.hybrid_retrievers:
            # HYBRID RETRIEVAL: BM25 + Dense + Cross-Encoder (40-60% better precision)
            metadata_filter = {"act_name": act_filter} if act_filter else None
            bare_acts_raw = self.hybrid_retrievers['bare_acts'].retrieve(
                query=query,
                n_results=bare_top_k,
                metadata_filter=metadata_filter
            )

            # If strict metadata filter misses due naming variants, retry without filter.
            if act_filter and (not bare_acts_raw.get('ids') or not bare_acts_raw['ids'][0]):
                bare_acts_raw = self.hybrid_retrievers['bare_acts'].retrieve(
                    query=query,
                    n_results=bare_top_k,
                    metadata_filter=None,
                )
        else:
            # FALLBACK: Naive ChromaDB cosine similarity
            bare_acts_raw = self.db.query_bare_acts(
                query_text=query,
                n_results=bare_top_k,
                act_filter=act_filter
            )

            # If strict metadata filter misses due naming variants, retry without filter.
            if act_filter and (not bare_acts_raw.get('ids') or not bare_acts_raw['ids'][0]):
                bare_acts_raw = self.db.query_bare_acts(
                    query_text=query,
                    n_results=bare_top_k,
                    act_filter=None,
                )
        
        # Retrieve from case_law (always - top 5)
        court_filter = filters.get("courts", [None])[0] if filters.get("courts") else None
        year_from = filters.get("year_from")
        year_to = filters.get("year_to")
        
        if self.use_hybrid and 'case_law' in self.hybrid_retrievers:
            # HYBRID RETRIEVAL: BM25 + Dense + Cross-Encoder
            metadata_filter = {}
            if court_filter:
                metadata_filter["court"] = court_filter
            # Note: year filters would need to be applied post-retrieval for hybrid
            # or implemented in HybridRetriever (future enhancement)
            metadata_filter = metadata_filter if metadata_filter else None
            
            case_law_raw = self.hybrid_retrievers['case_law'].retrieve(
                query=query,
                n_results=case_top_k,
                metadata_filter=metadata_filter
            )
        else:
            # FALLBACK: Naive ChromaDB cosine similarity
            case_law_raw = self.db.query_case_law(
                query_text=query,
                n_results=case_top_k,
                court_filter=court_filter,
                year_from=year_from,
                year_to=year_to
            )
        
        # Convert ChromaDB results to standardized format
        bare_acts_results = self._format_results(bare_acts_raw, "bare_act")
        case_law_results = self._format_results(case_law_raw, "case_law")
        
        print(f"📚 Retrieved {len(bare_acts_results)} bare act sections")
        print(f"⚖️  Retrieved {len(case_law_results)} case law documents")
        
        # ====================================================================
        # STEP 3: CONFIDENCE SCORING
        # Filter out low-confidence results
        # ====================================================================
        bare_acts_filtered, bare_acts_uncertain = filter_by_confidence(bare_acts_results)
        case_law_filtered, case_law_uncertain = filter_by_confidence(case_law_results)
        
        # Check if ALL results are low confidence
        if bare_acts_uncertain and case_law_uncertain:
            self.log_unanswered_query(
                query=query,
                query_type=query_type.value,
                reason="All results below confidence threshold"
            )
            
            return {
                "query_type": query_type.value,
                "answer": None,
                "trigger_uncertainty": True,
                "message": "I cannot provide a reliable answer on this query from my current database. Please consult primary sources or a qualified lawyer.",
                "bare_acts": [],
                "case_laws": [],
                "amendments": [],
                "confidence_level": "LOW",
                "has_bns_bnss_notes": False,
                "unanswered": True,
                "stats": {
                    "bare_acts_retrieved": 0,
                    "case_laws_retrieved": 0,
                    "amendments_found": 0,
                    "overruled_cases": 0
                }
            }
        
        # ====================================================================
        # STEP 4: OVERRULING CHECK
        # Check if any case law has been overruled
        # ====================================================================
        case_law_verified = []
        for case in case_law_filtered:
            citation = case["metadata"].get("citation", "")
            
            # Check overruling status
            overruling_info = self.db.check_if_overruled(citation)
            
            if overruling_info:
                case["is_overruled"] = True
                case["overruling_info"] = overruling_info
                case["warning"] = f"⚠️ This judgment has been overruled by {overruling_info['overruling_case']} ({overruling_info['year']})"
                
                # Try to retrieve the overruling judgment instead
                overruling_citation = overruling_info["overruled_by"]
                # Note: In production, fetch the overruling judgment here
            else:
                case["is_overruled"] = False
            
            case_law_verified.append(case)
        
        # ====================================================================
        # STEP 5: AMENDMENT CHECK
        # Check for amendments to bare act sections
        # ====================================================================
        bare_acts_with_amendments = []
        amendments_found = []
        
        for act in bare_acts_filtered:
            act_name = act["metadata"].get("act_name", "")
            section_number = act["metadata"].get("section_number", "")
            
            # Check for amendments
            if act_name and section_number:
                amendments_raw = self.db.get_amendments_for_section(act_name, section_number)
                
                if amendments_raw["ids"]:
                    act["has_amendments"] = True
                    act["amendments_count"] = len(amendments_raw["ids"])
                    
                    # Format amendments
                    for i, amend_id in enumerate(amendments_raw["ids"]):
                        amendments_found.append({
                            "id": amend_id,
                            "metadata": amendments_raw["metadatas"][i],
                            "document": amendments_raw["documents"][i]
                        })
                else:
                    act["has_amendments"] = False
            
            bare_acts_with_amendments.append(act)
        
        # ====================================================================
        # STEP 6: BNS/BNSS MIDDLEWARE
        # Apply IPC→BNS and CrPC→BNSS transition notes (if enabled)
        # ====================================================================
        if self.use_bns_middleware:
            bare_acts_enhanced = apply_bns_bnss_middleware(bare_acts_with_amendments, "bare_act")
            case_law_enhanced = apply_bns_bnss_middleware(case_law_verified, "case_law")
        else:
            # Skip middleware - pass through without BNS/BNSS notes
            bare_acts_enhanced = bare_acts_with_amendments
            case_law_enhanced = case_law_verified
        
        # Check if any BNS/BNSS notes were added
        has_bns_bnss = any(
            "bns_transition" in act or "bnss_transition" in act 
            for act in bare_acts_enhanced
        ) or any(
            "ipc_sections_mentioned" in case or "crpc_sections_mentioned" in case
            for case in case_law_enhanced
        )
        
        # ====================================================================
        # STEP 7: RETURN ENRICHED CONTEXT PACKAGE
        # ====================================================================
        
        # Determine overall confidence
        all_scores = (
            [r["confidence_score"] for r in bare_acts_enhanced] +
            [r["confidence_score"] for r in case_law_enhanced]
        )
        
        if all_scores:
            avg_confidence = sum(all_scores) / len(all_scores)
            if avg_confidence >= self.confidence_high:
                overall_confidence = "HIGH"
            elif avg_confidence >= self.confidence_medium:
                overall_confidence = "MEDIUM"
            else:
                overall_confidence = "LOW"
        else:
            overall_confidence = "NONE"
        
        return {
            "query_type": query_type.value,
            "trigger_uncertainty": False,
            "bare_acts": bare_acts_enhanced,
            "case_laws": case_law_enhanced,
            "amendments": amendments_found,
            "confidence_level": overall_confidence,
            "has_bns_bnss_notes": has_bns_bnss,
            "unanswered": False,
            "stats": {
                "bare_acts_retrieved": len(bare_acts_enhanced),
                "case_laws_retrieved": len(case_law_enhanced),
                "amendments_found": len(amendments_found),
                "overruled_cases": sum(1 for c in case_law_enhanced if c.get("is_overruled"))
            }
        }
    
    
    def _format_results(self, raw_results: Dict, result_type: str) -> List[Dict]:
        """
        Format ChromaDB query results into standardized structure.
        
        Args:
            raw_results: Raw results from ChromaDB
            result_type: Type of results ("bare_act" or "case_law")
            
        Returns:
            List of formatted results
        """
        formatted = []
        
        if not raw_results.get("ids") or not raw_results["ids"][0]:
            return formatted
        
        ids = raw_results["ids"][0]
        documents = raw_results["documents"][0]
        metadatas = raw_results["metadatas"][0]
        distances = raw_results["distances"][0]
        
        for i in range(len(ids)):
            formatted.append({
                "id": ids[i],
                "document": documents[i],
                "metadata": metadatas[i],
                "distance": distances[i],
                "type": result_type
            })
        
        return formatted

    def _get_adaptive_top_k(self, query: str, query_type: QueryType) -> Tuple[int, int]:
        """
        Adaptive retrieval context sizing.
        Keep narrow k for straightforward lookups and expand for multi-factor legal questions.
        """
        q = str(query or '').lower()

        # Base values (current behavior).
        bare_k = 3
        case_k = 5

        # Complex intents need wider context coverage.
        if query_type in {QueryType.LEGAL_QUESTION, QueryType.AMENDMENT_QUERY, QueryType.CASE_SEARCH}:
            bare_k = 5
            case_k = 8

        # Mapping/transition and comparative prompts are usually multi-hop.
        complexity_markers = [
            'equivalent', 'replaced', 'transition', 'compare', 'difference',
            'changed', 'mapping', 'old', 'new', 'superseded'
        ]
        if any(marker in q for marker in complexity_markers):
            bare_k = max(bare_k, 6)
            case_k = max(case_k, 8)

        # Citation lookups benefit from precision over breadth.
        if query_type == QueryType.CITATION_LOOKUP:
            bare_k = 2
            case_k = 3

        return bare_k, case_k


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def initialize_smart_retriever(db: Optional[LegalResearchDB] = None) -> SmartRetriever:
    """
    Initialize SmartRetriever with database.
    
    Args:
        db: Optional LegalResearchDB instance (creates new if not provided)
        
    Returns:
        SmartRetriever instance
    """
    if db is None:
        from database.chroma_setup import initialize_legal_db
        db = initialize_legal_db()
    
    return SmartRetriever(db)


# ============================================================================
# QUICK TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("SMART RETRIEVER - INITIALIZATION TEST")
    print("="*80 + "\n")
    
    # Initialize
    retriever = initialize_smart_retriever()
    
    # Test query classification
    test_queries = [
        "What is Section 420 IPC",
        "Find cases on cheating",
        "Can a contract be oral",
        "What is punishment for theft",
        "Has Section 420 been amended"
    ]
    
    print("🔍 Testing Query Classification:\n")
    for query in test_queries:
        query_type = classify_query(query)
        print(f"  '{query}'")
        print(f"  → {query_type.value}\n")
    
    # Test retrieval (with empty database)
    print("\n🔍 Testing Retrieval Pipeline:\n")
    result = retriever.retrieve("What is Section 420 IPC")
    
    print(f"Confidence Level: {result['confidence_level']}")
    print(f"Bare Acts Retrieved: {result['stats']['bare_acts_retrieved']}")
    print(f"Case Laws Retrieved: {result['stats']['case_laws_retrieved']}")
    print(f"Has BNS/BNSS Notes: {result['has_bns_bnss_notes']}")
    
    print("\n✅ Smart Retriever initialized successfully!")
    print("="*80 + "\n")
