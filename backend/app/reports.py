from io import BytesIO
from xml.sax.saxutils import escape
from typing import Any

import pandas as pd
from docx import Document
from docx.shared import Inches, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image as PDFImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .report_charts import metrics_chart, verification_chart

def csv_report(evaluation: dict[str, Any]) -> bytes:
    rows = [
        {"section": "metric", "metric": name, "category": "", "severity": "", "finding": "", "value": value}
        for name, value in evaluation.get("metrics", {}).items()
    ]
    verification = evaluation.get("verification_summary", {})
    rows.extend(
        {
            "section": "verification",
            "metric": f"{label} records",
            "category": "",
            "severity": "",
            "finding": "AI label matches the supplied reference answer." if label == "Verified"
            else "AI label does not match the supplied reference answer." if label == "Not verified"
            else "A required AI label or reference answer is missing.",
            "value": verification.get(key, 0),
        }
        for key, label in (
            ("verified", "Verified"),
            ("not_verified", "Not verified"),
            ("unscored", "Unscored"),
        )
    )
    rows.extend(
        {
            "section": "chart_data",
            "metric": f"{label} verification share",
            "category": "verification",
            "severity": "",
            "finding": "Aggregate verification chart data",
            "value": (
                verification.get(key, 0) / evaluation.get("evaluated_record_count", 1)
                if evaluation.get("evaluated_record_count")
                else 0
            ),
        }
        for key, label in (
            ("verified", "Verified"),
            ("not_verified", "Not verified"),
            ("unscored", "Unscored"),
        )
    )
    rows.extend(
        {
            "section": "finding",
            "metric": "",
            "category": issue["category"],
            "severity": issue["severity"],
            "finding": issue["message"],
            "value": "",
        }
        for issue in evaluation.get("issues", [])
    )
    rows.extend(
        {
            "section": "recommendation",
            "metric": "",
            "category": "",
            "severity": "",
            "finding": recommendation,
            "value": "",
        }
        for recommendation in _recommendations(evaluation.get("issues", []))
    )
    frame = pd.DataFrame(rows, columns=["section", "metric", "category", "severity", "finding", "value"])
    return frame.to_csv(index=False).encode("utf-8")


def docx_report(evaluation: dict[str, Any]) -> bytes:
    document = Document()
    title = document.add_heading("MediEval AI", 0)
    title.runs[0].font.color.rgb = RGBColor(30, 49, 80)
    subtitle = document.add_paragraph("DATASET EVALUATION REPORT")
    subtitle.runs[0].font.color.rgb = RGBColor(57, 132, 246)
    subtitle.runs[0].bold = True
    _add_summary(document, evaluation)
    document.add_heading("Verification & performance", level=1)
    document.add_picture(BytesIO(verification_chart(evaluation.get("verification_summary", {}))), width=Inches(6.2))
    document.add_picture(BytesIO(metrics_chart(evaluation.get("metrics", {}))), width=Inches(6.2))
    document.add_heading("Validation and AI safety findings", level=1)
    issues = evaluation.get("issues", [])
    for issue in issues:
        document.add_paragraph(f"{issue['severity'].upper()} — {issue['message']}", style="List Bullet")
    document.add_heading("Recommendations", level=1)
    for recommendation in _recommendations(issues):
        document.add_paragraph(recommendation, style="List Bullet")
    safety = document.add_paragraph("For dataset evaluation only. Not a diagnosis or clinical decision.")
    safety.runs[0].italic = True
    safety.runs[0].font.color.rgb = RGBColor(113, 130, 154)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def pdf_report(evaluation: dict[str, Any]) -> bytes:
    stream = BytesIO()
    document = SimpleDocTemplate(stream, pagesize=letter, title="MediEval AI Evaluation Report")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("MediEval AI", styles["Title"]),
        Paragraph("DATASET EVALUATION REPORT", styles["Heading2"]),
        Spacer(1, 12),
    ]
    story.extend(_pdf_summary(evaluation))
    story.extend(
        [
            Spacer(1, 15),
            Paragraph("Verification &amp; performance", styles["Heading2"]),
            Spacer(1, 7),
            _pdf_chart(verification_chart(evaluation.get("verification_summary", {})), width=440, height=269),
            Spacer(1, 10),
            _pdf_chart(metrics_chart(evaluation.get("metrics", {})), width=440, height=215),
            Spacer(1, 14),
        ]
    )
    story.append(Paragraph("Validation and AI safety findings", styles["Heading2"]))
    issue_rows = [["Category", "Severity", "Finding"]]
    issue_rows.extend(
        [[escape(issue["category"]), escape(issue["severity"]), escape(issue["message"])] for issue in evaluation.get("issues", [])]
    )
    if len(issue_rows) == 1:
        issue_rows.append(["—", "—", "No findings recorded."])
    table = Table(issue_rows, colWidths=[90, 60, 350], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf2ff")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d3deeb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([table, Spacer(1, 14), Paragraph("Recommendations", styles["Heading2"])])
    story.extend(Paragraph(f"&#8226; {escape(item)}", styles["BodyText"]) for item in _recommendations(evaluation.get("issues", [])))
    story.extend([Spacer(1, 12), Paragraph("For dataset evaluation only. Not a diagnosis.", styles["Italic"])])
    document.build(story)
    return stream.getvalue()


def _add_summary(document: Document, evaluation: dict[str, Any]) -> None:
    metrics = evaluation.get("metrics", {})
    verification = evaluation.get("verification_summary", {})
    document.add_paragraph(f"Records evaluated: {evaluation.get('evaluated_record_count', 0)}")
    document.add_paragraph(f"Unsupported claims: {evaluation.get('unsupported_count', 0)}")
    document.add_paragraph(
        "Reference verification — "
        f"Verified: {verification.get('verified', 0)} · "
        f"Not verified: {verification.get('not_verified', 0)} · "
        f"Unscored: {verification.get('unscored', 0)}"
    )
    document.add_paragraph(f"Overall score: {_format_metric(metrics.get('overall_score'), suffix='/100')}")
    document.add_paragraph(
        "Verified means the AI output label exactly matches the supplied reference answer. "
        "Records missing either are unscored."
    )


def _pdf_summary(evaluation: dict[str, Any]) -> list[Any]:
    metrics = evaluation.get("metrics", {})
    verification = evaluation.get("verification_summary", {})
    rows = [["Metric", "Result"]]
    for name in ("accuracy", "precision", "recall", "f1", "hallucination_rate", "overall_score"):
        rows.append([name.replace("_", " ").title(), _format_metric(metrics.get(name), suffix="/100" if name == "overall_score" else "")])
    rows.append(["Records evaluated", str(evaluation.get("evaluated_record_count", 0))])
    rows.append(["Unsupported claims", str(evaluation.get("unsupported_count", 0))])
    rows.extend(
        [
            ["Verified AI labels", str(verification.get("verified", 0))],
            ["Not verified AI labels", str(verification.get("not_verified", 0))],
            ["Unscored records", str(verification.get("unscored", 0))],
        ]
    )
    table = Table(rows, colWidths=[200, 300])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf2ff")), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey)]))
    return [table]


def _format_metric(value: Any, suffix: str = "") -> str:
    if value is None:
        return "Not available (no verified reference answers)" if not suffix else "Not available"
    if suffix == "/100":
        return f"{value:.2f}{suffix}"
    if isinstance(value, (float, int)) and 0 <= value <= 1:
        return f"{value * 100:.1f}%"
    return f"{value}{suffix}"


def _pdf_chart(content: bytes, width: int, height: int) -> PDFImage:
    image = PDFImage(BytesIO(content), width=width, height=height)
    image.hAlign = "CENTER"
    return image


def _recommendations(issues: list[dict[str, Any]]) -> list[str]:
    categories = {issue["category"] for issue in issues}
    recommendations = []
    if "data_quality" in categories:
        recommendations.append("Correct missing, inconsistent, or invalid fields against the dataset's authoritative source, then re-run validation.")
    if "clinical_review" in categories:
        recommendations.append("Route flagged measurements to an authorized human reviewer; do not treat range flags as diagnoses.")
    if "ai_safety" in categories:
        recommendations.append("Review flagged model outputs and restrict conclusions to facts supported by the supplied record.")
    if not recommendations:
        recommendations.append("Continue monitoring data quality and verify model outputs against reviewed reference answers.")
    return recommendations
