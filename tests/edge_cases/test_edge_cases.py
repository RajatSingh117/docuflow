"""Edge cases, security boundaries, and audit corrections verification tests — DocuFlow."""
import io
import os
import sqlite3
import pytest
from datetime import datetime, timezone
import pymupdf

from app.config import settings
from app.database import utc_now
from app.models.document import Document
from app.models.job import ProcessingJob, JobStatus
from app.services.auth_service import create_access_token, decode_access_token
from app.processors.pdf_processor import PDFProcessor


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

        record = {
            "invoice_number": "INV-100",
            "invoice_date": "2026-05-15",
            "due_date": "2026-05-01",
            "total_amount": 1000.0,
            "tax_amount": 100.0,
        }
        results = engine.validate_record(record, current_record_id=1)
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


# ── CORRECTION VERIFICATION TESTS (Issues 1–6) ────────────────────────────────

class TestDuplicateUploadCorrection:
    """Correction #2: SHA-256 duplicate detection returning HTTP 409."""

    def test_duplicate_document_upload_rejected_with_409(self, client, manager_headers, db_session):
        # Create a unique PDF
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Unique Invoice Content for SHA256 Dup Test")
        pdf_bytes = doc.tobytes()
        doc.close()

        file_payload = ("dup_invoice.pdf", pdf_bytes, "application/pdf")
        # 1. First upload succeeds
        r1 = client.post("/api/documents/upload", files={"file": file_payload}, headers=manager_headers)
        assert r1.status_code == 201
        first_doc_id = r1.json()["id"]

        # 2. Second upload with identical bytes rejected with 409 Conflict
        file_payload2 = ("dup_invoice_copy.pdf", pdf_bytes, "application/pdf")
        r2 = client.post("/api/documents/upload", files={"file": file_payload2}, headers=manager_headers)
        assert r2.status_code == 409
        assert "duplicate document detected" in r2.json()["detail"].lower()

        # 3. Verify only one document record exists in DB for this checksum
        matching = db_session.query(Document).filter(Document.checksum == r1.json()["checksum"]).all()
        assert len(matching) == 1


class TestDuplicateProcessingJobCorrection:
    """Correction #3: Prevention of duplicate in-flight processing jobs."""

    def test_duplicate_processing_job_rejected_with_409(self, client, manager_headers, db_session):
        # Create a document
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Content for In-Flight Job Test")
        pdf_bytes = doc.tobytes()
        doc.close()

        r_upload = client.post(
            "/api/documents/upload",
            files={"file": ("inflight_test.pdf", pdf_bytes, "application/pdf")},
            headers=manager_headers
        )
        doc_id = r_upload.json()["id"]

        # Manually create a job with status QUEUED
        job = ProcessingJob(
            document_id=doc_id,
            created_by=1,
            processing_type="pdf_digital",
            status=JobStatus.QUEUED
        )
        db_session.add(job)
        db_session.commit()

        # Attempt to create another job via API for the same document
        r_dup_job = client.post(
            "/api/processing/jobs",
            json={"document_id": doc_id, "processing_type": "auto"},
            headers=manager_headers
        )
        assert r_dup_job.status_code == 409
        assert "active processing job" in r_dup_job.json()["detail"].lower()


class TestStoragePathPortabilityCorrection:
    """Correction #4: Path traversal checks resolve against configured STORAGE_DIR."""

    def test_storage_dir_traversal_detection(self, client, viewer_headers, db_session):
        # Document with outside storage_reference should be rejected by traversal check
        bad_doc = Document(
            uploaded_by=1,
            original_filename="outside.pdf",
            stored_filename="outside.pdf",
            file_type="pdf",
            file_size=100,
            checksum="fakehash123",
            storage_reference=os.path.abspath("C:/Windows/System32/drivers/etc/hosts"),
        )
        db_session.add(bad_doc)
        db_session.commit()

        resp = client.get(f"/api/documents/{bad_doc.id}/download", headers=viewer_headers)
        assert resp.status_code == 400
        assert "traversal" in resp.json()["detail"].lower()


class TestPyMuPDFModernImportCorrection:
    """Correction #5: Modern import of PyMuPDF without deprecation warnings."""

    def test_pymupdf_extraction_clean(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Modern PyMuPDF Invoice INV-2026-99")
        temp_path = "storage/temp_test_pymupdf.pdf"
        doc.save(temp_path)
        doc.close()

        try:
            processor = PDFProcessor()
            result = processor.process(temp_path)
            assert "INV-2026-99" in result["raw_text"]
            assert "PyMuPDF" in result["metadata"]["processor"]
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestTimezoneAwareDatetimesCorrection:
    """Correction #6: Timezone-aware UTC datetimes."""

    def test_utc_now_returns_timezone_aware(self):
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_jwt_token_creation_and_expiration(self):
        token = create_access_token({"sub": "42", "role": "admin"})
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "42"
        assert "exp" in decoded
        # Expiry timestamp should be in the future
        assert decoded["exp"] > datetime.now(timezone.utc).timestamp()


class TestAlembicFreshDatabaseMigrationCorrection:
    """Correction #1: Fresh database migration creates all 11 application tables."""

    def test_alembic_upgrade_creates_all_tables_on_fresh_db(self):
        from alembic.config import Config
        from alembic import command

        test_db = "test_alembic_verification.db"
        if os.path.exists(test_db):
            os.remove(test_db)

        try:
            cfg = Config("alembic.ini")
            cfg.set_main_option("custom_db_url", f"sqlite:///{test_db}")
            command.upgrade(cfg, "head")

            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall()]
            conn.close()

            expected_tables = [
                "users", "documents", "processing_jobs", "processing_logs",
                "extracted_records", "extracted_fields", "validation_results",
                "generated_reports", "scheduled_jobs", "scheduled_job_executions", "audit_logs"
            ]
            for t in expected_tables:
                assert t in tables, f"Expected table '{t}' was not created by migration!"
        finally:
            if os.path.exists(test_db):
                os.remove(test_db)
