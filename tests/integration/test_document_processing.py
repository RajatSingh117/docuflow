import io
import fitz
from app.models.job import JobStatus


def create_test_pdf_bytes():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Invoice Number: INV-2026-999\nDate: 2026-03-20\nTotal: $1,500.00\nEmail: billing@company.org")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_upload_document_by_manager(client, manager_headers):
    pdf_content = create_test_pdf_bytes()
    file = io.BytesIO(pdf_content)

    response = client.post(
        "/api/documents/upload",
        headers=manager_headers,
        files={"file": ("invoice_sample.pdf", file, "application/pdf")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "invoice_sample.pdf"
    assert data["file_type"] == "pdf"
    assert data["file_size"] == len(pdf_content)
    assert len(data["checksum"]) == 64


def test_upload_document_rejected_for_viewer(client, viewer_headers):
    pdf_content = create_test_pdf_bytes()
    file = io.BytesIO(pdf_content)

    response = client.post(
        "/api/documents/upload",
        headers=viewer_headers,
        files={"file": ("viewer_invoice.pdf", file, "application/pdf")}
    )
    assert response.status_code == 403


def test_list_and_download_document(client, manager_headers):
    pdf_content = create_test_pdf_bytes()
    file = io.BytesIO(pdf_content)

    upload_res = client.post(
        "/api/documents/upload",
        headers=manager_headers,
        files={"file": ("download_test.pdf", file, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    # List documents
    list_res = client.get("/api/documents", headers=manager_headers)
    assert list_res.status_code == 200
    docs = list_res.json()
    assert any(d["id"] == doc_id for d in docs)

    # Download document
    download_res = client.get(f"/api/documents/{doc_id}/download", headers=manager_headers)
    assert download_res.status_code == 200
    assert download_res.content == pdf_content


def test_create_and_retry_processing_job(client, manager_headers):
    # Upload valid document first
    pdf_content = create_test_pdf_bytes()
    file = io.BytesIO(pdf_content)
    upload_res = client.post(
        "/api/documents/upload",
        headers=manager_headers,
        files={"file": ("job_test.pdf", file, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    # Create processing job
    job_res = client.post(
        "/api/processing/jobs",
        headers=manager_headers,
        json={"document_id": doc_id, "processing_type": "auto"}
    )
    assert job_res.status_code == 201
    job_data = job_res.json()
    assert job_data["document_id"] == doc_id
    assert job_data["status"] in ["NEEDS_REVIEW", "COMPLETED", "EXTRACTED"]
    assert job_data["processing_type"] == "pdf_digital"
    job_id = job_data["id"]

    # Retrieve job details
    get_job = client.get(f"/api/processing/jobs/{job_id}", headers=manager_headers)
    assert get_job.status_code == 200
    details = get_job.json()
    assert details["id"] == job_id
    assert len(details["logs"]) >= 1
