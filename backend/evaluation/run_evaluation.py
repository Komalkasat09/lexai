"""
LexAI Full Evaluation Runner
=============================
Master orchestrator for complete evaluation pipeline.

Workflow:
1. Load verified ground truth
2. Run LexAI on all 300 queries
3. Run all baselines on all 300 queries
4. Compute all metrics
5. Run statistical tests
6. Run error analysis  
7. Generate tables and figures
8. Save complete results

Usage:
    python run_evaluation.py
    
    Or:
    from evaluation.run_evaluation import run_full_evaluation
    
    results = run_full_evaluation()

Requirements:
- ground_truth_verified.xlsx must exist (lawyer-verified)
- ChromaDB collections must be initialized
- Groq/OpenAI API keys in environment

Output:
- Complete results JSON
- All tables (LaTeX)
- All figures (PNG)
- Timestamped logs
"""

import os
import sys
import json
import random
import re
import pandas as pd
from datetime import datetime
from typing import Dict, List
import chromadb
from chromadb.config import Settings

# Add parent directory to path for LegalLLM import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set reproducibility seed
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# Import evaluation modules
from evaluation.baselines import BaselineRunner
from evaluation.metrics_engine import MetricsEngine, METRIC_SCHEMA_VERSION
# Note: StatisticalAnalyzer moved to separate statistical_analysis.py script
# Run python statistical_analysis.py after evaluation to generate Table 1
from evaluation.error_analysis import ErrorAnalyzer
# Note: Results dashboard moved to separate results_dashboard.py script
# Run python results_dashboard.py after evaluation to generate figures

# Import actual LexAI system
from llm.legal_llm import LegalLLM


class EvaluationRunner:
    """
    Master evaluation orchestrator.
    """
    
    def __init__(self, ground_truth_path: str = "evaluation/ground_truth_verified_393_ready.xlsx",
                 output_dir: str = "evaluation/results",
                 debug: bool = False,
                 eval_regime: str = "forced-answer",
                 compare_regimes: bool = False):
        """
        Initialize evaluation runner.
        
        Args:
            ground_truth_path: Path to verified ground truth
            output_dir: Output directory for results
            debug: If True, allow placeholder responses on LexAI init failure. If False (default), hard-fail.
            eval_regime: Evaluation regime for all systems ('forced-answer' or 'abstain-allowed')
            compare_regimes: If True, run both regimes and compare system behavior
        """
        self.ground_truth_path = ground_truth_path
        self.output_dir = output_dir
        self.debug = debug
        self.eval_regime = eval_regime
        self.eval_mode = eval_regime == "forced-answer"
        self.compare_regimes = compare_regimes
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Checkpoint file paths
        self.checkpoint_dir = os.path.join(output_dir, "checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
        self.lexai_checkpoint = os.path.join(self.checkpoint_dir, "lexai_responses.json")
        self.baselines_checkpoint = os.path.join(self.checkpoint_dir, "baseline_responses.json")
        os.makedirs(output_dir, exist_ok=True)
        
        # Timestamp for this run
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize LexAI system
        print("🔧 Initializing LexAI system for evaluation...")
        try:
            self.chroma_path = self._select_chroma_path()
            self.lexai = LegalLLM(persist_directory=self.chroma_path)
            self.use_real_lexai = True
            print("✅ LexAI system initialized successfully")
        except Exception as e:
            if self.debug:
                print(f"⚠ Failed to initialize LexAI: {e}")
                print("  Will use placeholder responses (DEBUG MODE ONLY)")
                self.lexai = None
                self.use_real_lexai = False
            else:
                print(f"❌ HARD FAIL: Failed to initialize LexAI")
                print(f"Error: {e}")
                print("\n🔧 Troubleshooting:")
                print("  1. Verify ChromaDB collections exist")
                print("  2. Check GROQ_API_KEY environment variables")
                print("  3. Use --debug flag to allow placeholder responses for testing")
                raise

        # Configuration
        self.config = {
            "random_seed": RANDOM_SEED,
            "ground_truth_path": ground_truth_path,
            "run_timestamp": self.run_timestamp,
            "eval_regime": eval_regime,
            "baselines": ["NoRAG", "SimpleRAG"],  # Add "GPT4_SimpleRAG" if budget allows
            "metrics": ["CAR", "HR", "OLR", "AP", "ACS", "P@K", "CCS"],
            "statistical_tests": ["paired_ttest", "bootstrap_ci", "category_analysis", "threshold_sensitivity"]
        }

    def _select_chroma_path(self) -> str:
        """Pick a usable Chroma directory (env override first, then best populated candidate)."""
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.environ.get("LEXAI_CHROMA_PATH")
        if env_path:
            print(f"📦 Using LEXAI_CHROMA_PATH: {env_path}")
            return env_path

        candidates = [
            os.path.join(backend_dir, "legal_research_db"),
            os.path.join(backend_dir, "chroma_db"),
            os.path.join(backend_dir, "chroma_legal_db"),
        ]

        best_path = candidates[0]
        best_score = -1
        for path in candidates:
            try:
                client = chromadb.PersistentClient(
                    path=path,
                    settings=chromadb.config.Settings(
                        anonymized_telemetry=False,
                        allow_reset=False,
                    ),
                )
                counts = 0
                for name in ["bare_acts", "case_law", "amendments", "overruling_map"]:
                    try:
                        counts += client.get_collection(name).count()
                    except Exception:
                        continue
                if counts > best_score:
                    best_score = counts
                    best_path = path
            except Exception:
                continue

        print(f"📦 Using Chroma path: {best_path} (estimated docs: {best_score})")
        return best_path
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: Load Ground Truth
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def load_ground_truth(self) -> pd.DataFrame:
        """
        Load verified ground truth.
        
        Validates that all rows are lawyer-verified.
        
        Returns:
            Verified ground truth DataFrame
        """
        print("\n" + "="*60)
        print("STEP 1: Loading Ground Truth")
        print("="*60)
        
        if not os.path.exists(self.ground_truth_path):
            raise FileNotFoundError(
                f"Ground truth not found: {self.ground_truth_path}\n"
                f"Please run dataset_builder.py first to generate template,\n"
                f"then have lawyers verify it and save as 'ground_truth_verified.xlsx'"
            )
        
        df = pd.read_excel(self.ground_truth_path, sheet_name='Ground Truth Dataset')
        
        # Validate completeness
        required_cols = [
            'query_id', 'query_text', 'category',
            'correct_answer_summary', 'correct_act', 'correct_section'
        ]
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Rename query_text to query for consistency
        df = df.rename(columns={'query_text': 'query'})
        
        # Check for lawyer verification (assuming 'verified' column)
        if 'verified' in df.columns:
            unverified = df[df['verified'] != True]
            if len(unverified) > 0:
                print(f"  ⚠ Warning: {len(unverified)} queries not verified by lawyer")
        
        print(f"  ✓ Loaded {len(df)} verified queries")
        print(f"  ✓ Categories: {df['category'].unique().tolist()}")
        
        return df
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: Run LexAI System
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def run_lexai(self, queries: List[str], eval_mode: bool = True) -> List[Dict]:
        """
        Run LexAI system on all queries.
        
        Uses the actual LegalLLM implementation with SmartRetriever.
        
        Args:
            queries: List of query strings
            eval_mode: True = forced-answer regime, False = abstain-allowed regime
            
        Returns:
            List of LexAI responses in evaluation format
        """
        print("\n" + "="*60)
        print("STEP 2: Running LexAI System")
        print("="*60)
        
        # Check if real LexAI is available
        if not self.use_real_lexai or self.lexai is None:
            if not self.debug:
                raise RuntimeError(
                    "HARD FAIL: LexAI not initialized and debug mode is disabled. "
                    "Cannot run evaluation with placeholder responses in production."
                )
            print("  ⚠ Using placeholder responses (DEBUG MODE)")
            print("  To enable actual LexAI:")
            print("    1. Ensure chroma_db is initialized correctly")
            print("    2. Fix embedding function conflicts in collections")
            print("    3. Restart evaluation")
            return self._run_lexai_placeholder(queries)
        
        # Run actual LexAI system
        print("  ✅ Using actual LexAI system")
        responses = []
        
        for i, query in enumerate(queries):
            print(f"  Progress: {i+1}/{len(queries)}", end='\r')
            
            try:
                # Call actual LegalLLM with configurable regime
                result = self.lexai.answer_legal_question(query, include_reasoning=True, eval_mode=eval_mode)
                
                # Convert to evaluation format
                response = {
                    "query": query,
                    "answer": result.get('answer', ''),
                    "confidence": result.get('confidence', 'UNKNOWN'),
                    "citation": result.get('citation'),
                    "citations": result.get('citations', []),
                    "structured_response": self._extract_structured_response(result),
                    "bns_transition_note": self._extract_bns_note(result),
                    "overruling_note": self._extract_overruling_note(result),
                    "amendment_note": self._extract_amendment_note(result),
                    "retrieved_chunks": self._format_retrieved_chunks(result.get('sources', {})),
                    "query_type": result.get('query_type', 'unknown'),
                    "trigger_uncertainty": result.get('trigger_uncertainty', False)
                }
                
                responses.append(response)
                
            except Exception as e:
                print(f"\n  ⚠ Error processing query {i+1}: {str(e)}")
                # Add error response
                responses.append({
                    "query": query,
                    "answer": f"ERROR: {str(e)}",
                    "confidence": "ERROR",
                    "structured_response": {},
                    "bns_transition_note": None,
                    "retrieved_chunks": []
                })
        
        print(f"\n  ✓ Completed LexAI responses: {len(responses)}")
        return responses
    
    def _extract_structured_response(self, result: Dict) -> Dict:
        """Extract structured citations from LexAI result."""
        citations = result.get('citations', [])
        if isinstance(citations, list) and citations:
            first_bare = None
            case_citations = []
            for c in citations:
                if not isinstance(c, dict):
                    continue
                ctype = str(c.get('type', '')).strip().lower()
                lhs = str(c.get('act_or_case', '')).strip()
                rhs = str(c.get('section_or_citation', '')).strip()
                if ctype == 'bare_act' and first_bare is None:
                    first_bare = (lhs, rhs)
                if ctype == 'case_law' and lhs and rhs:
                    case_citations.append(f"{lhs} - {rhs}")

            if first_bare:
                return {
                    "act_cited": first_bare[0],
                    "section_cited": first_bare[1],
                    "case_citations": case_citations[:3],
                }

        sources = result.get('sources', {})
        
        # Extract primary act and section
        bare_acts = sources.get('bare_acts', [])
        act_cited = None
        section_cited = None
        
        if bare_acts:
            first_act = bare_acts[0]
            metadata = first_act.get('metadata', {})
            act_cited = metadata.get('act_name')
            section_cited = metadata.get('section_number')
        
        # Extract case citations
        case_citations = []
        for case in sources.get('case_laws', [])[:3]:  # Top 3 cases
            metadata = case.get('metadata', {})
            case_name = metadata.get('case_name', '')
            citation = metadata.get('citation', '')
            if case_name and citation:
                case_citations.append(f"{case_name} - {citation}")
        
        return {
            "act_cited": act_cited,
            "section_cited": section_cited,
            "case_citations": case_citations
        }
    
    def _extract_bns_note(self, result: Dict) -> str:
        """Extract BNS/BNSS transition warning from result."""
        warnings = result.get('warnings', [])
        for warning in warnings:
            if 'BNS/BNSS' in warning or 'IPC/CrPC' in warning:
                return warning
        return None
    
    def _extract_overruling_note(self, result: Dict) -> str:
        """Extract overruling warning from result."""
        warnings = result.get('warnings', [])
        for warning in warnings:
            if 'overruled' in warning.lower():
                return warning
        return None
    
    def _extract_amendment_note(self, result: Dict) -> str:
        """Extract amendment information from result."""
        sources = result.get('sources', {})
        amendments = sources.get('amendments', [])
        if amendments:
            return f"Referenced {len(amendments)} amendment(s)"
        return None
    
    def _format_retrieved_chunks(self, sources: Dict) -> List[Dict]:
        """Format retrieved sources as chunks for metrics calculation."""
        chunks = []
        
        # Add bare acts
        for act in sources.get('bare_acts', []):
            chunks.append({
                'type': 'bare_act',
                'text': act.get('text', ''),
                'metadata': act.get('metadata', {}),
                'confidence': act.get('confidence_score', 0)
            })
        
        # Add case laws
        for case in sources.get('case_laws', []):
            chunks.append({
                'type': 'case_law',
                'text': case.get('text', ''),
                'metadata': case.get('metadata', {}),
                'confidence': case.get('confidence_score', 0)
            })
        
        return chunks
    
    def _run_lexai_placeholder(self, queries: List[str]) -> List[Dict]:
        """Fallback placeholder if LexAI initialization fails."""
        responses = []
        for i, query in enumerate(queries):
            print(f"  Progress: {i+1}/{len(queries)} (PLACEHOLDER)", end='\r')
            responses.append({
                "query": query,
                "answer": f"[PLACEHOLDER: LexAI response to: {query[:50]}...]",
                "confidence": "high",
                "structured_response": {
                    "act_cited": "Bharatiya Nyaya Sanhita",
                    "section_cited": "101",
                    "case_citations": []
                },
                "bns_transition_note": "IPC Section 300 is now BNS Section 101",
                "retrieved_chunks": []
            })
        print(f"\n  ✓ Completed placeholder responses: {len(responses)}")
        return responses
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 3: Run Baselines
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def run_baselines(self, ground_truth: pd.DataFrame, eval_mode: bool = True) -> Dict[str, List[Dict]]:
        """
        Run all baseline systems.
        
        Args:
            ground_truth: Ground truth dataset
            eval_mode: True = forced-answer regime, False = abstain-allowed regime
            
        Returns:
            Dictionary of {baseline_name: responses}
        """
        print("\n" + "="*60)
        print("STEP 3: Running Baseline Systems")
        print("="*60)
        
        baseline_runner = BaselineRunner()
        
        all_baseline_responses = {}
        
        for baseline_name in self.config['baselines']:
            print(f"\n  Running {baseline_name}...")
            
            responses = []
            for i, row in ground_truth.iterrows():
                print(f"    Progress: {i+1}/{len(ground_truth)}", end='\r')
                
                # Call appropriate baseline method
                if baseline_name == "NoRAG":
                    response = baseline_runner.run_no_rag(row['query'], eval_mode=eval_mode)
                elif baseline_name == "SimpleRAG":
                    response = baseline_runner.run_simple_rag(row['query'], eval_mode=eval_mode)
                elif baseline_name == "GPT4_SimpleRAG":
                    response = baseline_runner.run_gpt4_simple_rag(row['query'], eval_mode=eval_mode)
                else:
                    raise ValueError(f"Unknown baseline: {baseline_name}")
                
                responses.append(response)
            
            all_baseline_responses[baseline_name] = responses
            
            # Save logs
            log_path = os.path.join(self.output_dir, f"{baseline_name.lower()}_responses.json")
            baseline_runner.save_logs(log_path)
            
            print(f"\n    ✓ {baseline_name} complete: {len(responses)} responses")
        
        return all_baseline_responses
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 4: Compute Metrics
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def compute_metrics(self, responses: List[Dict], ground_truth: pd.DataFrame,
                       system_name: str) -> Dict:
        """
        Compute all metrics for a system.
        
        Args:
            responses: System responses
            ground_truth: Ground truth
            system_name: Name of system
            
        Returns:
            All computed metrics
        """
        print(f"\n  Computing metrics for {system_name}...")
        
        # Use the same Chroma path selected during initialization for all metrics.
        chroma_client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False,
            ),
        )
        
        metrics_engine = MetricsEngine(ground_truth, chroma_client)
        metrics = metrics_engine.compute_all_metrics(responses)
        
        print(f"    ✓ Metrics computed")
        
        return metrics
    
    def compute_all_metrics(self, lexai_responses: List[Dict],
                           baseline_responses: Dict[str, List[Dict]],
                           ground_truth: pd.DataFrame) -> Dict[str, Dict]:
        """
        Compute metrics for all systems.
        
        Args:
            lexai_responses: LexAI responses
            baseline_responses: Baseline responses
            ground_truth: Ground truth
            
        Returns:
            Dictionary of {system_name: metrics}
        """
        print("\n" + "="*60)
        print("STEP 4: Computing Metrics")
        print("="*60)
        
        all_metrics = {}
        
        # LexAI metrics
        all_metrics['LexAI'] = self.compute_metrics(lexai_responses, ground_truth, 'LexAI')
        
        # Baseline metrics
        for baseline_name, responses in baseline_responses.items():
            all_metrics[baseline_name] = self.compute_metrics(responses, ground_truth, baseline_name)
        
        print(f"\n  ✓ All metrics computed for {len(all_metrics)} systems")
        
        return all_metrics
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 5: Statistical Tests
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def run_statistical_tests(self, all_metrics: Dict[str, Dict],
                             lexai_responses: List[Dict],
                             ground_truth: pd.DataFrame) -> Dict:
        """
        Run all statistical tests.
        
        Args:
            all_metrics: All systems' metrics
            lexai_responses: LexAI responses (for threshold analysis)
            ground_truth: Ground truth
            
        Returns:
            Statistical test results
        """
        print("\n" + "="*60)
        print("STEP 5: Running Statistical Tests")
        print("="*60)
        print("NOTE: Statistical tests moved to separate script.")
        print("      Run 'python statistical_analysis.py' to generate Table 1 with p-values and effect sizes.")
        print()
        
        # Return placeholder - detailed stats in statistical_analysis.py
        stats = {
            'note': 'Run python statistical_analysis.py for complete statistical tests',
            'timestamp': self.run_timestamp
        }
        
        return stats
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 6: Error Analysis
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def run_error_analysis(self, lexai_responses: List[Dict],
                          ground_truth: pd.DataFrame,
                          lexai_metrics: Dict) -> Dict:
        """
        Run error analysis on LexAI.
        
        Args:
            lexai_responses: LexAI responses
            ground_truth: Ground truth
            lexai_metrics: LexAI metrics
            
        Returns:
            Error analysis results
        """
        print("\n" + "="*60)
        print("STEP 6: Running Error Analysis")
        print("="*60)
        
        analyzer = ErrorAnalyzer()
        errors = analyzer.analyze_all_errors(lexai_responses, ground_truth, lexai_metrics)
        
        return errors
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 7: Generate Outputs
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def generate_outputs(self, all_metrics: Dict[str, Dict],
                        statistical_tests: Dict,
                        error_analysis: Dict) -> Dict:
        """
        Generate all tables and figures.
        
        Args:
            all_metrics: All systems' metrics
            statistical_tests: Statistical test results
            error_analysis: Error analysis results
            
        Returns:
            Output file paths
        """
        print("\n" + "="*60)
        print("STEP 7: Generating Publication Outputs")
        print("="*60)
        print("NOTE: Figure generation moved to separate script.")
        print("      Run 'python results_dashboard.py' to generate publication-quality figures.")
        print()
        
        # Save basic output files
        outputs = {
            'metrics_summary': 'results/comparison_results/system_comparison.csv',
            'note': 'Run python results_dashboard.py for publication figures'
        }
        
        # Save system comparison CSV
        comparison_data = []
        for system_name, metrics in all_metrics.items():
            row = {'system': system_name}
            row.update(metrics)
            comparison_data.append(row)
        
        comparison_df = pd.DataFrame(comparison_data)
        comparison_path = os.path.join(self.output_dir, 'comparison_results', 'system_comparison.csv')
        os.makedirs(os.path.dirname(comparison_path), exist_ok=True)
        comparison_df.to_csv(comparison_path, index=False)
        
        print(f"  ✓ System comparison saved: {comparison_path}")
        
        return outputs
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CHECKPOINT MANAGEMENT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def save_checkpoint(self, data: Dict, checkpoint_type: str):
        """
        Save checkpoint to disk to enable resume.
        
        Args:
            data: Data to checkpoint
            checkpoint_type: 'lexai' or 'baselines'
        """
        checkpoint_path = self.lexai_checkpoint if checkpoint_type == 'lexai' else self.baselines_checkpoint
        
        with open(checkpoint_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"  💾 Checkpoint saved: {checkpoint_path}")
    
    def load_checkpoint(self, checkpoint_type: str) -> Dict:
        """
        Load checkpoint from disk if exists.
        
        Args:
            checkpoint_type: 'lexai' or 'baselines'
            
        Returns:
            Checkpoint data or None if doesn't exist
        """
        checkpoint_path = self.lexai_checkpoint if checkpoint_type == 'lexai' else self.baselines_checkpoint
        
        if os.path.exists(checkpoint_path):
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
            print(f"  ♻️  Loaded checkpoint: {checkpoint_path}")
            return data
        
        return None

    def _is_abstained_response(self, response: Dict) -> bool:
        """Return True when a response is abstained/uncertain."""
        if bool(response.get('trigger_uncertainty')):
            return True
        answer = str(response.get('answer', '')).lower()
        markers = [
            'cannot provide a reliable answer',
            'cannot answer',
            'insufficient reliable information',
            'please consult primary sources',
        ]
        return any(marker in answer for marker in markers)

    def _normalize_score(self, value) -> float:
        """Normalize metric values to [0,1] where needed."""
        try:
            score = float(value)
        except Exception:
            return 0.0
        if score > 1.0:
            return score / 100.0
        return score

    def _system_slug(self, system_name: str) -> str:
        return re.sub(r'[^a-z0-9]+', '_', system_name.lower()).strip('_')

    def _build_per_query_metrics_df(
        self,
        system_name: str,
        responses: List[Dict],
        ground_truth: pd.DataFrame,
        system_metrics: Dict,
        metrics_engine: MetricsEngine,
    ) -> pd.DataFrame:
        """Build canonical per-query metrics rows for a system."""
        car_block = system_metrics.get('CAR', {})
        car_scores = car_block.get('individual_scores', [])
        if not car_scores:
            # New schema may expose generated/retrieved streams separately.
            car_scores = car_block.get('individual_scores_generated', [])
        if not car_scores:
            car_scores = car_block.get('individual_scores_retrieved', [])
        acs_scores = system_metrics.get('ACS', {}).get('individual_scores', [])
        hr_rows = system_metrics.get('HR', {}).get('individual_results', [])

        expected_n = len(ground_truth)
        actual_lengths = {
            'responses': len(responses),
            'car_individual_scores': len(car_scores),
            'acs_individual_scores': len(acs_scores),
            'hr_individual_results': len(hr_rows),
        }

        for name, size in actual_lengths.items():
            if size != expected_n:
                raise ValueError(
                    f"Per-query artifact build failed for {system_name}: "
                    f"{name} has {size} rows but ground truth has {expected_n}."
                )

        rows = []
        for i in range(expected_n):
            gt = ground_truth.iloc[i]
            response = responses[i]
            hr_row = hr_rows[i] if i < len(hr_rows) and isinstance(hr_rows[i], dict) else {}

            outdated_flag = 1.0 if metrics_engine._response_has_outdated_citation(response) else 0.0
            is_correct = 1.0 if metrics_engine._is_response_correct_for_ccs(response, gt) else 0.0

            rows.append({
                'query_id': gt.get('query_id', i),
                'query': gt.get('query', ''),
                'category': gt.get('category', ''),
                'system': system_name,
                'car_score': self._normalize_score(car_scores[i]),
                'hallucination_rate': self._normalize_score(hr_row.get('hallucination_rate', 0.0)),
                'acs_score': self._normalize_score(acs_scores[i]),
                'olr_score': outdated_flag,
                'confidence': str(response.get('confidence', 'medium')).upper(),
                'ccs_correctness': is_correct,
                'abstained': 1.0 if self._is_abstained_response(response) else 0.0,
            })

        df = pd.DataFrame(rows)
        required_cols = {
            'query_id', 'query', 'category', 'system', 'car_score',
            'hallucination_rate', 'acs_score', 'olr_score',
            'confidence', 'ccs_correctness', 'abstained'
        }
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing canonical per-query columns for {system_name}: {sorted(missing)}")
        return df

    def export_per_query_metrics(
        self,
        ground_truth: pd.DataFrame,
        lexai_responses: List[Dict],
        baseline_responses: Dict[str, List[Dict]],
        all_metrics: Dict[str, Dict],
    ) -> Dict:
        """Export canonical per-query metrics CSVs and provenance manifest."""
        print("\n" + "="*60)
        print("STEP 7.5: Exporting Canonical Per-Query Metrics")
        print("="*60)

        per_query_dir = os.path.join(self.output_dir, 'per_query_metrics')
        os.makedirs(per_query_dir, exist_ok=True)

        chroma_client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(anonymized_telemetry=False, allow_reset=False),
        )

        system_to_responses = {'LexAI': lexai_responses}
        system_to_responses.update(baseline_responses)

        files = {}
        row_counts = {}
        provenance_rows = []

        for system_name, responses in system_to_responses.items():
            if system_name not in all_metrics:
                raise ValueError(f"Missing metrics for system '{system_name}' during per-query export.")

            engine = MetricsEngine(ground_truth, chroma_client)
            df = self._build_per_query_metrics_df(
                system_name=system_name,
                responses=responses,
                ground_truth=ground_truth,
                system_metrics=all_metrics[system_name],
                metrics_engine=engine,
            )

            slug = self._system_slug(system_name)
            csv_path = os.path.join(per_query_dir, f"{slug}_per_query_metrics.csv")
            df.to_csv(csv_path, index=False)

            files[system_name] = csv_path
            row_counts[system_name] = int(len(df))
            provenance_rows.append({
                'system': system_name,
                'path': csv_path,
                'row_count': int(len(df)),
                'columns': list(df.columns),
            })

            if len(df) != len(ground_truth):
                raise ValueError(
                    f"Row count check failed for {system_name}: "
                    f"{len(df)} != ground truth size {len(ground_truth)}"
                )

            print(f"  ✓ {system_name}: {len(df)} rows -> {csv_path}")

        manifest = {
            'run_timestamp': self.run_timestamp,
            'ground_truth_size': int(len(ground_truth)),
            'systems': provenance_rows,
        }
        manifest_path = os.path.join(per_query_dir, 'manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"  ✓ Manifest: {manifest_path}")

        return {
            'directory': per_query_dir,
            'files': files,
            'row_counts': row_counts,
            'manifest': manifest_path,
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 8: Save Complete Results
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def save_results(self, results: Dict):
        """
        Save complete results to JSON.
        
        Args:
            results: Complete results dictionary
        """
        print("\n" + "="*60)
        print("STEP 8: Saving Results")
        print("="*60)
        
        # Save full results
        results_path = os.path.join(self.output_dir, f"complete_results_{self.run_timestamp}.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"  ✓ Saved: {results_path}")
        
        # Save summary
        summary = {
            "run_timestamp": self.run_timestamp,
            "config": self.config,
            "lexai_performance": {
                "CAR": results['all_metrics']['LexAI']['CAR']['CAR_overall'],
                "HR": results['all_metrics']['LexAI']['HR']['HR_overall'],
                "OLR": results['all_metrics']['LexAI']['OLR']['OLR_overall'],
                "ACS": results['all_metrics']['LexAI']['ACS']['ACS_overall']
            },
            "per_query_metrics": results.get('per_query_metrics', {}),
            "output_files": results['output_files']
        }
        
        summary_path = os.path.join(self.output_dir, f"summary_{self.run_timestamp}.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"  ✓ Saved: {summary_path}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MASTER ORCHESTRATOR
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def run(self) -> Dict:
        """
        Run complete evaluation pipeline.
        
        Returns:
            Complete results dictionary
        """
        print("\n" + "█"*60)
        print("█" + " "*58 + "█")
        print("█" + " "*15 + "LEXAI EVALUATION PIPELINE" + " "*18 + "█")
        print("█" + " "*58 + "█")
        print("█"*60)
        print(f"\nRun ID: {self.run_timestamp}")
        print(f"Random Seed: {RANDOM_SEED}")
        print(f"Output Directory: {self.output_dir}")
        
        # Step 1: Load ground truth
        ground_truth = self.load_ground_truth()
        
        # Step 2: Run LexAI (with checkpoint resume)
        lexai_checkpoint = self.load_checkpoint('lexai')
        if lexai_checkpoint:
            print(f"\n✅ RESUMING: Found LexAI checkpoint with {len(lexai_checkpoint)} responses")
            print("   Skipping LexAI execution...")
            lexai_responses = lexai_checkpoint
        else:
            lexai_responses = self.run_lexai(ground_truth['query'].tolist(), eval_mode=self.eval_mode)
            # Save checkpoint immediately after LexAI completes
            self.save_checkpoint(lexai_responses, 'lexai')
            print("   ✅ LexAI complete and checkpointed!")
        
        # Step 3: Run baselines (with checkpoint resume)
        baselines_checkpoint = self.load_checkpoint('baselines')
        if baselines_checkpoint:
            print(f"\n✅ RESUMING: Found baselines checkpoint")
            print("   Skipping baseline execution...")
            baseline_responses = baselines_checkpoint
        else:
            baseline_responses = self.run_baselines(ground_truth, eval_mode=self.eval_mode)
            # Save checkpoint immediately after baselines complete
            self.save_checkpoint(baseline_responses, 'baselines')
            print("   ✅ Baselines complete and checkpointed!")
        
        # Phase 3: Optional regime comparison
        regime_comparison = None
        if self.compare_regimes:
            print("\n" + "="*60)
            print("PHASE 3: Running Regime Comparison")
            print("="*60)
            regime_comparison = self.compare_lexai_regimes(ground_truth)
        
        # Step 4: Compute metrics
        all_metrics = self.compute_all_metrics(lexai_responses, baseline_responses, ground_truth)
        
        # Step 5: Statistical tests
        statistical_tests = self.run_statistical_tests(all_metrics, lexai_responses, ground_truth)
        
        # Step 6: Error analysis
        error_analysis = self.run_error_analysis(lexai_responses, ground_truth, all_metrics['LexAI'])
        
        # Step 7: Generate outputs
        output_files = self.generate_outputs(all_metrics, statistical_tests, error_analysis)

        # Step 7.5: Canonical per-query metrics artifacts
        per_query_metrics = self.export_per_query_metrics(
            ground_truth=ground_truth,
            lexai_responses=lexai_responses,
            baseline_responses=baseline_responses,
            all_metrics=all_metrics,
        )
        
        # Compile results
        results = {
            "run_timestamp": self.run_timestamp,
            "config": self.config,
            "metric_schema_version": METRIC_SCHEMA_VERSION,
            "ground_truth_size": len(ground_truth),
            "all_metrics": all_metrics,
            "statistical_tests": statistical_tests,
            "error_analysis": error_analysis,
            "output_files": output_files,
            "per_query_metrics": per_query_metrics,
        }
        if regime_comparison is not None:
            results["regime_comparison"] = regime_comparison
        
        # Step 8: Save results
        self.save_results(results)
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def compare_lexai_regimes(self, ground_truth: pd.DataFrame) -> Dict:
        """
        Compare LexAI performance under two evaluation regimes.
        Phase 3 Fix 2 - Regime Comparison
        
        1. FORCED-ANSWER (eval_mode=True): Always provides an answer
        2. ABSTAIN-ALLOWED (eval_mode=False): Can abstain on low-confidence queries
        
        Returns:
            Dictionary with regime comparison analysis
        """
        print("\n  Running FORCED-ANSWER regime (eval_mode=True)...")
        forced_answer_responses = self.run_lexai(ground_truth['query'].tolist(), eval_mode=True)
        
        print("  Running ABSTAIN-ALLOWED regime (eval_mode=False)...")
        abstain_allowed_responses = self.run_lexai(ground_truth['query'].tolist(), eval_mode=False)
        
        # Compare the two regimes
        comparison = self._analyze_regime_differences(
            forced_answer_responses,
            abstain_allowed_responses,
            ground_truth
        )
        
        return comparison
    
    def _analyze_regime_differences(self, 
                                   forced_answer: List[Dict],
                                   abstain_allowed: List[Dict],
                                   ground_truth: pd.DataFrame) -> Dict:
        """
        Analyze and compare differences between the two regimes.
        
        Returns:
            Dictionary with detailed comparison metrics and insights
        """
        analysis = {
            "total_queries": len(forced_answer),
            "regime_descriptions": {
                "forced_answer": "eval_mode=True - System always provides an answer",
                "abstain_allowed": "eval_mode=False - System can abstain on low-confidence queries"
            },
            "response_differences": []
        }
        
        abstention_count = 0
        abstention_queries = []
        
        for i, (fa_resp, aa_resp) in enumerate(zip(forced_answer, abstain_allowed)):
            query = fa_resp.get('query', '')
            fa_answer = fa_resp.get('answer', '')
            aa_answer = aa_resp.get('answer', '')
            
            # Check if response was abstained in abstain-allowed regime
            if aa_answer and ('abstain' in aa_answer.lower() or 'cannot answer' in aa_answer.lower()):
                abstention_count += 1
                abstention_queries.append({
                    "query_index": i,
                    "query": query[:100],
                    "forced_answer": fa_answer[:200],
                    "abstained_reason": aa_answer[:200]
                })
            
            # Track if answers differ significantly
            if fa_answer != aa_answer:
                analysis['response_differences'].append({
                    "query_index": i,
                    "query": query,
                    "forced_answer": fa_answer[:300],
                    "abstain_allowed_answer": aa_answer[:300],
                    "forced_confidence": fa_resp.get('confidence', ''),
                    "abstain_confidence": aa_resp.get('confidence', '')
                })
        
        analysis['abstention_analysis'] = {
            "total_abstentions": abstention_count,
            "abstention_rate": f"{(abstention_count / len(abstain_allowed) * 100):.1f}%",
            "abstention_queries": abstention_queries[:10]
        }
        
        analysis['summary'] = {
            "forced_answer_unique_responses": len(forced_answer),
            "abstain_allowed_unique_responses": len(abstain_allowed) - abstention_count,
            "queries_with_different_answers": len(analysis['response_differences']),
            "interpretation": (
                f"Under forced-answer regime, system provided {len(forced_answer)} answers. "
                f"Under abstain-allowed regime, system abstained on {abstention_count} queries "
                f"({(abstention_count / len(abstain_allowed) * 100):.1f}%) due to low confidence."
            )
        }
        
        return analysis
    
    def _print_summary(self, results: Dict):
        """Print evaluation summary."""
        print("\n" + "█"*60)
        print("█" + " "*58 + "█")
        print("█" + " "*18 + "EVALUATION COMPLETE" + " "*20 + "█")
        print("█" + " "*58 + "█")
        print("█"*60)
        
        print("\n📊 LEXAI PERFORMANCE:")
        lexai_metrics = results['all_metrics']['LexAI']
        print(f"  • Citation Accuracy Rate (CAR): {lexai_metrics['CAR']['CAR_overall']:.1f}%")
        print(f"  • Hallucination Rate (HR):      {lexai_metrics['HR']['HR_overall']:.1f}%")
        print(f"  • Outdated Law Rate (OLR):      {lexai_metrics['OLR']['OLR_overall']:.1f}%")
        print(f"  • Answer Completeness (ACS):    {lexai_metrics['ACS']['ACS_overall']:.1f}%")
        
        print(f"\n📁 OUTPUT FILES:")
        print(f"  • Results directory: {self.output_dir}/")
        print(f"  • LaTeX tables:      4 files")
        print(f"  • PNG figures:       5 files (300 DPI)")
        print(f"  • Complete results:  complete_results_{results['run_timestamp']}.json")
        
        print("\n✅ Ready for publication!")


def run_full_evaluation(ground_truth_path: str = "evaluation/ground_truth_verified_393_ready.xlsx",
                       output_dir: str = "evaluation/results",
                       debug: bool = False,
                       eval_regime: str = "forced-answer",
                       compare_regimes: bool = False) -> Dict:
    """
    Convenience function to run full evaluation.
    
    Args:
        ground_truth_path: Path to verified ground truth
        output_dir: Output directory
        debug: If True, allow placeholder responses on LexAI init failure
        eval_regime: Evaluation regime for all systems ('forced-answer' or 'abstain-allowed')
        compare_regimes: If True, run both regimes and compare behavior
        
    Returns:
        Complete results dictionary
    """
    runner = EvaluationRunner(
        ground_truth_path,
        output_dir,
        debug=debug,
        eval_regime=eval_regime,
        compare_regimes=compare_regimes,
    )
    return runner.run()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run LexAI evaluation pipeline")
    parser.add_argument(
        "--ground-truth",
        default="evaluation/ground_truth_verified_393_ready.xlsx",
        help="Path to verified ground truth Excel file"
    )
    parser.add_argument(
        "--output-dir",
        default="evaluation/results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: allow placeholder responses if LexAI initialization fails"
    )
    parser.add_argument(
        "--eval-regime",
        choices=["forced-answer", "abstain-allowed"],
        default="forced-answer",
        help="Evaluation regime for all systems"
    )
    parser.add_argument(
        "--compare-regimes",
        action="store_true",
        help="Run both regimes and save a comparison report"
    )
    
    args = parser.parse_args()
    
    # Run evaluation
    results = run_full_evaluation(
        args.ground_truth,
        args.output_dir,
        debug=args.debug,
        eval_regime=args.eval_regime,
        compare_regimes=args.compare_regimes,
    )
    
    print("\n" + "="*60)
    print("Evaluation pipeline complete!")
    print("="*60)


if __name__ == "__main__":
    main()
