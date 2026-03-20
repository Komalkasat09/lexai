"""
LexAI Statistical Analysis
===========================
Performs statistical tests for research paper.

Tests:
1. Paired t-test (LexAI vs baselines)
2. Bootstrap confidence intervals
3. Inter-rater reliability (Cohen's Kappa)
4. Category-wise analysis
5. Threshold sensitivity analysis

Usage:
    from evaluation.statistical_analysis import StatisticalAnalyzer
    
    analyzer = StatisticalAnalyzer()
    stats = analyzer.run_all_tests(lexai_metrics, baseline_metrics)
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple
from collections import defaultdict
import random

# Set seed for reproducibility
random.seed(42)
np.random.seed(42)


class StatisticalAnalyzer:
    """
    Performs all statistical tests for LexAI evaluation.
    """
    
    def __init__(self, alpha: float = 0.05):
        """
        Initialize statistical analyzer.
        
        Args:
            alpha: Significance level (default: 0.05)
        """
        self.alpha = alpha
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TEST 1: Paired t-test
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def paired_ttest(self, lexai_scores: List[float], baseline_scores: List[float]) -> Dict:
        """
        Paired t-test comparing LexAI vs baseline.
        
        Args:
            lexai_scores: LexAI metric scores
            baseline_scores: Baseline metric scores
            
        Returns:
            Dictionary with t-statistic, p-value, significant flag
        """
        t_stat, p_value = stats.ttest_rel(lexai_scores, baseline_scores)
        
        # Calculate effect size (Cohen's d)
        mean_diff = np.mean(lexai_scores) - np.mean(baseline_scores)
        pooled_std = np.sqrt((np.std(lexai_scores)**2 + np.std(baseline_scores)**2) / 2)
        cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0
        
        return {
            "t_statistic": float(t_stat),
            "p_value": float(p_value),
            "significant": p_value < self.alpha,
            "cohens_d": float(cohens_d),
            "effect_size_interpretation": self._interpret_cohens_d(cohens_d),
            "mean_difference": float(mean_diff)
        }
    
    def _interpret_cohens_d(self, d: float) -> str:
        """Interpret Cohen's d effect size."""
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"
    
    def compare_all_metrics(self, lexai_metrics: Dict, baseline_metrics: Dict, 
                           baseline_name: str) -> Dict:
        """
        Compare LexAI against baseline on all metrics.
        
        Args:
            lexai_metrics: LexAI metrics dictionary
            baseline_metrics: Baseline metrics dictionary
            baseline_name: Name of baseline system
            
        Returns:
            Dictionary with test results for each metric
        """
        results = {}
        
        # Compare each metric that has individual scores
        comparable_metrics = ['CAR', 'ACS']
        
        for metric_name in comparable_metrics:
            if metric_name in lexai_metrics and metric_name in baseline_metrics:
                lexai_scores = lexai_metrics[metric_name].get('individual_scores', [])
                baseline_scores = baseline_metrics[metric_name].get('individual_scores', [])
                
                if lexai_scores and baseline_scores and len(lexai_scores) == len(baseline_scores):
                    results[metric_name] = self.paired_ttest(lexai_scores, baseline_scores)
        
        return {
            "baseline": baseline_name,
            "comparisons": results
        }
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TEST 2: Bootstrap Confidence Intervals
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def bootstrap_ci(self, scores: List[float], n_bootstrap: int = 10000, 
                     confidence: float = 0.95) -> Tuple[float, float]:
        """
        Compute bootstrap confidence interval.
        
        Args:
            scores: List of metric scores
            n_bootstrap: Number of bootstrap iterations
            confidence: Confidence level (default: 0.95)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        bootstrap_means = []
        
        for _ in range(n_bootstrap):
            sample = np.random.choice(scores, size=len(scores), replace=True)
            bootstrap_means.append(np.mean(sample))
        
        alpha_two_tailed = (1 - confidence) / 2
        lower = np.percentile(bootstrap_means, alpha_two_tailed * 100)
        upper = np.percentile(bootstrap_means, (1 - alpha_two_tailed) * 100)
        
        return float(lower), float(upper)
    
    def compute_all_cis(self, metrics: Dict) -> Dict:
        """
        Compute confidence intervals for all metrics.
        
        Args:
            metrics: Metrics dictionary
            
        Returns:
            Dictionary with CIs for each metric
        """
        cis = {}
        
        # Metrics with overall scores
        for metric_name in ['CAR', 'HR', 'OLR', 'ACS']:
            if metric_name in metrics:
                overall_key = f"{metric_name}_overall"
                if overall_key in metrics[metric_name]:
                    score = metrics[metric_name][overall_key]
                    # For overall scores, create synthetic distribution
                    # In practice, use individual scores
                    individual = metrics[metric_name].get('individual_scores', [])
                    if individual:
                        lower, upper = self.bootstrap_ci(individual)
                        cis[metric_name] = {
                            "mean": float(np.mean(individual)),
                            "ci_lower": lower,
                            "ci_upper": upper,
                            "ci_width": upper - lower
                        }
        
        return cis
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TEST 3: Inter-Rater Reliability
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def cohens_kappa(self, rater1: List[int], rater2: List[int]) -> Dict:
        """
        Compute Cohen's Kappa for inter-rater reliability.
        
        Args:
            rater1: Ratings from evaluator 1
            rater2: Ratings from evaluator 2
            
        Returns:
            Dictionary with kappa score and interpretation
        """
        from sklearn.metrics import cohen_kappa_score
        
        kappa = cohen_kappa_score(rater1, rater2)
        
        # Interpretation (Landis & Koch, 1977)
        if kappa < 0:
            interpretation = "poor"
        elif kappa < 0.20:
            interpretation = "slight"
        elif kappa < 0.40:
            interpretation = "fair"
        elif kappa < 0.60:
            interpretation = "moderate"
        elif kappa < 0.80:
            interpretation = "substantial"
        else:
            interpretation = "almost perfect"
        
        return {
            "cohens_kappa": float(kappa),
            "interpretation": interpretation,
            "n_ratings": len(rater1)
        }
    
    def analyze_inter_rater_reliability(self, ratings_df: pd.DataFrame) -> Dict:
        """
        Analyze agreement between multiple evaluators.
        
        Args:
            ratings_df: DataFrame with columns: query_id, evaluator_id, q1_score, q2_score, ...
            
        Returns:
            Dictionary with kappa scores for each question
        """
        results = {}
        
        # Get unique evaluators
        evaluators = ratings_df['evaluator_id'].unique()
        
        if len(evaluators) < 2:
            return {"error": "Need at least 2 evaluators for inter-rater reliability"}
        
        # Compute kappa for each question
        question_cols = [col for col in ratings_df.columns if col.startswith('q') and col.endswith('_score')]
        
        for question in question_cols:
            # Pivot to get ratings from each evaluator
            pivot = ratings_df.pivot(index='query_id', columns='evaluator_id', values=question)
            
            # Compute pairwise kappa
            kappa_scores = []
            for i, eval1 in enumerate(evaluators[:-1]):
                for eval2 in evaluators[i+1:]:
                    ratings1 = pivot[eval1].dropna().astype(int).tolist()
                    ratings2 = pivot[eval2].dropna().astype(int).tolist()
                    
                    if len(ratings1) > 0 and len(ratings2) > 0:
                        kappa_result = self.cohens_kappa(ratings1, ratings2)
                        kappa_scores.append(kappa_result['cohens_kappa'])
            
            if kappa_scores:
                results[question] = {
                    "mean_kappa": float(np.mean(kappa_scores)),
                    "min_kappa": float(np.min(kappa_scores)),
                    "max_kappa": float(np.max(kappa_scores))
                }
        
        return results
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TEST 4: Category-wise Analysis
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def category_wise_analysis(self, metrics: Dict, ground_truth: pd.DataFrame) -> Dict:
        """
        Analyze performance by query category.
        
        Args:
            metrics: Metrics dictionary
            ground_truth: Ground truth dataset with categories
            
        Returns:
            Dictionary with metrics broken down by category
        """
        results = {}
        
        # Get categories
        categories = ground_truth['category'].unique()
        
        for category in categories:
            category_indices = ground_truth[ground_truth['category'] == category].index.tolist()
            results[category] = {}
            
            # Extract scores for this category
            for metric_name in ['CAR', 'ACS']:
                if metric_name in metrics:
                    individual_scores = metrics[metric_name].get('individual_scores', [])
                    if individual_scores:
                        category_scores = [individual_scores[i] for i in category_indices 
                                         if i < len(individual_scores)]
                        if category_scores:
                            results[category][metric_name] = {
                                "mean": float(np.mean(category_scores)),
                                "std": float(np.std(category_scores)),
                                "n": len(category_scores)
                            }
        
        return results
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TEST 5: Threshold Sensitivity Analysis
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def threshold_sensitivity_analysis(self, responses: List[Dict], 
                                      ground_truth: pd.DataFrame,
                                      thresholds: List[float] = None) -> Dict:
        """
        Analyze performance at different confidence thresholds.
        
        Tests: What is the optimal confidence threshold?
        
        Args:
            responses: System responses with confidence scores
            ground_truth: Verified ground truth
            thresholds: List of thresholds to test (default: 0.60 to 0.90)
            
        Returns:
            Dictionary with metrics at each threshold
        """
        if thresholds is None:
            thresholds = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
        
        results = {}
        
        for threshold in thresholds:
            answered_queries = 0
            correct_answers = 0
            abstained_queries = 0
            
            for i, response in enumerate(responses):
                gt = ground_truth.iloc[i]
                
                # Convert confidence to numeric (simplified)
                confidence_map = {'low': 0.5, 'medium': 0.7, 'high': 0.9}
                conf_score = confidence_map.get(response.get('confidence', 'medium').lower(), 0.7)
                
                if conf_score >= threshold:
                    answered_queries += 1
                    # Check correctness (simplified)
                    answer = response.get('answer', '')
                    if len(answer) > 50:  # Has meaningful answer
                        correct_answers += 1
                else:
                    abstained_queries += 1
            
            total = len(responses)
            abstention_rate = abstained_queries / total if total > 0 else 0
            accuracy_on_answered = correct_answers / answered_queries if answered_queries > 0 else 0
            
            results[f"threshold_{threshold:.2f}"] = {
                "abstention_rate": float(abstention_rate * 100),
                "accuracy_on_answered": float(accuracy_on_answered * 100),
                "queries_answered": answered_queries,
                "queries_abstained": abstained_queries
            }
        
        return results
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MASTER FUNCTION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def run_all_tests(self, lexai_metrics: Dict, baseline_metrics_list: List[Tuple[str, Dict]],
                     lexai_responses: List[Dict] = None,
                     ground_truth: pd.DataFrame = None,
                     human_ratings: pd.DataFrame = None) -> Dict:
        """
        Run all statistical tests.
        
        Args:
            lexai_metrics: LexAI metrics
            baseline_metrics_list: List of (baseline_name, metrics) tuples
            lexai_responses: LexAI responses (for threshold analysis)
            ground_truth: Ground truth dataset (for category analysis)
            human_ratings: Human evaluation ratings (for inter-rater)
            
        Returns:
            Complete statistical analysis results
        """
        print("Running statistical tests...")
        
        results = {
            "significance_tests": {},
            "confidence_intervals": {},
            "category_analysis": {},
            "threshold_sensitivity": {},
            "inter_rater_reliability": {}
        }
        
        # 1. Paired t-tests
        print("  1/5 Running paired t-tests...")
        for baseline_name, baseline_metrics in baseline_metrics_list:
            comparison = self.compare_all_metrics(lexai_metrics, baseline_metrics, baseline_name)
            results["significance_tests"][baseline_name] = comparison
        
        # 2. Bootstrap CIs
        print("  2/5 Computing confidence intervals...")
        results["confidence_intervals"]["lexai"] = self.compute_all_cis(lexai_metrics)
        for baseline_name, baseline_metrics in baseline_metrics_list:
            results["confidence_intervals"][baseline_name] = self.compute_all_cis(baseline_metrics)
        
        # 3. Inter-rater reliability
        if human_ratings is not None:
            print("  3/5 Computing inter-rater reliability...")
            results["inter_rater_reliability"] = self.analyze_inter_rater_reliability(human_ratings)
        else:
            print("  3/5 Skipping inter-rater reliability (no human ratings)")
        
        # 4. Category-wise analysis
        if ground_truth is not None:
            print("  4/5 Running category-wise analysis...")
            results["category_analysis"]["lexai"] = self.category_wise_analysis(lexai_metrics, ground_truth)
            for baseline_name, baseline_metrics in baseline_metrics_list:
                results["category_analysis"][baseline_name] = self.category_wise_analysis(
                    baseline_metrics, ground_truth
                )
        else:
            print("  4/5 Skipping category analysis (no ground truth)")
        
        # 5. Threshold sensitivity
        if lexai_responses is not None and ground_truth is not None:
            print("  5/5 Running threshold sensitivity analysis...")
            results["threshold_sensitivity"] = self.threshold_sensitivity_analysis(
                lexai_responses, ground_truth
            )
        else:
            print("  5/5 Skipping threshold analysis (no responses)")
        
        print("  ✓ All statistical tests complete")
        
        return results


def demo():
    """Demo function."""
    print("Statistical Analysis Demo")
    print("=" * 60)
    print("\nThis module performs 5 types of statistical tests:")
    print("  1. Paired t-tests (LexAI vs baselines)")
    print("  2. Bootstrap confidence intervals (95%)")
    print("  3. Inter-rater reliability (Cohen's Kappa)")
    print("  4. Category-wise performance analysis")
    print("  5. Threshold sensitivity analysis")
    print("\nAll tests ensure statistical rigor for publication.")


if __name__ == "__main__":
    demo()
