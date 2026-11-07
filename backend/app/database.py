import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import DATABASE_PATH

SAFE_ISSUE_MESSAGES = {
    "missing_values": "Missing values were detected in one or more columns.",
    "duplicate_records": "Duplicate records were detected.",
    "invalid_numeric": "Non-numeric values were detected in numeric fields.",
    "invalid_range": "Values were outside configured data-validity bounds.",
    "invalid_reference_range": "One or more supplied reference ranges were invalid.",
    "outside_reference_range": "Measurements outside supplied reference ranges require human review.",
    "inconsistent_units": "Inconsistent units were detected across records.",
    "conflicting_information": "Conflicting measurements were detected for a record and test.",
    "unusual_values": "Statistically unusual values were flagged for human review.",
    "unsupported_claims": "AI outputs could not be supported by supplied fields or used diagnostic language.",
}


def connect(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL,
                record_count INTEGER NOT NULL,
                issue_count INTEGER NOT NULL,
                missing_count INTEGER NOT NULL,
                unsupported_count INTEGER NOT NULL,
                score REAL,
                metrics_json TEXT NOT NULL,
                issues_json TEXT NOT NULL DEFAULT '[]',
                verified_count INTEGER NOT NULL DEFAULT 0,
                not_verified_count INTEGER NOT NULL DEFAULT 0,
                unscored_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(evaluations)")}
        migrations = {
            "issues_json": "TEXT NOT NULL DEFAULT '[]'",
            "verified_count": "INTEGER NOT NULL DEFAULT 0",
            "not_verified_count": "INTEGER NOT NULL DEFAULT 0",
            "unscored_count": "INTEGER NOT NULL DEFAULT 0",
        }
        for column, definition in migrations.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE evaluations ADD COLUMN {column} {definition}")


def save_evaluation(
    filename: str,
    result: dict[str, Any],
    database_path: Path = DATABASE_PATH,
) -> dict[str, Any]:
    evaluation_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    safe_filename = f"dataset{Path(filename).suffix.lower()}"
    validation = result["validation"]
    evaluation = result["evaluation"]
    metrics = evaluation["metrics"]
    verification = evaluation["verification_summary"]
    issues = [
        {
            "code": issue["code"],
            "category": issue["category"],
            "severity": issue["severity"],
            "message": SAFE_ISSUE_MESSAGES.get(issue["code"], "An evaluation finding was detected."),
            "human_review_required": issue["human_review_required"],
        }
        for issue in validation["issues"] + evaluation["issues"]
    ]
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO evaluations
            (id, filename, created_at, record_count, issue_count, missing_count,
             unsupported_count, score, metrics_json, issues_json, verified_count,
             not_verified_count, unscored_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evaluation_id,
                safe_filename,
                created_at,
                validation["record_count"],
                validation["issue_count"],
                validation["missing_value_count"],
                evaluation["unsupported_count"],
                metrics.get("overall_score"),
                json.dumps(metrics),
                json.dumps(issues),
                verification["verified"],
                verification["not_verified"],
                verification["unscored"],
            ),
        )
    return {"id": evaluation_id, "created_at": created_at}


def list_evaluations(database_path: Path = DATABASE_PATH, limit: int = 20) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM evaluations ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_serialize(row) for row in rows]


def get_evaluation(evaluation_id: str, database_path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM evaluations WHERE id = ?", (evaluation_id,)
        ).fetchone()
    return _serialize(row) if row else None


def dashboard_summary(database_path: Path = DATABASE_PATH) -> dict[str, Any]:
    with connect(database_path) as connection:
        totals = connection.execute(
            """
            SELECT COUNT(*) AS evaluations,
                   COALESCE(SUM(record_count), 0) AS records,
                   COALESCE(SUM(issue_count), 0) AS issues,
                   COALESCE(SUM(missing_count), 0) AS missing,
                   COALESCE(SUM(unsupported_count), 0) AS unsupported,
                   AVG(score) AS average_score
            FROM evaluations
            """
        ).fetchone()
    return dict(totals)


def _serialize(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "filename": row["filename"],
        "created_at": row["created_at"],
        "record_count": row["record_count"],
        "issue_count": row["issue_count"],
        "missing_value_count": row["missing_count"],
        "unsupported_count": row["unsupported_count"],
        "score": row["score"],
        "metrics": json.loads(row["metrics_json"]),
        "issues": json.loads(row["issues_json"]),
        "verification_summary": {
            "verified": row["verified_count"],
            "not_verified": row["not_verified_count"],
            "unscored": row["unscored_count"],
            "scored": row["verified_count"] + row["not_verified_count"],
        },
    }
