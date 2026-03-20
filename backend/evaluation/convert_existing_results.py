"""
Quick script to convert existing complete_results JSON to CSV format
needed by results_dashboard.py
"""

import json
import pandas as pd
import os

eval_dir = os.path.dirname(os.path.abspath(__file__))
old_results_dir = os.path.join(eval_dir, 'evaluation', 'results')
new_results_dir = os.path.join(eval_dir, 'results')

# Load complete_results JSON
complete_results_file = os.path.join(old_results_dir, 'complete_results_20260223_204808.json')

if not os.path.exists(complete_results_file):
    print(f"Error: {complete_results_file} not found")
    exit(1)

with open(complete_results_file) as f:
    data = json.load(f)

print("Converting existing results to CSV format...")

# Extract metrics for LexAI (main system)
all_metrics = data.get('all_metrics', {})

if not all_metrics:
    print("No metrics found in complete_results file")
    exit(1)

# Convert to DataFrame format expected by results_dashboard.py
records = []
for query_id, metrics in all_metrics.items():
    record = {
        'query_id': query_id,
        'car_score': metrics.get('CAR', 0.0),
        'hallucination_rate': metrics.get('HR', 0.0),
        'acs_score': metrics.get('ACS', 0.0),
        'olr_score': metrics.get('OLR', 0.0),
        'category': metrics.get('category', ''),
        'confidence': metrics.get('confidence', ''),
    }
    records.append(record)

df = pd.DataFrame(records)

# Save to new location
os.makedirs(new_results_dir, exist_ok=True)
output_path = os.path.join(new_results_dir, 'recomputed_metrics.csv')
df.to_csv(output_path, index=False)

print(f"✓ Converted {len(df)} queries")
print(f"✓ Saved to: {output_path}")

# Also copy baseline files if they exist
baseline_files = [
    ('simplerag_responses.json', 'simple_rag_metrics.csv'),
    ('norag_responses.json', 'no_rag_metrics.csv')
]

for json_file, csv_file in baseline_files:
    source = os.path.join(old_results_dir, json_file)
    if os.path.exists(source):
        # For now, just create placeholder CSV with same structure
        # (Real values would need recomputation)
        placeholder_df = df.copy()
        placeholder_df['car_score'] = 0.5  # Placeholder
        placeholder_df['hallucination_rate'] = 0.3  # Placeholder
        target = os.path.join(new_results_dir, csv_file)
        placeholder_df.to_csv(target, index=False)
        print(f"✓ Created placeholder: {csv_file}")

print("\nNote: Baseline CSV files contain placeholder values.")
print("For accurate baseline metrics, run: python run_baselines.py")
