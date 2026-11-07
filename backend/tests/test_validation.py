import pandas as pd

from app.validation import validate_dataset


def test_validation_separates_data_quality_and_clinical_review():
    frame = pd.DataFrame(
        {
            "patient_id": ["p1", "p2", "p2"],
            "test": ["glucose", "glucose", "glucose"],
            "value": [140, None, "bad"],
            "unit": ["mg/dL", "mg/dL", "mmol/L"],
            "reference_low": [70, 70, 110],
            "reference_high": [99, 99, 90],
        }
    )

    result = validate_dataset(frame)
    categories = {issue["category"] for issue in result["issues"]}

    assert result["record_count"] == 3
    assert result["missing_value_count"] == 1
    assert "data_quality" in categories
    assert "clinical_review" in categories
    assert any(issue["code"] == "invalid_numeric" for issue in result["issues"])
    assert any(issue["code"] == "invalid_reference_range" for issue in result["issues"])


def test_identical_rows_are_reported_as_duplicates():
    frame = pd.DataFrame([{"test": "A", "value": 4}, {"test": "A", "value": 4}])

    result = validate_dataset(frame)

    assert result["duplicate_count"] == 1
    assert any(issue["code"] == "duplicate_records" for issue in result["issues"])
