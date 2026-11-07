from io import BytesIO
from pathlib import Path

import pandas as pd

from .config import ALLOWED_EXTENSIONS, IDENTIFIER_HINTS, MAX_RECORDS


class DatasetError(ValueError):
    pass


def read_dataset(filename: str, content: bytes) -> pd.DataFrame:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DatasetError("Unsupported file type. Upload CSV, Excel (.xlsx/.xls), or JSON.")
    if not content:
        raise DatasetError("The uploaded file is empty.")
    try:
        if extension == ".csv":
            frame = pd.read_csv(BytesIO(content))
        elif extension in {".xlsx", ".xls"}:
            frame = pd.read_excel(BytesIO(content))
        else:
            frame = pd.read_json(BytesIO(content))
    except (ValueError, UnicodeDecodeError, ImportError) as error:
        raise DatasetError(f"Could not read the uploaded dataset: {error}") from error
    if frame.empty:
        raise DatasetError("The uploaded dataset has no records.")
    if len(frame) > MAX_RECORDS:
        raise DatasetError(f"Datasets are limited to {MAX_RECORDS:,} records.")
    if len(frame.columns) == 0:
        raise DatasetError("The uploaded dataset has no columns.")
    frame.columns = [str(column).strip() for column in frame.columns]
    if any(not column for column in frame.columns):
        raise DatasetError("Column names cannot be empty.")
    if frame.columns.duplicated().any():
        raise DatasetError("Column names must be unique.")
    if any(
        isinstance(value, (dict, list, set, tuple))
        for column in frame.columns
        for value in frame[column].dropna()
    ):
        raise DatasetError("Nested JSON values are not supported. Upload flat, tabular records instead.")
    frame = frame.replace(r"^\s*$", pd.NA, regex=True)
    return frame


def is_identifier_column(column: str) -> bool:
    normalized = column.lower().replace("-", "_").replace(" ", "_")
    return any(hint in normalized for hint in IDENTIFIER_HINTS)


def preview_records(frame: pd.DataFrame, limit: int = 8) -> list[dict[str, object]]:
    preview = frame.head(limit).copy()
    for column in preview.columns:
        if is_identifier_column(column):
            preview[column] = "[redacted]"
    preview = preview.astype(object).where(pd.notna(preview), None)
    return preview.to_dict(orient="records")


def column_profile(frame: pd.DataFrame) -> list[dict[str, object]]:
    profiles = []
    for column in frame.columns:
        series = frame[column]
        profiles.append(
            {
                "name": column,
                "inferred_type": str(series.dtype),
                "missing_count": int(series.isna().sum()),
                "unique_count": int(series.nunique(dropna=True)),
                "identifier_redacted": is_identifier_column(column),
            }
        )
    return profiles
