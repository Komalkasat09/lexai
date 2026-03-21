import json
import pandas as pd
import sys
sys.path.insert(0,'/Users/komalkasat09/legal-website/backend')
from evaluation.metrics_engine import MetricsEngine

hindi_gt_path='evaluation/hindi_queries.xlsx'
hindi_resp_path='evaluation/evaluation/results/checkpoints/lexai_hindi_responses.json'
empty_log_path='evaluation/evaluation/results/checkpoints/lexai_hindi_empty_responses.json'
english_gt_path='evaluation/ground_truth_verified.xlsx'
english_resp_path='evaluation/evaluation/results/checkpoints/lexai_responses.json'
out_json='evaluation/evaluation/results/hindi_eval_summary.json'

hindi_gt=pd.read_excel(hindi_gt_path)
with open(hindi_resp_path,'r',encoding='utf-8') as f:
    hindi_responses=json.load(f)

resp_df=pd.DataFrame({'resp_idx':range(len(hindi_responses)),'query':[str(r.get('query','')).strip() for r in hindi_responses],'answer':[str(r.get('answer','')).strip() for r in hindi_responses]})
hindi_join=hindi_gt.rename(columns={'hindi_query':'query'})
merged=resp_df.merge(hindi_join[['query_id','query','english_query']],on='query',how='left')
empty_mask=merged['answer'].eq('')
empty_rows=merged[empty_mask]
non_empty_rows=merged[~empty_mask]
with open(empty_log_path,'w',encoding='utf-8') as f:
    json.dump(empty_rows[['resp_idx','query_id','query','english_query']].fillna('').to_dict(orient='records'),f,ensure_ascii=False,indent=2)

eng_gt=pd.read_excel(english_gt_path,sheet_name='Ground Truth Dataset')
metric_gt=non_empty_rows.merge(eng_gt[['query_id','category','correct_answer_summary','correct_act','correct_section','correct_citation']],on='query_id',how='left')
filtered_responses=[hindi_responses[int(i)] for i in non_empty_rows['resp_idx'].tolist()]
engine_h=MetricsEngine(metric_gt,None)
car_h=engine_h.compute_citation_accuracy(filtered_responses)
acs_h=engine_h.compute_completeness_score(filtered_responses)

eng_gt_eval=eng_gt.rename(columns={'query_text':'query'})
with open(english_resp_path,'r',encoding='utf-8') as f:
    eng_responses=json.load(f)
engine_e=MetricsEngine(eng_gt_eval,None)
car_e=engine_e.compute_citation_accuracy(eng_responses)
acs_e=engine_e.compute_completeness_score(eng_responses)

english_car=float(car_e.get('CAR_overall',0.0))
english_acs=float(acs_e.get('ACS_overall',0.0))
hindi_car=float(car_h.get('CAR_overall',0.0))
hindi_acs=float(acs_h.get('ACS_overall',0.0))
english_n=len(eng_responses)
hindi_total_n=len(hindi_responses)
hindi_eval_n=len(filtered_responses)
overall_n=english_n+hindi_total_n
overall_eval_n=english_n+hindi_eval_n
overall_car=((english_car*english_n)+(hindi_car*hindi_eval_n))/max(1,overall_eval_n)
overall_acs=((english_acs*english_n)+(hindi_acs*hindi_eval_n))/max(1,overall_eval_n)

summary={'english':{'queries':english_n,'car_percent':english_car,'acs':english_acs},'hindi':{'queries_total':hindi_total_n,'queries_evaluated':hindi_eval_n,'car_percent':hindi_car,'acs':hindi_acs},'overall':{'queries_total':overall_n,'queries_evaluated_for_metrics':overall_eval_n,'car_percent':overall_car,'acs':overall_acs},'empty_hindi_responses':int(len(empty_rows)),'empty_log_path':empty_log_path}
with open(out_json,'w',encoding='utf-8') as f:
    json.dump(summary,f,ensure_ascii=False,indent=2)

print(f"Hindi queries evaluated: {hindi_eval_n}")
print(f"Hindi total queries: {hindi_total_n}")
print(f"Empty Hindi responses: {len(empty_rows)}")
print(f"CAR (Hindi): {hindi_car:.4f}%")
print(f"ACS (Hindi): {hindi_acs:.4f}")
print(f"CAR (English): {english_car:.4f}%")
print(f"ACS (English): {english_acs:.4f}")
print(f"CAR (Overall): {overall_car:.4f}%")
print(f"ACS (Overall): {overall_acs:.4f}")
