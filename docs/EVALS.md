# Maintainer's Copilot Evaluation

## 1. Evaluation Overview

The project evaluates two major capabilities:

1. issue classification
2. RAG retrieval

The goal is to avoid relying only on manual demos. Golden sets and metrics help catch regressions.

## 2. Classification Evaluation

The classifier predicts one of:

```text
bug
feature
docs
question
```

Models compared:

- classical ML baseline
- fine-tuned transformer
- LLM baseline

## 3. Classification Golden Set

A 25-example classification golden set exists.

Purpose:

- stable hand-curated examples
- regression testing
- comparison across models

Metrics:

- accuracy
- macro-F1
- per-class F1
- confusion matrix

## 4. Classification Artifacts

Relevant files include:

```text
ml/artifacts/transformer_metrics_pandas.json
ml/artifacts/transformer_confusion_matrix_pandas.png
ml/model_card_pandas_transformer.json
ml/artifacts/llm_baseline_metrics_pandas.json
```

If classical metrics are present, include them in the final comparison table.

## 5. Classification Comparison Table

Fill exact values from the metrics JSON files before final submission.

| Model | Accuracy | Macro-F1 | Bug F1 | Feature F1 | Docs F1 | Question F1 | Latency | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Classical ML | TODO | TODO | TODO | TODO | TODO | TODO | TODO | low |
| Fine-tuned DistilBERT | TODO | TODO | TODO | TODO | TODO | TODO | TODO | low after training |
| LLM baseline | TODO | TODO | TODO | TODO | TODO | TODO | TODO | higher |

Deployment choice:

```text
Fine-tuned DistilBERT classifier
```

Reason:

- better production control
- lower per-request cost than an LLM baseline
- predictable latency
- trained on the target issue labels

## 6. RAG Evaluation

RAG is evaluated on a 25-example golden set.

Each example includes:

- question
- ideal answer
- ground-truth chunks

## 7. RAG Golden Set Status

Current status:

```text
total_examples = 25
mapped examples = 25
placeholders = 0
missing chunk IDs = 0
skipped_examples = 0
```

## 8. Embedding Comparison

Compared:

```text
sentence-transformers/all-MiniLM-L6-v2
BAAI/bge-small-en
```

Selected:

```text
BAAI/bge-small-en
```

## 9. Best Retrieval Configuration

```text
embedding_model = BAAI/bge-small-en
embeddings_file = rag/data/embeddings_BAAI_bge-small-en.jsonl
dense_weight = 0.8
sparse_weight = 0.2
```

## 10. Final RAG Retrieval Metrics

```text
hit@5 = 1.0000
MRR@10 ≈ 0.7307
skipped_examples = 0
```

## 11. Why hit@5 and MRR@10 Matter

### hit@5

Checks whether at least one relevant ground-truth chunk appears in the top 5 results.

### MRR@10

Measures how highly the first relevant chunk appears in the top 10.

A higher MRR means the retriever is ranking useful chunks closer to the top.

## 12. Query Transformation Evaluation

The selected query transformation is deterministic keyword expansion.

Example:

```text
csv -> read_csv, parser, DataFrame, delimiter
```

Reason:

- reproducible
- fast
- no LLM cost
- preserves technical terms

## 13. RAG Fallback

The evaluated RAG pipeline uses BGE embeddings.

The local API includes a sparse fallback if embedding dependencies are unavailable.

This fallback is not the evaluated retrieval result. It is a graceful degradation path for local integration and demo stability.

## 14. CI Goal

Final CI should run:

```bash
pytest
python evals/eval_classification.py
python evals/eval_rag.py
```

If a threshold file exists:

```text
evals/eval_thresholds.yaml
```

thresholds should be non-zero.

Suggested thresholds:

```yaml
classification:
  macro_f1_min: 0.65

rag:
  hit_at_5_min: 0.70
  mrr_at_10_min: 0.50
```

Final values should reflect the real metrics and should not be set to zero.
