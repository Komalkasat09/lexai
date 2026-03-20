# Learned Statutory Transition Classifier

Binary classifier: given a section reference string (e.g. "Section 302 of the Indian Penal Code"), predicts whether it has been **superseded** by BNS/BNSS and returns the replacement (e.g. "BNS Section 103").

- **Embedding:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Classifier:** `sklearn.linear_model.LogisticRegression` (no neural fine-tuning)

## File structure

| File | Purpose |
|------|--------|
| `dataset_builder.py` | Build train/test from IPC/CrPC maps + negative acts; 80/20 split → `data/train.csv`, `data/test.csv` |
| `train_classifier.py` | Encode with MiniLM, train LR, save artifacts to `artifacts/` |
| `transition_classifier.py` | `TransitionClassifier` class: `predict(text)` → `{is_superseded, replacement}`; NN for replacement |
| `evaluation.py` | Confusion matrix + classification report |
| `smart_retriever_patch.py` | BEFORE/AFTER snippet for integrating classifier into `retrieval/smart_retriever.py` |
| `experiment_runner.py` | OLR ablation: `run_experiment(use_hardcoded=True)` vs `use_learned=True` (synthetic or retrieval) |
| `ablation_table.py` | **Table III** ablation: Rule-Based vs Learned on full test set — Accuracy, Precision, Recall, F1, Error cases, Inference (s) |
| `latex_and_contribution.md` | LaTeX table (Table 2) + short technical contribution explanation |

## Usage (from `backend/`)

```bash
cd backend

# 1. Build dataset (requires retrieval.smart_retriever maps)
python -m transition_classifier.dataset_builder
# For ~288 test examples (e.g. to match another evaluation size):
python -m transition_classifier.dataset_builder --target-test-size 288

# 2. Train and save artifacts
python -m transition_classifier.train_classifier

# 3. Print confusion matrix and report
python -m transition_classifier.evaluation

# 4. (Optional) Run OLR ablation (3-query synthetic or retrieval)
python -m transition_classifier.experiment_runner

# 5. Print Table III — Rule-Based vs Learned on full test set (Accuracy, P, R, F1, Errors, Inference s)
python -m transition_classifier.ablation_table
# With a custom test CSV (e.g. your 288-query set with columns text, label):
python -m transition_classifier.ablation_table --test-csv /path/to/your_288_test.csv

# 6. Build realistic paper-protocol benchmark (fully data-driven)
python -m transition_classifier.paper_protocol_dataset

# 7. Train on paper protocol split
python -m transition_classifier.train_classifier \
	--train-csv transition_classifier/data/paper_protocol_train.csv \
	--test-csv transition_classifier/data/paper_protocol_test.csv

# 8. Evaluate computed metrics on paper protocol test set
python -m transition_classifier.ablation_table \
	--train-csv transition_classifier/data/paper_protocol_train.csv \
	--test-csv transition_classifier/data/paper_protocol_test.csv
```

## Dependencies

- `sentence-transformers`, `scikit-learn`, `pandas`, `joblib` (see `backend/requirements.txt`).
