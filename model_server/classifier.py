"""Issue classification logic for the model server.

This file owns the classifier implementation used by the /classify endpoint.

For the foundation version, this uses a small rule-based placeholder so the
endpoint can work immediately.

Later, this file should load the selected deployment model:
- fine-tuned DistilBERT
- saved tokenizer
- saved label mapping
- model card / SHA-256 validation

The rest of the system should not care how classification is implemented.
It only needs a stable function that returns label, confidence, and model name.
"""

from model_server.schemas import ClassifyIssueRequest, ClassifyIssueResponse, IssueLabel


MODEL_NAME = "rule-based-placeholder"


def build_issue_text(request: ClassifyIssueRequest) -> str:
    """Combine issue title and body into one text string.

    The classifier usually needs both title and body because:
    - the title gives a short summary
    - the body gives reproduction details, errors, logs, and context
    """
    body = request.body or ""
    return f"{request.title}\n\n{body}".lower()


def classify_issue(request: ClassifyIssueRequest) -> ClassifyIssueResponse:
    """Classify a GitHub issue into bug, feature, docs, or question.

    This temporary version uses keyword rules.

    Later replacement:
    This function should call the fine-tuned DistilBERT model and return
    its predicted label and confidence.
    """
    text = build_issue_text(request)

    label: IssueLabel
    confidence: float

    if any(keyword in text for keyword in ["error", "bug", "crash", "fail", "traceback"]):
        label = "bug"
        confidence = 0.70

    elif any(keyword in text for keyword in ["feature", "enhancement", "support for", "add"]):
        label = "feature"
        confidence = 0.65

    elif any(keyword in text for keyword in ["docs", "documentation", "readme", "typo"]):
        label = "docs"
        confidence = 0.65

    elif any(keyword in text for keyword in ["how do i", "question", "usage", "can i", "is it possible"]):
        label = "question"
        confidence = 0.65

    else:
        # Default fallback when the placeholder has no strong signal.
        label = "question"
        confidence = 0.40

    return ClassifyIssueResponse(
        label=label,
        confidence=confidence,
        model=MODEL_NAME,
    )