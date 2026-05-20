"""Issue classification logic for the model server.

This file loads the fine-tuned DistilBERT model and uses it to classify
GitHub issues into one of four labels:

- bug
- feature
- docs
- question

The model is loaded from:

ml/artifacts/final_transformer_model_pandas/

Important architecture rule:
Only the model server loads ML artifacts directly.
The main API calls this service over HTTP instead of importing the model.
"""

from functools import lru_cache
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from model_server.schemas import ClassifyIssueRequest, ClassifyIssueResponse, IssueLabel


# Path to the extracted fine-tuned model folder.
# This folder must contain config.json, model.safetensors, tokenizer.json, etc.
MODEL_DIR = Path("ml/artifacts/final_transformer_model_pandas")

# Name shown in API responses so we know the real model is being used.
MODEL_NAME = "fine-tuned-distilbert-pandas"

# The label order must match the order used during training.
ID_TO_LABEL: dict[int, IssueLabel] = {
    0: "bug",
    1: "feature",
    2: "docs",
    3: "question",
}


def get_device() -> torch.device:
    """Return the device used for inference.

    In Docker/local CPU environments, this will usually be CPU.
    If CUDA is available, the model can use GPU automatically.
    """
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@lru_cache
def load_model_and_tokenizer() -> tuple[AutoTokenizer, AutoModelForSequenceClassification]:
    """Load and cache the fine-tuned model and tokenizer.

    The cache is important because loading the model on every request would be slow.
    With lru_cache, the model loads once per process and is reused for later requests.

    Raises:
        FileNotFoundError: If the extracted model directory does not exist.
    """
    if not MODEL_DIR.exists():
        raise FileNotFoundError(
            f"Model directory not found: {MODEL_DIR}. "
            "Extract final_transformer_model_pandas.zip into ml/artifacts/ first."
        )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)

    device = get_device()
    model.to(device)
    model.eval()

    return tokenizer, model


def build_issue_text(request: ClassifyIssueRequest) -> str:
    """Combine issue title and body into one classifier input string.

    The title gives the short issue summary.
    The body gives the detailed reproduction steps, errors, and context.
    """
    body = request.body or ""
    return f"{request.title}\n\n{body}"


def classify_issue(request: ClassifyIssueRequest) -> ClassifyIssueResponse:
    """Classify a GitHub issue using the fine-tuned DistilBERT model.

    This function is called by the /classify endpoint in model_server/main.py.
    """
    tokenizer, model = load_model_and_tokenizer()
    device = get_device()

    text = build_issue_text(request)

    inputs = tokenizer(
        text,
        truncation=True,
        padding=True,
        max_length=256,
        return_tensors="pt",
    )

    # Move tokenized input tensors to the same device as the model.
    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        probabilities = torch.softmax(outputs.logits, dim=-1)
        predicted_id = int(torch.argmax(probabilities, dim=-1).item())
        confidence = float(probabilities[0][predicted_id].item())

    label = ID_TO_LABEL[predicted_id]

    return ClassifyIssueResponse(
        label=label,
        confidence=confidence,
        model=MODEL_NAME,
    )