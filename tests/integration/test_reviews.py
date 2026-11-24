import io
import pymupdf as fitz


def create_invoice_pdf():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 50),
        "Invoice Number: INV-REV-001\nInvoice Date: 2026-06-01\nDue Date: 2026-06-30\nTotal Amount: $2,500.00\nEmail: accounts@client.org"
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_review_and_approval_workflow(client, manager_headers, viewer_headers):
    # 1. Upload invoice document
    pdf_bytes = create_invoice_pdf()
    file = io.BytesIO(pdf_bytes)
    upload_res = client.post(
        "/api/documents/upload",
        headers=manager_headers,
        files={"file": ("review_test.pdf", file, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    # 2. Start processing job
    job_res = client.post(
        "/api/processing/jobs",
        headers=manager_headers,
        json={"document_id": doc_id, "processing_type": "auto"}
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 3. Retrieve review data for this job
    review_res = client.get(f"/api/reviews/jobs/{job_id}", headers=manager_headers)
    assert review_res.status_code == 200
    review_data = review_res.json()
    assert len(review_data["records"]) >= 1
    record = review_data["records"][0]
    record_id = record["id"]

    # Find total_amount field
    total_field = next(f for f in record["fields"] if f["field_name"] == "total_amount")
    field_id = total_field["id"]

    # 4. Viewer should be forbidden from editing fields
    viewer_edit = client.put(
        f"/api/reviews/fields/{field_id}",
        headers=viewer_headers,
        json={"value": "3000.00"}
    )
    assert viewer_edit.status_code == 403

    # 5. Manager edits total_amount
    manager_edit = client.put(
        f"/api/reviews/fields/{field_id}",
        headers=manager_headers,
        json={"value": "3200.00"}
    )
    assert manager_edit.status_code == 200
    updated_field = manager_edit.json()
    assert updated_field["normalized_value"] == "3200.00"
    assert updated_field["confidence_score"] == 1.0

    # 6. Approve single record
    approve_res = client.post(
        f"/api/reviews/records/{record_id}/approve",
        headers=manager_headers,
        json={"force_override": False}
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["is_approved"] is True

    # 7. Approve all job records and complete job
    job_approve_res = client.post(
        f"/api/reviews/jobs/{job_id}/approve",
        headers=manager_headers
    )
    assert job_approve_res.status_code == 200
    assert job_approve_res.json()["status"] == "COMPLETED"
