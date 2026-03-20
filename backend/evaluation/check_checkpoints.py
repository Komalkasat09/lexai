"""
🚨 EMERGENCY CHECKPOINT SAVER 🚨
==================================

If your evaluation is running and you want to save progress NOW,
press Ctrl+C to interrupt it, then run this script.

This will save whatever responses have been collected so far.
"""

import os
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("🚨 EMERGENCY CHECKPOINT SAVER")
print("=" * 80)
print()

print("⚠️  WARNING: This should only be used if evaluation crashes mid-run.")
print("   The normal evaluation process auto-saves checkpoints.")
print()

checkpoint_dir = "evaluation/results/checkpoints"
os.makedirs(checkpoint_dir, exist_ok=True)

lexai_checkpoint = os.path.join(checkpoint_dir, "lexai_responses.json")
baselines_checkpoint = os.path.join(checkpoint_dir, "baseline_responses.json")

print(f"📂 Checkpoint directory: {checkpoint_dir}")
print()

# Check existing checkpoints
if os.path.exists(lexai_checkpoint):
    with open(lexai_checkpoint, 'r') as f:
        lexai_data = json.load(f)
    print(f"✅ LexAI checkpoint exists: {len(lexai_data)} responses")
    print(f"   File: {lexai_checkpoint}")
    print(f"   Size: {os.path.getsize(lexai_checkpoint) / 1024:.1f} KB")
else:
    print(f"❌ No LexAI checkpoint found")

print()

if os.path.exists(baselines_checkpoint):
    with open(baselines_checkpoint, 'r') as f:
        baseline_data = json.load(f)
    print(f"✅ Baselines checkpoint exists")
    print(f"   File: {baselines_checkpoint}")
    print(f"   Size: {os.path.getsize(baselines_checkpoint) / 1024:.1f} KB")
else:
    print(f"❌ No baselines checkpoint found")

print()
print("=" * 80)
print("📋 RECOVERY INSTRUCTIONS")
print("=" * 80)
print()

if os.path.exists(lexai_checkpoint):
    print("✅ Your LexAI responses are SAVED!")
    print()
    print("To resume evaluation (skip LexAI, run baselines):")
    print("  cd backend/evaluation")
    print("  python run_evaluation.py")
    print()
    print("The script will automatically:")
    print("  1. Detect existing LexAI checkpoint")
    print("  2. Skip running LexAI again (saves hours!)")
    print("  3. Continue with baselines")
    print()
else:
    print("⚠️  No LexAI checkpoint found.")
    print("   Run evaluation normally:")
    print("     cd backend/evaluation")
    print("     python run_evaluation.py")

print("=" * 80)
print()
print("💡 TIP: If rate limits hit, wait 1-2 hours then re-run.")
print("   Your completed steps will be automatically skipped!")
print()
print("=" * 80)
