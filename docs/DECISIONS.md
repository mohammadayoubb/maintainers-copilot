# DECISIONS.md — Classification Section

## Classification Dataset Decision

### Chosen Repository

I selected:

```text
pandas-dev/pandas
```

Repository URL:

```text
https://github.com/pandas-dev/pandas
```

The project requires closed issues from one open-source repository and classification into four labels:

```text
bug
feature
docs
question
```

I selected `pandas-dev/pandas` because it provides clean maintainer-applied labels that map directly to the required project labels:

| GitHub Label | Project Label |
|---|---|
| Bug | bug |
| Enhancement | feature |
| Docs | docs |
| Usage Question | question |

This made it more suitable than the earlier repositories I tested.

### Repositories Rejected

Before selecting Pandas, I tested several repositories:

| Repository | Reason Rejected |
|---|---|
| `fastapi/fastapi` | The mapped dataset was heavily imbalanced and the `docs` class had too few usable examples. |
| `streamlit/streamlit` | It had useful bug and feature labels, but the final mapped dataset still missed a usable docs class. |
| `langchain-ai/langchain` | The fetched issue labels did not provide enough documentation examples, and pagination also limited the number of fetched issues. |
| `microsoft/vscode` | It had strong bug, feature, and question labels, but no usable docs examples from the tested label mapping. |

The final decision was based on dataset quality, not project popularity. Since the classifier must support all four labels, I rejected repositories where one class was missing or too small.

---

## Dataset Construction

### Fetching Strategy

Instead of randomly fetching closed issues, I fetched closed issues by maintainer label group.

This helped build a balanced dataset across the four required classes.

The fetch groups were:

| Target Label | GitHub Label |
|---|---|
| bug | Bug |
| feature | Enhancement |
| docs | Docs |
| question | Usage Question |

This produced a cleaner dataset because every fetched issue already had a maintainer-applied label that mapped directly to a project class.

### Final Dataset Size

The final processed dataset contains:

```text
1178 issues
```

Class distribution:

| Label | Count |
|---|---:|
| bug | 319 |
| docs | 289 |
| question | 286 |
| feature | 284 |

This distribution is balanced enough for comparing the three classifiers.

### Split Strategy

I used a class-wise time-aware split.

Within each label, issues were sorted by creation date, then split into:

```text
70% train
15% validation
15% test
```

This preserves time ordering inside each class while also making sure that every class appears in train, validation, and test.

Split distribution:

| Split | bug | docs | feature | question |
|---|---:|---:|---:|---:|
| train | 223 | 202 | 198 | 200 |
| validation | 48 | 43 | 43 | 43 |
| test | 48 | 44 | 43 | 43 |

This avoids the failure case I saw in earlier repositories where a class disappeared from one split.

---

## Classical ML Baseline

### Model

The classical baseline used:

```text
TF-IDF + Logistic Regression
```

This model was chosen because it is simple, fast, explainable, and gives a strong traditional ML baseline before comparing against deep learning and LLM approaches.

### Results

| Metric | Value |
|---|---:|
| Validation Accuracy | 0.7288 |
| Validation Macro-F1 | 0.7299 |
| Test Accuracy | 0.6292 |
| Test Macro-F1 | 0.6287 |

The classical model performed reasonably well, especially for a lightweight baseline. However, TF-IDF features are limited because they mostly capture word and phrase patterns rather than deeper semantic meaning.

---

## Fine-Tuned Transformer

### Model

The fine-tuned transformer used:

```text
distilbert-base-uncased
```

The model was trained for four-way issue classification:

```text
bug
feature
docs
question
```

### Hyperparameters

| Hyperparameter | Value |
|---|---:|
| Epochs | 3 |
| Learning Rate | 2e-5 |
| Batch Size | 16 |
| Max Length | 256 |
| Weight Decay | 0.01 |
| Seed | 42 |

### Freeze Policy

I used no freezing.

The full DistilBERT encoder and classification head were fine-tuned.

Reason:

The dataset is balanced and domain-specific enough to let the transformer adapt to GitHub issue language. Full fine-tuning gives the model a better chance to learn the difference between bugs, feature requests, docs issues, and usage questions.

### Results

| Metric | Value |
|---|---:|
| Test Accuracy | 0.6910 |
| Test Macro-F1 | 0.6892 |
| Test Weighted-F1 | 0.6861 |

Per-class F1:

| Label | F1 |
|---|---:|
| bug | 0.5854 |
| feature | 0.8889 |
| docs | 0.6444 |
| question | 0.6383 |

The transformer outperformed the classical baseline overall. Its strongest class was `feature`, and its weakest class was `bug`.

The model card includes the architecture, labels, hyperparameters, freeze policy, dataset split, final metrics, and SHA-256 hashes for saved model artifacts.

---

## LLM Baseline

### Model

The LLM baseline used:

```text
gpt-4o-mini
```

The LLM was prompted to classify each test issue into exactly one of:

```text
bug
feature
docs
question
```

It returned JSON with a predicted label and short reason.

### Results

| Metric | Value |
|---|---:|
| Test Accuracy | 0.6292 |
| Test Macro-F1 | 0.5884 |
| Test Weighted-F1 | 0.5891 |
| Average Latency | 1.58 seconds/example |
| Estimated Total Cost | $0.0159 |

Per-class F1:

| Label | F1 |
|---|---:|
| bug | 0.5942 |
| feature | 0.8791 |
| docs | 0.6842 |
| question | 0.1961 |

The LLM baseline performed well on `feature` and reasonably on `docs`, but it performed poorly on `question`. Many usage questions were misclassified as bugs, which reduced the macro-F1 score.

---

## Three-Way Classification Comparison

| Model | Accuracy | Macro-F1 | Notes |
|---|---:|---:|---|
| TF-IDF + Logistic Regression | 0.6292 | 0.6287 | Simple and fast classical baseline |
| Fine-tuned DistilBERT | 0.6910 | 0.6892 | Best overall performance |
| GPT-4o-mini LLM Baseline | 0.6292 | 0.5884 | Low setup cost, but weak on questions |

---

## Deployment Choice

### Selected Model

I selected:

```text
Fine-tuned DistilBERT
```

### Reason

The fine-tuned transformer achieved the best macro-F1 among the three classifiers.

It also avoids per-request LLM cost and gives more predictable behavior than prompt-only classification. Compared to the classical baseline, it captures richer language patterns and performed better overall on the test set.

Deployment choice:

```text
Fine-tuned DistilBERT ships because it achieved the highest macro-F1 while avoiding the recurring cost and latency of an LLM-based classifier.
```
