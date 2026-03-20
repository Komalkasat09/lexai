# Table 2 — Transition Classifier Performance (LaTeX)

```latex
\begin{table}[t]
\centering
\caption{Transition classifier performance on held-out test set. Binary classification: section reference superseded (IPC$\rightarrow$BNS, CrPC$\rightarrow$BNSS) or not. Embedding: \texttt{paraphrase-multilingual-MiniLM-L12-v2}; classifier: Logistic Regression.}
\label{tab:transition-classifier}
\begin{tabular}{lcccc}
\toprule
\textbf{Metric} & \textbf{Precision} & \textbf{Recall} & \textbf{F1} & \textbf{Accuracy} \\
\midrule
Superseded (positive) & $P$ & $R$ & $F_1$ & --- \\
Macro / Binary       & $P$ & $R$ & $F_1$ & $A$ \\
\bottomrule
\end{tabular}
\end{table}
```

**Usage:** Replace $P$, $R$, $F_1$, $A$ with the values printed by `train_classifier.py` or `evaluation.run_evaluation()` (e.g. after running the pipeline, copy precision, recall, F1, accuracy into the table). Requires `booktabs`: `\usepackage{booktabs}`.

---

## Example filled table (placeholder values)

```latex
\begin{table}[t]
\centering
\caption{Transition classifier performance (test set).}
\label{tab:transition-classifier}
\begin{tabular}{lcccc}
\toprule
& Precision & Recall & F1 & Accuracy \\
\midrule
Transition classifier (MiniLM + LR) & 0.92 & 0.88 & 0.90 & 0.91 \\
\bottomrule
\end{tabular}
\end{table}
```

---

# Table III — Transition Classifier Ablation (LaTeX)

Fill with output from `python -m transition_classifier.ablation_table` (run after `train_classifier.py`).

```latex
\begin{table}[t]
\centering
\caption{Transition classifier ablation. Rule-based uses manually curated IPC-to-BNS dictionary. Learned uses MiniLM + Logistic Regression. Test set: $N$ examples, 80/20 stratified split.}
\label{tab:transition-ablation}
\begin{tabular}{lcc}
\toprule
\textbf{Metric} & \textbf{Rule-Based} & \textbf{Learned (Ours)} \\
\midrule
Accuracy & $A_{\mathrm{rule}}$ & $A_{\mathrm{learned}}$ \\
Precision (macro) & $P_{\mathrm{rule}}$ & $P_{\mathrm{learned}}$ \\
Recall (macro) & $R_{\mathrm{rule}}$ & $R_{\mathrm{learned}}$ \\
F1 (macro) & $F_{\mathrm{rule}}$ & $F_{\mathrm{learned}}$ \\
Error cases & $E_{\mathrm{rule}}$ & $E_{\mathrm{learned}}$ \\
Inference (s) & $t_{\mathrm{rule}}$ & $t_{\mathrm{learned}}$ \\
\bottomrule
\end{tabular}
\end{table}
```

---

# Why This Is a Genuine Technical Contribution

1. **Generalization beyond hardcoded maps**  
   The current RAG system relies on exact key lookup in `IPC_BNS_MAP` and `CRPC_BNSS_MAP`. Any new act (e.g. future recodifications) or paraphrased section reference (“Sec. 302 IPC”, “Section 302 of the Indian Penal Code”) requires manual map updates or brittle regex. A learned classifier operates on the *text* of the section reference, so it can generalize to unseen phrasings and, with additional training data, to new statutes without changing code.

2. **Lightweight and reproducible**  
   Using only a fixed sentence-transformers encoder and a linear classifier (no neural fine-tuning) keeps the system small, fast to train, and easy to reproduce. No GPU is required for training or inference, which is important for legal tech adoption and auditing.

3. **Enables controlled ablation**  
   Replacing the hardcoded path with a single call to `TransitionClassifier.predict()` makes it possible to run **OLR ablation** (e.g. `run_experiment(use_hardcoded=True)` vs `use_learned=True`) and report whether the learned component actually reduces outdated law citations in end-to-end evaluation. That supports a research narrative: “we replace a hand-maintained map with a learned component and show its effect on OLR.”

4. **Nearest-neighbor replacement**  
   When the classifier predicts “superseded”, the replacement string is obtained by nearest-neighbor search over positive (text, replacement) pairs in embedding space. So the system can suggest a replacement even for section references that are not in the original map (e.g. minor IPC sections not explicitly listed), improving coverage while staying interpretable.

5. **Extensibility to new acts**  
   The same pipeline (dataset from act→replacement lists, train LR on embeddings, NN for replacement) can be reused when new transition tables are introduced (e.g. another act replaced by a new code). The contribution is therefore a **reusable design** for statutory transition awareness in legal RAG, not only a one-off IPC/CrPC patch.
