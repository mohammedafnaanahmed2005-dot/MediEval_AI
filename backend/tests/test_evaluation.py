import pandas as pd
import pytest

from app.evaluation import evaluate_dataset


def test_metrics_compare_predictions_to_verified_answers():
    frame = pd.DataFrame(
        {
            "value": [120, 80, 60],
            "reference_low": [70, 70, 70],
            "reference_high": [100, 100, 100],
            "ai_result": ["above_range", "within_range", "below_range"],
            "reference_answer": ["above_range", "within_range", "within_range"],
        }
    )

    result = evaluate_dataset(frame)

    assert result["has_reference_answers"]
    assert result["metrics"]["accuracy"] == pytest.approx(0.6667)
    assert result["verification_summary"] == {
        "verified": 2,
        "not_verified": 1,
        "unscored": 0,
        "scored": 3,
    }
    assert [row["verified"] for row in result["record_findings"]] == [True, True, False]
    assert result["unsupported_count"] == 0
    assert "not a diagnosis" in result["methodology"]


def test_claim_without_evidence_is_flagged_and_no_reference_means_no_accuracy():
    frame = pd.DataFrame({"ai_interpretation": ["Patient has diabetes."]})

    result = evaluate_dataset(frame)

    assert result["unsupported_count"] == 1
    assert result["metrics"]["accuracy"] is None
    assert result["record_findings"][0]["human_review_required"]


def test_reference_answers_without_ai_labels_do_not_produce_an_ai_score():
    frame = pd.DataFrame(
        {
            "value": [120],
            "reference_low": [70],
            "reference_high": [100],
            "reference_answer": ["above_range"],
        }
    )

    result = evaluate_dataset(frame)

    assert not result["has_reference_answers"]
    assert result["metrics"]["accuracy"] is None
    assert result["metrics"]["overall_score"] is None


def test_common_ai_output_and_expected_answer_columns_are_detected():
    frame = pd.DataFrame(
        {
            "AI Generated Output": ["High", "normal", "Below range"],
            "Expected Answer": ["above range", "within range", "within range"],
        }
    )

    result = evaluate_dataset(frame)

    assert result["column_mapping"] == {
        "ai_label": "AI Generated Output",
        "reference_answer": "Expected Answer",
    }
    assert result["verification_summary"] == {
        "verified": 2,
        "not_verified": 1,
        "unscored": 0,
        "scored": 3,
    }
    assert result["metrics"]["accuracy"] == pytest.approx(0.6667)


def test_free_text_range_labels_are_normalized_for_comparison():
    frame = pd.DataFrame(
        {
            "ai_output": ["Value is above the supplied reference range.", "Value falls within the range."],
            "ground_truth": ["above_range", "normal"],
        }
    )

    result = evaluate_dataset(frame)

    assert result["verification_summary"]["verified"] == 2
    assert result["metrics"]["accuracy"] == 1
