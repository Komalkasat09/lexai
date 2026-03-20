import pandas as pd
import re

gt = pd.read_excel('ground_truth_verified.xlsx', sheet_name=0)
print(f"Before: {gt['correct_act'].notna().sum()} rows with citations")

# Convert columns to object dtype to accept strings
gt['correct_act'] = gt['correct_act'].astype('object')
gt['correct_section'] = gt['correct_section'].astype('object')

for i in range(len(gt)):
    query = str(gt.loc[i, 'query_text'])
    
    # Pattern 1: "Section XXX [of the] Act"
    match = re.search(r'Section\s+(\d+[A-Z]?(?:\([a-z]\))?)\s+(?:of\s+(?:the\s+)?)?(.+?(?:Act|IPC|BNS|CrPC|BNSS))', query, re.I)
    if match:
        gt.at[i, 'correct_section'] = match.group(1)
        act_name = match.group(2).strip()
        # Normalize common act names
        if 'negotiable' in act_name.lower():
            gt.at[i, 'correct_act'] = 'NI ACT'
        elif 'evidence' in act_name.lower():
            gt.at[i, 'correct_act'] = 'EVIDENCE ACT'
        elif 'companies' in act_name.lower():
            gt.at[i, 'correct_act'] = 'COMPANIES ACT'
        elif 'information technology' in act_name.lower() or 'IT Act' in act_name:
            gt.at[i, 'correct_act'] = 'IT ACT'
        elif 'arbitration' in act_name.lower():
            gt.at[i, 'correct_act'] = 'ARBITRATION ACT'
        elif 'ipc' in act_name.lower() or 'indian penal' in act_name.lower():
            gt.at[i, 'correct_act'] = 'IPC'
        elif 'bns' in act_name.lower() or 'bharatiya nyaya' in act_name.lower():
            gt.at[i, 'correct_act'] = 'BNS'
        elif 'crpc' in act_name.lower() or 'criminal procedure' in act_name.lower():
            gt.at[i, 'correct_act'] = 'CRPC'
        elif 'bnss' in act_name.lower():
            gt.at[i, 'correct_act'] = 'BNSS'
        else:
            gt.at[i, 'correct_act'] = act_name.upper()
        continue
    
    # Pattern 2: "Act Section XXX" or "XXX Act"
    match = re.search(r'(IPC|BNS|CrPC|BNSS|NI Act)\s+(?:Section\s+)?(\d+[A-Z]?)', query, re.I)
    if match:
        gt.at[i, 'correct_act'] = match.group(1).upper()
        gt.at[i, 'correct_section'] = match.group(2)
        continue
    
    # Pattern 3: "Section XXX IPC/BNS/etc" (simpler)
    match = re.search(r'Section\s+(\d+[A-Z]?)\s+(IPC|BNS|CrPC|BNSS)', query, re.I)
    if match:
        gt.at[i, 'correct_section'] = match.group(1)
        gt.at[i, 'correct_act'] = match.group(2).upper()

populated = gt['correct_act'].notna().sum()
print(f"After: {populated} rows with citations")
print(f"\nSample populated rows:")
print(gt[gt['correct_act'].notna()][['query_id', 'query_text', 'correct_act', 'correct_section']].head(5))

gt.to_excel('ground_truth_verified.xlsx', sheet_name='Ground Truth Dataset', index=False)
print(f"\n✅ Ground truth updated with {populated} citations!")
