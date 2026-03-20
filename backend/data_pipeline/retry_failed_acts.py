"""
Retry Failed Acts
==================
Re-runs bare_acts_loader.py with increased timeouts.
The loader automatically skips already-loaded acts.
"""

import subprocess
import sys

print("\n" + "="*60)
print("RETRYING FAILED ACTS")
print("="*60)
print("\nThe bare_acts_loader will automatically skip acts that")
print("are already loaded and retry only the failed ones.")
print("\nWith increased timeout (60s) and updated direct URLs,")
print("the failed acts should now load successfully.")
print("\n" + "="*60 + "\n")

response = input("Press ENTER to start retry... ")

# Run the main loader - it will skip already-loaded acts
result = subprocess.run(
    [sys.executable, "bare_acts_loader.py"],
    cwd="."
)

sys.exit(result.returncode)

