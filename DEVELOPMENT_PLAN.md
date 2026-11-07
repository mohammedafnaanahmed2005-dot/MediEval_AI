# MediEval AI Development Plan

## Delivery approach

Build in small Agile increments with a working, locally runnable vertical slice at each step. The initial release is a safety-focused evaluation platform, not a diagnostic product. No model or external AI service is called; explanations are deterministic comparisons against reference bounds supplied in the dataset.

## Phases and acceptance checks

1. **Foundation and dataset validation** — FastAPI structure, SQLite aggregate history, CSV/Excel/JSON parsing, limits, previews with identifier redaction, data-quality checks, and synthetic example data. Acceptance: malformed/oversized inputs fail clearly; raw datasets are not persisted.
2. **AI-output evaluation** — Compare predictions with verified answers; report accuracy, macro precision/recall/F1, hallucination rate, and an overall score only when ground truth exists. Explanations cite supplied values/ranges; unsupported or diagnostic claims are flagged. Acceptance: missing references yield unavailable metrics, never fabricated scores.
3. **Dashboard and upload workflow** — Responsive React dashboard, accessible navigation, upload/preview, validation findings, and interactive visualizations. Acceptance: users can load the synthetic example, upload a file, and inspect results.
4. **Reports and history** — CSV, PDF, and DOCX exports plus aggregate dashboard history. Acceptance: exports contain summary findings and do not reconstruct or expose patient-level rows.
5. **Verification and handoff** — Unit/API tests, frontend build, API documentation, setup instructions, and local launch guidance. Acceptance: checks pass and FastAPI Swagger is available at `/docs`.

## Initial architecture

- `backend/app`: API, parsing, validation, evaluation, SQLite, and report modules.
- `backend/tests`: isolated unit and API tests.
- `backend/sample-data`: synthetic-only demonstration dataset.
- `frontend/src`: React app, reusable UI components, API client, and charts.

## Safety and privacy controls

- Distinguish data-quality defects from findings that require clinical review.
- Never infer a diagnosis or fill in missing values.
- Suppress identifying values in dataset previews and persist aggregate metrics only.
- Mark out-of-range and unusual measurements for human review; do not call them diagnoses.
- Keep reference ranges and units tied to the uploaded dataset rather than assumed medical standards.
