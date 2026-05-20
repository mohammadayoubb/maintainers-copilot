"""Classification evaluation script.

This script evaluates the issue classifier against the classification golden set.

Flow:
1. Read evals/golden/classification_golden.jsonl
2. Send each example to the main API classification endpoint
3. Compare predicted labels against expected labels
4. Calculate accuracy, macro-F1, and per-class metrics
5. Save the result to evals/eval_report.json

This is the foundation for the CI classification gate.
Later, GitHub Actions can run this script and fail if scores drop below
the thresholds in evals/eval_thresholds.yaml.
"""

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


# Golden set file containing 25 hand-curated classification examples.
GOLDEN_PATH = Path("evals/golden/classification_golden.jsonl")

# Eval report output path.
REPORT_PATH = Path("evals/eval_report.json")

# The main API endpoint that wraps the model-server classifier.
CLASSIFICATION_API_URL = os.getenv(
    "CLASSIFICATION_API_URL",
    "http://localhost:8000/classification/classify",
)

LABELS = ["bug", "feature", "docs", "question"]


def load_golden_examples(path: Path) -> list[dict[str, Any]]:
    """Load classification golden examples from a JSONL file.

    Each line must contain:
    - id
    - title
    - body
    - expected_label
    """
    examples: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                examples.append(json.loads(line))

    return examples


def call_classifier(title: str, body: str | None) -> dict[str, Any]:
    """Call the main API classifier endpoint.

    Args:
        title: Issue title.
        body: Issue body.

    Returns:
        Parsed JSON response containing label, confidence, and model.

    Raises:
        RuntimeError: If the API cannot be reached or returns an error.
    """
    payload = {
        "title": title,
        "body": body,
    }

    request_body = json.dumps(payload).encode("utf-8")

    request = urllib_request.Request(
        url=CLASSIFICATION_API_URL,
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=20) as response:
            response_body = response.read().decode("utf-8")
            return dict(json.loads(response_body))

    except HTTPError as exc:
        raise RuntimeError(
            f"Classifier API returned HTTP {exc.code}: {exc.read().decode('utf-8')}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"Classifier API is unreachable at {CLASSIFICATION_API_URL}."
        ) from exc


def safe_divide(numerator: float, denominator: float) -> float:
    """Divide safely and return 0 when denominator is 0."""
    if denominator == 0:
        return 0.0

    return numerator / denominator


def calculate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate accuracy and per-class precision/recall/F1.

    This avoids needing sklearn inside the eval script.
    """
    total = len(rows)
    correct = sum(1 for row in rows if row["correct"])

    per_class: dict[str, dict[str, float]] = {}

    for label in LABELS:
        true_positive = sum(
            1 for row in rows if row["expected_label"] == label and row["predicted_label"] == label
        )
        false_positive = sum(
            1 for row in rows if row["expected_label"] != label and row["predicted_label"] == label
        )
        false_negative = sum(
            1 for row in rows if row["expected_label"] == label and row["predicted_label"] != label
        )
        support = sum(1 for row in rows if row["expected_label"] == label)

        precision = safe_divide(true_positive, true_positive + false_positive)
        recall = safe_divide(true_positive, true_positive + false_negative)
        f1 = safe_divide(2 * precision * recall, precision + recall)

        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }

    macro_f1 = sum(per_class[label]["f1"] for label in LABELS) / len(LABELS)

    return {
        "accuracy": safe_divide(correct, total),
        "macro_f1": macro_f1,
        "total_examples": total,
        "correct_examples": correct,
        "per_class": per_class,
    }


def run_eval() -> dict[str, Any]:
    """Run the classification evaluation and return the report."""
    examples = load_golden_examples(GOLDEN_PATH)
    rows: list[dict[str, Any]] = []
    prediction_counts: dict[str, int] = defaultdict(int)

    for example in examples:
        response = call_classifier(
            title=str(example["title"]),
            body=example.get("body"),
        )

        predicted_label = str(response["label"])
        expected_label = str(example["expected_label"])

        prediction_counts[predicted_label] += 1

        rows.append(
            {
                "id": example["id"],
                "title": example["title"],
                "expected_label": expected_label,
                "predicted_label": predicted_label,
                "confidence": response.get("confidence"),
                "model": response.get("model"),
                "correct": predicted_label == expected_label,
            }
        )

    metrics = calculate_metrics(rows)

    return {
        "task": "classification",
        "classifier_endpoint": CLASSIFICATION_API_URL,
        "metrics": metrics,
        "prediction_counts": dict(prediction_counts),
        "examples": rows,
    }


def main() -> None:
    """Run eval and write eval_report.json."""
    report = run_eval()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("Classification eval complete.")
    print(f"Accuracy: {report['metrics']['accuracy']:.4f}")
    print(f"Macro-F1: {report['metrics']['macro_f1']:.4f}")
    print(f"Report written to: {REPORT_PATH}")


if __name__ == "__main__":
    main()