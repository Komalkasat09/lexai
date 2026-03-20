import json
import pandas as pd

with open('results/checkpoints/lexai_responses.json') as f:
    lexai = json.load(f)
with open('results/checkpoints/baseline_responses.json') as f:
    baseline = json.load(f)

norag  = baseline['NoRAG']
simple = baseline['SimpleRAG']

gt_df = pd.read_excel('ground_truth_verified.xlsx', sheet_name=0)

# ── Ground truth coverage ────────────────────────────────────────────────────
empty_section = gt_df[
    gt_df['correct_section'].isna() |
    (gt_df['correct_section'].astype(str).str.strip() == '') |
    (gt_df['correct_section'].astype(str).str.strip() == 'nan')
]
has_section = gt_df[~gt_df.index.isin(empty_section.index)]
print(f"Queries WITH  correct_section: {len(has_section)}/{len(gt_df)}")
print(f"Queries WITH NO correct_section: {len(empty_section)}/{len(gt_df)}")

print("\nSample queries with no correct_section:")
for _, row in empty_section.head(5).iterrows():
    qid  = row['query_id']
    cat  = row['category']
    qtxt = str(row['query_text'])[:60]
    print(f"  ID={qid}  cat={cat}  query={qtxt}")

# ── SimpleRAG citation examples ───────────────────────────────────────────────
print("\nSimpleRAG citation examples (first 5):")
for r in simple[:5]:
    print("  ", r.get('citations', []))

# ── LexAI citation examples (structured_response) ────────────────────────────
print("\nLexAI responses with non-null act_cited (first 5):")
shown = 0
for r in lexai:
    sr  = r.get('structured_response', {}) or {}
    act = sr.get('act_cited')
    sec = sr.get('section_cited')
    if act and act not in (None, 'None', ''):
        q = r.get('query', '')[:60]
        a = (r.get('answer', '') or '')[:80]
        print(f"  Q: {q}")
        print(f"    act={act}  sec={sec}")
        print(f"    ans: {a}")
        shown += 1
        if shown >= 5:
            break

# ── CAR breakdown on GT-covered queries only ──────────────────────────────────
print("\n=== CAR breakdown — GT queries with known correct_section ===")
print(f"Total GT queries with section: {len(has_section)}")

norag_correct = 0
lexai_correct = 0

for i, gt_row in has_section.iterrows():
    if i >= len(norag) or i >= len(lexai):
        break
    correct_sec = str(gt_row['correct_section']).strip()
    correct_act = str(gt_row['correct_act']).strip().lower()

    # NoRAG
    nr = norag[i]
    for c in nr.get('citations', []):
        if correct_sec in str(c):
            norag_correct += 1
            break

    # LexAI
    lr = lexai[i]
    sr = lr.get('structured_response', {}) or {}
    sec = str(sr.get('section_cited', '') or '').strip()
    if sec == correct_sec:
        lexai_correct += 1
    else:
        # fallback: (Citation: ...) in answer text
        ans = lr.get('answer', '') or ''
        if f"Section {correct_sec}" in ans:
            lexai_correct += 1

print(f"NoRAG correct: {norag_correct}/{len(has_section)}")
print(f"LexAI correct: {lexai_correct}/{len(has_section)}")

# ── HR: SimpleRAG vs LexAI — how many citations does each produce? ─────────────
print("\n=== HR diagnostic — citation counts ===")
lexai_with_cites = sum(
    1 for r in lexai
    if (r.get('structured_response') or {}).get('act_cited') not in (None, 'None', '')
)
simple_with_cites = sum(
    1 for r in simple
    if r.get('citations', [])
)
print(f"LexAI  responses with citations: {lexai_with_cites}/{len(lexai)}")
print(f"SimpleRAG responses with citations: {simple_with_cites}/{len(simple)}")

# Show 3 SimpleRAG citations in detail (act + section)
print("\nSimpleRAG detailed citation sample (first 3 with citations):")
shown = 0
for r in simple:
    cites = r.get('citations', [])
    if cites and shown < 3:
        ans = r.get('answer', '')[:100]
        print(f"  citations: {cites}")
        print(f"  answer:    {ans}")
        shown += 1

# HR: how does recompute_fixed parse SimpleRAG citations vs what it checks in ChromaDB
print("\n=== How recompute_fixed currently normalises SimpleRAG citations ===")
import re

def parse_baseline_cite(cite):
    if isinstance(cite, str):
        section_match = re.search(r'Section\s+(\d+[A-Z]?)', cite, re.I)
        act_match = re.search(
            r'(IPC|BNS|CrPC|BNSS|NI Act|Companies Act|Evidence Act|'
            r'Indian Penal Code|Bharatiya Nyaya Sanhita)',
            cite, re.I
        )
        if section_match and act_match:
            return {'act': act_match.group(1), 'section': section_match.group(1)}
    return None

parsed_sample = 0
for r in simple:
    for c in r.get('citations', []):
        p = parse_baseline_cite(c)
        if p and parsed_sample < 5:
            print(f"  raw: {c!r}  →  parsed: {p}")
            parsed_sample += 1
    if parsed_sample >= 5:
        break
