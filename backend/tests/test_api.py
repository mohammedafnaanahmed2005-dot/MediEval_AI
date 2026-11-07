from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import app


def test_rejects_unsupported_file_type():
    with TestClient(app) as client:
        response = client.post(
            "/api/evaluations/upload",
            files={"file": ("dataset.txt", b"test", "text/plain")},
        )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_redacts_identifiers_and_exports_aggregate_reports():
    content = (
        "patient_id,value,reference_low,reference_high,ai_result,reference_answer,ai_interpretation\n"
        "REAL-PATIENT-123,120,70,100,above_range,above_range,Value is above the supplied reference range.\n"
        "REAL-PATIENT-456,80,70,100,within_range,within_range,Value falls within the supplied reference range.\n"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/evaluations/upload",
            files={"file": ("safe-test.csv", content.encode(), "text/csv")},
        )
        assert response.status_code == 200
        result = response.json()
        evaluation_id = result["id"]

        assert result["preview"][0]["patient_id"] == "[redacted]"
        assert result["privacy"]["raw_dataset_saved"] is False
        assert result["evaluation"]["metrics"]["accuracy"] == 1

        detail = client.get(f"/api/evaluations/{evaluation_id}").json()
        assert "REAL-PATIENT-123" not in str(detail)
        assert detail["filename"] == "dataset.csv"
        assert any(issue["category"] == "clinical_review" for issue in detail["issues"])

        for extension, media_type in (
            ("csv", "text/csv"),
            ("pdf", "application/pdf"),
            ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ):
            report = client.get(f"/api/reports/{evaluation_id}/{extension}")
            assert report.status_code == 200
            assert report.headers["content-type"].startswith(media_type)
            assert b"REAL-PATIENT-123" not in report.content
            if extension == "csv":
                assert b"accuracy" in report.content
                assert b"recommendation" in report.content
                assert b"Not verified records" in report.content
                assert b"chart_data" in report.content
            elif extension == "pdf":
                assert report.content.count(b"/Subtype /Image") >= 2
            else:
                with ZipFile(BytesIO(report.content)) as archive:
                    assert "word/media/image1.png" in archive.namelist()
                    assert "word/media/image2.png" in archive.namelist()
                    document_xml = archive.read("word/document.xml")
                    assert b"Not verified" in document_xml
                    assert b"Verified: 2" in document_xml


def test_upload_can_use_manually_selected_custom_label_columns():
    content = (
        "Model response,Reviewed truth\n"
        "Elevated,Above reference range\n"
        "Normal,Within range\n"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/evaluations/upload",
            files={"file": ("custom.csv", content.encode(), "text/csv")},
            data={
                "ai_label_column": "Model response",
                "reference_answer_column": "Reviewed truth",
            },
        )

    assert response.status_code == 200
    result = response.json()
    assert result["evaluation"]["column_mapping"] == {
        "ai_label": "Model response",
        "reference_answer": "Reviewed truth",
    }
    assert result["evaluation"]["verification_summary"]["verified"] == 2
    assert result["evaluation"]["metrics"]["accuracy"] == 1
