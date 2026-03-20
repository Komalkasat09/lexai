"""
Transition Classifier Ablation — Table III style.
Compares Rule-Based (IPC/CrPC dictionary lookup) vs Learned (MiniLM + Logistic Regression)
on the full test set. Outputs: Accuracy, Precision (macro), Recall (macro), F1 (macro),
Error cases, Inference (s). Use 80/20 stratified split; test set size reported.
"""

import os
import re
import sys
import time
import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


def _parse_section_and_act(text: str):
    """Extract section number and act type (ipc, crpc, other) from text."""
    text = (text or "").strip()
    m = re.search(r"[Ss]ection\s+(\d+[A-Z]?)", text)
    section = m.group(1) if m else None
    text_lower = text.lower()
    if "indian penal code" in text_lower or " ipc" in text_lower or text_lower.rstrip().endswith("ipc"):
        act = "ipc"
    elif "criminal procedure" in text_lower or "crpc" in text_lower or "cr.p.c" in text_lower:
        act = "crpc"
    else:
        act = "other"
    return section, act


def rule_based_predict(text: str) -> int:
    """Rule-based: 1 if section is in IPC_BNS_MAP or CRPC_BNSS_MAP, else 0."""
    from retrieval.smart_retriever import IPC_BNS_MAP, CRPC_BNSS_MAP

    section, act = _parse_section_and_act(text)
    if not section:
        return 0
    if act == "ipc" and section in IPC_BNS_MAP:
        return 1
    if act == "crpc" and section in CRPC_BNSS_MAP:
        return 1
    return 0


def run_rule_based_evaluation(test_df: pd.DataFrame) -> dict:
    """Run rule-based on test set; return metrics and inference time."""
    X_text = test_df["text"].astype(str).tolist()
    y_true = test_df["label"].values

    t0 = time.perf_counter()
    y_pred = np.array([rule_based_predict(t) for t in X_text])
    inference_s = time.perf_counter() - t0

    n_errors = int((y_true != y_pred).sum())
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "error_cases": n_errors,
        "inference_s": inference_s,
        "y_pred": y_pred,
    }


def run_learned_evaluation(test_df: pd.DataFrame, artifacts_dir: str = None) -> dict:
    """Run learned classifier on test set; return metrics and inference time."""
    from sentence_transformers import SentenceTransformer
    import joblib

    artifacts_dir = artifacts_dir or ARTIFACTS_DIR
    encoder_path = os.path.join(artifacts_dir, "encoder")
    clf_path = os.path.join(artifacts_dir, "classifier.joblib")

    if not os.path.isdir(encoder_path):
        raise FileNotFoundError(f"Run train_classifier.py first. Missing: {encoder_path}")

    X_text = test_df["text"].astype(str).tolist()
    y_true = test_df["label"].values

    encoder = SentenceTransformer(encoder_path)
    clf = joblib.load(clf_path)

    t0 = time.perf_counter()
    X_emb = encoder.encode(X_text)
    y_pred = clf.predict(X_emb)
    inference_s = time.perf_counter() - t0

    n_errors = int((y_true != y_pred).sum())
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "error_cases": n_errors,
        "inference_s": inference_s,
        "y_pred": y_pred,
    }


def _fmt(v, num_fmt=".4f"):
    if isinstance(v, float) and np.isnan(v):
        return "N/A"
    if num_fmt == ".4f":
        return f"{v:.4f}"
    if num_fmt == ".3f":
        return f"{v:.3f}"
    return str(v)


def print_ablation_table(rule_metrics: dict, learned_metrics: dict, n_test: int, n_train: int):
    """Print Table III style comparison."""
    print("\n" + "=" * 70)
    print("  TABLE III — TRANSITION CLASSIFIER ABLATION")
    print("  Rule-Based: IPC/CrPC dictionary lookup. Learned: MiniLM + Logistic Regression.")
    print(f"  Test set: {n_test} examples. 80/20 stratified split (train: {n_train}).")
    print("=" * 70)
    print(f"{'Metric':<22} {'Rule-Based':<18} {'Learned (Ours)':<18}")
    print("-" * 70)
    print(f"{'Accuracy':<22} {_fmt(rule_metrics['accuracy']):<18} {_fmt(learned_metrics['accuracy']):<18}")
    print(f"{'Precision (macro)':<22} {_fmt(rule_metrics['precision']):<18} {_fmt(learned_metrics['precision']):<18}")
    print(f"{'Recall (macro)':<22} {_fmt(rule_metrics['recall']):<18} {_fmt(learned_metrics['recall']):<18}")
    print(f"{'F1 (macro)':<22} {_fmt(rule_metrics['f1']):<18} {_fmt(learned_metrics['f1']):<18}")
    print(f"{'Error cases':<22} {rule_metrics['error_cases']:<18} {learned_metrics['error_cases']:<18}")
    print(f"{'Inference (s)':<22} {_fmt(rule_metrics['inference_s'], '.3f'):<18} {_fmt(learned_metrics['inference_s'], '.3f'):<18}")
    print("=" * 70 + "\n")


def main():
    import argparse
    p = argparse.ArgumentParser(description="Table III: Rule-Based vs Learned transition classifier ablation.")
    p.add_argument(
        "--test-csv",
        default=None,
        help="Path to test CSV with columns 'text' and 'label' (optional; default: transition_classifier/data/test.csv). Use this for a custom set (e.g. 288 queries).",
    )
    p.add_argument(
        "--train-csv",
        default=None,
        help="Path to train CSV used only for reporting train size (optional; default: transition_classifier/data/train.csv).",
    )
    args = p.parse_args()

    test_path = args.test_csv or os.path.join(DATA_DIR, "test.csv")
    train_path = args.train_csv or os.path.join(DATA_DIR, "train.csv")
    if not os.path.exists(test_path):
        raise SystemExit(
            f"Test set not found: {test_path}\n"
            "Run: python -m transition_classifier.dataset_builder [--target-test-size 288]"
        )
    test_df = pd.read_csv(test_path)
    # Support alternate column names (e.g. query_text -> text, category/label)
    if "text" not in test_df.columns and "query_text" in test_df.columns:
        test_df = test_df.rename(columns={"query_text": "text"})
    if "label" not in test_df.columns and "is_superseded" in test_df.columns:
        test_df["label"] = test_df["is_superseded"].astype(int)
    if "text" not in test_df.columns or "label" not in test_df.columns:
        raise SystemExit(f"Test CSV must have 'text' and 'label' columns. Found: {list(test_df.columns)}")

    n_test = len(test_df)
    n_train = len(pd.read_csv(train_path)) if os.path.exists(train_path) else 0

    rule_metrics = run_rule_based_evaluation(test_df)
    try:
        learned_metrics = run_learned_evaluation(test_df)
    except FileNotFoundError:
        print("Learned classifier not found. Run train_classifier.py first.")
        learned_metrics = {
            "accuracy": float("nan"), "precision": float("nan"), "recall": float("nan"), "f1": float("nan"),
            "error_cases": 0, "inference_s": 0.0,
        }

    print("\nMetrics calculated from the provided test CSV.")
    print_ablation_table(rule_metrics, learned_metrics, n_test, n_train)


if __name__ == "__main__":
    main()
