"""
Fix citation formats and recompute metrics from checkpoints.

This script normalizes the citation formats from different systems:
- LexAI: structured_response -> citations list of dicts
- Baselines: string citations -> dicts with type, act_or_case, section_or_citation
"""

import json
import pandas as pd
import re
from typing import List, Dict
from metrics_engine import MetricsEngine

# Paths
LEXAI_CHECKPOINT = "/Users/komalkasat09/Desktop/legal-website/backend/evaluation/results/checkpoints/lexai_responses.json"
BASELINE_CHECKPOINT = "/Users/komalkasat09/Desktop/legal-website/backend/evaluation/results/checkpoints/baseline_responses.json"
GROUND_TRUTH = "/Users/komalkasat09/Desktop/legal-website/backend/evaluation/ground_truth_verified.xlsx"
OUTPUT_DIR = "/Users/komalkasat09/Desktop/legal-website/backend/evaluation/results/"


def normalize_lexai_citations(response: Dict) -> Dict:
    """
    Convert LexAI structured_response to citations list.
    
    Input:
        structured_response: {
            act_cited: str or None,
            section_cited: str or None,
            case_citations: list of strings
        }
    
    Output:
        citations: list of dicts with {type, act_or_case, section_or_citation}
    """
    citations = []
    structured = response.get('structured_response', {})
    
    if structured:
        # Handle act + section
        act_cited = structured.get('act_cited')
        section_cited = structured.get('section_cited')
        
        if act_cited and section_cited:
            citations.append({
                'type': 'bare_act',
                'act_or_case': act_cited,
                'section_or_citation': section_cited
            })
        
        # Handle case citations
        case_citations = structured.get('case_citations', [])
        if case_citations:
            for case in case_citations:
                if isinstance(case, str) and case.strip():
                    citations.append({
                        'type': 'case_law',
                        'act_or_case': case,
                        'section_or_citation': case
                    })
    
    response['citations'] = citations
    return response


def parse_act_section(citation_str: str) -> Dict:
    """
    Parse citation strings like:
    - "the Indian Penal Code Section 420"
    - "IPC Section 302"
    - "Section 498A, Indian Penal Code, 1860"
    
    Returns dict with type, act_or_case, section_or_citation
    """
    citation_str = citation_str.strip()
    
    # Pattern 1: "the Indian Penal Code Section 420"
    # Pattern 2: "IPC Section 302"
    # Pattern 3: "Section 498A, Indian Penal Code"
    
    # Try to extract section number
    section_match = re.search(r'Section\s+(\d+[A-Z]*)', citation_str, re.IGNORECASE)
    section = section_match.group(1) if section_match else None
    
    # Try to extract act name
    act_patterns = [
        r'(Indian Penal Code)',
        r'(IPC)',
        r'(Code of Criminal Procedure)',
        r'(CrPC)',
        r'(Evidence Act)',
        r'(Constitution of India)',
        r'(Bharatiya Nyaya Sanhita)',
        r'(BNS)',
        r'(Bharatiya Nagarik Suraksha Sanhita)',
        r'(BNSS)',
        r'([A-Z][a-zA-Z\s]+Act[,\s]*\d{4}?)',  # "Some Act, 1860"
    ]
    
    act = None
    for pattern in act_patterns:
        match = re.search(pattern, citation_str, re.IGNORECASE)
        if match:
            act = match.group(1)
            break
    
    if not act:
        # If no act found, use the whole string as act name
        act = citation_str
    
    return {
        'type': 'bare_act',
        'act_or_case': act,
        'section_or_citation': section if section else ''
    }


def normalize_baseline_citations(response: Dict) -> Dict:
    """
    Convert baseline string citations to dict format.
    
    Input:
        citations: list of strings like "the Indian Penal Code Section 420"
    
    Output:
        citations: list of dicts with {type, act_or_case, section_or_citation}
    """
    citations = response.get('citations', [])
    
    if not citations or not isinstance(citations, list):
        response['citations'] = []
        return response
    
    normalized = []
    for citation in citations:
        if isinstance(citation, str):
            parsed = parse_act_section(citation)
            normalized.append(parsed)
        elif isinstance(citation, dict):
            # Already in correct format
            normalized.append(citation)
    
    response['citations'] = normalized
    return response


def compute_metrics_for_system(system_name: str, responses: List[Dict], ground_truth_df: pd.DataFrame) -> tuple:
    """Compute metrics for a single system."""
    print(f"\n{'='*60}")
    print(f"Computing metrics for {system_name}")
    print(f"{'='*60}")
    
    engine = MetricsEngine(ground_truth_df=ground_truth_df, chroma_client=None)
    
    # Compute Citation Accuracy Rate
    car_result = engine.compute_citation_accuracy(responses)
    print(f"\n🎯 Citation Accuracy Rate (CAR): {car_result['CAR_overall']:.2f}%")
    print(f"   - Individual scores: {len(car_result['individual_scores'])} queries")
    
    # Compute Hallucination Rate
    hr_result = engine.compute_hallucination_rate(responses)
    print(f"\n🚫 Hallucination Rate (HR): {hr_result['HR_overall']:.2f}%")
    print(f"   - Total claims: {hr_result['total_claims']}")
    print(f"   - Hallucinated: {hr_result['hallucinated_claims']}")
    
    # Compute Outdated Law Rate (requires ChromaDB - skip for now)
    olr = 0.0
    print(f"\n📅 Outdated Law Rate (OLR): {olr:.2f}% (requires ChromaDB)")
    
    # Compute Answer Completeness Score
    acs_result = engine.compute_completeness_score(responses)
    print(f"\n📋 Answer Completeness Score (ACS): {acs_result['ACS_overall']:.2f}%")
    print(f"   - Individual scores: {len(acs_result['individual_scores'])} queries")
    
    print(f"\n{'='*60}\n")
    
    return car_result, hr_result, acs_result


def save_to_csv(system_name: str, car_result: Dict, hr_result: Dict, acs_result: Dict, output_path: str):
    """Save per-query metrics to CSV."""
    # Get individual scores
    car_scores = car_result.get('individual_scores', [])
    hr_individual = hr_result.get('individual_results', [])
    acs_scores = acs_result.get('individual_scores', [])
    
    # Build rows
    rows = []
    for i in range(len(car_scores)):
        row = {
            'query_id': i,
            'car_score': car_scores[i] if i < len(car_scores) else 0,
            'acs_score': acs_scores[i] if i < len(acs_scores) else 0,
        }
        
        # Add HR data if available
        if i < len(hr_individual):
            hr_item = hr_individual[i]
            row['hr_total_claims'] = hr_item.get('total_claims', 0)
            row['hr_hallucinated'] = hr_item.get('hallucinated_count', 0)
            row['hr_rate'] = hr_item.get('hallucination_rate', 0)
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    print(f"✅ Saved {len(df)} rows to {output_path}")


def main():
    print("🔧 Loading checkpoint files...")
    
    # Load LexAI responses
    with open(LEXAI_CHECKPOINT, 'r') as f:
        lexai_responses = json.load(f)
    print(f"   Loaded {len(lexai_responses)} LexAI responses")
    
    # Load baseline responses
    with open(BASELINE_CHECKPOINT, 'r') as f:
        baseline_data = json.load(f)
    simple_rag_responses = baseline_data.get('SimpleRAG', [])
    no_rag_responses = baseline_data.get('NoRAG', [])
    print(f"   Loaded {len(simple_rag_responses)} SimpleRAG responses")
    print(f"   Loaded {len(no_rag_responses)} NoRAG responses")
    
    # Load ground truth
    ground_truth_df = pd.read_excel(GROUND_TRUTH, sheet_name=1)
    print(f"   Loaded {len(ground_truth_df)} ground truth entries")
    
    print("\n🔄 Normalizing citation formats...")
    
    # Normalize LexAI citations
    for response in lexai_responses:
        normalize_lexai_citations(response)
    print("   ✓ Normalized LexAI citations")
    
    # Normalize baseline citations
    for response in simple_rag_responses:
        normalize_baseline_citations(response)
    print("   ✓ Normalized SimpleRAG citations")
    
    for response in no_rag_responses:
        normalize_baseline_citations(response)
    print("   ✓ Normalized NoRAG citations")
    
    # Compute metrics for each system
    print("\n" + "="*60)
    print("COMPUTING METRICS")
    print("="*60)
    
    # LexAI
    lexai_car, lexai_hr, lexai_acs = compute_metrics_for_system(
        "LexAI", lexai_responses, ground_truth_df
    )
    save_to_csv(
        "LexAI", lexai_car, lexai_hr, lexai_acs,
        OUTPUT_DIR + "recomputed_metrics.csv"
    )
    
    # SimpleRAG
    simple_rag_car, simple_rag_hr, simple_rag_acs = compute_metrics_for_system(
        "SimpleRAG", simple_rag_responses, ground_truth_df
    )
    save_to_csv(
        "SimpleRAG", simple_rag_car, simple_rag_hr, simple_rag_acs,
        OUTPUT_DIR + "simple_rag_metrics.csv"
    )
    
    # NoRAG
    no_rag_car, no_rag_hr, no_rag_acs = compute_metrics_for_system(
        "NoRAG", no_rag_responses, ground_truth_df
    )
    save_to_csv(
        "NoRAG", no_rag_car, no_rag_hr, no_rag_acs,
        OUTPUT_DIR + "no_rag_metrics.csv"
    )
    
    # Print summary table
    print("\n" + "="*80)
    print("FINAL SUMMARY STATISTICS")
    print("="*80)
    print(f"{'System':<15} {'CAR':>10} {'HR':>10} {'OLR':>10} {'ACS':>10}")
    print("-"*80)
    print(f"{'LexAI':<15} {lexai_car['CAR_overall']:>9.2f}% {lexai_hr['HR_overall']:>9.2f}% {'0.00%':>10} {lexai_acs['ACS_overall']:>9.2f}%")
    print(f"{'SimpleRAG':<15} {simple_rag_car['CAR_overall']:>9.2f}% {simple_rag_hr['HR_overall']:>9.2f}% {'0.00%':>10} {simple_rag_acs['ACS_overall']:>9.2f}%")
    print(f"{'NoRAG':<15} {no_rag_car['CAR_overall']:>9.2f}% {no_rag_hr['HR_overall']:>9.2f}% {'0.00%':>10} {no_rag_acs['ACS_overall']:>9.2f}%")
    print("="*80)
    print("\nOLR = 0.00% (ChromaDB connection not available)")
    print("\n✅ All metrics computed and saved!")


if __name__ == "__main__":
    main()
