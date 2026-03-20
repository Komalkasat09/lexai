"""
Quick test of evaluation pipeline with 5 queries.
"""

import pandas as pd

# Read the full dataset
df = pd.read_excel('evaluation/ground_truth_verified.xlsx', sheet_name='Ground Truth Dataset')

# Take first 5 queries for quick test
df_test = df.head(5).copy()

# Save to a test file (keep original column names)
df_test.to_excel('evaluation/ground_truth_test_5.xlsx', sheet_name='Ground Truth Dataset', index=False)

print(f"✅ Created test dataset with {len(df_test)} queries")
print(f"   Categories: {df_test['category'].unique().tolist()}")
print(f"   File: evaluation/ground_truth_test_5.xlsx")
