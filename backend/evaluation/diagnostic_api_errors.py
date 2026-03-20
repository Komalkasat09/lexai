"""Count how many LexAI responses are API errors and show statistics"""
import json, sys, os
eval_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(eval_dir, 'results', 'checkpoints', 'lexai_responses.json')) as f:
    lexai_all = json.load(f)

ERROR_MARKERS = [
    'Error: All API keys failed',
    'Rate limit reached',
    'Error code: 429',
    'Error code: 503',
    'Error code: 500',
]

def is_error(r):
    ans = r.get('answer', '')
    return any(m.lower() in ans.lower() for m in ERROR_MARKERS)

def has_stale_structured(r):
    """Detect responses where the LLM failed but structured_response has leftover data."""
    if not is_error(r):
        return False
    sr = r.get('structured_response') or {}
    act = sr.get('act_cited')
    sec = sr.get('section_cited')
    if act in (None, 'None', '', 'null'):
        act = None
    if sec in (None, 'None', '', 'null'):
        sec = None
    return bool(act and sec)

total = len(lexai_all)
errors = sum(1 for r in lexai_all if is_error(r))
stale  = sum(1 for r in lexai_all if has_stale_structured(r))
good   = total - errors

print(f"Total LexAI responses:  {total}")
print(f"  API error responses:  {errors}  ({errors/total*100:.1f}%)")
print(f"    of which have stale structured_response: {stale}")
print(f"  Valid responses:      {good}  ({good/total*100:.1f}%)")
print()

# Show first 10 error examples with stale data
print("Examples of stale structured_response in error responses:")
shown = 0
for i, r in enumerate(lexai_all):
    if has_stale_structured(r) and shown < 5:
        sr = r.get('structured_response', {})
        print(f"  Q{i+1}: act_cited={sr.get('act_cited')!r}, section_cited={sr.get('section_cited')!r}")
        print(f"        query: {r.get('query','')[:60]}")
        shown += 1

print()
# For valid responses with structured citations
valid_with_citations = [r for r in lexai_all if not is_error(r)]
have_act = sum(1 for r in valid_with_citations if r.get('structured_response', {}).get('act_cited') not in (None, 'None', '', 'null'))
print(f"Valid responses with non-null act_cited: {have_act}/{len(valid_with_citations)}")
