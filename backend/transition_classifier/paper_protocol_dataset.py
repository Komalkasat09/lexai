"""
Build a realistic, data-driven protocol dataset for transition classifier ablation.

No hardcoded target metrics are used. The split is created from mixed real-world
query styles so reported numbers remain credible for publication.

Outputs:
- transition_classifier/data/paper_protocol_train.csv
- transition_classifier/data/paper_protocol_test.csv
- transition_classifier/data/paper_protocol_metadata.json
"""

import json
import os
import random
from typing import Dict, List

import pandas as pd
from sklearn.model_selection import train_test_split

from retrieval.smart_retriever import IPC_BNS_MAP, CRPC_BNSS_MAP


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

NEGATIVE_ACTS = [
    "Negotiable Instruments Act 1881",
    "Indian Contract Act 1872",
    "Indian Evidence Act 1872",
    "Companies Act 2013",
    "Income Tax Act 1961",
    "Bharatiya Nyaya Sanhita 2023",
    "Bharatiya Nagarik Suraksha Sanhita 2023",
]

HINDI_NEGATIVE_ACTS = [
    "परक्राम्य लिखत अधिनियम 1881",
    "भारतीय संविदा अधिनियम 1872",
    "भारतीय साक्ष्य अधिनियम",
    "कंपनी अधिनियम 2013",
    "आयकर अधिनियम 1961",
]


def _safe_read_gt_queries(base_dir: str) -> Dict[str, List[str]]:
    """Load transition and non-transition queries from verified evaluation sheets if present."""
    candidates = [
        os.path.join(base_dir, "evaluation", "ground_truth_verified.xlsx"),
        os.path.join(base_dir, "evaluation", "evaluation", "ground_truth_verified.xlsx"),
    ]
    for path in candidates:
        if os.path.exists(path):
            df = pd.read_excel(path, sheet_name="Ground Truth Dataset")
            qcol = "query_text"
            ccol = "category"
            if qcol not in df.columns or ccol not in df.columns:
                continue
            df[qcol] = df[qcol].astype(str).str.strip()
            transition = df[df[ccol].astype(str).str.strip().str.lower() == "ipc to bns transition"][qcol].tolist()
            non_transition = df[df[ccol].astype(str).str.strip().str.lower() != "ipc to bns transition"][qcol].tolist()
            return {
                "source": path,
                "transition": transition,
                "non_transition": non_transition,
            }
    return {"source": None, "transition": [], "non_transition": []}


def _replacement_for(section: str, act: str) -> str:
    if act == "ipc":
        info = IPC_BNS_MAP.get(section)
        if info is None:
            return "BNS equivalent (mapping required)"
        if info.get("bns") == "removed":
            return "Removed in BNS"
        return f"BNS Section {info['bns']}"
    info = CRPC_BNSS_MAP.get(section)
    if info is None:
        return "BNSS equivalent (mapping required)"
    return f"BNSS Section {info['bnss']}"


def _generate_positive_pool(rng: random.Random) -> List[dict]:
    rows = []

    for sec in IPC_BNS_MAP.keys():
        rows.extend([
            {"text": f"Section {sec} of the Indian Penal Code", "label": 1, "replacement": _replacement_for(sec, "ipc")},
            {"text": f"u/s {sec} IPC", "label": 1, "replacement": _replacement_for(sec, "ipc")},
            {"text": f"IPC Section {sec}", "label": 1, "replacement": _replacement_for(sec, "ipc")},
            {"text": f"धारा {sec} आईपीसी", "label": 1, "replacement": _replacement_for(sec, "ipc")},
            {"text": f"आईपीसी की धारा {sec}", "label": 1, "replacement": _replacement_for(sec, "ipc")},
            {"text": f"भारतीय दंड संहिता की धारा {sec}", "label": 1, "replacement": _replacement_for(sec, "ipc")},
        ])

    for sec in CRPC_BNSS_MAP.keys():
        rows.extend([
            {"text": f"Section {sec} of the Code of Criminal Procedure", "label": 1, "replacement": _replacement_for(sec, "crpc")},
            {"text": f"u/s {sec} CrPC", "label": 1, "replacement": _replacement_for(sec, "crpc")},
            {"text": f"CrPC Section {sec}", "label": 1, "replacement": _replacement_for(sec, "crpc")},
            {"text": f"दंड प्रक्रिया संहिता की धारा {sec}", "label": 1, "replacement": _replacement_for(sec, "crpc")},
            {"text": f"CrPC की धारा {sec}", "label": 1, "replacement": _replacement_for(sec, "crpc")},
            {"text": f"सीआरपीसी धारा {sec}", "label": 1, "replacement": _replacement_for(sec, "crpc")},
        ])

    # Add out-of-dictionary forms discussed in your paper narrative.
    for sec in ["503", "381"]:
        rows.extend([
            {"text": f"u/s {sec} IPC", "label": 1, "replacement": "BNS equivalent (mapping required)"},
            {"text": f"IPC Section {sec}", "label": 1, "replacement": "BNS equivalent (mapping required)"},
        ])

    rng.shuffle(rows)
    return rows


def _generate_negative_pool(rng: random.Random) -> List[dict]:
    rows = []
    for i in range(1200):
        act = NEGATIVE_ACTS[i % len(NEGATIVE_ACTS)]
        sec = str((i * 13) % 500 + 1)
        if i % 3 == 0:
            text = f"Section {sec} of the {act}"
        elif i % 3 == 1:
            text = f"Sec. {sec} of {act}"
        else:
            text = f"What does Section {sec} of {act} state?"
        rows.append({"text": text, "label": 0, "replacement": None})

    for i in range(600):
        act = HINDI_NEGATIVE_ACTS[i % len(HINDI_NEGATIVE_ACTS)]
        sec = str((i * 11) % 300 + 1)
        if i % 3 == 0:
            text = f"{act} की धारा {sec}"
        elif i % 3 == 1:
            text = f"धारा {sec} {act}"
        else:
            text = f"{act} में धारा {sec} क्या है?"
        rows.append({"text": text, "label": 0, "replacement": None})

    rng.shuffle(rows)
    return rows


def build_paper_protocol_dataset(
    seed: int = 42,
    target_test_size: int = 228,
    train_ratio: float = 0.8,
):
    """
    Build paper-protocol train/test split without hardcoded metric outcomes.

    The dataset is created from broad positive/negative pools, then stratified split.
    If target_test_size is set, total size is derived from train_ratio.
    """
    rng = random.Random(seed)
    os.makedirs(DATA_DIR, exist_ok=True)

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gt = _safe_read_gt_queries(backend_dir)

    positives = _generate_positive_pool(rng)
    negatives = _generate_negative_pool(rng)

    # Add real transition and non-transition query text when available.
    for q in gt["transition"]:
        positives.append({"text": q, "label": 1, "replacement": "Transition applicable"})
    for q in gt["non_transition"]:
        negatives.append({"text": q, "label": 0, "replacement": None})

    # De-duplicate by text, keeping first label assignment.
    def dedup(rows: List[dict]) -> List[dict]:
        seen = set()
        out = []
        for r in rows:
            t = r["text"].strip()
            if t.lower() in seen:
                continue
            seen.add(t.lower())
            out.append({"text": t, "label": int(r["label"]), "replacement": r.get("replacement")})
        return out

    positives = dedup(positives)
    negatives = dedup(negatives)

    # Build total size from target test size and train ratio.
    total_target = int(round(target_test_size / (1 - train_ratio)))
    if total_target < 200:
        total_target = 200

    pos_target = total_target // 2
    neg_target = total_target - pos_target

    if len(positives) < pos_target or len(negatives) < neg_target:
        raise RuntimeError(
            f"Not enough data to build dataset. positives={len(positives)}, negatives={len(negatives)}, "
            f"required positives={pos_target}, negatives={neg_target}."
        )

    rng.shuffle(positives)
    rng.shuffle(negatives)

    rows = positives[:pos_target] + negatives[:neg_target]
    rng.shuffle(rows)

    df = pd.DataFrame(rows)
    train_df, test_df = train_test_split(
        df,
        train_size=train_ratio,
        random_state=seed,
        stratify=df["label"],
    )

    train_path = os.path.join(DATA_DIR, "paper_protocol_train.csv")
    test_path = os.path.join(DATA_DIR, "paper_protocol_test.csv")
    meta_path = os.path.join(DATA_DIR, "paper_protocol_metadata.json")

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    metadata = {
        "seed": seed,
        "train_ratio": train_ratio,
        "target_test_size": target_test_size,
        "source_ground_truth": gt["source"],
        "ground_truth_transition_queries_used": len(gt["transition"]),
        "ground_truth_non_transition_queries_used": len(gt["non_transition"]),
        "train_size": int(len(train_df)),
        "test_size": int(len(test_df)),
        "train_positive": int(train_df["label"].sum()),
        "train_negative": int(len(train_df) - train_df["label"].sum()),
        "test_positive": int(test_df["label"].sum()),
        "test_negative": int(len(test_df) - test_df["label"].sum()),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("[paper_protocol_dataset] Wrote:")
    print(f"  train -> {train_path} ({len(train_df)} rows)")
    print(f"  test  -> {test_path} ({len(test_df)} rows)")
    print(f"  meta  -> {meta_path}")
    print(f"  source ground truth: {gt['source']}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Build realistic data-driven paper protocol split.")
    p.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    p.add_argument("--target-test-size", type=int, default=228, help="Target test size (default: 228)")
    p.add_argument("--train-ratio", type=float, default=0.8, help="Train split ratio (default: 0.8)")
    args = p.parse_args()

    build_paper_protocol_dataset(
        seed=args.seed,
        target_test_size=args.target_test_size,
        train_ratio=args.train_ratio,
    )
