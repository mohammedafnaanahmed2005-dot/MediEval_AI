from typing import Any

import numpy as np
import pandas as pd

NUMERIC_HINTS = (
    "age", "value", "reference_low", "ref_low", "range_low", "reference_high",
    "ref_high", "range_high", "measurement", "result_value", "systolic", "diastolic",
)


def validate_dataset(frame: pd.DataFrame) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    missing_by_column = {
        str(column): int(count)
        for column, count in frame.isna().sum().items()
        if count
    }
    missing_count = int(frame.isna().sum().sum())
    for column, count in missing_by_column.items():
        issues.append(
            _issue(
                "missing_values",
                "data_quality",
                "medium",
                f"{count} record(s) have missing values in “{column}”.",
                {"column": column, "affected_records": count},
            )
        )

    duplicate_count = int(frame.duplicated().sum())
    if duplicate_count:
        issues.append(
            _issue(
                "duplicate_records",
                "data_quality",
                "medium",
                f"{duplicate_count} duplicate record(s) detected.",
                {"duplicate_records": duplicate_count},
            )
        )

    numeric_columns = [
        column
        for column in frame.columns
        if any(hint in str(column).lower() for hint in NUMERIC_HINTS)
        and not str(column).lower().startswith(("ai_", "model_", "prediction"))
    ]
    numeric_data: dict[str, pd.Series] = {}
    for column in numeric_columns:
        raw = frame[column]
        numeric = pd.to_numeric(raw, errors="coerce")
        invalid_mask = raw.notna() & numeric.isna()
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            issues.append(
                _issue(
                    "invalid_numeric",
                    "data_quality",
                    "high",
                    f"{invalid_count} non-numeric value(s) found in “{column}”.",
                    {"column": str(column), "affected_records": invalid_count},
                )
            )
        numeric_data[str(column).lower()] = numeric

    age_column = _find_column(frame, ("age", "age_years"))
    if age_column is not None:
        ages = pd.to_numeric(frame[age_column], errors="coerce")
        invalid_age = (ages < 0) | (ages > 130)
        count = int(invalid_age.sum())
        if count:
            issues.append(
                _issue(
                    "invalid_range",
                    "data_quality",
                    "high",
                    f"{count} age value(s) fall outside the configured data-validity range (0–130).",
                    {"column": str(age_column), "affected_records": count},
                )
            )

    value_column = _find_column(frame, ("value", "result", "measurement"))
    low_column = _find_column(frame, ("reference_low", "ref_low", "range_low", "low"))
    high_column = _find_column(frame, ("reference_high", "ref_high", "range_high", "high"))
    if value_column is not None and low_column is not None and high_column is not None:
        values = pd.to_numeric(frame[value_column], errors="coerce")
        lows = pd.to_numeric(frame[low_column], errors="coerce")
        highs = pd.to_numeric(frame[high_column], errors="coerce")
        invalid_ranges = lows.notna() & highs.notna() & (lows > highs)
        count = int(invalid_ranges.sum())
        if count:
            issues.append(
                _issue(
                    "invalid_reference_range",
                    "data_quality",
                    "high",
                    f"{count} reference range(s) have a lower bound greater than the upper bound.",
                    {"affected_records": count},
                )
            )
        out_of_range = values.notna() & lows.notna() & highs.notna() & ~invalid_ranges & (
            (values < lows) | (values > highs)
        )
        count = int(out_of_range.sum())
        if count:
            issues.append(
                _issue(
                    "outside_reference_range",
                    "clinical_review",
                    "review",
                    f"{count} measurement(s) are outside their supplied reference range; human review required.",
                    {"column": str(value_column), "affected_records": count},
                )
            )

    unit_column = _find_column(frame, ("unit", "units"))
    test_column = _find_column(frame, ("test", "test_name", "analyte", "measurement"))
    if unit_column is not None:
        groups = frame.groupby(test_column, dropna=True) if test_column is not None else [(None, frame)]
        for test, group in groups:
            units = sorted(
                {str(unit).strip() for unit in group[unit_column].dropna() if str(unit).strip()}
            )
            if len(units) > 1:
                issues.append(
                    _issue(
                        "inconsistent_units",
                        "data_quality",
                        "medium",
                        f"Multiple units are used for {test or 'the dataset'}: {', '.join(units)}.",
                        {"test": str(test) if test is not None else None, "unit_count": len(units)},
                    )
                )

    patient_column = _find_column(frame, ("patient_id", "patientid", "mrn", "record_id"))
    if patient_column is not None and test_column is not None and value_column is not None:
        for _, group in frame.groupby([patient_column, test_column], dropna=True):
            values = pd.to_numeric(group[value_column], errors="coerce").dropna().unique()
            if len(values) > 1:
                issues.append(
                    _issue(
                        "conflicting_information",
                        "data_quality",
                        "medium",
                        "Conflicting measurements were found for the same record and test.",
                        {"affected_records": int(len(group))},
                    )
                )

    outlier_count = 0
    if value_column is not None:
        values = pd.to_numeric(frame[value_column], errors="coerce").dropna()
        if len(values) >= 4:
            q1, q3 = values.quantile([0.25, 0.75])
            spread = q3 - q1
            if spread > 0:
                outlier_count = int(((values < q1 - 1.5 * spread) | (values > q3 + 1.5 * spread)).sum())
                if outlier_count:
                    issues.append(
                        _issue(
                            "unusual_values",
                            "clinical_review",
                            "review",
                            f"{outlier_count} statistically unusual value(s) flagged for human review; this is not a diagnosis.",
                            {"column": str(value_column), "affected_records": outlier_count},
                        )
                    )

    return {
        "record_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "missing_value_count": missing_count,
        "missing_by_column": missing_by_column,
        "duplicate_count": duplicate_count,
        "issue_count": len(issues),
        "issues": issues,
        "quality_summary": {
            "data_quality_issue_count": sum(issue["category"] == "data_quality" for issue in issues),
            "clinical_review_count": sum(issue["category"] == "clinical_review" for issue in issues),
            "unusual_value_count": outlier_count,
        },
    }


def _find_column(frame: pd.DataFrame, aliases: tuple[str, ...]) -> Any | None:
    lookup = {str(column).lower().strip().replace(" ", "_"): column for column in frame.columns}
    for alias in aliases:
        if alias in lookup:
            return lookup[alias]
    for column in frame.columns:
        if any(alias in str(column).lower().replace(" ", "_") for alias in aliases):
            return column
    return None


def _issue(code: str, category: str, severity: str, message: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": code,
        "category": category,
        "severity": severity,
        "message": message,
        "evidence": evidence,
        "human_review_required": category == "clinical_review",
    }
