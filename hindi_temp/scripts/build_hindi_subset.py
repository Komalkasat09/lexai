import re
import pandas as pd

in_path = 'evaluation/ground_truth_verified.xlsx'
out_path = 'evaluation/hindi_queries.xlsx'

df = pd.read_excel(in_path, sheet_name='Ground Truth Dataset').copy()

def build_section_ref(row):
    act = str(row.get('correct_act', '')).strip()
    sec = str(row.get('correct_section', '')).strip()
    if act and act.lower() != 'nan' and sec and sec.lower() != 'nan':
        return f"{act} Section {sec}"
    q = str(row.get('query_text', ''))
    m = re.search(r'(Section\s+[0-9A-Za-z()/.]+)\s*(IPC|BNS|CrPC|BNSS|NI Act|Evidence Act)?', q, re.I)
    if m:
        act2 = m.group(2) if m.group(2) else 'Unknown Act'
        return f"{act2} {m.group(1)}"
    return ''

df['section_reference'] = df.apply(build_section_ref, axis=1)

categories = list(df['category'].dropna().unique())
selected = []
used_ids = set()
used_refs = set()

while len(selected) < 40:
    progressed = False
    for cat in categories:
        group = df[df['category'] == cat]
        cand = group[~group['query_id'].isin(used_ids)]
        cand_unique = cand[cand['section_reference'].apply(lambda x: str(x) not in used_refs)]
        pick = None
        if not cand_unique.empty:
            pick = cand_unique.iloc[0]
        elif not cand.empty:
            pick = cand.iloc[0]
        if pick is not None:
            selected.append(pick)
            used_ids.add(pick['query_id'])
            used_refs.add(str(pick['section_reference']))
            progressed = True
            if len(selected) >= 40:
                break
    if not progressed:
        break

if len(selected) < 40:
    rem = df[~df['query_id'].isin(used_ids)]
    for _, row in rem.iterrows():
        selected.append(row)
        if len(selected) >= 40:
            break

sel = pd.DataFrame(selected).head(40).copy()

def to_hindi(q):
    q = str(q).strip()
    replacements = {
        'Indian Penal Code': 'भारतीय दंड संहिता',
        'Code of Criminal Procedure': 'दंड प्रक्रिया संहिता',
        'Negotiable Instruments Act': 'परक्राम्य लिखत अधिनियम',
        'What does ': '',
    }
    for k, v in replacements.items():
        q = q.replace(k, v)

    patterns = [
        (r'^What does (Section .+?) say\?$', r'\1 में क्या कहा गया है?'),
        (r'^Explain (Section .+?)$', r'\1 की व्याख्या करें।'),
        (r'^What is (Section .+?)\?$', r'\1 क्या है?'),
        (r'^Show me (Section .+?)$', r'मुझे \1 दिखाइए।'),
        (r'^What does (Section .+?) cover\?$', r'\1 में क्या प्रावधान है?'),
        (r'^What is the punishment for (.+)\?$', r'\1 के लिए सजा क्या है?'),
        (r'^What is the sentence for (.+)\?$', r'\1 के लिए दंड क्या है?'),
        (r'^How many years imprisonment for (.+)\?$', r'\1 के लिए कितने वर्ष की सजा है?'),
        (r'^How long can you be jailed for (.+)\?$', r'\1 के लिए कितनी अवधि की जेल हो सकती है?'),
        (r'^Has (.+) been overruled\?$', r'क्या \1 को निरस्त किया जा चुका है?'),
        (r'^What happened to (.+)\?$', r'\1 के साथ क्या हुआ?'),
        (r'^What changed in (.+)\?$', r'\1 में क्या बदलाव हुआ है?'),
        (r'^Are there new provisions for (.+)\?$', r'क्या \1 के लिए नए प्रावधान हैं?'),
        (r'^What are the legal requirements for (.+)\?$', r'\1 के लिए कानूनी आवश्यकताएँ क्या हैं?'),
        (r'^What are the ingredients of (.+)\?$', r'\1 के आवश्यक तत्व क्या हैं?'),
    ]
    for p, r in patterns:
        if re.match(p, q):
            return re.sub(p, r, q)
    if q.endswith('?'):
        q = q[:-1]
    return f"{q} के बारे में कानूनी स्थिति क्या है?"

out = pd.DataFrame({
    'query_id': sel['query_id'],
    'english_query': sel['query_text'],
    'hindi_query': sel['query_text'].map(to_hindi),
    'section_reference': sel['section_reference'],
    'ground_truth_answer': sel['correct_answer_summary'],
})
out = out[['query_id', 'english_query', 'hindi_query', 'section_reference', 'ground_truth_answer']]
out.to_excel(out_path, index=False)

print('saved', out_path)
print('rows', len(out))
print('columns', list(out.columns))
print('categories', sel['category'].value_counts().to_dict())
