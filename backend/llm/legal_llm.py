"""
STEP 4: LEGAL LLM LAYER
=======================
Production-grade LLM integration for legal research assistant.

This module provides deterministic, citation-aware legal Q&A using:
- Groq API (llama-3.3-70b-versatile) with temperature=0.0, seed=42
- SmartRetriever for enriched context retrieval
- Strict system prompt to prevent hallucinations
- Confidence-based response filtering
- Proper legal citation formatting

Author: Legal Research System
Date: February 2026
"""

import os
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env files in predictable locations.
def _load_env_files() -> List[str]:
    """Load .env from backend and workspace root if present."""
    module_dir = Path(__file__).resolve().parent
    candidate_paths = [
        module_dir.parent / ".env",           # backend/.env (primary)
        module_dir.parent.parent / ".env",    # workspace root .env (fallback)
    ]

    loaded_files: List[str] = []
    for env_path in candidate_paths:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            loaded_files.append(str(env_path))

    # Keep default discovery as a last fallback for unusual run layouts.
    if not loaded_files:
        load_dotenv(override=False)

    return loaded_files


_LOADED_ENV_FILES = _load_env_files()

# Import SmartRetriever from Step 3
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from retrieval.smart_retriever import SmartRetriever
from database.chroma_setup import LegalResearchDB

# ============================================================================
# GROQ CONFIGURATION (Deterministic Settings)
# ============================================================================
def _collect_groq_api_keys() -> List[str]:
    """
    Collect API keys from GROQ_API_KEY and GROQ_API_KEY_<n> env vars.
    Supports any number of keys (including 17+) and preserves numeric order.
    """
    keys: List[str] = []

    primary = os.getenv("GROQ_API_KEY", "").strip()
    if primary:
        keys.append(primary)

    numbered_keys = []
    for env_name, env_value in os.environ.items():
        if not env_value:
            continue

        match = re.fullmatch(r"GROQ_API_KEY_(\d+)", env_name)
        if match:
            numbered_keys.append((int(match.group(1)), env_value.strip()))

    numbered_keys.sort(key=lambda item: item[0])
    for _, key in numbered_keys:
        if key and key not in keys:
            keys.append(key)

    return keys


GROQ_API_KEYS = _collect_groq_api_keys()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE = 0.0  # Fully deterministic
GROQ_SEED = 42  # Consistent seed for reproducibility
GROQ_MAX_TOKENS = 2048

# ============================================================================
# STRICT LEGAL SYSTEM PROMPT
# ============================================================================
LEGAL_SYSTEM_PROMPT = """You are an expert legal research assistant for Indian law, designed to help practicing lawyers with accurate, reliable legal information.

CRITICAL RULES (NEVER VIOLATE):
1. **Only use information from the provided context** - NEVER add information from your training data
2. **Always cite sources** - Every legal statement must reference the act/section/case provided
3. **Acknowledge limitations** - If the context is insufficient, clearly state "The provided context does not contain..."
4. **Warn about transitions** - If you see BNS/BNSS notes (IPC/CrPC replacements), prominently mention the transition
5. **Flag uncertainties** - If confidence is LOW or MEDIUM, explicitly warn the user
6. **Never fabricate** - If you don't know, say "I cannot provide a reliable answer based on the current database"
7. **Preserve legal language** - Use precise legal terminology, don't oversimplify
8. **Check dates** - Always mention the year of cases/amendments
9. **Note overruling** - If a case is marked as overruled, DO NOT rely on it

RESPONSE FORMAT:
- Start with a direct answer to the question
- Cite the source immediately (Act Section/Case Citation)
- Explain the legal reasoning
- Warn about BNS/BNSS transitions if applicable
- End with confidence level and any caveats

TONE: Professional, precise, helpful to practicing lawyers. This is NOT a chatbot - treat it as a serious legal research tool."""

# ============================================================================
# HELPER PROMPTS
# ============================================================================
SECTION_EXPLANATION_PROMPT = """Explain the following legal provision in detail, covering:
1. Purpose and scope of the section
2. Key elements/ingredients
3. Punishments/consequences (if applicable)
4. Important case law interpretations (if provided)
5. Recent amendments (if any)
6. BNS/BNSS transition notes (if applicable)

Be comprehensive but precise."""

CASE_SUMMARY_PROMPT = """Summarize this legal judgment, covering:
1. Case name and citation
2. Court and year
3. Facts of the case (brief)
4. Legal issue(s)
5. Held/Judgment
6. Legal principles established
7. Overruling status (if any)

Focus on legally relevant points, not procedural details."""

CITATION_FORMAT_PROMPT = """Format all citations using standard Indian legal citation style:
- Acts: Act Name Year, Section Number
- Cases: Party v. Party, Citation, (Court Year)
- Example: "Indian Penal Code 1860, Section 420" or "State v. Kumar, AIR 2020 SC 1234"
"""


class LegalLLM:
    """
    Legal LLM wrapper with strict accuracy controls and retrieval integration.
    """
    
    def __init__(self, persist_directory: str = "./legal_research_db",
                 confidence_high: float = None, confidence_medium: float = None,
                 use_bns_middleware: bool = True,
                 use_reranker: bool = True,
                 use_bm25: bool = True,
                 use_query_routing: bool = True):
        """
        Initialize Legal LLM with SmartRetriever and Groq client.
        
        Args:
            persist_directory: Path to ChromaDB database
            confidence_high: High confidence threshold for retrieval (default: 0.75)
            confidence_medium: Medium confidence threshold for retrieval (default: 0.60)
            use_bns_middleware: Enable BNS/BNSS transition middleware (default: True)
        """
        # Initialize database and SmartRetriever
        self.db = LegalResearchDB(persist_directory=persist_directory)
        self.retriever = SmartRetriever(self.db, 
                                       confidence_high=confidence_high,
                                       confidence_medium=confidence_medium,
                                       use_bns_middleware=use_bns_middleware,
                                       use_reranker=use_reranker,
                                       use_bm25=use_bm25,
                                       use_query_routing=use_query_routing)
        
        # Initialize Groq client with fallback API keys
        if not GROQ_API_KEYS:
            searched = ", ".join(_LOADED_ENV_FILES) if _LOADED_ENV_FILES else "default dotenv discovery"
            raise ValueError(
                "No GROQ API keys found in environment. "
                "Expected GROQ_API_KEY and/or GROQ_API_KEY_<n>. "
                f"Dotenv sources: {searched}"
            )
        
        self.api_keys = GROQ_API_KEYS.copy()
        self.current_key_index = 0
        self.groq_client = Groq(api_key=self.api_keys[self.current_key_index])
        # key index -> unix timestamp until which key should be skipped
        self._key_cooldown_until: Dict[int, float] = {}
        
        print(f"✅ LegalLLM initialized with SmartRetriever and {len(self.api_keys)} Groq API key(s)")
    
    def _rotate_api_key(self) -> bool:
        """
        Rotate to the next available API key.
        
        Returns:
            True if a new key is available, False if all keys have been tried
        """
        self.current_key_index += 1
        if self.current_key_index >= len(self.api_keys):
            return False
        
        self.groq_client = Groq(api_key=self.api_keys[self.current_key_index])
        print(f"⚠️  Rotated to API key #{self.current_key_index + 1}")
        return True

    def _parse_retry_after_seconds(self, error_text: str) -> float:
        """Parse provider retry hint like 'Please try again in 1m7.39s'."""
        text = str(error_text)
        m = re.search(r"please try again in\s*([0-9]+)m([0-9]+(?:\.[0-9]+)?)s", text, re.IGNORECASE)
        if m:
            minutes = int(m.group(1))
            seconds = float(m.group(2))
            return minutes * 60 + seconds
        m = re.search(r"please try again in\s*([0-9]+(?:\.[0-9]+)?)s", text, re.IGNORECASE)
        if m:
            return float(m.group(1))
        # Fallback small wait to avoid hot-looping on unknown limit messages.
        return 10.0

    def _mark_current_key_cooldown(self, seconds: float) -> None:
        until = time.time() + max(1.0, float(seconds))
        self._key_cooldown_until[self.current_key_index] = until

    def _rotate_to_available_key(self) -> bool:
        """Rotate to next key whose cooldown has expired."""
        if not self.api_keys:
            return False

        now = time.time()
        n = len(self.api_keys)
        start = self.current_key_index
        for step in range(1, n + 1):
            idx = (start + step) % n
            if now >= self._key_cooldown_until.get(idx, 0.0):
                self.current_key_index = idx
                self.groq_client = Groq(api_key=self.api_keys[self.current_key_index])
                print(f"⚠️  Rotated to API key #{self.current_key_index + 1}")
                return True
        return False

    def _min_cooldown_wait(self) -> float:
        """Minimum wait until any key becomes available again."""
        now = time.time()
        waits = [max(0.0, t - now) for t in self._key_cooldown_until.values() if t > now]
        if not waits:
            return 0.0
        return min(waits)
    
    
    def _format_retrieval_context(self, retrieval_result: Dict[str, Any]) -> str:
        """
        Format SmartRetriever output into structured context for LLM.
        
        Args:
            retrieval_result: Output from SmartRetriever.retrieve()
        
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Header with query type and confidence
        context_parts.append(f"RETRIEVAL SUMMARY:")
        context_parts.append(f"Query Type: {retrieval_result.get('query_type', 'unknown')}")
        context_parts.append(f"Confidence Level: {retrieval_result.get('confidence_level', 'NONE')}")
        context_parts.append(f"BNS/BNSS Transition Notes: {'Yes' if retrieval_result.get('has_bns_bnss_notes') else 'No'}")
        context_parts.append("")
        
        # Bare Acts
        bare_acts = retrieval_result.get('bare_acts', [])
        if bare_acts:
            context_parts.append("=" * 80)
            context_parts.append("BARE ACTS / STATUTORY PROVISIONS:")
            context_parts.append("=" * 80)
            
            for i, act in enumerate(bare_acts, 1):
                meta = act.get('metadata', {})
                context_parts.append(f"\n[ACT {i}]")
                context_parts.append(f"Act: {meta.get('act_name', 'Unknown')}")
                context_parts.append(f"Section: {meta.get('section_number', 'Unknown')}")
                context_parts.append(f"Title: {meta.get('section_title', 'N/A')}")
                context_parts.append(f"Confidence: {act.get('confidence_score', 0):.3f}")
                
                # BNS/BNSS transition note
                if act.get('bns_bnss_note'):
                    context_parts.append(f"⚠️  TRANSITION: {act['bns_bnss_note']}")
                
                context_parts.append(f"\nText:\n{act.get('text', 'No text available')}")
                
                # Amendment info
                if act.get('has_amendments'):
                    context_parts.append(f"\n📋 This section has {act.get('amendments_count', 0)} amendment(s)")
        
        # Case Law
        case_laws = retrieval_result.get('case_laws', [])
        if case_laws:
            context_parts.append("\n" + "=" * 80)
            context_parts.append("CASE LAW / JUDICIAL PRECEDENTS:")
            context_parts.append("=" * 80)
            
            for i, case in enumerate(case_laws, 1):
                meta = case.get('metadata', {})
                context_parts.append(f"\n[CASE {i}]")
                context_parts.append(f"Case Name: {meta.get('case_name', 'Unknown')}")
                context_parts.append(f"Citation: {meta.get('citation', 'N/A')}")
                context_parts.append(f"Court: {meta.get('court', 'Unknown')}, Year: {meta.get('year', 'N/A')}")
                context_parts.append(f"Confidence: {case.get('confidence_score', 0):.3f}")
                
                # Overruling warning
                if case.get('is_overruled'):
                    context_parts.append(f"⚠️  WARNING: {case.get('warning', 'This case has been overruled')}")
                
                # BNS/BNSS note
                if case.get('bns_bnss_note'):
                    context_parts.append(f"📋 {case['bns_bnss_note']}")
                
                context_parts.append(f"\nFacts/Holding:\n{case.get('text', 'No text available')}")
        
        # Amendments
        amendments = retrieval_result.get('amendments', [])
        if amendments:
            context_parts.append("\n" + "=" * 80)
            context_parts.append("AMENDMENTS / LEGISLATIVE CHANGES:")
            context_parts.append("=" * 80)
            
            for i, amend in enumerate(amendments, 1):
                context_parts.append(f"\n[AMENDMENT {i}]")
                context_parts.append(f"Amendment: {amend.get('amendment_name', 'Unknown')}")
                context_parts.append(f"Year: {amend.get('year', 'N/A')}")
                context_parts.append(f"Act: {amend.get('act_name', 'Unknown')}, Section: {amend.get('section_number', 'N/A')}")
                context_parts.append(f"\nChanges:\n{amend.get('text', 'No details available')}")
        
        # Stats
        stats = retrieval_result.get('stats', {})
        context_parts.append("\n" + "=" * 80)
        context_parts.append(f"RETRIEVAL STATISTICS:")
        context_parts.append(f"Bare Acts: {stats.get('bare_acts_retrieved', 0)}")
        context_parts.append(f"Case Laws: {stats.get('case_laws_retrieved', 0)}")
        context_parts.append(f"Amendments: {stats.get('amendments_found', 0)}")
        context_parts.append(f"Overruled Cases: {stats.get('overruled_cases', 0)}")
        context_parts.append("=" * 80)
        
        return "\n".join(context_parts)
    
    
    def _call_groq_llm(self, user_prompt: str, system_prompt: str = LEGAL_SYSTEM_PROMPT, context: str = "") -> str:
        """
        Call Groq LLM with deterministic settings and automatic API key fallback.
        
        Args:
            user_prompt: User's question/instruction
            system_prompt: System prompt (defaults to LEGAL_SYSTEM_PROMPT)
            context: Retrieved context to include
        
        Returns:
            LLM response text
        """
        # Combine context and user prompt
        full_user_message = ""
        if context:
            full_user_message += f"CONTEXT:\n{context}\n\n"
        full_user_message += f"QUESTION:\n{user_prompt}"
        
        # Try with available keys, respecting per-key cooldowns from provider hints.
        max_retries = max(len(self.api_keys) * 2, 1)
        for attempt in range(max_retries):
            try:
                response = self.groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_user_message}
                    ],
                    temperature=GROQ_TEMPERATURE,
                    seed=GROQ_SEED,
                    max_tokens=GROQ_MAX_TOKENS
                )
                
                return response.choices[0].message.content
            
            except Exception as e:
                error_msg = str(e).lower()
                # Check if it's a rate limit or authentication error
                if any(keyword in error_msg for keyword in ['rate', 'limit', 'quota', 'expired', 'invalid', 'unauthorized', 'authentication']):
                    wait_s = self._parse_retry_after_seconds(str(e))
                    self._mark_current_key_cooldown(wait_s)
                    print(f"⚠️  API key error (attempt {attempt + 1}/{max_retries}): {str(e)}")

                    if attempt < max_retries - 1 and self._rotate_to_available_key():
                        print("🔄 Retrying with next API key...")
                        continue

                    # No key currently available: wait for nearest cooldown and retry once.
                    min_wait = self._min_cooldown_wait()
                    if min_wait > 0 and attempt < max_retries - 1:
                        sleep_for = min(min_wait + 0.5, 75.0)
                        print(f"⏳ All keys cooling down; sleeping {sleep_for:.1f}s before retry...")
                        time.sleep(sleep_for)
                        # After sleep, try selecting an available key.
                        if self._rotate_to_available_key():
                            print("🔄 Retrying after cooldown...")
                            continue

                    return (
                        f"Error: All API keys are rate-limited right now. Last error: {str(e)}\n\n"
                        "Please wait for cooldown, reduce request volume, or increase Groq quota."
                    )
                else:
                    # Non-key related error, don't retry
                    return f"Error calling Groq API: {str(e)}\n\nPlease check your internet connection."
        
        return "Error: Maximum retry attempts reached with all API keys."

    def _build_structured_citations(self, retrieval_result: Dict[str, Any], query: str = "") -> List[Dict[str, str]]:
        """Build evaluator-friendly citations from retrieved sources while preserving original section references."""
        citations: List[Dict[str, str]] = []

        query_upper = str(query).upper()

        def _extract_query_act_hint() -> str:
            if any(tok in query_upper for tok in ["IPC", "आईपीसी", "INDIAN PENAL CODE", "भारतीय दंड संहिता"]):
                return "IPC"
            if any(tok in query_upper for tok in ["CRPC", "सीआरपीसी", "CODE OF CRIMINAL PROCEDURE", "दंड प्रक्रिया संहिता"]):
                return "CRPC"
            if any(tok in query_upper for tok in ["CPC", "CODE OF CIVIL PROCEDURE"]):
                return "CPC"
            if any(tok in query_upper for tok in ["IT ACT", "आईटी अधिनियम", "INFORMATION TECHNOLOGY ACT"]):
                return "IT ACT"
            if any(tok in query_upper for tok in ["BNSS", "बीएनएसएस", "BHARATIYA NAGARIK SURAKSHA SANHITA"]):
                return "BNSS"
            if any(tok in query_upper for tok in ["BNS", "बीएनएस", "BHARATIYA NYAYA SANHITA"]):
                return "BNS"
            if any(tok in query_upper for tok in ["BSA", "BHARATIYA SAKSHYA ADHINIYAM"]):
                return "BSA"
            if any(tok in query_upper for tok in ["POCSO", "PROTECTION OF CHILDREN FROM SEXUAL OFFENCES"]):
                return "POCSO"
            if any(tok in query_upper for tok in ["NI ACT", "NEGOTIABLE INSTRUMENTS ACT", "NIA"]):
                return "NIA"
            if any(tok in query_upper for tok in ["HMA", "HINDU MARRIAGE ACT"]):
                return "HMA"
            if any(tok in query_upper for tok in ["SPECIFIC RELIEF ACT"]):
                return "SRA"
            if any(tok in query_upper for tok in ["LIMITATION ACT"]):
                return "LA"
            if any(tok in query_upper for tok in ["TRANSFER OF PROPERTY ACT"]):
                return "TPA"
            if any(tok in query_upper for tok in ["ARBITRATION ACT", "ARBITRATION AND CONCILIATION ACT"]):
                return "ACA"
            if any(tok in query_upper for tok in ["DOMESTIC VIOLENCE ACT", "PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE"]):
                return "PWDVA"
            return ""

        def _extract_query_section_hint() -> str:
            # Handles: "Section 420", "धारा 420", "धारा 156(3)", "IPC 120B".
            m = re.search(r'(?:SECTION|SEC\.?|S\.?|धारा)\s*(\d+[A-Z]?)', query_upper)
            if m:
                return m.group(1)
            m = re.search(r'(?:IPC|CRPC|BNS|BNSS)\s*(\d+[A-Z]?)', query_upper)
            if m:
                return m.group(1)
            return ""

        def _canonical_act_label(act_name: str) -> str:
            name = str(act_name or '').strip()
            key = name.upper()
            mapping = {
                'BHARATIYA NYAYA SANHITA 2023': 'BNS',
                'BHARATIYA NYAYA SANHITA': 'BNS',
                'BHARATIYA NAGARIK SURAKSHA SANHITA 2023': 'BNSS',
                'BHARATIYA NAGARIK SURAKSHA SANHITA': 'BNSS',
                'BHARATIYA SAKSHYA ADHINIYAM 2023': 'BSA',
                'BHARATIYA SAKSHYA ADHINIYAM': 'BSA',
                'INDIAN PENAL CODE 1860': 'IPC',
                'INDIAN PENAL CODE': 'IPC',
                'CODE OF CIVIL PROCEDURE 1908': 'CPC',
                'CODE OF CIVIL PROCEDURE': 'CPC',
                'CODE OF CRIMINAL PROCEDURE 1973': 'CRPC',
                'CODE OF CRIMINAL PROCEDURE': 'CRPC',
                'INDIAN EVIDENCE ACT 1872': 'IEA',
                'INDIAN EVIDENCE ACT': 'IEA',
                'NEGOTIABLE INSTRUMENTS ACT 1881': 'NIA',
                'NEGOTIABLE INSTRUMENTS ACT': 'NIA',
                'SPECIFIC RELIEF ACT 1963': 'SRA',
                'SPECIFIC RELIEF ACT': 'SRA',
                'LIMITATION ACT 1963': 'LA',
                'LIMITATION ACT': 'LA',
                'TRANSFER OF PROPERTY ACT 1882': 'TPA',
                'TRANSFER OF PROPERTY ACT': 'TPA',
                'ARBITRATION AND CONCILIATION ACT 1996': 'ACA',
                'ARBITRATION AND CONCILIATION ACT': 'ACA',
                'HINDU MARRIAGE ACT 1955': 'HMA',
                'HINDU MARRIAGE ACT': 'HMA',
                'PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE ACT 2005': 'PWDVA',
                'PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE ACT': 'PWDVA',
                'PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT 2012': 'POCSO',
                'PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT': 'POCSO',
            }
            return mapping.get(key, name)

        def _canonical_section_label(section_value: str) -> str:
            raw = str(section_value or '').strip()
            if not raw:
                return ''
            raw = re.sub(r'(?i)^section\s*', '', raw).strip()
            raw = re.sub(r'[^0-9A-Za-z()\-]+', '', raw)
            if not raw:
                return ''
            return f"Section {raw}"

        hinted_act = _extract_query_act_hint()
        hinted_section = _extract_query_section_hint()

        if hinted_act and hinted_section:
            citations.append({
                'type': 'query_hint',
                'act_or_case': _canonical_act_label(hinted_act),
                'section_or_citation': _canonical_section_label(hinted_section),
                '_score': 1000,
            })

        # Prefer citations that explicitly match section numbers mentioned in the query.
        query_sections = set()
        for m in re.findall(r'(?<!\d)(\d+[A-Z]?)(?!\d)', query_upper):
            query_sections.add(str(m).strip())

        is_section_lookup = bool(re.search(r'\b(SECTION|SEC\.?|S\.?|धारा)\s*\d+', query_upper))
        hinted_act_canonical = _canonical_act_label(hinted_act) if hinted_act else ''
        hinted_section_canonical = _canonical_section_label(hinted_section) if hinted_section else ''

        def _score_citation(act_value: str, section_value: str) -> int:
            sec = str(section_value).strip().upper().replace('SECTION', '').strip()
            act_norm = _canonical_act_label(act_value).upper()
            score = 0
            if sec in query_sections:
                score += 100
            if hinted_act_canonical and act_norm == hinted_act_canonical.upper():
                score += 60
            if hinted_section_canonical and _canonical_section_label(sec).upper() == hinted_section_canonical.upper():
                score += 80
            # Strongly boost exact act+section pair for section lookups.
            if is_section_lookup and hinted_act_canonical and hinted_section_canonical:
                if act_norm == hinted_act_canonical.upper() and _canonical_section_label(sec).upper() == hinted_section_canonical.upper():
                    score += 400
            return score

        for act in retrieval_result.get('bare_acts', []):
            meta = act.get('metadata', {}) or {}
            act_name = str(meta.get('act_name', '')).strip()
            section_number = str(meta.get('section_number', '')).strip()

            if act_name and section_number:
                citations.append({
                    'type': 'bare_act',
                    'act_or_case': _canonical_act_label(act_name),
                    'section_or_citation': _canonical_section_label(section_number),
                    '_score': _score_citation(act_name, section_number),
                })

            # Add transition mapping as an additional citation instead of replacing the original.
            trans = act.get('bns_transition') or act.get('bnss_transition')
            if isinstance(trans, dict):
                replaced_by = str(trans.get('replaced_by', '')).strip()
                if replaced_by.upper().startswith('BNS SECTION'):
                    citations.append({
                        'type': 'bare_act_transition',
                        'act_or_case': 'BNS',
                        'section_or_citation': _canonical_section_label(replaced_by.split()[-1]),
                        '_score': 10,
                    })
                elif replaced_by.upper().startswith('BNSS SECTION'):
                    citations.append({
                        'type': 'bare_act_transition',
                        'act_or_case': 'BNSS',
                        'section_or_citation': _canonical_section_label(replaced_by.split()[-1]),
                        '_score': 10,
                    })

        for case in retrieval_result.get('case_laws', []):
            meta = case.get('metadata', {}) or {}
            case_name = str(meta.get('case_name', '')).strip()
            citation = str(meta.get('citation', '')).strip()
            if case_name and citation:
                citations.append({
                    'type': 'case_law',
                    'act_or_case': case_name,
                    'section_or_citation': citation,
                    '_score': 0,
                })

        citations = sorted(citations, key=lambda c: c.get('_score', 0), reverse=True)

        # Remove duplicates while preserving order.
        deduped: List[Dict[str, str]] = []
        seen = set()
        for c in citations:
            key = (str(c.get('act_or_case', '')).strip().upper(), str(c.get('section_or_citation', '')).strip().upper())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(c)
        citations = deduped

        for c in citations:
            c.pop('_score', None)

        return citations

    def _append_citation_footer(self, answer: str, citations: List[Dict[str, str]]) -> str:
        """Append a compact citation footer so generated text and structured fields stay aligned."""
        if not citations:
            return answer

        lines = []
        for c in citations[:4]:
            lhs = str(c.get('act_or_case', '')).strip()
            rhs = str(c.get('section_or_citation', '')).strip()
            if lhs and rhs:
                lines.append(f"- {lhs} {rhs}")
        if not lines:
            return answer

        footer = "\n\nSources:\n" + "\n".join(lines)
        if "Sources:" in answer:
            return answer
        return answer.rstrip() + footer
    
    
    def answer_legal_question(self, query: str, include_reasoning: bool = True, eval_mode: bool = False) -> Dict[str, Any]:
        """
        Answer a legal question using retrieval + LLM.
        
        This is the main function for legal Q&A. It:
        1. Retrieves relevant context using SmartRetriever
        2. Checks confidence level (triggers uncertainty if LOW)
        3. Formats context for LLM
        4. Generates answer with strict accuracy controls
        5. Returns structured response with citations
        
        Args:
            query: User's legal question
            include_reasoning: Include legal reasoning in response (default: True)
            eval_mode: If True, bypass uncertainty abstention for evaluation-only runs
        
        Returns:
            {
                "answer": str,              # LLM-generated answer
                "confidence": str,          # HIGH/MEDIUM/LOW
                "trigger_uncertainty": bool, # True if should show uncertainty warning
                "sources": {                # Retrieved sources
                    "bare_acts": List[Dict],
                    "case_laws": List[Dict],
                    "amendments": List[Dict]
                },
                "warnings": List[str],      # BNS/BNSS, overruling warnings
                "query_type": str,          # Detected query type
                "stats": Dict               # Retrieval stats
            }
        """
        print(f"\n🔍 Processing query: {query}")
        
        # Step 1: Retrieve context
        retrieval_result = self.retriever.retrieve(query)
        
        # Step 2: Check if uncertainty should be triggered (production default).
        # In eval_mode we intentionally bypass abstention so offline evaluation
        # can inspect generated answers even for low-confidence retrievals.
        if (not eval_mode) and (retrieval_result.get('trigger_uncertainty') or retrieval_result.get('confidence_level') == 'LOW'):
            return {
                "answer": retrieval_result.get('message', 
                    "I cannot provide a reliable answer based on the current database. "
                    "The retrieved information has low confidence. Please consult primary sources or a qualified lawyer."),
                "confidence": "LOW",
                "trigger_uncertainty": True,
                "sources": {
                    "bare_acts": [],
                    "case_laws": [],
                    "amendments": []
                },
                "warnings": ["⚠️ Insufficient reliable information in database"],
                "query_type": retrieval_result.get('query_type', 'unknown'),
                "stats": retrieval_result.get('stats', {})
            }
        
        # Step 3: Format context for LLM
        formatted_context = self._format_retrieval_context(retrieval_result)
        
        # Step 4: Build user prompt
        user_prompt = query
        if include_reasoning:
            user_prompt += "\n\nProvide a detailed answer with legal reasoning and cite all sources."
        
        # Step 5: Call LLM
        llm_answer = self._call_groq_llm(user_prompt, LEGAL_SYSTEM_PROMPT, formatted_context)

        # Build structured citations from retrieval (transition-aware) and align answer footer.
        citations = self._build_structured_citations(retrieval_result, query=query)
        llm_answer = self._append_citation_footer(llm_answer, citations)
        
        # Step 6: Collect warnings
        warnings = []
        if retrieval_result.get('has_bns_bnss_notes'):
            warnings.append("⚠️ This answer references IPC/CrPC sections that have been replaced by BNS/BNSS (2023)")
        
        if retrieval_result.get('stats', {}).get('overruled_cases', 0) > 0:
            warnings.append("⚠️ Some retrieved cases have been overruled - check individual case warnings")
        
        if retrieval_result.get('confidence_level') == 'MEDIUM':
            warnings.append("⚠️ Medium confidence - verify with primary sources")
        
        # Step 7: Return structured response
        return {
            "answer": llm_answer,
            "confidence": retrieval_result.get('confidence_level', 'NONE'),
            "trigger_uncertainty": False,
            "citation": citations[0].get('section_or_citation') if citations else None,
            "citations": citations,
            "sources": {
                "bare_acts": retrieval_result.get('bare_acts', []),
                "case_laws": retrieval_result.get('case_laws', []),
                "amendments": retrieval_result.get('amendments', [])
            },
            "warnings": warnings,
            "query_type": retrieval_result.get('query_type', 'unknown'),
            "stats": retrieval_result.get('stats', {})
        }
    
    
    def explain_section(self, act_name: str, section_number: str) -> Dict[str, Any]:
        """
        Provide detailed explanation of a specific legal section.
        
        Args:
            act_name: Name of the Act (e.g., "Indian Penal Code 1860")
            section_number: Section number (e.g., "420")
        
        Returns:
            Same structure as answer_legal_question()
        """
        query = f"Explain {act_name} Section {section_number} in detail"
        result = self.answer_legal_question(query, include_reasoning=True)
        
        # Add section-specific prompt for better formatting
        if not result['trigger_uncertainty']:
            # Re-call with section explanation prompt
            retrieval_result = self.retriever.retrieve(query)
            formatted_context = self._format_retrieval_context(retrieval_result)
            
            enhanced_prompt = f"{SECTION_EXPLANATION_PROMPT}\n\nSection: {act_name}, Section {section_number}"
            
            llm_answer = self._call_groq_llm(enhanced_prompt, LEGAL_SYSTEM_PROMPT, formatted_context)
            result['answer'] = llm_answer
        
        return result
    
    
    def summarize_judgment(self, citation: str) -> Dict[str, Any]:
        """
        Summarize a legal judgment by citation.
        
        Args:
            citation: Case citation (e.g., "AIR 2020 SC 1234")
        
        Returns:
            Same structure as answer_legal_question()
        """
        query = f"Summarize the judgment {citation}"
        result = self.answer_legal_question(query, include_reasoning=False)
        
        # Use case summary prompt
        if not result['trigger_uncertainty']:
            retrieval_result = self.retriever.retrieve(query)
            formatted_context = self._format_retrieval_context(retrieval_result)
            
            enhanced_prompt = f"{CASE_SUMMARY_PROMPT}\n\nCase Citation: {citation}"
            
            llm_answer = self._call_groq_llm(enhanced_prompt, LEGAL_SYSTEM_PROMPT, formatted_context)
            result['answer'] = llm_answer
        
        return result
    
    
    def compare_sections(self, old_section: str, new_section: str) -> Dict[str, Any]:
        """
        Compare IPC/CrPC section with new BNS/BNSS section.
        
        Args:
            old_section: Old section (e.g., "IPC 420")
            new_section: New section (e.g., "BNS 318")
        
        Returns:
            Comparison analysis
        """
        query = f"Compare {old_section} with {new_section} and explain the differences"
        
        result = self.answer_legal_question(query, include_reasoning=True)
        
        return result
    
    
    def get_legal_opinion(self, facts: str, legal_issue: str) -> Dict[str, Any]:
        """
        Generate legal opinion based on facts and issue.
        
        WARNING: This is for research assistance only, NOT formal legal advice.
        
        Args:
            facts: Brief facts of the case
            legal_issue: Specific legal issue to address
        
        Returns:
            Legal opinion with citations
        """
        query = f"Facts: {facts}\n\nLegal Issue: {legal_issue}\n\nProvide a legal opinion with relevant case law and statutory provisions."
        
        result = self.answer_legal_question(query, include_reasoning=True)
        
        # Add disclaimer
        result['answer'] = (
            "⚠️ DISCLAIMER: This is a research opinion, not formal legal advice.\n\n" + 
            result['answer'] +
            "\n\n⚠️ Always consult a qualified lawyer for formal legal advice."
        )
        
        return result


# ============================================================================
# STANDALONE TESTING
# ============================================================================
if __name__ == "__main__":
    """
    Test LegalLLM with sample queries.
    """
    print("=" * 80)
    print("LEGAL LLM - STANDALONE TEST")
    print("=" * 80)
    
    # Check for GROQ_API_KEY
    if not GROQ_API_KEYS:
        print("\n❌ No GROQ_API_KEY environment variables set")
        print("Set at least one in your shell:")
        print("  export GROQ_API_KEY='your-api-key-here'")
        print("Or for multiple fallback keys:")
        print("  export GROQ_API_KEY_2='your-backup-key-here'")
        exit(1)
    
    print(f"\n✅ Found {len(GROQ_API_KEYS)} Groq API key(s) configured")
    
    try:
        # Initialize LegalLLM
        legal_llm = LegalLLM(persist_directory="./legal_research_db")
        
        # Test queries
        test_queries = [
            "What is Section 420 IPC?",
            "What is the punishment for cheating?",
            "Can mere breach of promise to marry be rape?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'─' * 80}")
            print(f"Query {i}: {query}")
            print('─' * 80)
            
            result = legal_llm.answer_legal_question(query)
            
            print(f"\n📋 Query Type: {result['query_type']}")
            print(f"🎯 Confidence: {result['confidence']}")
            print(f"⚠️  Trigger Uncertainty: {result['trigger_uncertainty']}")
            
            if result['warnings']:
                print(f"\n⚠️  Warnings:")
                for warning in result['warnings']:
                    print(f"  • {warning}")
            
            print(f"\n📊 Stats:")
            stats = result['stats']
            print(f"  • Bare Acts: {stats.get('bare_acts_retrieved', 0)}")
            print(f"  • Case Laws: {stats.get('case_laws_retrieved', 0)}")
            print(f"  • Amendments: {stats.get('amendments_found', 0)}")
            
            print(f"\n💬 Answer:\n{result['answer']}")
        
        print(f"\n{'=' * 80}")
        print("✅ LegalLLM test complete!")
        print('=' * 80)
    
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
