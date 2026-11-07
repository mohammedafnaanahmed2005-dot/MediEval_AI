# MediEval AI — Medical Dataset Evaluation Platform

## Project summary

MediEval AI is a local web application for checking structured medical datasets and comparing supplied AI labels with verified reference answers. A practical evaluation gap is that datasets often use different column names, and a score without row-level evidence can hide missing labels or mismatches. MediEval profiles data, lets users map custom label columns, separates unscored rows from incorrect labels, and shows the comparison and its evidence. In the included eight-row synthetic example, seven AI labels match their references and one does not; this demonstrates the evaluation workflow, not the performance of a medical AI model.

**Safety:** MediEval AI is an evaluation tool, not a diagnosis system. Its deterministic checks do not provide medical advice, infer missing facts, or replace qualified human review.

## Video walkthrough

[Watch the MediEval AI walkthrough on YouTube](https://www.youtube.com/watch?v=MONa761eQf0)

The video should be accessible to anyone with the link. If YouTube requests sign-in or permission, update the video's visibility/sharing settings.

## Domain and expertise

The project is in medical dataset quality assurance and responsible evaluation of AI-generated structured outputs. Its evaluation draws on software-based data validation, supplied reference ranges, evidence-grounded output checks, and standard classification metrics (accuracy, macro precision, macro recall, and F1).

The checks are intentionally limited to the information and reference answers supplied with a dataset. They are not a substitute for clinical expertise, medical-device validation, or review by a qualified professional.

## What it tests and why it matters

- **Dataset quality:** missing values, duplicate rows, invalid numeric values, conflicting information, range/unit issues, and unusual values for review.
- **Reference agreement:** compares an AI label with a supplied verified answer for each row. Rows missing either label are unscored, not treated as correct.
- **AI-output safety signals:** flags selected unsupported or diagnostic-sounding claims using deterministic rules and available fields; it does not establish clinical truth.
- **Summary measures:** accuracy, macro precision, macro recall, macro F1, a rule-based hallucination rate, and an overall score when suitable reference labels exist.
- **Evidence and review:** shows row-level comparisons and explanations; clinically significant out-of-range values are review flags, not diagnoses.

The application is intended for developers, researchers, and data teams evaluating structured model outputs against their own verified references. These checks matter because missing or incorrectly mapped labels can make a model appear better (or worse) than the evidence supports. Results depend on the quality and appropriateness of the supplied reference answers.

## Models tested and results

**No generative AI model is invoked or benchmarked by this application.** MediEval AI is a deterministic evaluator: users upload model outputs that were produced elsewhere, then map the AI-output and reference-answer columns. Consequently, there are no tested model IDs/versions, model settings such as temperature, or per-model benchmark scores to report.

The following is a reproducible **workflow demonstration**, not a model benchmark:

| Dataset / run | Date | Settings | Records | Accuracy | Macro precision | Macro recall | Macro F1 | Hallucination rate | Overall score |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Included synthetic `demo-labs.csv` | 2026-11-07 | One deterministic pass; 8 rows; `ai_result` compared with `reference_answer`; no model or temperature | 8 | 87.5% | 93.3% | 88.9% | 91.1% | 12.5% | 88.9/100 |

The sample has **7 verified** and **1 not-verified** label. Its records are synthetic and the score describes agreement with the sample's supplied labels only; it is not evidence of clinical accuracy or generalization. Scores can differ if the sample or evaluation implementation changes.

## Failure analysis

No separate language model was run as part of this project, so this README does not claim observed model failure causes. The synthetic demonstration contains one label/reference mismatch; it shows that the comparison detects disagreement, but does not explain why a model would make that error.

The evaluator can expose several practical failure conditions:

- If AI-output or reference columns are not mapped correctly, the comparison is invalid. Confirm the selected fields before interpreting results.
- If either label is absent for a row, that row is unscored; it is not counted as verified.
- If labels are free text, ambiguous, or outside the supported normalization rules, normalization may not reflect their intended meaning. Review the supplied values and mappings.
- Rule-based unsupported-claim checks are limited heuristics, not comprehensive medical-language understanding.
- A mismatch or out-of-range value is a signal for inspection, not proof of a medical error or diagnosis.

To make claims about a particular model, run it on a documented dataset, preserve the exact model ID/version and inference settings, and report repeated-run methodology and results alongside dataset limitations.

## Prior work and sources

- The included `backend/sample-data/demo-labs.csv` is a small synthetic demonstration dataset created for this project. It contains no real patient records and is not an established medical benchmark.
- No external clinical dataset or existing medical-AI benchmark is currently bundled or used for the results above.
- Accuracy, precision, recall, and F1 are established classification measures. The app computes its own deterministic implementation; it does not call scikit-learn or claim that these measures alone establish clinical safety.
- The AI labels and reference answers used for any real evaluation should come from a separately documented model run and a suitably verified source. Record dataset provenance, licensing, and limitations before sharing results.

## Setup and run

### Prerequisites

- Windows with PowerShell
- Python 3.10 or later
- Node.js 20 or later (includes npm)
- Internet access on first run so the launcher can install missing dependencies

### One-command startup

Open a terminal in the project folder and run:

```powershell
Set-Location C:\gggg
.\start.ps1
```

If PowerShell blocks script execution, run it for this process only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\start.ps1
```

The launcher creates the project virtual environment if needed, installs missing backend/frontend dependencies, starts the API and web app in separate PowerShell windows, and checks their health. Keep both service windows open while using the app. Open:

- Web app: <http://127.0.0.1:5173>
- FastAPI Swagger documentation: <http://127.0.0.1:8000/docs>
- API health: <http://127.0.0.1:8000/api/health>

Choose **Evaluate dataset → Load synthetic example** to try the workflow. For your own CSV, confirm or select the AI-output and verified-reference columns in the evaluation results.

### Manual startup

From the project folder, start the backend in one terminal:

```powershell
Set-Location C:\gggg
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location C:\gggg\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal, install and start the frontend:

```powershell
Set-Location C:\gggg\frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open <http://127.0.0.1:5173>. Vite proxies API requests to the local backend.

### API keys, runtime, and cost

No API key or `.env` file is required. The current application does not call an external LLM or other paid API, and it has no model-provider API-key configuration. Do not put secrets in source code. If an external model integration is added later, provide its key through a provider-approved environment variable and document that integration separately.

Runtime depends on the computer, network, and dataset size. On first startup, dependency installation may take several minutes; later launches and evaluation of a small CSV should usually take seconds. These are practical estimates, not a formal performance benchmark. There is no per-request model API charge in the current implementation; local compute, electricity, and internet costs are not estimated.

### Tests

Run backend tests:

```powershell
Set-Location C:\gggg\backend
..\.venv\Scripts\python.exe -m pytest
```

Build the frontend:

```powershell
Set-Location C:\gggg\frontend
npm run build
```

## Architecture

- **Frontend:** React, Vite, TypeScript, responsive healthcare dashboard styling, and Plotly charts.
- **Backend:** FastAPI with Pandas/NumPy validation and deterministic evaluation.
- **Persistence:** SQLite stores aggregate evaluation summaries, not uploaded row data.
- **Reports:** CSV, PDF, and DOCX exports.

## Privacy and safety

Uploaded rows are processed in memory and are not written to SQLite. Identifier-like columns are redacted in previews. SQLite stores aggregate counts, issue summaries, and metrics. Use synthetic data for demonstrations, and confirm your organization's privacy, security, and regulatory requirements before processing real patient data.

An out-of-range value is a human-review flag, not a clinical conclusion. Classification metrics are omitted unless structured AI labels and verified reference answers are available.
