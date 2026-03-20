"""
Learned statutory transition classifier.
Binary classifier: section reference superseded (IPC→BNS, CrPC→BNSS) or not.
Uses sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 + sklearn LogisticRegression.
"""

from .transition_classifier import TransitionClassifier

__all__ = ["TransitionClassifier"]
