"""
LexAI Baseline Systems
======================
Implements 3 baseline systems for comparison in research evaluation.

Baselines:
1. NoRAG - Direct LLM without retrieval
2. SimpleRAG - Naive RAG without intelligence layers
3. GPT4_SimpleRAG - SimpleRAG with GPT-4 (optional, budget permitting)

Usage:
    from evaluation.baselines import BaselineRunner
    
    runner = BaselineRunner()
    response = runner.run_no_rag("What is Section 420 IPC?")
    response = runner.run_simple_rag("What is Section 420 IPC?")
"""

import os
import sys
import importlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import random

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from groq import Groq
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings

# Set random seed for reproducibility
random.seed(42)

# Load environment variables from backend/.env then workspace root/.env.
def _load_env_files() -> List[str]:
    base_dir = Path(__file__).resolve().parent.parent
    candidate_paths = [
        base_dir / ".env",
        base_dir.parent / ".env",
    ]
    loaded = []
    for env_path in candidate_paths:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            loaded.append(str(env_path))

    if not loaded:
        load_dotenv(override=False)
    return loaded


_LOADED_ENV_FILES = _load_env_files()


def _collect_groq_api_keys() -> List[str]:
    """Collect GROQ_API_KEY plus all GROQ_API_KEY_<n> values in numeric order."""
    keys: List[str] = []

    primary = os.getenv("GROQ_API_KEY", "").strip()
    if primary:
        keys.append(primary)

    numbered = []
    for env_name, env_value in os.environ.items():
        if not env_value:
            continue
        match = re.fullmatch(r"GROQ_API_KEY_(\d+)", env_name)
        if match:
            numbered.append((int(match.group(1)), env_value.strip()))

    numbered.sort(key=lambda item: item[0])
    for _, key in numbered:
        if key and key not in keys:
            keys.append(key)

    return keys


class BaselineRunner:
    """
    Runs baseline systems for LexAI evaluation.
    All baselines return same output format for fair comparison.
    """
    
    def __init__(self, groq_api_key: Optional[str] = None, openai_api_key: Optional[str] = None):
        """
        Initialize baseline systems with API key fallback support.
        
        Args:
            groq_api_key: Groq API key (uses env vars if not provided)
            openai_api_key: OpenAI API key for GPT-4 baseline (optional)
        """
        # Initialize Groq client with fallback API keys
        if groq_api_key:
            self.api_keys = [groq_api_key]
        else:
            self.api_keys = _collect_groq_api_keys()
        
        if not self.api_keys:
            searched = ", ".join(_LOADED_ENV_FILES) if _LOADED_ENV_FILES else "default dotenv discovery"
            raise ValueError(
                "No GROQ API keys found in environment. "
                "Expected GROQ_API_KEY and/or GROQ_API_KEY_<n>. "
                f"Dotenv sources: {searched}"
            )
        
        self.current_key_index = 0
        self.groq_api_key = self.api_keys[self.current_key_index]
        self.groq_client = Groq(api_key=self.groq_api_key)
        self.llm_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        print(f"✅ Initialized with {len(self.api_keys)} Groq API key(s)")
        
        # Initialize OpenAI for GPT-4 baseline (optional)
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_client = None
        if self.openai_api_key:
            try:
                openai_module = importlib.import_module("openai")
                self.openai_client = openai_module.OpenAI(api_key=self.openai_api_key)
            except ImportError:
                print("Warning: openai package not installed. GPT-4 baseline unavailable.")
        
        # Initialize ChromaDB for SimpleRAG
        self._init_chromadb()
        
        # Response logs for analysis
        self.response_logs = []
    
    def _rotate_api_key(self) -> bool:
        """
        Rotate to the next available API key.
        
        Returns:
            True if a new key is available, False if all keys have been tried
        """
        self.current_key_index += 1
        if self.current_key_index >= len(self.api_keys):
            self.current_key_index = 0  # Reset for next round
            return False
        
        self.groq_api_key = self.api_keys[self.current_key_index]
        self.groq_client = Groq(api_key=self.groq_api_key)
        print(f"⚠️  Rotated to API key #{self.current_key_index + 1}")
        return True
    
    def _call_groq_with_retry(self, messages: list, **kwargs) -> Any:
        """
        Call Groq API with automatic retry on API key errors.
        
        Args:
            messages: Chat messages for the API
            **kwargs: Additional arguments for the API call
            
        Returns:
            Completion response
            
        Raises:
            Exception: If all API keys fail
        """
        max_retries = len(self.api_keys)
        
        for attempt in range(max_retries):
            try:
                completion = self.groq_client.chat.completions.create(
                    model=self.llm_model,
                    messages=messages,
                    **kwargs
                )
                return completion
                
            except Exception as e:
                error_msg = str(e).lower()
                # Check if it's a rate limit or authentication error
                if any(keyword in error_msg for keyword in ['rate', 'limit', 'quota', 'expired', 'invalid', 'unauthorized', 'authentication']):
                    print(f"⚠️  API key error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    # Try to rotate to next key
                    if attempt < max_retries - 1 and self._rotate_api_key():
                        print(f"🔄 Retrying with next API key...")
                        continue
                    else:
                        raise Exception(f"All {len(self.api_keys)} API keys failed: {str(e)}")
                else:
                    # Non-key related error, raise immediately
                    raise
        
        raise Exception("Maximum retry attempts reached with all API keys")
    
    def _init_chromadb(self):
        """Initialize ChromaDB client for SimpleRAG baseline."""
        # Keep baseline retrieval on the same DB used by LexAI/evaluation.
        chroma_path = os.environ.get("LEXAI_CHROMA_PATH")
        if not chroma_path:
            chroma_path = str(Path(__file__).parent.parent / "legal_research_db")
        
        self.chroma_client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # For SimpleRAG: merge all collections into one view
        # We'll query all collections and merge results
        self.collection_names = ["bare_acts", "case_law", "amendments", "overruling_map"]
        self.collections = {}
        
        for name in self.collection_names:
            try:
                self.collections[name] = self.chroma_client.get_collection(name=name)
            except Exception as e:
                print(f"Warning: Could not load collection '{name}': {e}")
    
    def _log_response(self, system: str, query: str, response: Dict, elapsed_time: float):
        """Log baseline response for later analysis."""
        self.response_logs.append({
            "system": system,
            "query": query,
            "response": response,
            "elapsed_time": elapsed_time,
            "timestamp": datetime.now().isoformat()
        })

    def _distance_to_confidence(self, distance: float) -> str:
        """Convert ChromaDB distance (0-2) into confidence label."""
        similarity = max(0.0, min(1.0, 1.0 - (float(distance) / 2.0)))
        if similarity >= 0.80:
            return "high"
        if similarity >= 0.65:
            return "medium"
        return "low"

    def _apply_eval_regime(self, response: Dict, eval_mode: bool) -> Dict:
        """
        Apply evaluation regime to baseline response.
        - eval_mode=True: forced-answer, always return answer.
        - eval_mode=False: abstain when confidence is low.
        """
        confidence = str(response.get("confidence", "medium")).lower()
        if (not eval_mode) and confidence == "low":
            response = dict(response)
            response["trigger_uncertainty"] = True
            response["answer"] = (
                "I cannot provide a reliable answer based on available evidence. "
                "Please consult primary sources or a qualified lawyer."
            )
            response["citations"] = []
        else:
            response["trigger_uncertainty"] = False
        return response
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BASELINE 1: NoRAG (Direct LLM without retrieval)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def run_no_rag(self, query: str, eval_mode: bool = True) -> Dict:
        """
        BASELINE 1: NoRAG
        
        Direct LLM call without any retrieval.
        Tests what LLM knows from training data alone.
        
        Args:
            query: Legal research query
            
        Returns:
            Response in standard format
        """
        start_time = datetime.now()
        
        system_prompt = """You are a legal research assistant for Indian law.
Answer questions about Indian legal statutes, cases, and procedures.
Provide citations and section numbers when possible.
Be concise and accurate."""
        
        try:
            # Direct LLM call with no context (with automatic API key retry)
            completion = self._call_groq_with_retry(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.0,  # Fully deterministic
                max_tokens=1024,
                top_p=1,
                stream=False
            )
            
            answer = completion.choices[0].message.content
            
            # Parse response for citations (very basic)
            # NoRAG has no structured citation extraction
            citations = self._extract_citations_from_text(answer)
            
            if len(citations) >= 2:
                confidence = "high"
            elif len(citations) == 1:
                confidence = "medium"
            else:
                confidence = "low"

            response = {
                "answer": answer,
                "citations": citations,
                "confidence": confidence,
                "bns_bnss_notes": [],  # NoRAG doesn't have structured notes
                "amendment_notes": [],
                "disclaimer": "Response generated from LLM training data without retrieval. May not reflect recent law changes.",
                "system": "NoRAG",
                "retrieval_used": False
            }
            
        except Exception as e:
            response = {
                "answer": f"Error: {str(e)}",
                "citations": [],
                "confidence": "low",
                "bns_bnss_notes": [],
                "amendment_notes": [],
                "disclaimer": "Error occurred during processing",
                "system": "NoRAG",
                "retrieval_used": False,
                "error": str(e)
            }
        
        response = self._apply_eval_regime(response, eval_mode)

        elapsed = (datetime.now() - start_time).total_seconds()
        self._log_response("NoRAG", query, response, elapsed)
        
        return response
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BASELINE 2: SimpleRAG (Naive RAG without intelligence)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def run_simple_rag(self, query: str, top_k: int = 3, eval_mode: bool = True) -> Dict:
        """
        BASELINE 2: SimpleRAG
        
        Naive RAG implementation:
        - Queries all ChromaDB collections
        - Takes top K results
        - No confidence thresholding
        - No overruling check
        - No amendment awareness
        - No BNS/BNSS mapping
        
        Args:
            query: Legal research query
            top_k: Number of results to retrieve (default: 3)
            
        Returns:
            Response in standard format
        """
        start_time = datetime.now()
        
        try:
            # Query all collections and merge results
            all_results = []
            
            for collection_name, collection in self.collections.items():
                try:
                    results = collection.query(
                        query_texts=[query],
                        n_results=top_k
                    )
                    
                    if results and results['documents']:
                        for i, doc in enumerate(results['documents'][0]):
                            all_results.append({
                                "text": doc,
                                "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                                "distance": results['distances'][0][i] if results['distances'] else 1.0,
                                "collection": collection_name
                            })
                
                except Exception as e:
                    print(f"Warning: Error querying {collection_name}: {e}")
                    continue
            
            # Sort by distance and take top K
            all_results.sort(key=lambda x: x['distance'])
            top_results = all_results[:top_k]
            
            # Build context from retrieved chunks
            context = "\n\n".join([
                f"Source {i+1} ({r['collection']}):\n{r['text']}"
                for i, r in enumerate(top_results)
            ])
            
            # Simple system prompt (no intelligence layers)
            system_prompt = """You are a legal research assistant for Indian law.
Use the provided context to answer the question accurately.
Cite relevant sections and cases from the context."""
            
            user_message = f"""Context:
{context}

Question: {query}

Provide a clear answer based on the context above."""
            
            # LLM call with retrieved context (with automatic API key retry)
            completion = self._call_groq_with_retry(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0,  # Fully deterministic
                max_tokens=1024,
                top_p=1,
                stream=False
            )
            
            answer = completion.choices[0].message.content
            
            # Extract citations (basic extraction)
            citations = self._extract_citations_from_text(answer)
            
            # Add citations from metadata
            for result in top_results:
                meta = result.get('metadata', {})
                if 'section' in meta:
                    citations.append(f"{meta.get('act', 'Unknown Act')} Section {meta['section']}")
                if 'citation' in meta:
                    citations.append(meta['citation'])
            
            # Remove duplicates
            citations = list(set(citations))
            
            if top_results:
                avg_distance = sum(float(r.get("distance", 2.0)) for r in top_results) / len(top_results)
                confidence = self._distance_to_confidence(avg_distance)
            else:
                confidence = "low"

            response = {
                "answer": answer,
                "citations": citations,
                "confidence": confidence,
                "bns_bnss_notes": [],  # SimpleRAG doesn't check transitions
                "amendment_notes": [],  # SimpleRAG doesn't check amendments
                "disclaimer": "Response based on retrieved context. Does not check for overruled cases or recent amendments.",
                "system": "SimpleRAG",
                "retrieval_used": True,
                "num_chunks_retrieved": len(top_results),
                "retrieved_chunks": [r['text'][:200] + "..." for r in top_results]  # First 200 chars
            }
            
        except Exception as e:
            response = {
                "answer": f"Error: {str(e)}",
                "citations": [],
                "confidence": "low",
                "bns_bnss_notes": [],
                "amendment_notes": [],
                "disclaimer": "Error occurred during processing",
                "system": "SimpleRAG",
                "retrieval_used": False,
                "error": str(e)
            }
        
        response = self._apply_eval_regime(response, eval_mode)

        elapsed = (datetime.now() - start_time).total_seconds()
        self._log_response("SimpleRAG", query, response, elapsed)
        
        return response
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BASELINE 3: GPT4_SimpleRAG (Optional, if budget allows)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def run_gpt4_simple_rag(self, query: str, top_k: int = 3, eval_mode: bool = True) -> Dict:
        """
        BASELINE 3: GPT4_SimpleRAG (Optional)
        
        Same as SimpleRAG but using GPT-4 as LLM.
        Tests whether model choice matters vs architecture.
        
        Run only on 50-query subset due to cost.
        
        Args:
            query: Legal research query
            top_k: Number of results to retrieve
            
        Returns:
            Response in standard format
        """
        if not self.openai_client:
            return {
                "answer": "GPT-4 baseline not available (API key not configured)",
                "citations": [],
                "confidence": "low",
                "bns_bnss_notes": [],
                "amendment_notes": [],
                "disclaimer": "GPT-4 baseline requires OpenAI API key",
                "system": "GPT4_SimpleRAG",
                "retrieval_used": False,
                "error": "OpenAI client not initialized"
            }
        
        start_time = datetime.now()
        
        try:
            # Same retrieval as SimpleRAG
            all_results = []
            
            for collection_name, collection in self.collections.items():
                try:
                    results = collection.query(
                        query_texts=[query],
                        n_results=top_k
                    )
                    
                    if results and results['documents']:
                        for i, doc in enumerate(results['documents'][0]):
                            all_results.append({
                                "text": doc,
                                "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                                "distance": results['distances'][0][i] if results['distances'] else 1.0,
                                "collection": collection_name
                            })
                
                except Exception as e:
                    continue
            
            all_results.sort(key=lambda x: x['distance'])
            top_results = all_results[:top_k]
            
            context = "\n\n".join([
                f"Source {i+1} ({r['collection']}):\n{r['text']}"
                for i, r in enumerate(top_results)
            ])
            
            system_prompt = """You are a legal research assistant for Indian law.
Use the provided context to answer the question accurately.
Cite relevant sections and cases from the context."""
            
            user_message = f"""Context:
{context}

Question: {query}

Provide a clear answer based on the context above."""
            
            # GPT-4 call
            completion = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",  # or "gpt-4" depending on access
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0,  # Fully deterministic
                max_tokens=1024,
            )
            
            answer = completion.choices[0].message.content
            
            citations = self._extract_citations_from_text(answer)
            
            for result in top_results:
                meta = result.get('metadata', {})
                if 'section' in meta:
                    citations.append(f"{meta.get('act', 'Unknown Act')} Section {meta['section']}")
                if 'citation' in meta:
                    citations.append(meta['citation'])
            
            citations = list(set(citations))
            
            if top_results:
                avg_distance = sum(float(r.get("distance", 2.0)) for r in top_results) / len(top_results)
                confidence = self._distance_to_confidence(avg_distance)
            else:
                confidence = "low"

            response = {
                "answer": answer,
                "citations": citations,
                "confidence": confidence,
                "bns_bnss_notes": [],
                "amendment_notes": [],
                "disclaimer": "Response from GPT-4 with simple RAG. Does not check for overruled cases or amendments.",
                "system": "GPT4_SimpleRAG",
                "retrieval_used": True,
                "num_chunks_retrieved": len(top_results),
                "model": "gpt-4-turbo-preview"
            }
            
        except Exception as e:
            response = {
                "answer": f"Error: {str(e)}",
                "citations": [],
                "confidence": "low",
                "bns_bnss_notes": [],
                "amendment_notes": [],
                "disclaimer": "Error occurred during GPT-4 processing",
                "system": "GPT4_SimpleRAG",
                "retrieval_used": False,
                "error": str(e)
            }
        
        response = self._apply_eval_regime(response, eval_mode)

        elapsed = (datetime.now() - start_time).total_seconds()
        self._log_response("GPT4_SimpleRAG", query, response, elapsed)
        
        return response
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # UTILITY METHODS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _extract_citations_from_text(self, text: str) -> List[str]:
        """
        Extract legal citations from text using basic patterns.
        
        Looks for:
        - Section numbers (e.g., "Section 420", "Sec 302")
        - Case citations (e.g., "AIR 1978 SC 597")
        - Act names
        
        Args:
            text: Text to extract citations from
            
        Returns:
            List of extracted citations
        """
        import re
        
        citations = []
        
        # Section patterns
        section_pattern = r'(?:Section|Sec\.?|§)\s*(\d+[A-Z]?(?:\(\d+\))?)\s+(?:of\s+)?([A-Z][A-Za-z\s]+(?:Act|Code))'
        sections = re.findall(section_pattern, text, re.IGNORECASE)
        for section, act in sections:
            citations.append(f"{act.strip()} Section {section}")
        
        # Case citation patterns (AIR, SCC, etc.)
        case_pattern = r'(?:AIR|SCC|SCR|Cri\.?\s*L\.?\s*J\.?)\s+\d{4}\s+(?:SC|HC|[A-Z]{2,})\s+\d+'
        cases = re.findall(case_pattern, text, re.IGNORECASE)
        citations.extend(cases)
        
        # Act names mentioned
        act_pattern = r'(?:IPC|BNS|CrPC|BNSS|Companies Act|Evidence Act|Contract Act|Arbitration Act)'
        acts = re.findall(act_pattern, text, re.IGNORECASE)
        
        return list(set(citations))  # Remove duplicates
    
    def save_logs(self, filepath: str):
        """
        Save all response logs to JSON file.
        
        Args:
            filepath: Path to save logs
        """
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.response_logs, f, indent=2)
        
        print(f"Saved {len(self.response_logs)} response logs to {filepath}")
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about baseline runs.
        
        Returns:
            Dictionary with statistics per baseline system
        """
        stats = {}
        
        for system in ["NoRAG", "SimpleRAG", "GPT4_SimpleRAG"]:
            system_logs = [log for log in self.response_logs if log['system'] == system]
            
            if system_logs:
                stats[system] = {
                    "num_queries": len(system_logs),
                    "avg_response_time": sum(log['elapsed_time'] for log in system_logs) / len(system_logs),
                    "errors": len([log for log in system_logs if 'error' in log['response']]),
                    "avg_citations": sum(len(log['response']['citations']) for log in system_logs) / len(system_logs)
                }
        
        return stats


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTING / DEMO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def demo_baselines():
    """Demo function to test all three baselines."""
    print("=" * 60)
    print("LexAI Baseline Systems Demo")
    print("=" * 60)
    
    runner = BaselineRunner()
    
    test_queries = [
        "What is Section 420 IPC?",
        "What is the punishment for murder under IPC?",
        "Has Section 377 IPC been struck down?",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {query}")
        print('='*60)
        
        # Test NoRAG
        print("\n[BASELINE 1: NoRAG]")
        response = runner.run_no_rag(query)
        print(f"Answer: {response['answer'][:200]}...")
        print(f"Citations: {response['citations']}")
        
        # Test SimpleRAG
        print("\n[BASELINE 2: SimpleRAG]")
        response = runner.run_simple_rag(query)
        print(f"Answer: {response['answer'][:200]}...")
        print(f"Citations: {response['citations']}")
        print(f"Retrieved: {response.get('num_chunks_retrieved', 0)} chunks")
        
        # Test GPT4 (if available)
        if runner.openai_client:
            print("\n[BASELINE 3: GPT4_SimpleRAG]")
            response = runner.run_gpt4_simple_rag(query)
            print(f"Answer: {response['answer'][:200]}...")
            print(f"Citations: {response['citations']}")
    
    # Print statistics
    print("\n" + "="*60)
    print("Baseline Statistics")
    print("="*60)
    stats = runner.get_statistics()
    for system, system_stats in stats.items():
        print(f"\n{system}:")
        for key, value in system_stats.items():
            print(f"  {key}: {value}")
    
    # Save logs
    runner.save_logs("evaluation/logs/baseline_demo_logs.json")
    print(f"\n✓ Logs saved to evaluation/logs/baseline_demo_logs.json")


if __name__ == "__main__":
    demo_baselines()
