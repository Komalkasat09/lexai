"""
Step 2 — Fine-tune (train) statutory transition classifier.
Uses sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 for embeddings and
sklearn.linear_model.LogisticRegression for binary classification.
Computes accuracy, precision, recall, F1 on test set.
"""

import os
import sys
import pickle
import joblib
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Backend root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Default paths
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


def load_data(train_csv: str = None, test_csv: str = None):
    """Load train and test CSVs from data/."""
    train_path = train_csv or os.path.join(DATA_DIR, "train.csv")
    test_path = test_csv or os.path.join(DATA_DIR, "test.csv")
    if not os.path.exists(train_path) or not os.path.exists(test_path):
        raise FileNotFoundError(
            "Run dataset_builder.py first to create train.csv and test.csv in data/"
        )
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    return train_df, test_df


def train(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    model_name: str = MODEL_NAME,
    save_dir: str = ARTIFACTS_DIR,
):
    """
    Encode texts with MiniLM, train LogisticRegression, evaluate on test set.
    Saves: encoder (SentenceTransformer), classifier (LogisticRegression), and
    positive examples for later NN replacement lookup.
    """
    os.makedirs(save_dir, exist_ok=True)

    X_train_text = train_df["text"].astype(str).tolist()
    y_train = train_df["label"].values
    X_test_text = test_df["text"].astype(str).tolist()
    y_test = test_df["label"].values

    print(f"[train_classifier] Loading encoder: {model_name}")
    encoder = SentenceTransformer(model_name)

    print("[train_classifier] Encoding training set...")
    X_train = encoder.encode(X_train_text, show_progress_bar=True)
    print("[train_classifier] Encoding test set...")
    X_test = encoder.encode(X_test_text, show_progress_bar=True)

    print("[train_classifier] Training LogisticRegression...")
    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    print("\n--- Transition Classifier Test Set Results ---")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1:        {f1:.4f}")
    print("---------------------------------------------\n")

    # Save artifacts for TransitionClassifier
    encoder_path = os.path.join(save_dir, "encoder")
    encoder.save(encoder_path)
    clf_path = os.path.join(save_dir, "classifier.joblib")
    joblib.dump(clf, clf_path)
    # Positive examples (text, replacement) for NN replacement
    pos = train_df[train_df["label"] == 1][["text", "replacement"]].dropna()
    pos_path = os.path.join(save_dir, "positive_examples.pkl")
    with open(pos_path, "wb") as f:
        pickle.dump(pos.to_dict("records"), f)

    print(f"[train_classifier] Saved encoder -> {encoder_path}")
    print(f"[train_classifier] Saved classifier -> {clf_path}")
    print(f"[train_classifier] Saved positive examples -> {pos_path}")

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "y_test": y_test,
        "y_pred": y_pred,
    }


if __name__ == "__main__":
    import argparse

    from .dataset_builder import build_dataset

    p = argparse.ArgumentParser(description="Train transition classifier (MiniLM + Logistic Regression).")
    p.add_argument("--train-csv", default=None, help="Path to training CSV (default: transition_classifier/data/train.csv)")
    p.add_argument("--test-csv", default=None, help="Path to test CSV (default: transition_classifier/data/test.csv)")
    p.add_argument("--artifacts-dir", default=ARTIFACTS_DIR, help="Output artifact directory (default: transition_classifier/artifacts)")
    p.add_argument("--model-name", default=MODEL_NAME, help="SentenceTransformer model name/path")
    args = p.parse_args()

    # Ensure default data exists only when default paths are used.
    if args.train_csv is None and args.test_csv is None:
        if not os.path.exists(os.path.join(DATA_DIR, "train.csv")):
            build_dataset()

    train_df, test_df = load_data(train_csv=args.train_csv, test_csv=args.test_csv)
    train(train_df, test_df, model_name=args.model_name, save_dir=args.artifacts_dir)
