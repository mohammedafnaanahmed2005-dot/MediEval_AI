from collections import Counter
from typing import Any

import numpy as np
import pandas as pd

from .validation import _find_column, _issue

LABEL_ALIASES = {
    "normal": "within_range",
    "normal_range": "within_range",
    "within_normal_range": "within_range",
    "within_normal_limits": "within_range",
    "within range": "within_range",
    "within_range": "within_range",
    "high": "above_range",
    "above": "above_range",
    "elevated": "above_range",
    "above_reference": "above_range",
    "above range": "above_range",
    "above_range": "above_range",
    "low": "below_range",
    "below": "below_range",
    "below_reference": "below_range",
    "below range": "below_range",
    "below_range": "below_range",
    "unknown": "insufficient_information",
    "insufficient information": "insufficient_information",
    "insufficient_information": "insufficient_information",
}
UNSUPPORTED_TERMS = (
    "diagnosed with",
    "diagnosis of",
    "prescribe",
    "prescription",
    "cancer",
    "diabetes",
    "heart disease",
    "infection",
)


def evaluate_dataset(
    frame: pd.DataFrame,
    ai_label_column: str | None = None,
    reference_answer_column: str | None = None,
) -> dict[str, Any]:
    value_column = _find_column(frame, ("value", "result", "measurement"))
    low_column = _find_column(frame, ("reference_low", "ref_low", "range_low", "low"))
    high_column = _find_column(frame, ("reference_high", "ref_high", "range_high", "high"))
    ai_column = (
        _find_evaluation_column(frame, "ai")
        if ai_label_column is None
        else _select_column(frame, ai_label_column)
    )
    reference_column = (
        _find_evaluation_column(frame, "reference")
        if reference_answer_column is None
        else _select_column(frame, reference_answer_column)
    )

    predictions: list[str] = []
    references: list[str] = []
    output_rows: list[dict[str, Any]] = []
    unsupported_count = 0
    verified_count = 0
    not_verified_count = 0
    unscored_count = 0
    claim_column = _find_column(frame, ("ai_interpretation", "model_output", "ai_claim"))

    for index, row in frame.iterrows():
        provided_prediction = _normalize_label(row[ai_column]) if ai_column is not None else None
        reference = _normalize_label(row[reference_column]) if reference_column is not None else None
        supported, explanation = _supported_statement(row, value_column, low_column, high_column)
        data_label = _data_label(row, value_column, low_column, high_column)
        prediction = provided_prediction or data_label or "insufficient_information"
        verified = None
        if provided_prediction is not None and reference is not None:
            verified = provided_prediction == reference
            if verified:
                verified_count += 1
            else:
                not_verified_count += 1
        else:
            unscored_count += 1
        claim = str(row[claim_column]).strip() if claim_column is not None and pd.notna(row[claim_column]) else ""
        unsupported = bool(
            (claim and not _claim_supported(claim, data_label))
            or (provided_prediction is not None and data_label is not None and provided_prediction != data_label)
        )
        unsupported_count += int(unsupported)
        if provided_prediction is not None and reference is not None:
            predictions.append(provided_prediction)
            references.append(reference)
        output_rows.append(
            {
                "record_number": int(index) + 1,
                "prediction": prediction,
                "reference": reference,
                "verified": verified,
                "explanation": explanation,
                "supported": supported and not unsupported,
                "unsupported_claim": unsupported,
                "human_review_required": prediction in {"above_range", "below_range"} or unsupported,
            }
        )

    metrics = _metrics(predictions, references, unsupported_count, len(frame))
    comparison = _comparison_counts(predictions, references)
    issues = []
    if unsupported_count:
        issues.append(
            _issue(
                "unsupported_claims",
                "ai_safety",
                "high",
                f"{unsupported_count} AI claim(s) could not be supported by the supplied fields or use diagnostic language.",
                {"unsupported_claims": unsupported_count},
            )
        )
    return {
        "metrics": metrics,
        "unsupported_count": unsupported_count,
        "evaluated_record_count": len(frame),
        "has_reference_answers": bool(predictions and references),
        "column_mapping": {
            "ai_label": str(ai_column) if ai_column is not None else None,
            "reference_answer": str(reference_column) if reference_column is not None else None,
        },
        "verification_summary": {
            "verified": verified_count,
            "not_verified": not_verified_count,
            "unscored": unscored_count,
            "scored": verified_count + not_verified_count,
        },
        "comparison": comparison,
        "record_findings": output_rows,
        "issues": issues,
        "methodology": (
            "Deterministic, data-only rule checks. Classification metrics are computed only when structured AI labels and verified reference answers "
            "are present. Overall score weights accuracy (50%), macro precision (20%), macro recall (20%), and the inverse "
            "hallucination rate (10%). A result outside a supplied range is a review flag, not a diagnosis."
        ),
    }


def _normalize_column_name(column: Any) -> str:
    return "".join(character.lower() if character.isalnum() else "_" for character in str(column).lstrip("\ufeff")).strip("_")


def _select_column(frame: pd.DataFrame, requested: str) -> Any | None:
    if not requested:
        return None
    return next((column for column in frame.columns if str(column) == requested), None)


def _find_evaluation_column(frame: pd.DataFrame, role: str) -> Any | None:
    aliases = {
        "ai": (
            "ai_result", "ai_prediction", "ai_label", "prediction", "predicted_label",
            "predicted_result", "model_label", "model_prediction", "ai_output",
            "ai_answer", "ai_interpretation", "ai_generated_answer", "generated_answer",
            "generated_output", "model_answer", "prediction_result", "prediction_output",
        ),
        "reference": (
            "reference_answer", "verified_answer", "ground_truth", "expected_result",
            "expected_answer", "correct_answer", "reference_label", "actual_label",
            "ground_truth_label", "gold_label", "expected_output", "reference_output",
            "reference_result", "ground_truth_answer", "gold_standard", "actual_answer",
            "expected", "reference", "actual", "label",
        ),
    }[role]
    normalized_columns = {column: _normalize_column_name(column) for column in frame.columns}
    for alias in aliases:
        for column, normalized in normalized_columns.items():
            if normalized == alias:
                return column

    if role == "ai":
        indicators = ("ai", "model", "generated", "predicted")
        outputs = ("prediction", "label", "result", "output", "answer", "interpretation")
    else:
        indicators = ("reference", "ground_truth", "truth", "expected", "correct", "gold", "actual", "verified")
        outputs = ("answer", "label", "result", "output", "prediction", "value")
    candidates = [
        column
        for column, normalized in normalized_columns.items()
        if any(indicator in normalized for indicator in indicators)
        and any(output in normalized for output in outputs)
        and not any(excluded in normalized for excluded in ("range", "low", "high", "unit"))
    ]
    return candidates[0] if len(candidates) == 1 else None


def _supported_statement(
    row: pd.Series,
    value_column: Any | None,
    low_column: Any | None,
    high_column: Any | None,
) -> tuple[bool, str]:
    if value_column is None or low_column is None or high_column is None:
        return False, "Insufficient supplied values or reference bounds for a supported range comparison."
    value = _number(row[value_column])
    low = _number(row[low_column])
    high = _number(row[high_column])
    if value is None or low is None or high is None or low > high:
        return False, "Insufficient supplied values or valid reference bounds for a supported range comparison."
    status = "above" if value > high else "below" if value < low else "within"
    return True, f"Supplied value is {status} the supplied reference range ({low:g}–{high:g}). Human review is required for out-of-range values."


def _data_label(
    row: pd.Series,
    value_column: Any | None,
    low_column: Any | None,
    high_column: Any | None,
) -> str | None:
    if value_column is None or low_column is None or high_column is None:
        return None
    value = _number(row[value_column])
    low = _number(row[low_column])
    high = _number(row[high_column])
    if value is None or low is None or high is None or low > high:
        return None
    return "above_range" if value > high else "below_range" if value < low else "within_range"


def _claim_supported(claim: str, data_label: str | None) -> bool:
    normalized = claim.lower()
    if any(term in normalized for term in UNSUPPORTED_TERMS):
        return False
    if data_label is None:
        return any(term in normalized for term in ("insufficient information", "cannot determine", "not provided"))
    claim_label = None
    if any(term in normalized for term in ("above", "elevated", "high", "exceeds")):
        claim_label = "above_range"
    elif any(term in normalized for term in ("below", "low", "less than")):
        claim_label = "below_range"
    elif any(term in normalized for term in ("within", "normal range", "in range")):
        claim_label = "within_range"
    return claim_label == data_label


def _normalize_label(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    normalized_key = "".join(character if character.isalnum() else "_" for character in normalized).strip("_")
    known = LABEL_ALIASES.get(normalized_key) or LABEL_ALIASES.get(normalized)
    if known is not None:
        return known

    positive = normalized.replace("-", " ")
    if any(term in positive for term in ("insufficient information", "cannot determine", "unable to assess")):
        return "insufficient_information"
    if "not above" not in positive and (
        any(term in positive for term in ("above range", "above the range", "elevated", "high", "exceeds range"))
        or ("above" in positive and "range" in positive)
    ):
        return "above_range"
    if "not below" not in positive and (
        any(term in positive for term in ("below range", "below the range", "low", "decreased"))
        or ("below" in positive and "range" in positive)
    ):
        return "below_range"
    if any(term in positive for term in ("within range", "within the range", "normal", "in range")) or (
        "within" in positive and "range" in positive
    ):
        return "within_range"
    return normalized_key


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _metrics(predictions: list[str], references: list[str], unsupported_count: int, total: int) -> dict[str, Any]:
    if not references:
        return {
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "hallucination_rate": unsupported_count / total if total else 0,
            "overall_score": None,
        }
    labels = sorted(set(references) | set(predictions))
    correct = sum(predicted == actual for predicted, actual in zip(predictions, references))
    per_label = []
    for label in labels:
        true_positive = sum(p == label and a == label for p, a in zip(predictions, references))
        false_positive = sum(p == label and a != label for p, a in zip(predictions, references))
        false_negative = sum(p != label and a == label for p, a in zip(predictions, references))
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
        per_label.append((precision, recall))
    precision = float(np.mean([item[0] for item in per_label]))
    recall = float(np.mean([item[1] for item in per_label]))
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    accuracy = correct / len(references)
    hallucination_rate = unsupported_count / total if total else 0
    score = max(0, min(100, 100 * (0.5 * accuracy + 0.2 * precision + 0.2 * recall + 0.1 * (1 - hallucination_rate))))
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "overall_score": round(score, 2),
    }


def _comparison_counts(predictions: list[str], references: list[str]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter(zip(references, predictions))
    return [
        {"reference": reference, "prediction": prediction, "count": count}
        for (reference, prediction), count in sorted(counts.items())
    ]
