import pandas as pd, re
gt = pd.read_excel('ground_truth_verified.xlsx', sheet_name=1)
for i in range(len(gt)):
    q = str(gt.at[i, 'query_text'])
    m = re.search(r'Section\s+(\d+[A-Z]?)\s+(IPC|BNS|CrPC|BNSS)', q, re.I)
    if m:
        gt.at[i, 'correct_section'] = m.group(1)
        gt.at[i, 'correct_act'] = m.group(2).upper()
print(f"Populated {gt['correct_act'].notna().sum()} rows")
with pd.ExcelWriter('ground_truth_verified.xlsx', mode='a', if_sheet_exists='replace') as w:
    gt.to_excel(w, sheet_name='Ground Truth Dataset', index=False)
print("✅ Updated ground truth")
