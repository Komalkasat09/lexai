"""
Step 3 & 4 — Confusion matrix and classification report for transition classifier.
Formatted print and sklearn.metrics.
"""

import os
import sys
import pandas as pd
import numpy as np
from sklearn.metrics import (
    confusion_matrix,
    classification_report,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_confusion_matrix_and_report(y_true, y_pred, labels=(0, 1)):
    """
    Print confusion matrix as formatted table and sklearn classification report.
    labels: (negative_label, positive_label) e.g. (0, 1).
    """
    cm = confusion_matrix(y_true, y_pred, labels=list(labels))
    # Header
    print("\n--- Confusion Matrix ---")
    print(f"              Predicted")
    print(f"              {labels[0]}    {labels[1]}")
    print(f"Actual {labels[0]}  {cm[0,0]:4d}  {cm[0,1]:4d}")
    print(f"Actual {labels[1]}  {cm[1,0]:4d}  {cm[1,1]:4d}")
    print("------------------------\n")

    print("--- Classification Report ---")
    print(classification_report(y_true, y_pred, target_names=["Not superseded", "Superseded"], digits=4))
    print("-----------------------------\n")


def run_evaluation(
    test_csv_path: str = None,
    artifacts_dir: str = None,
):
    """
    Load test set and trained classifier, run predictions, print confusion matrix
    and classification report. Optionally return metrics dict for LaTeX/experiments.
    """
    from sentence_transformers import SentenceTransformer
    import joblib

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    artifacts_dir = artifacts_dir or os.path.join(os.path.dirname(__file__), "artifacts")
    test_csv_path = test_csv_path or os.path.join(data_dir, "test.csv")

    if not os.path.exists(test_csv_path):
        raise FileNotFoundError(f"Test set not found: {test_csv_path}. Run dataset_builder.py first.")
    if not os.path.isdir(artifacts_dir):
        raise FileNotFoundError(f"Artifacts not found: {artifacts_dir}. Run train_classifier.py first.")

    test_df = pd.read_csv(test_csv_path)
    X_text = test_df["text"].astype(str).tolist()
    y_true = test_df["label"].values

    encoder = SentenceTransformer(os.path.join(artifacts_dir, "encoder"))
    clf = joblib.load(os.path.join(artifacts_dir, "classifier.joblib"))
    X_emb = encoder.encode(X_text)
    y_pred = clf.predict(X_emb)

    print_confusion_matrix_and_report(y_true, y_pred)

    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    return metrics


if __name__ == "__main__":
    run_evaluation()
