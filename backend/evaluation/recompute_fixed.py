"""
Recompute metrics from checkpoint files and generate CSV for dashboard
"""
import json
import pandas as pd
import os, sys, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.metrics_engine import MetricsEngine
import chromadb

eval_dir = os.path.dirname(os.path.abspath(__file__))
print("Loading ground truth...")
gt_file = os.path.join(eval_dir, 'ground_truth_verified.xlsx')
gt_df = pd.read_excel(gt_file, sheet_name=0)  # Use sheet 0
print(f"✓ Loaded {len(gt_df)} ground truth queries")
print(f"  - {gt_df['correct_act'].notna().sum()} queries have ground truth citations")

print("\nLoading checkpoint responses...")
lexai_checkpoint = os.path.join(eval_dir, 'results', 'checkpoints', 'lexai_responses.json')
baseline_checkpoint = os.path.join(eval_dir, 'results', 'checkpoints', 'baseline_responses.json')

with open(lexai_checkpoint) as f:
    lexai_responses = json.load(f)
print(f"✓ Loaded {len(lexai_responses)} LexAI responses")

with open(baseline_checkpoint) as f:
    baseline_data = json.load(f)
simple_rag_responses = baseline_data.get('SimpleRAG', [])
no_rag_responses = baseline_data.get('NoRAG', [])
print(f"✓ Loaded {len(simple_rag_responses)} SimpleRAG responses")
print(f"✓ Loaded {len(no_rag_responses)} NoRAG responses")

print("\nMatching responses to ground truth...")

def match_responses_to_gt(responses, gt_df, has_query_field=True):
    matched = []
    if has_query_field:
        for i, response in enumerate(responses):
            query_text = response.get('query', '')
            gt_match = gt_df[gt_df['query_text'] == query_text]
            if not gt_match.empty:
                gt_row = gt_match.iloc[0]
                matched.append({'response': response, 'gt': gt_row.to_dict(), 'query_id': gt_row['query_id'], 'category': gt_row['category']})
    else:
        for i, response in enumerate(responses):
            if i < len(gt_df):
                gt_row = gt_df.iloc[i]
                matched.append({'response': response, 'gt': gt_row.to_dict(), 'query_id': gt_row['query_id'], 'category': gt_row['category']})
    return matched

lexai_matched = match_responses_to_gt(lexai_responses, gt_df, has_query_field=True)
simple_rag_matched = match_responses_to_gt(simple_rag_responses, gt_df, has_query_field=False)
no_rag_matched = match_responses_to_gt(no_rag_responses, gt_df, has_query_field=False)

print(f"Matched {len(lexai_matched)} LexAI responses")
print(f"Matched {len(simple_rag_matched)} SimpleRAG responses")
print(f"Matched {len(no_rag_matched)} NoRAG responses")

def _parse_possibly_stringified_list(value):
    """
    Responses sometimes store lists as their repr(): "['a', 'b']".
    Parse them back to a real Python list.  Returns [] on failure.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if value in ('', 'None', 'null', '[]'):
            return []
        # Try ast.literal_eval first (handles repr of list of strings)
        import ast
        try:
            result = ast.literal_eval(value)
            if isinstance(result, list):
                return result
        except Exception:
            pass
        # Fallback: try JSON
        import json as _json
        try:
            result = _json.loads(value)
            if isinstance(result, list):
                return result
        except Exception:
            pass
    return []


# ── API-error detection helpers (LexAI) ─────────────────────────────────────
_API_ERROR_MARKERS = [
    'Error: All API keys failed',
    'Rate limit reached',
    'Error code: 429',
    'All API keys failed',
]

def _is_api_error_response(response):
    """Return True if the LexAI response is an API-rate-limit / key failure."""
    answer = response.get('answer', '') or ''
    return any(m.lower() in answer.lower() for m in _API_ERROR_MARKERS)

# Act name patterns used in answer text scanning
_ACT_TEXT_ALIASES = [
    r'Indian\s+Penal\s+Code(?:\s+(?:18)?60)?(?:\s*\(IPC\))?',
    r'IPC(?:\s+18?60)?',
    r'Bharatiya\s+Nyaya\s+Sanhita(?:\s+2023)?(?:\s*\(BNS\))?',
    r'BNS(?:\s+2023)?',
    r'Code\s+of\s+Criminal\s+Procedure(?:\s+19?73)?(?:\s*\(CrPC\))?',
    r'CrPC(?:\s+19?73)?',
    r'Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita(?:\s+2023)?(?:\s*\(BNSS\))?',
    r'BNSS(?:\s+2023)?',
    r'Negotiable\s+Instruments\s+Act(?:\s+18?81)?(?:\s*\(NI\s+Act\))?',
    r'NI\s+Act',
    r'Companies\s+Act(?:\s+20?13)?',
    r'Indian\s+Evidence\s+Act(?:\s+18?72)?',
    r'Bharatiya\s+Sakshya\s+(?:Adhiniyam|Act)(?:\s+2023)?',
    r'Arbitration(?:\s+and\s+Conciliation)?\s+Act(?:\s+19?96)?',
]
_ACT_BLOCK = '(?:' + '|'.join(_ACT_TEXT_ALIASES) + ')'

# Three inline mention patterns:
# 1. (Citation: IPC Section 420)
# 2. Section 420 of [Act]
# 3. [Act] Section 420  /  [Act], Section 420
_CITE_PATTERNS = [
    re.compile(
        r'\(Citation:\s*(' + _ACT_BLOCK + r')[^)]*?\s+Section\s+(\d+[A-Z]?)\)',
        re.I
    ),
    re.compile(
        r'Section\s+(\d+[A-Z]?)\s+of\s+(?:the\s+)?(' + _ACT_BLOCK + r')',
        re.I
    ),
    re.compile(
        r'(' + _ACT_BLOCK + r')[,\s]+Section\s+(\d+[A-Z]?)',
        re.I
    ),
]

def _extract_citation_labels_from_text(answer_text, strict=False):
    """
    Scan LexAI answer text for inline act/section mentions.

    strict=False (default — used for CAR):
      All three patterns:
        (Citation: Act Section X)
        Section 420 of the Indian Penal Code
        Indian Penal Code Section 420 / IPC, Section 420

    strict=True (used for HR):
      Only Pattern 1 — explicit (Citation: ...) assertion labels.
      Avoids false hallucination flags from defensive disclaimers like
      "Section 323 IPC is not available in the provided context".
    """
    seen = set()
    citations = []

    def _add(act_raw, sec_raw):
        key = (act_raw.strip().lower(), sec_raw.strip())
        if key not in seen:
            seen.add(key)
            citations.append({
                'type': 'bare_act',
                'act_or_case': act_raw.strip(),
                'section_or_citation': sec_raw.strip(),
            })

    # Pattern 1: (Citation: Act Section X) — explicit assertion
    for m in _CITE_PATTERNS[0].finditer(answer_text):
        _add(m.group(1), m.group(2))

    if not strict:
        # Pattern 2: Section X of [Act]
        for m in _CITE_PATTERNS[1].finditer(answer_text):
            _add(m.group(2), m.group(1))

        # Pattern 3: [Act] Section X
        for m in _CITE_PATTERNS[2].finditer(answer_text):
            _add(m.group(1), m.group(2))

    return citations
# ────────────────────────────────────────────────────────────────────────────


def normalize_citations(response, system_type):
    normalized = response.copy()
    if system_type == 'lexai':
        # ── API error guard ────────────────────────────────────────────────
        # When LexAI's API keys are exhausted the 'answer' field contains an
        # error string like "Error: All API keys failed…".  The
        # structured_response may contain STALE data from the previous valid
        # call.  Treat these responses as abstentions: no citations, HR = 0.
        if _is_api_error_response(response):
            normalized['citations'] = []
            normalized['_is_api_error'] = True
            return normalized
        # ──────────────────────────────────────────────────────────────────

        structured = response.get('structured_response', {}) or {}

        act = structured.get('act_cited')
        section = structured.get('section_cited')

        # act_cited / section_cited are sometimes the string "None"
        if act in (None, 'None', '', 'null'):
            act = None
        if section in (None, 'None', '', 'null'):
            section = None

        answer_text = response.get('answer', '') or ''

        # ── CAR citations: all 3 patterns (generous — finds correct answers) ─
        # structured_response.act_cited reflects the RETRIEVED CHUNK's act,
        # not the query's answer act, so text scanning is the primary source.
        citations = _extract_citation_labels_from_text(answer_text, strict=False)
        if not citations and act and section:
            citations.append({'type': 'bare_act', 'act_or_case': act, 'section_or_citation': section})

        # ── HR citations: P1 only — explicit (Citation: ...) assertions ───
        # P2/P3 match contextual/defensive mentions (e.g. "Section 323 IPC is
        # not available in the provided context... Indian Penal Code 1860,
        # Section 323") which fail ChromaDB even though the citation is valid.
        # Using only explicit (Citation:...) labels avoids corpus-gap false
        # positives and measures real hallucination (fabricated references).
        hr_citations = _extract_citation_labels_from_text(answer_text, strict=True)

        normalized['hr_citations'] = hr_citations

        # case_citations: often a stringified list AND may contain VIBER_ chunk IDs
        raw_case_cites = _parse_possibly_stringified_list(
            structured.get('case_citations', [])
        )
        for case_cite in raw_case_cites:
            if not isinstance(case_cite, str):
                continue
            # VIBER_ entries are retrieval chunk IDs — they are NOT real case citations
            if 'VIBER_' in case_cite:
                continue
            # Real case citations look like "AIR 2002 SC 123" or "2019 SCC (1) 244"
            if re.search(r'(?:AIR|SCC|SCR|SCALE|ALL|BLJR)\s+\d{4}', case_cite, re.I):
                citations.append({
                    'type': 'case_law',
                    'act_or_case': case_cite,
                    'section_or_citation': case_cite,
                })

        normalized['citations'] = citations
    else:
        # Baseline (SimpleRAG / NoRAG): citations field may be a stringified list
        raw_citations = _parse_possibly_stringified_list(
            response.get('citations', [])
        )
        citations = []
        for cite in raw_citations:
            if isinstance(cite, str):
                section_match = re.search(r'Section\s+(\d+[A-Z]?)', cite, re.I)
                act_match = re.search(
                    r'(IPC|BNS|CrPC|BNSS|NI Act|Companies Act|Evidence Act|'
                    r'Indian Penal Code|Bharatiya Nyaya Sanhita)',
                    cite, re.I
                )
                if section_match and act_match:
                    citations.append({
                        'type': 'bare_act',
                        'act_or_case': act_match.group(1),
                        'section_or_citation': section_match.group(1),
                    })
                # else: bare strings with no recognisable section/act → discard
            elif isinstance(cite, dict):
                citations.append(cite)
        normalized['citations'] = citations
    return normalized

def compute_metrics_for_system(responses, gt_df, system_name, system_type):
    print(f"\nComputing metrics for {system_name}...")
    normalized_responses = [normalize_citations(r, system_type) for r in responses]

    if system_type == 'lexai':
        n_errors = sum(1 for r in normalized_responses if r.get('_is_api_error'))
        n_valid  = len(normalized_responses) - n_errors
        print(f"  ⚠  API error responses (abstentions): {n_errors}/{len(normalized_responses)} ({100*n_errors/len(normalized_responses):.1f}%)")
        print(f"  ✓  Valid responses evaluated:          {n_valid}")
    backend_dir = os.path.dirname(eval_dir)
    chroma_path = os.path.join(backend_dir, 'chroma_db')
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    engine = MetricsEngine(gt_df, chroma_client)

    car_result = engine.compute_citation_accuracy(normalized_responses)
    # For HR: swap citations → hr_citations so only explicit (Citation:...) labels
    # are verified, avoiding corpus-gap false positives from contextual mentions.
    hr_responses = []
    for r in normalized_responses:
        rc = r.copy()
        if 'hr_citations' in rc:
            rc['citations'] = rc.pop('hr_citations')
        hr_responses.append(rc)
    hr_result  = engine.compute_hallucination_rate(hr_responses)
    olr_result = engine.compute_outdated_law_rate(normalized_responses)
    acs_result = engine.compute_completeness_score(normalized_responses)

    # ── CAR: one score per response ──────────────────────────────────────
    car_scores = car_result.get('individual_scores', []) if isinstance(car_result, dict) else []

    # ── HR: one score per response ───────────────────────────────────────
    hr_scores = []
    if isinstance(hr_result, dict):
        for item in hr_result.get('individual_results', []):
            hr_scores.append(item.get('hallucination_rate', 0.0) if isinstance(item, dict) else 0.0)

    # ── OLR: compute per-response (single-element batch per response) ────
    # Rather than broadcasting the batch-level OLR to all rows, compute
    # a binary per-response signal: 1.0 if the response cites a replaced
    # act without acknowledging the replacement, 0.0 otherwise.
    olr_scores = [
        1.0 if engine._response_has_outdated_citation(r) else 0.0
        for r in normalized_responses
    ]

    # ── ACS: individual_scores already computed per response ─────────────
    acs_scores = acs_result.get('individual_scores', []) if isinstance(acs_result, dict) else []

    # ── Identify GT-annotated rows for CAR masking ───────────────────────
    # CAR is only meaningful where a correct_section is known (89/293).
    # Assign NaN for the 204 queries without GT so they don't dilute the mean.
    import numpy as np
    has_gt = ~(
        gt_df['correct_section'].isna() |
        (gt_df['correct_section'].astype(str).str.strip() == '') |
        (gt_df['correct_section'].astype(str).str.strip() == 'nan')
    )

    results = []
    for i, response in enumerate(normalized_responses):
        gt_row = gt_df.iloc[i]
        # CAR: use NaN for rows with no GT annotation
        car_val = (car_scores[i] if i < len(car_scores) else 0.0) if has_gt.iloc[i] else float('nan')
        results.append({
            'query_id':           gt_row['query_id'],
            'category':           gt_row['category'],
            'car_score':          car_val,
            'hallucination_rate': hr_scores[i] if i < len(hr_scores) else 0.0,
            'olr_score':          olr_scores[i] if i < len(olr_scores) else 0.0,
            'acs_score':          acs_scores[i] if i < len(acs_scores) else 0.0,
            'confidence':         response.get('confidence', 'UNKNOWN'),
        })

    df = pd.DataFrame(results)
    car_mean  = df['car_score'].mean()        # mean ignores NaN by default
    hr_mean   = df['hallucination_rate'].mean()
    olr_mean  = df['olr_score'].mean()
    acs_mean  = df['acs_score'].mean()
    n_car_gt  = has_gt.sum()
    print(f"  CAR coverage: {n_car_gt}/{len(df)} GT queries ({n_car_gt/len(df)*100:.1f}%)")
    print(f"  CAR (over {n_car_gt} GT queries): {car_mean*100:.2f}%")
    print(f"  HR  overall:  {hr_mean*100:.2f}%")
    print(f"  OLR overall:  {olr_result.get('OLR_overall', 0):.2f}%  (response-level: {olr_result.get('OLR_response_level', 0):.1f}%)")
    print(f"  ACS overall:  {acs_mean:.2f}%")

    return df

simple_rag_gt = gt_df.iloc[:len(simple_rag_matched)]
no_rag_gt = gt_df.iloc[:len(no_rag_matched)]

lexai_df = compute_metrics_for_system([m['response'] for m in lexai_matched], gt_df, 'LexAI', 'lexai')
simple_rag_df = compute_metrics_for_system([m['response'] for m in simple_rag_matched], simple_rag_gt, 'SimpleRAG', 'baseline')
no_rag_df = compute_metrics_for_system([m['response'] for m in no_rag_matched], no_rag_gt, 'NoRAG', 'baseline')

output_dir = os.path.join(eval_dir, 'results')
os.makedirs(output_dir, exist_ok=True)

lexai_csv = os.path.join(output_dir, 'recomputed_metrics.csv')
simple_rag_csv = os.path.join(output_dir, 'simple_rag_metrics.csv')
no_rag_csv = os.path.join(output_dir, 'no_rag_metrics.csv')

lexai_df.to_csv(lexai_csv, index=False)
simple_rag_df.to_csv(simple_rag_csv, index=False)
no_rag_df.to_csv(no_rag_csv, index=False)

print(f"\n✅ Metrics saved!")
print(f"  ✓ {lexai_csv} ({len(lexai_df)} rows)")
print(f"  ✓ {simple_rag_csv} ({len(simple_rag_df)} rows)")
print(f"  ✓ {no_rag_csv} ({len(no_rag_df)} rows)")

print("\n📊 Summary statistics:")
for name, df in [('LexAI', lexai_df), ('SimpleRAG', simple_rag_df), ('NoRAG', no_rag_df)]:
    print(f"\n{name}:")
    print(f"  CAR:  {df['car_score'].mean():.3f}")
    print(f"  HR:   {df['hallucination_rate'].mean():.3f}")
    print(f"  OLR:  {df['olr_score'].mean():.3f}")
    print(f"  ACS:  {df['acs_score'].mean():.3f}")

print("\n✅ Ready for visualization!")
print("Run: python results_dashboard.py")
print("Run: python statistical_analysis.py")
