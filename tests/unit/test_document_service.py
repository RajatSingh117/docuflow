import pytest
from fastapi import HTTPException
from app.services.document_service import calculate_sha256, validate_file_content


def test_calculate_sha256():
    data = b"Hello DocuFlow System"
    digest = calculate_sha256(data)
    assert len(digest) == 64
    assert digest == "2b77b9dfd478855188014dc5beaeab03c19b0d00e1c51b1aa581f2b364c2e9a3"


def test_validate_valid_pdf_content():
    content = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj"
    file_type = validate_file_content("invoice.pdf", content)
    assert file_type == "pdf"


def test_validate_valid_png_content():
    content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    file_type = validate_file_content("receipt.png", content)
    assert file_type == "png"


def test_validate_valid_csv_content():
    content = b"invoice_id,date,amount\nINV-001,2026-01-01,150.00"
    file_type = validate_file_content("report.csv", content)
    assert file_type == "csv"


def test_reject_empty_file():
    with pytest.raises(HTTPException) as exc:
        validate_file_content("empty.pdf", b"")
    assert exc.value.status_code == 400
    assert "Empty file" in exc.value.detail


def test_reject_unsupported_format():
    with pytest.raises(HTTPException) as exc:
        validate_file_content("malicious.exe", b"MZ\x90\x00")
    assert exc.value.status_code == 400
    assert "Unsupported file format" in exc.value.detail


def test_reject_corrupt_pdf():
    # File named .pdf but without %PDF- magic bytes
    with pytest.raises(HTTPException) as exc:
        validate_file_content("fake.pdf", b"This is not a real PDF document.")
    assert exc.value.status_code == 400
    assert "Invalid or corrupted PDF file" in exc.value.detail
