# Maintainer's Copilot Technical Decisions

## 1. Dataset Choice

Chosen repository:

```text
pandas-dev/pandas
```

Reason:

- It is a mature open-source project.
- It has many closed issues.
- It has real maintainer discussions.
- It contains technical issue reports involving functions, files, stack traces, and errors.
- Its labels can be mapped into the required project labels.

Project labels:

```text
bug
feature
docs
question
```

## 2. Label Mapping

The project maps original GitHub labels into four simplified maintainer triage labels.

Example mapping:

| Project label | GitHub label examples |
|---|---|
| `bug` | bug, regression, crash, error |
| `feature` | enhancement, feature request |
| `docs` | documentation, docs |
| `question` | question, support, usage |

The exact mapping should be kept in the dataset/preprocessing code and summarized here.

## 3. Time-Aware Split

The dataset split is time-aware.

Reason:

- Train data should be older.
- Test data should be newer.
- This better simulates real maintainer use, where the system is evaluated on future issues.

## 4. Classification Models

The project compares three approaches:

| Model type | Purpose |
|---|---|
| Classical ML | Fast baseline |
| Fine-tuned transformer | Main learned classifier |
| LLM baseline | Flexible but slower/costlier comparison |

### Classical ML

Used as a baseline to prove that the transformer adds value over a simpler approach.

### Fine-Tuned Transformer

Model:

```text
distilbert-base-uncased
```

Purpose:

- classify issue text into `bug`, `feature`, `docs`, or `question`
- provide a production-friendly model with predictable cost and latency

Deployment choice:

```text
Fine-tuned DistilBERT classifier
```

Reason:

- better production control than an LLM baseline
- lower cost than calling an LLM for every issue
- faster and easier to deploy behind the model-server contract

Final metric values should be filled from the metrics artifacts:

```text
ml/artifacts/transformer_metrics_pandas.json
ml/artifacts/classical_metrics.json
ml/artifacts/llm_baseline_metrics_pandas.json
```

## 5. LLM Baseline

The LLM baseline was used for comparison, not as the main deployed classifier.

Reason:

- good for measuring how well a general model can classify issues
- useful baseline
- not ideal for every classification request because of cost, latency, and external dependency risk

## 6. NER Tool

NER is implemented as an integration tool that extracts code-shaped entities.

Entity examples:

- function names
- file names
- error classes
- package names
- versions
- command snippets

Reason:

Issue triage often depends on quickly identifying the subsystem or error involved.

## 7. Summarization Tool

Summarization is exposed through the model server contract.

Purpose:

- condense long issue threads
- identify likely resolution/status
- list open questions for maintainers

## 8. RAG Corpus

The RAG corpus is built from:

- resolved pandas issues
- maintainer comments
- structured chunks

Reason:

The chatbot should ground answers in project-specific maintainer history instead of relying only on generic model knowledge.

## 9. Chunking Strategy

The project avoids naive fixed-size chunking.

For issues, chunks preserve issue structure:

- problem description
- maintainer answer
- resolution-style comments

Reason:

Maintainer answers and issue problem statements are semantically different and should not be blindly mixed.

## 10. Embedding Model Decision

Compared embedding models:

```text
sentence-transformers/all-MiniLM-L6-v2
BAAI/bge-small-en
```

Selected model:

```text
BAAI/bge-small-en
```

Reason:

It performed best on the project's own RAG golden set.

Final RAG retrieval results:

```text
hit@5 = 1.0000
MRR@10 ≈ 0.7307
```

## 11. Hybrid Retrieval Weight

Selected weighting:

```text
dense_weight = 0.8
sparse_weight = 0.2
```

Reason:

This gave the best retrieval quality on the RAG golden set while still preserving keyword sensitivity for technical issue terms.

## 12. Query Transformation

Technique:

```text
deterministic rule-based query expansion
```

Example:

```text
csv -> read_csv, parser, DataFrame, delimiter
```

Reason:

- fast
- cheap
- deterministic
- reproducible
- good for technical GitHub issue retrieval

## 13. RAG Fallback

The production/evaluated path is embedding-based RAG.

A local sparse fallback exists for graceful degradation when embedding dependencies are unavailable.

Reason:

- prevents chatbot failure during local integration
- keeps the tool usable
- shows graceful degradation
- does not replace the evaluated BGE retrieval path

## 14. Memory Type

Long-term memory type:

```text
semantic
```

Reason:

The assistant needs to remember reusable preferences or maintainer facts across conversations.

Example:

```text
This user prefers concise maintainer answers.
```

Memory writes are explicit only.

## 15. Redis TTL

Short-term memory TTL:

```text
1800 seconds = 30 minutes
```

Reason:

- long enough for normal pauses during a chat
- short enough to avoid retaining temporary state forever

## 16. Streamlit UI

Streamlit is used for the internal/admin UI.

Reason:

- fast to build
- good for internal tools
- supports login and chat quickly
- not intended as the production embedded surface

## 17. Widget UI

The widget is the production-shaped embedded surface.

It is loaded through:

```html
<script src="http://localhost:8000/widget.js" data-widget-id="demo-widget"></script>
```

Reason:

- host apps can embed it with one script tag
- iframe isolation avoids CSS conflicts
- postMessage supports resize behavior

## 18. CORS

Local CORS currently allows:

```text
http://localhost:5174
http://localhost:8080
http://127.0.0.1:5174
http://127.0.0.1:8080
```

Reason:

The browser widget and host app need to call the FastAPI backend during local demo.

A future production version should enforce origins from the widget configuration table.

## 19. Vault

Vault stores secrets such as:

- JWT signing key
- API keys
- service credentials

The API loads required secrets during startup and refuses to boot if required secrets are missing.

## 20. Redaction

Redaction runs before sensitive text is stored or emitted.

Reason:

Users may paste stack traces, API keys, tokens, or credentials into issue text.

## 21. Exception Handling

Domain errors are mapped at the API boundary.

Examples:

| Domain error | HTTP status |
|---|---|
| `NotFoundError` | 404 |
| `PermissionDeniedError` | 403 |
| `ValidationDomainError` | 400 |
| `ToolFailureError` | 502 |

Reason:

Users should see structured safe errors, not stack traces.
