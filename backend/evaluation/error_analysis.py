"""
LexAI Error Analysis
====================
Systematic analysis of system errors for research insights.

Analyses:
1. Failure categorization (6 categories)
2. Confusion matrices (confidence vs accuracy)
3. Query difficulty correlation
4. BNS transition deep-dive
5. Qualitative example selection

Usage:
    from evaluation.error_analysis import ErrorAnalyzer
    
    analyzer = ErrorAnalyzer()
    errors = analyzer.analyze_all_errors(responses, ground_truth)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from collections import defaultdict, Counter
import re


class ErrorAnalyzer:
    """
    Analyzes errors for research insights.
    """
    
    def __init__(self):
        """Initialize error analyzer."""
        self.error_categories = [
            "database_gap",        # Missing legal doc in ChromaDB
            "retrieval_failure",   # Failed to retrieve relevant chunks
            "llm_hallucination",   # LLM fabricated info
            "transition_missed",   # Missed IPC→BNS transition
            "overruling_missed",   # Cited overruled case
            "amendment_missed"     # Missed recent amendment
        ]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANALYSIS 1: Failure Categorization
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def categorize_error(self, response: Dict, ground_truth: pd.Series, 
                        retrieved_chunks: List[Dict] = None) -> str:
        """
        Categorize a single error.
        
        Args:
            response: System response
            ground_truth: Ground truth row
            retrieved_chunks: Retrieved RAG chunks
            
        Returns:
            Error category name
        """
        answer = response.get('answer', '')
        
        # Check for BNS transition errors
        if ground_truth.get('correct_act') == 'Bharatiya Nyaya Sanhita':
            if 'Indian Penal Code' in answer or 'IPC' in answer:
                return "transition_missed"
        
        # Check for overruling errors
        if pd.notna(ground_truth.get('overruling_note')):
            # If ground truth mentions overruling, check if system detected it
            if not response.get('bns_transition_note') and not response.get('overruling_note'):
                return "overruling_missed"
        
        # Check for amendment errors
        if pd.notna(ground_truth.get('amendment_note')):
            if not response.get('amendment_note'):
                return "amendment_missed"
        
        # Check retrieval quality
        if retrieved_chunks is not None:
            if len(retrieved_chunks) == 0:
                return "retrieval_failure"
            
            # Check if retrieved chunks are relevant
            gt_section = ground_truth.get('correct_section')
            gt_act = ground_truth.get('correct_act')
            
            relevant = False
            for chunk in retrieved_chunks[:3]:  # Top 3
                chunk_text = chunk.get('text', '')
                if gt_section and str(gt_section) in chunk_text:
                    relevant = True
                    break
            
            if not relevant:
                return "retrieval_failure"
        
        # Check for hallucinations
        if self._detect_hallucination(response):
            return "llm_hallucination"
        
        # Default to database gap
        return "database_gap"
    
    def _detect_hallucination(self, response: Dict) -> bool:
        """
        Detect if response contains hallucinated content.
        
        Simplified check - in production, use ChromaDB verification.
        """
        answer = response.get('answer', '')
        
        # Check for overly confident statements on rare topics
        rare_patterns = [
            r'Section \d{4}',  # Sections with 4 digits (likely fake)
            r'Article \d{4}',  # Articles with 4 digits
            r'\d{4} SCC \d{3}',  # Invalid SCC citation format
        ]
        
        for pattern in rare_patterns:
            if re.search(pattern, answer):
                return True
        
        return False
    
    def analyze_failures(self, responses: List[Dict], ground_truth: pd.DataFrame) -> Dict:
        """
        Categorize all failures.
        
        Args:
            responses: All system responses
            ground_truth: Ground truth dataset
            
        Returns:
            Dictionary with error counts and examples
        """
        error_counts = Counter()
        error_examples = defaultdict(list)
        
        for i, response in enumerate(responses):
            gt = ground_truth.iloc[i]
            
            # Only analyze errors (simplified: no abstentions, low confidence)
            confidence = response.get('confidence', 'medium').lower()
            if confidence == 'low' or len(response.get('answer', '')) < 50:
                category = self.categorize_error(
                    response, 
                    gt, 
                    response.get('retrieved_chunks')
                )
                error_counts[category] += 1
                
                # Store example
                if len(error_examples[category]) < 5:  # Keep 5 examples per category
                    # Handle both numeric and string query_ids
                    try:
                        qid = int(gt['query_id'])
                    except (ValueError, TypeError):
                        qid = str(gt['query_id'])
                    
                    # Safely handle string truncation
                    response_text = response.get('answer', '')
                    if isinstance(response_text, str):
                        response_text = response_text[:200]
                    else:
                        response_text = str(response_text)[:200]
                    
                    gt_text = gt.get('correct_answer_summary', '')
                    if isinstance(gt_text, str):
                        gt_text = gt_text[:200]
                    else:
                        gt_text = str(gt_text) if gt_text is not None else ''
                        gt_text = gt_text[:200]
                    
                    error_examples[category].append({
                        "query_id": qid,
                        "query": gt['query'],
                        "category": gt['category'],
                        "response": response_text,
                        "ground_truth": gt_text
                    })
        
        # Calculate percentages
        total_errors = sum(error_counts.values())
        error_distribution = {
            cat: {
                "count": error_counts[cat],
                "percentage": float(error_counts[cat] / total_errors * 100) if total_errors > 0 else 0
            }
            for cat in self.error_categories
        }
        
        return {
            "total_errors": total_errors,
            "distribution": error_distribution,
            "examples": dict(error_examples)
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANALYSIS 2: Confusion Matrices
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def build_confidence_confusion_matrix(self, responses: List[Dict], 
                                         ground_truth: pd.DataFrame) -> Dict:
        """
        Build confusion matrix: predicted confidence vs actual accuracy.
        
        Shows: Are high-confidence answers actually correct?
        
        Args:
            responses: System responses
            ground_truth: Ground truth
            
        Returns:
            Confusion matrix and metrics
        """
        # Initialize matrix
        matrix = {
            'low': {'correct': 0, 'incorrect': 0},
            'medium': {'correct': 0, 'incorrect': 0},
            'high': {'correct': 0, 'incorrect': 0}
        }
        
        for i, response in enumerate(responses):
            gt = ground_truth.iloc[i]
            confidence = response.get('confidence', 'medium').lower()
            
            # Simplified correctness check
            is_correct = self._check_correctness(response, gt)
            
            if confidence in matrix:
                if is_correct:
                    matrix[confidence]['correct'] += 1
                else:
                    matrix[confidence]['incorrect'] += 1
        
        # Calculate accuracy per confidence level
        accuracy_by_confidence = {}
        for conf in ['low', 'medium', 'high']:
            total = matrix[conf]['correct'] + matrix[conf]['incorrect']
            acc = matrix[conf]['correct'] / total if total > 0 else 0
            accuracy_by_confidence[conf] = {
                "accuracy": float(acc * 100),
                "total_predictions": total
            }
        
        return {
            "matrix": matrix,
            "accuracy_by_confidence": accuracy_by_confidence
        }
    
    def _check_correctness(self, response: Dict, ground_truth: pd.Series) -> bool:
        """
        Check if response is correct (simplified).
        
        In production, use full metrics from MetricsEngine.
        """
        answer = response.get('answer', '').lower()
        gt_act = str(ground_truth.get('correct_act', '')).lower()
        gt_section = str(ground_truth.get('correct_section', ''))
        
        # Check if mentions correct act and section
        has_act = gt_act in answer if gt_act else False
        has_section = gt_section in answer if gt_section else False
        
        return has_act and has_section
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANALYSIS 3: Query Difficulty Correlation
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def analyze_difficulty_correlation(self, responses: List[Dict], 
                                      ground_truth: pd.DataFrame) -> Dict:
        """
        Analyze: Do harder queries lead to more errors?
        
        Args:
            responses: System responses
            ground_truth: Ground truth with difficulty levels
            
        Returns:
            Accuracy breakdown by difficulty
        """
        difficulty_scores = {'easy': [], 'medium': [], 'hard': []}
        
        for i, response in enumerate(responses):
            gt = ground_truth.iloc[i]
            difficulty = gt.get('difficulty', 'medium').lower()
            
            is_correct = self._check_correctness(response, gt)
            
            if difficulty in difficulty_scores:
                difficulty_scores[difficulty].append(1 if is_correct else 0)
        
        # Calculate accuracy per difficulty
        results = {}
        for diff in ['easy', 'medium', 'hard']:
            scores = difficulty_scores[diff]
            if scores:
                results[diff] = {
                    "accuracy": float(np.mean(scores) * 100),
                    "n_queries": len(scores),
                    "std": float(np.std(scores) * 100)
                }
        
        # Compute correlation
        all_difficulties = []
        all_scores = []
        diff_map = {'easy': 1, 'medium': 2, 'hard': 3}
        
        for i, response in enumerate(responses):
            gt = ground_truth.iloc[i]
            diff = gt.get('difficulty', 'medium').lower()
            if diff in diff_map:
                all_difficulties.append(diff_map[diff])
                all_scores.append(1 if self._check_correctness(response, gt) else 0)
        
        if len(all_difficulties) > 1:
            correlation = float(np.corrcoef(all_difficulties, all_scores)[0, 1])
        else:
            correlation = 0.0
        
        return {
            "by_difficulty": results,
            "correlation": correlation,
            "correlation_interpretation": "negative" if correlation < -0.3 else "weak" if abs(correlation) < 0.3 else "positive"
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANALYSIS 4: BNS Transition Deep-Dive
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def analyze_bns_transitions(self, responses: List[Dict], 
                               ground_truth: pd.DataFrame) -> Dict:
        """
        Deep-dive into BNS transition handling.
        
        Research question: Does LexAI correctly warn about IPC→BNS changes?
        
        Args:
            responses: System responses
            ground_truth: Ground truth
            
        Returns:
            BNS transition analysis
        """
        bns_queries = ground_truth[ground_truth['category'] == 'IPC to BNS Transition']
        
        results = {
            "total_bns_queries": len(bns_queries),
            "transition_detected": 0,
            "transition_missed": 0,
            "false_positives": 0,
            "examples": []
        }
        
        for idx in bns_queries.index:
            if idx < len(responses):
                response = responses[idx]
                gt = ground_truth.iloc[idx]
                
                # Check if system detected transition
                has_transition_note = bool(response.get('bns_transition_note'))
                should_have_note = pd.notna(gt.get('correct_bns_section'))
                
                if has_transition_note and should_have_note:
                    results["transition_detected"] += 1
                elif not has_transition_note and should_have_note:
                    results["transition_missed"] += 1
                    
                    # Add example
                    if len(results["examples"]) < 5:
                        results["examples"].append({
                            "query": gt['query'],
                            "expected_bns_section": gt.get('correct_bns_section', 'N/A'),
                            "system_response": response.get('answer', '')[:150]
                        })
        
        # Calculate detection rate
        total_should_detect = results["transition_detected"] + results["transition_missed"]
        detection_rate = results["transition_detected"] / total_should_detect if total_should_detect > 0 else 0
        
        results["detection_rate"] = float(detection_rate * 100)
        
        return results
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ANALYSIS 5: Qualitative Example Selection
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def select_examples_for_paper(self, responses: List[Dict], 
                                  ground_truth: pd.DataFrame,
                                  metrics: Dict) -> Dict:
        """
        Select best/worst/interesting examples for paper.
        
        Args:
            responses: System responses
            ground_truth: Ground truth
            metrics: Computed metrics
            
        Returns:
            Selected examples with scores
        """
        examples = {
            "best_examples": [],
            "worst_examples": [],
            "interesting_cases": []
        }
        
        # Score each response
        scored_responses = []
        for i, response in enumerate(responses):
            gt = ground_truth.iloc[i]
            
            # Compute simple score
            is_correct = self._check_correctness(response, gt)
            confidence = response.get('confidence', 'medium').lower()
            conf_score = {'low': 0.5, 'medium': 0.7, 'high': 0.9}.get(confidence, 0.7)
            
            score = 1.0 if is_correct else 0.0
            score += conf_score * 0.5  # Bonus for appropriate confidence
            
            scored_responses.append({
                "index": i,
                "score": score,
                "query": gt['query'],
                "category": gt['category'],
                "response": response
            })
        
        # Sort by score
        scored_responses.sort(key=lambda x: x['score'], reverse=True)
        
        # Best examples (top 5)
        for item in scored_responses[:5]:
            examples["best_examples"].append({
                "query": item['query'],
                "category": item['category'],
                "answer": item['response'].get('answer', '')[:300],
                "confidence": item['response'].get('confidence'),
                "score": float(item['score'])
            })
        
        # Worst examples (bottom 5)
        for item in scored_responses[-5:]:
            examples["worst_examples"].append({
                "query": item['query'],
                "category": item['category'],
                "answer": item['response'].get('answer', '')[:300],
                "confidence": item['response'].get('confidence'),
                "score": float(item['score'])
            })
        
        # Interesting cases (high confidence but wrong, or low confidence but right)
        for item in scored_responses:
            response = item['response']
            is_correct = self._check_correctness(response, ground_truth.iloc[item['index']])
            confidence = response.get('confidence', 'medium').lower()
            
            # High confidence but wrong
            if confidence == 'high' and not is_correct:
                if len(examples["interesting_cases"]) < 10:
                    examples["interesting_cases"].append({
                        "type": "overconfident_error",
                        "query": item['query'],
                        "category": item['category'],
                        "answer": response.get('answer', '')[:300]
                    })
            
            # Low confidence but right
            if confidence == 'low' and is_correct:
                if len(examples["interesting_cases"]) < 10:
                    examples["interesting_cases"].append({
                        "type": "underconfident_success",
                        "query": item['query'],
                        "category": item['category'],
                        "answer": response.get('answer', '')[:300]
                    })
        
        return examples
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MASTER FUNCTION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def analyze_all_errors(self, responses: List[Dict], ground_truth: pd.DataFrame,
                          metrics: Dict = None) -> Dict:
        """
        Run all error analyses.
        
        Args:
            responses: System responses
            ground_truth: Ground truth dataset
            metrics: Computed metrics (optional)
            
        Returns:
            Complete error analysis
        """
        print("Running error analysis...")
        
        results = {}
        
        # 1. Failure categorization
        print("  1/5 Categorizing failures...")
        results["failure_categories"] = self.analyze_failures(responses, ground_truth)
        
        # 2. Confusion matrix
        print("  2/5 Building confusion matrix...")
        results["confusion_matrix"] = self.build_confidence_confusion_matrix(responses, ground_truth)
        
        # 3. Difficulty correlation
        print("  3/5 Analyzing difficulty correlation...")
        results["difficulty_correlation"] = self.analyze_difficulty_correlation(responses, ground_truth)
        
        # 4. BNS transition analysis
        print("  4/5 Analyzing BNS transitions...")
        results["bns_analysis"] = self.analyze_bns_transitions(responses, ground_truth)
        
        # 5. Example selection
        print("  5/5 Selecting qualitative examples...")
        results["examples"] = self.select_examples_for_paper(responses, ground_truth, metrics or {})
        
        print("  ✓ Error analysis complete")
        
        return results


def demo():
    """Demo function."""
    print("Error Analysis Demo")
    print("=" * 60)
    print("\nThis module performs 5 error analyses:")
    print("  1. Failure categorization (6 categories)")
    print("  2. Confidence confusion matrix")
    print("  3. Query difficulty correlation")
    print("  4. BNS transition deep-dive")
    print("  5. Qualitative example selection")
    print("\nProvides systematic error insights for research paper.")


if __name__ == "__main__":
    demo()
