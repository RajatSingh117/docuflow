import io
import pymupdf as fitz
from pathlib import Path


def create_invoice_pdf():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 50),
        "Invoice Number: INV-REPORT-99\nInvoice Date: 2026-07-01\nDue Date: 2026-07-31\nTotal Amount: $5,400.00\nEmail: reports@company.org"
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_generate_and_download_reports(client, manager_headers, viewer_headers):
    # 1. Upload & process document
    pdf_bytes = create_invoice_pdf()
    file = io.BytesIO(pdf_bytes)
    upload_res = client.post(
        "/api/documents/upload",
        headers=manager_headers,
        files={"file": ("report_doc.pdf", file, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    job_res = client.post(
        "/api/processing/jobs",
        headers=manager_headers,
        json={"document_id": doc_id, "processing_type": "auto"}
    )
    job_id = job_res.json()["id"]

    # 2. Approve job records
    client.post(f"/api/reviews/jobs/{job_id}/approve", headers=manager_headers)

    # 3. Generate Excel Report
    excel_res = client.post(
        "/api/reports/generate",
        headers=manager_headers,
        json={"job_id": job_id, "report_type": "excel"}
    )
    assert excel_res.status_code == 201
    excel_data = excel_res.json()
    assert excel_data["report_type"] == "excel"
    assert excel_data["filename"].endswith(".xlsx")
    excel_rep_id = excel_data["id"]

    # 4. Generate PDF Report
    pdf_res = client.post(
        "/api/reports/generate",
        headers=manager_headers,
        json={"job_id": job_id, "report_type": "pdf"}
    )
    assert pdf_res.status_code == 201
    pdf_data = pdf_res.json()
    assert pdf_data["report_type"] == "pdf"
    assert pdf_data["filename"].endswith(".pdf")
    pdf_rep_id = pdf_data["id"]

    # 5. List reports
    list_res = client.get("/api/reports", headers=viewer_headers)
    assert list_res.status_code == 200
    reports_list = list_res.json()
    assert len(reports_list) >= 2

    # 6. Download Excel report
    download_excel = client.get(f"/api/reports/{excel_rep_id}/download", headers=viewer_headers)
    assert download_excel.status_code == 200
    assert len(download_excel.content) > 1000

    # 7. Download PDF report
    download_pdf = client.get(f"/api/reports/{pdf_rep_id}/download", headers=viewer_headers)
    assert download_pdf.status_code == 200
    assert download_pdf.content.startswith(b"%PDF-")


def test_unauthenticated_cannot_download_report(client):
    res = client.get("/api/reports/1/download")
    assert res.status_code == 401
