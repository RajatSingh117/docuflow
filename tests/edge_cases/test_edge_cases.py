"""Edge cases and security boundary tests — DocuFlow."""
import io
import pytest


class TestDocumentUploadEdgeCases:
    def test_upload_empty_file_rejected(self, client, manager_headers):
        file_payload = ("empty.pdf", b"", "application/pdf")
        resp = client.post(
            "/api/documents/upload",
            files={"file": file_payload},
            headers=manager_headers,
        )
        assert resp.status_code == 400
        assert "empty file" in resp.json()["detail"].lower()

    def test_upload_corrupt_pdf_rejected(self, client, manager_headers):
        corrupt_bytes = b"NOT_A_REAL_PDF_HEADER_1234567890"
        file_payload = ("corrupt.pdf", corrupt_bytes, "application/pdf")
        resp = client.post(
            "/api/documents/upload",
            files={"file": file_payload},
            headers=manager_headers,
        )
        assert resp.status_code == 400
        assert "invalid or corrupted" in resp.json()["detail"].lower()

    def test_upload_unsupported_file_extension(self, client, manager_headers):
        file_payload = ("malicious.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/octet-stream")
        resp = client.post(
            "/api/documents/upload",
            files={"file": file_payload},
            headers=manager_headers,
        )
        assert resp.status_code == 400
        assert "unsupported" in resp.json()["detail"].lower()

    def test_upload_spoofed_png_rejected(self, client, manager_headers):
        # Named .png but doesn't start with PNG magic bytes \x89PNG\r\n\x1a\n
        spoofed_bytes = b"BM1234FakeBitmapData"
        file_payload = ("fake.png", spoofed_bytes, "image/png")
        resp = client.post(
            "/api/documents/upload",
            files={"file": file_payload},
            headers=manager_headers,
        )
        assert resp.status_code == 400
        assert "png" in resp.json()["detail"].lower()

    def test_upload_spoofed_xlsx_rejected(self, client, manager_headers):
        # Named .xlsx but doesn't start with PK zip signature
        fake_excel = b"This is not a zip or xlsx file"
        file_payload = ("sheet.xlsx", fake_excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp = client.post(
            "/api/documents/upload",
            files={"file": file_payload},
            headers=manager_headers,
        )
        assert resp.status_code == 400
        assert "excel" in resp.json()["detail"].lower()


class TestSecurityHardening:
    def test_security_headers_present_on_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert "Content-Security-Policy" in resp.headers
        assert "frame-ancestors 'none'" in resp.headers["Content-Security-Policy"]

    def test_security_headers_present_on_api_endpoints(self, client, viewer_headers):
        resp = client.get("/api/analytics/dashboard", headers=viewer_headers)
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_document_download_nonexistent_returns_404(self, client, viewer_headers):
        resp = client.get("/api/documents/999999/download", headers=viewer_headers)
        assert resp.status_code == 404

    def test_report_download_nonexistent_returns_404(self, client, viewer_headers):
        resp = client.get("/api/reports/999999/download", headers=viewer_headers)
        assert resp.status_code == 404


class TestValidationConsistencyEdgeCases:
    def test_due_date_before_invoice_date_triggers_warning(self):
        from app.validators.engine import ValidationEngine
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        engine = ValidationEngine(mock_db)

        # Record where due date is before invoice date
        record = {
            "invoice_number": "INV-100",
            "invoice_date": "2026-05-15",
            "due_date": "2026-05-01",  # 14 days earlier
            "total_amount": 1000.0,
            "tax_amount": 100.0,
        }
        results = engine.validate_record(record, current_record_id=1)
        # Should flag a warning on due_date
        due_date_results = [r for r in results if r["field_name"] == "due_date"]
        assert len(due_date_results) > 0
        assert any(r["status"] in ("WARNING", "INVALID") for r in due_date_results)

    def test_invalid_email_format_flagged(self):
        from app.validators.engine import ValidationEngine
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        engine = ValidationEngine(mock_db)

        record = {
            "invoice_number": "INV-101",
            "invoice_date": "2026-05-15",
            "email": "not-a-valid-email-address",
            "total_amount": 500.0,
        }
        results = engine.validate_record(record, current_record_id=2)
        email_results = [r for r in results if r["field_name"] == "email"]
        assert len(email_results) > 0
        assert any(r["status"] == "INVALID" for r in email_results)
