from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .config import DATABASE_PATH, MAX_UPLOAD_BYTES
from .database import dashboard_summary, get_evaluation, initialize_database, list_evaluations, save_evaluation
from .datasets import DatasetError, column_profile, preview_records, read_dataset
from .evaluation import evaluate_dataset
from .reports import csv_report, docx_report, pdf_report
from .validation import validate_dataset

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="MediEval AI API",
    description="A data-quality and AI-output evaluation API. It is not a diagnosis system.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "MediEval AI"}


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    evaluations = list_evaluations(limit=10)
    return {
        "summary": dashboard_summary(),
        "recent_evaluations": evaluations,
        "trend": [
            {"date": item["created_at"][:10], "score": item["score"], "records": item["record_count"]}
            for item in reversed(evaluations)
        ],
    }


@app.get("/api/evaluations")
def evaluations() -> list[dict[str, Any]]:
    return list_evaluations(limit=100)


@app.get("/api/evaluations/{evaluation_id}")
def evaluation_detail(evaluation_id: str) -> dict[str, Any]:
    result = get_evaluation(evaluation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Evaluation not found.")
    return result


@app.post("/api/evaluations/upload")
async def upload_evaluation(
    file: UploadFile = File(...),
    ai_label_column: str | None = Form(default=None),
    reference_answer_column: str | None = Form(default=None),
) -> dict[str, Any]:
    filename = Path(file.filename or "dataset").name
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.")
    try:
        frame = read_dataset(filename, content)
    except DatasetError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    for label, column in (
        ("AI label", ai_label_column),
        ("reference answer", reference_answer_column),
    ):
        if column and column not in frame.columns:
            raise HTTPException(status_code=400, detail=f"Selected {label} column was not found in the uploaded dataset.")
    validation = validate_dataset(frame)
    evaluation = evaluate_dataset(
        frame,
        ai_label_column=ai_label_column,
        reference_answer_column=reference_answer_column,
    )
    response = {
        "filename": filename,
        "columns": column_profile(frame),
        "preview": preview_records(frame),
        "validation": validation,
        "evaluation": evaluation,
        "privacy": {
            "raw_dataset_saved": False,
            "identifiers_redacted_in_preview": True,
            "stored_fields": "Aggregate metrics and counts only; row-level data is not persisted.",
        },
    }
    persisted = save_evaluation(filename, response, DATABASE_PATH)
    response["id"] = persisted["id"]
    response["created_at"] = persisted["created_at"]
    return response


@app.get("/api/reports/{evaluation_id}/{format}")
def download_report(evaluation_id: str, format: str) -> Response:
    if format not in {"csv", "pdf", "docx"}:
        raise HTTPException(status_code=400, detail="Supported report formats are csv, pdf, and docx.")
    stored = get_evaluation(evaluation_id, DATABASE_PATH)
    if stored is None:
        raise HTTPException(status_code=404, detail="Evaluation not found.")
    # Persisted records intentionally contain only summary metrics; report summaries never reconstruct row-level data.
    evaluation = {
        "metrics": stored["metrics"],
        "evaluated_record_count": stored["record_count"],
        "unsupported_count": stored["unsupported_count"],
        "verification_summary": stored["verification_summary"],
        "issues": stored["issues"],
        "record_findings": [],
    }
    generators = {"csv": csv_report, "pdf": pdf_report, "docx": docx_report}
    media_types = {
        "csv": "text/csv; charset=utf-8",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    body = generators[format](evaluation)
    return Response(
        content=body,
        media_type=media_types[format],
        headers={"Content-Disposition": f'attachment; filename="medieval-evaluation-{evaluation_id[:8]}.{format}"'},
    )
