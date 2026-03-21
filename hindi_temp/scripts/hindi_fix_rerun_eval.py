import json
import sys
from pathlib import Path
import pandas as pd

backend_root = Path.cwd()
sys.path.insert(0, str(backend_root))

from evaluation.run_evaluation import EvaluationRunner
from evaluation.metrics_engine import MetricsEngine

hindi_path = Path('evaluation/hindi_queries.xlsx')
responses_path = Path('evaluation/evaluation/results/checkpoints/lexai_hindi_responses.json')
empty_log_path = Path('evaluation/evaluation/results/checkpoints/lexai_hindi_empty_responses.json')
summary_path = Path('evaluation/evaluation/results/hindi_eval_summary.json')
gt_path = Path('evaluation/ground_truth_verified.xlsx')

hdf = pd.read_excel(hindi_path)
required_cols = ['query_id', 'english_query', 'hindi_query', 'section_reference', 'ground_truth_answer']
missing = [c for c in required_cols if c not in hdf.columns]
if missing:
    raise ValueError(f"Missing columns in Hindi file: {missing}")

fix = {
    'What does Section 420 IPC say?': 'धारा 420 आईपीसी में क्या प्रावधान है?',
    'What is the punishment for rape under BNS?': 'बीएनएस के तहत बलात्कार के लिए क्या दंड है?',
    'Has Section 66A IT Act been struck down?': 'क्या आईटी अधिनियम की धारा 66A निरस्त कर दी गई है?',
    'Has IPC 302 been replaced?': 'क्या आईपीसी की धारा 302 को प्रतिस्थापित किया गया है?',
    'Landmark cases on cheque bounce Section 138': 'धारा 138 चेक बाउंस पर प्रमुख फैसले कौन-कौन से हैं?',
    'Has the Section 377 judgment been challenged after decriminalization?': 'क्या अपराधमुक्ति के बाद धारा 377 पर दिए गए फैसले को चुनौती दी गई है?',
    'What are the grounds for quashing FIR under Section 482?': 'धारा 482 के तहत एफआईआर रद्द करने के आधार क्या हैं?',
    'What is Section 498A IPC?': 'आईपीसी की धारा 498A क्या है?',
    'What is the punishment for dowry harassment under Section 498A?': 'धारा 498A के तहत दहेज उत्पीड़न के लिए क्या दंड है?',
    'What are the new bail provisions under BNSS 2023?': 'बीएनएसएस 2023 में जमानत संबंधी नए प्रावधान क्या हैं?',
    'What is IPC 376 called in BNS?': 'बीएनएस में आईपीसी 376 के समकक्ष कौन-सी धारा है?',
    'Supreme Court cases on sedition Section 124A': 'धारा 124A देशद्रोह पर सुप्रीम कोर्ट के प्रमुख फैसले कौन-कौन से हैं?',
    'Is A.K. Gopalan v State of Madras still good law?': 'क्या A.K. Gopalan v. State of Madras अभी भी प्रभावी विधि है?',
    'What is the doctrine of common intention under Section 34 IPC?': 'आईपीसी की धारा 34 के तहत समान आशय का सिद्धांत क्या है?',
    'What does Section 354 IPC cover?': 'आईपीसी की धारा 354 में क्या प्रावधान है?',
    'What is the sentence for criminal breach of trust under IPC 406?': 'आईपीसी की धारा 406 के तहत आपराधिक न्यासभंग के लिए क्या सजा है?',
    'What happened to Section 377 IPC?': 'आईपीसी की धारा 377 का क्या हुआ?',
    'What is IPC 307 called in BNS?': 'बीएनएस में आईपीसी 307 के समकक्ष कौन-सी धारा है?',
    'Cases on adultery Section 497 IPC': 'आईपीसी धारा 497 (व्यभिचार) पर प्रमुख फैसले कौन-कौन से हैं?',
    'What happened to the judgment in Suresh Kumar Koushal case?': 'Suresh Kumar Koushal मामले के फैसले का क्या हुआ?',
    'What are the ingredients to prove cheating under IPC 420?': 'आईपीसी धारा 420 के तहत धोखाधड़ी सिद्ध करने के आवश्यक तत्व क्या हैं?',
    'Explain Section 506 IPC': 'आईपीसी धारा 506 की व्याख्या करें।',
    'How many years for kidnapping under IPC 363?': 'आईपीसी धारा 363 के तहत अपहरण के लिए कितने वर्ष की सजा है?',
    'What changed in CrPC after BNSS came into force?': 'बीएनएसएस लागू होने के बाद सीआरपीसी में क्या बदलाव हुए?',
    'What is the BNS section for criminal breach of trust?': 'आपराधिक न्यासभंग के लिए बीएनएस में कौन-सी धारा है?',
    'Cases on Section 156(3) CrPC investigation direction': 'धारा 156(3) सीआरपीसी के जांच निर्देशों पर प्रमुख फैसले कौन-कौन से हैं?',
    'Has ADM Jabalpur v Shukla been overruled?': 'क्या ADM Jabalpur v. Shukla को निरस्त किया जा चुका है?',
    'What must prosecution prove in a murder trial?': 'हत्या के मुकदमे में अभियोजन को क्या साबित करना होता है?',
    'What is Section 323 IPC about?': 'आईपीसी की धारा 323 के बारे में क्या प्रावधान है?',
    'How long imprisonment for robbery under IPC 392?': 'आईपीसी धारा 392 के तहत लूट के लिए अधिकतम कारावास अवधि क्या है?',
    'Was adultery decriminalized in India?': 'क्या भारत में व्यभिचार को अपराधमुक्त कर दिया गया है?',
    'What is IPC 120B called in BNS?': 'बीएनएस में आईपीसी 120B के समकक्ष कौन-सी धारा है?',
    'Cases on Section 313 CrPC statement of accused': 'धारा 313 सीआरपीसी के तहत अभियुक्त के बयान पर प्रमुख फैसले कौन-कौन से हैं?',
    'Is the Joseph Shine judgment on adultery still valid?': 'क्या व्यभिचार पर Joseph Shine का फैसला अभी भी मान्य है?',
    'What is the legal position on anticipatory bail for economic offences?': 'आर्थिक अपराधों में अग्रिम जमानत पर कानूनी स्थिति क्या है?',
    'Explain Section 279 IPC': 'आईपीसी धारा 279 की व्याख्या करें।',
    'What is the sentence for causing grievous hurt under IPC 325?': 'आईपीसी धारा 325 के तहत गंभीर चोट पहुंचाने के लिए क्या सजा है?',
    'Has the definition of rape been amended?': 'क्या बलात्कार की परिभाषा में संशोधन किया गया है?',
    'What is IPC 304B (dowry death) called in BNS?': 'बीएनएस में आईपीसी 304B (दहेज मृत्यु) के समकक्ष कौन-सी धारा है?',
    'Supreme Court on electronic evidence Section 65B': 'धारा 65B इलेक्ट्रॉनिक साक्ष्य पर सुप्रीम कोर्ट का दृष्टिकोण क्या है?',
}

if set(hdf['english_query']) != set(fix.keys()):
    missing_en = sorted(set(hdf['english_query']) - set(fix.keys()))
    extra_en = sorted(set(fix.keys()) - set(hdf['english_query']))
    raise ValueError(f"English query mismatch. missing={missing_en} extra={extra_en}")

hdf['hindi_query'] = hdf['english_query'].map(fix)
hdf.to_excel(hindi_path, index=False)
print(f"Updated Hindi queries: {hindi_path} ({len(hdf)} rows)")

runner = EvaluationRunner(
    ground_truth_path=str(gt_path),
    output_dir='evaluation/evaluation/results'
)
queries = hdf['hindi_query'].tolist()
responses = runner.run_lexai(queries)

responses_path.parent.mkdir(parents=True, exist_ok=True)
responses_path.write_text(json.dumps(responses, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Saved fresh Hindi responses: {responses_path} ({len(responses)} records)")

empty_idx = []
for i, r in enumerate(responses):
    ans = (r.get('answer') or '').strip()
    if not ans:
        empty_idx.append(i)

empty_payload = [
    {
        'row_index': i,
        'query_id': hdf.iloc[i]['query_id'],
        'english_query': hdf.iloc[i]['english_query'],
        'hindi_query': hdf.iloc[i]['hindi_query'],
    }
    for i in empty_idx
]
empty_log_path.write_text(json.dumps(empty_payload, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Empty Hindi responses: {len(empty_payload)} logged at {empty_log_path}")

gt = pd.read_excel(gt_path, sheet_name='Ground Truth Dataset')
gt = gt.rename(columns={'query_text': 'query'})
subset_gt = gt.set_index('query_id').reindex(hdf['query_id']).reset_index()

empty_set = set(empty_idx)
valid_indices = [i for i in range(len(responses)) if i not in empty_set]
valid_responses = [responses[i] for i in valid_indices]
valid_gt = subset_gt.iloc[valid_indices].reset_index(drop=True)

if len(valid_responses) == 0:
    hindi_car = 0.0
    hindi_acs = 0.0
else:
    me = MetricsEngine(ground_truth_df=valid_gt, chroma_client=None)
    car = me.compute_citation_accuracy(valid_responses)
    acs = me.compute_completeness_score(valid_responses)
    hindi_car = float(car['CAR_overall'])
    hindi_acs = float(acs['ACS_overall'])

if summary_path.exists():
    old_summary = json.loads(summary_path.read_text(encoding='utf-8'))
else:
    old_summary = {}

english = old_summary.get('english', {
    'queries': 293,
    'car_percent': 69.6245733788396,
    'acs': 63.76665529010239,
})
eng_q = int(english['queries'])
eng_car = float(english['car_percent'])
eng_acs = float(english['acs'])

h_total = len(hdf)
h_eval = len(valid_responses)

total_eval = eng_q + h_eval
overall_car = ((eng_car * eng_q) + (hindi_car * h_eval)) / total_eval if total_eval else 0.0
overall_acs = ((eng_acs * eng_q) + (hindi_acs * h_eval)) / total_eval if total_eval else 0.0

summary = {
    'english': {
        'queries': eng_q,
        'car_percent': eng_car,
        'acs': eng_acs,
    },
    'hindi': {
        'queries_total': h_total,
        'queries_evaluated': h_eval,
        'car_percent': hindi_car,
        'acs': hindi_acs,
    },
    'overall': {
        'queries_total': eng_q + h_total,
        'queries_evaluated_for_metrics': total_eval,
        'car_percent': overall_car,
        'acs': overall_acs,
    },
    'empty_hindi_responses': len(empty_payload),
    'empty_log_path': str(empty_log_path).replace('\\\\', '/'),
}

summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Updated Hindi summary: {summary_path}")

print('\nFINAL TABLE IV (Updated)')
print('| Language | Queries | CAR | ACS |')
print('|---|---:|---:|---:|')
print(f"| English | {eng_q} | {eng_car:.2f}% | {eng_acs:.2f} |")
print(f"| Hindi | {h_total} | {hindi_car:.2f}% | {hindi_acs:.2f} |")
print(f"| Overall | {eng_q + h_total} | {overall_car:.2f}% | {overall_acs:.2f} |")
