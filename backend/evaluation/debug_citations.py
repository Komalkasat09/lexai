"""Debug citation normalization"""
import json

# Load and check LexAI citations
with open('/Users/komalkasat09/Desktop/legal-website/backend/evaluation/results/checkpoints/lexai_responses.json', 'r') as f:
    lexai = json.load(f)

print("="*60)
print("LexAI Sample (Before/After Normalization)")
print("="*60)

for i in range(3):
    resp = lexai[i]
    print(f"\nQuery {i}: {resp['query']}")
    print(f"Original citations: {resp.get('citations')}")
    print(f"Structured response: {resp.get('structured_response')}")
    
# Load baselines
with open('/Users/komalkasat09/Desktop/legal-website/backend/evaluation/results/checkpoints/baseline_responses.json', 'r') as f:
    baselines = json.load(f)

print("\n" + "="*60)
print("NoRAG Sample (Before Normalization)")
print("="*60)

for i in range(3):
    resp = baselines['NoRAG'][i]
    print(f"\nQuery {i}")
    print(f"Original citations: {resp.get('citations')}")

print("\n" + "="*60)
print("SimpleRAG Sample (Before Normalization)")
print("="*60)

for i in range(3):
    resp = baselines['SimpleRAG'][i]
    print(f"\nQuery {i}")
    print(f"Original citations: {resp.get('citations')}")
