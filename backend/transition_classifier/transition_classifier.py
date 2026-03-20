"""
TransitionClassifier: predicts whether a section reference is superseded (IPC→BNS,
CrPC→BNSS) and returns replacement via nearest-neighbor over positive examples.
"""

import os
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import joblib

# Default artifact paths (relative to this package)
DEFAULT_ARTIFACTS = os.path.join(os.path.dirname(__file__), "artifacts")


class TransitionClassifier:
    """
    Binary classifier for statutory transition: is this section reference
    superseded by BNS/BNSS? If yes, predict replacement via NN over positives.
    """

    def __init__(self, model_path: str = None):
        """
        Load encoder, logistic classifier, and positive-examples list.
        model_path: directory containing encoder/, classifier.joblib, positive_examples.pkl.
        If None, uses DEFAULT_ARTIFACTS (run train_classifier.py first).
        """
        self.artifacts_dir = model_path or DEFAULT_ARTIFACTS
        encoder_path = os.path.join(self.artifacts_dir, "encoder")
        clf_path = os.path.join(self.artifacts_dir, "classifier.joblib")
        pos_path = os.path.join(self.artifacts_dir, "positive_examples.pkl")

        if not os.path.isdir(encoder_path):
            raise FileNotFoundError(
                f"Encoder not found at {encoder_path}. Run train_classifier.py first."
            )
        self.encoder = SentenceTransformer(encoder_path)
        self.clf = joblib.load(clf_path)
        with open(pos_path, "rb") as f:
            self.positive_examples = pickle.load(f)  # list of {"text", "replacement"}
        self._pos_texts = [ex["text"] for ex in self.positive_examples]
        self._pos_embeddings = None  # lazy

    def _get_pos_embeddings(self):
        if self._pos_embeddings is None:
            self._pos_embeddings = self.encoder.encode(self._pos_texts)
        return self._pos_embeddings

    def predict(self, text: str) -> dict:
        """
        Predict whether the section reference is superseded and (if so) replacement.
        Returns:
            {"is_superseded": bool, "replacement": str or None}
        """
        text = str(text).strip()
        emb = self.encoder.encode([text])
        is_superseded = bool(self.clf.predict(emb)[0])
        replacement = None
        if is_superseded:
            pos_emb = self._get_pos_embeddings()
            sims = cosine_similarity(emb, pos_emb)[0]
            idx = int(np.argmax(sims))
            replacement = self.positive_examples[idx]["replacement"]
        return {"is_superseded": is_superseded, "replacement": replacement}
