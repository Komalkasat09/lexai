"""
Step 1 — Dataset creation for statutory transition classifier.
Loads positive examples from IPC→BNS and CrPC→BNSS maps; generates negative
examples from non-transition acts (NI Act, Contract Act, Evidence Act, etc.).
Output: train.csv, test.csv (80/20 split).
"""

import os
import sys
import random
import pandas as pd
from sklearn.model_selection import train_test_split

# Add backend root for retrieval import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Positive examples: import from existing smart_retriever maps
from retrieval.smart_retriever import IPC_BNS_MAP, CRPC_BNSS_MAP


# ---------------------------------------------------------------------------
# Negative acts: acts that have NOT been superseded by BNS/BNSS (as of 2024)
# Section numbers are plausible sections for each act (for realistic negatives)
# ---------------------------------------------------------------------------
NEGATIVE_ACTS = [
    ("Negotiable Instruments Act 1881", list(range(1, 150))),   # Sections 1-149
    ("Indian Contract Act 1872", list(range(1, 75)) + [76, 124, 125, 126, 127]),
    ("Indian Evidence Act 1872", list(range(1, 120)) + ["65B", "32", "27", "24"]),
    ("Companies Act 2013", list(range(1, 470))),   # sample; we'll take subset
    ("Income Tax Act 1961", list(range(1, 300))), # sample
]

# Hindi paraphrases to improve multilingual transition detection.
HINDI_IPC_TEMPLATES = [
    "धारा {sec} आईपीसी",
    "आईपीसी की धारा {sec}",
    "IPC धारा {sec}",
    "भारतीय दंड संहिता की धारा {sec}",
]

HINDI_CRPC_TEMPLATES = [
    "धारा {sec} दंड प्रक्रिया संहिता",
    "CrPC की धारा {sec}",
    "सीआरपीसी धारा {sec}",
    "Code of Criminal Procedure की धारा {sec}",
]

HINDI_NEGATIVE_ACTS = [
    ("परक्राम्य लिखत अधिनियम 1881", list(range(1, 90))),
    ("भारतीय संविदा अधिनियम 1872", list(range(1, 80))),
    ("भारतीय साक्ष्य अधिनियम", list(range(1, 90)) + ["65B"]),
    ("कंपनी अधिनियम 2013", list(range(1, 120))),
    ("आयकर अधिनियम 1961", list(range(1, 120))),
]

# Cap sections per act so we get ~200+ negatives without huge lists
MAX_SECTIONS_PER_ACT = 50


def _positive_examples():
    """Build positive samples from IPC_BNS_MAP and CRPC_BNSS_MAP."""
    samples = []
    # IPC → BNS
    for section_num, info in IPC_BNS_MAP.items():
        if info.get("bns") == "removed":
            replacement = "Removed in BNS"
        else:
            replacement = f"BNS Section {info['bns']}"
        text = f"Section {section_num} of the Indian Penal Code"
        samples.append({"text": text, "label": 1, "replacement": replacement})
        for template in HINDI_IPC_TEMPLATES:
            samples.append({
                "text": template.format(sec=section_num),
                "label": 1,
                "replacement": replacement,
            })

    # CrPC → BNSS
    for section_num, info in CRPC_BNSS_MAP.items():
        replacement = f"BNSS Section {info['bnss']}"
        text = f"Section {section_num} of the Code of Criminal Procedure"
        samples.append({"text": text, "label": 1, "replacement": replacement})
        for template in HINDI_CRPC_TEMPLATES:
            samples.append({
                "text": template.format(sec=section_num),
                "label": 1,
                "replacement": replacement,
            })
    return samples


def _negative_examples(target_count: int = 220):
    """Generate negative samples from acts that are not superseded."""
    samples = []
    for act_name, sections in NEGATIVE_ACTS:
        # Normalize section numbers to string and take up to MAX_SECTIONS_PER_ACT
        sec_list = [str(s) for s in sections][:MAX_SECTIONS_PER_ACT]
        for sec in sec_list:
            text = f"Section {sec} of the {act_name}"
            samples.append({"text": text, "label": 0, "replacement": None})

    for act_name, sections in HINDI_NEGATIVE_ACTS:
        sec_list = [str(s) for s in sections][:MAX_SECTIONS_PER_ACT]
        for sec in sec_list:
            samples.append({
                "text": f"{act_name} की धारा {sec}",
                "label": 0,
                "replacement": None,
            })
            samples.append({
                "text": f"धारा {sec} {act_name}",
                "label": 0,
                "replacement": None,
            })
    random.shuffle(samples)
    # Trim or pad to target_count
    if len(samples) >= target_count:
        return samples[:target_count]
    # If we need more, duplicate with slight variation (e.g. "Sec. X" vs "Section X")
    out = list(samples)
    while len(out) < target_count:
        s = random.choice(samples).copy()
        s["text"] = s["text"].replace("Section ", "Sec. ", 1)  # slight variation
        out.append(s)
    return out[:target_count]


def build_dataset(
    output_dir: str = None,
    train_ratio: float = 0.8,
    seed: int = 42,
    target_total: int = None,
    target_test_size: int = None,
) -> pd.DataFrame:
    """
    Build full dataset: positives from maps, negatives from other acts.
    Split 80/20 train/test (stratified), save CSVs.

    Args:
        target_total: If set, generate at least this many total examples (by adding negatives).
        target_test_size: If set, aim for this many test examples (implies target_total = target_test_size / (1 - train_ratio)).
    """
    random.seed(seed)
    output_dir = output_dir or os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(output_dir, exist_ok=True)

    positives = _positive_examples()
    n_pos = len(positives)
    if target_test_size is not None:
        target_total = max(target_total or 0, int(target_test_size / (1 - train_ratio)))
    if target_total is not None:
        n_neg = max(0, target_total - n_pos)
    else:
        n_neg = max(280, 400 - n_pos)
    negatives = _negative_examples(target_count=n_neg)

    rows = positives + negatives
    random.shuffle(rows)
    df = pd.DataFrame(rows)
    # 80/20 stratified split so train/test keep same label ratio
    train_df, test_df = train_test_split(
        df, train_size=train_ratio, random_state=seed, stratify=df["label"]
    )

    train_path = os.path.join(output_dir, "train.csv")
    test_path = os.path.join(output_dir, "test.csv")
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"[dataset_builder] Positives: {n_pos}, Negatives: {len(negatives)}, Total: {len(df)}")
    print(f"[dataset_builder] Train: {len(train_df)} -> {train_path}")
    print(f"[dataset_builder] Test: {len(test_df)} -> {test_path}")
    return df


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Build transition classifier train/test CSV (80/20 stratified).")
    p.add_argument("--target-test-size", type=int, default=None, help="Target number of test examples (e.g. 288).")
    p.add_argument("--target-total", type=int, default=None, help="Target total dataset size.")
    p.add_argument("--train-ratio", type=float, default=0.8, help="Train fraction (default 0.8).")
    p.add_argument("--seed", type=int, default=42, help="Random seed.")
    args = p.parse_args()
    build_dataset(
        train_ratio=args.train_ratio,
        seed=args.seed,
        target_total=args.target_total,
        target_test_size=args.target_test_size,
    )
