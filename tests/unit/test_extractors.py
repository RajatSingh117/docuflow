from app.extractors.normalizers import (
    normalize_date,
    normalize_amount,
    normalize_currency,
    normalize_phone
)
from app.extractors.confidence import calculate_field_confidence
from app.extractors.pattern_extractor import PatternExtractor


def test_normalize_date():
    assert normalize_date("2026-05-18") == "2026-05-18"
    assert normalize_date("18/05/2026") == "2026-05-18"
    assert normalize_date("May 18, 2026") == "2026-05-18"


def test_normalize_amount():
    assert normalize_amount("$1,250.50") == 1250.50
    assert normalize_amount("1.250,50 €") == 1250.50
    assert normalize_amount("450") == 450.0
    assert normalize_amount("invalid") is None


def test_normalize_currency():
    assert normalize_currency("$100") == "USD"
    assert normalize_currency("EUR 450") == "EUR"
    assert normalize_currency("£50") == "GBP"
    assert normalize_currency("₹1500") == "INR"


def test_calculate_field_confidence():
    # Exact anchor match on digital source
    conf_high = calculate_field_confidence("INV-2026-01", "INV-2026-01", has_anchor_match=True, source="digital_pdf")
    assert conf_high >= 0.95

    # OCR text match without anchor
    conf_med = calculate_field_confidence("1250.00", "1250.00", has_anchor_match=False, source="ocr")
    assert 0.70 <= conf_med <= 0.90

    # Empty value
    assert calculate_field_confidence("", None, has_anchor_match=False) == 0.0


def test_pattern_extractor_from_text():
    sample_invoice = """
    ACME Corporation
    Invoice Number: INV-98421
    Invoice Date: 2026-03-15
    Due Date: 2026-04-15
    Bill To: John Smith
    Contact: billing@acme.org
    Phone: (555) 234-5678
    Total Amount: $4,500.00
    Tax Amount: $350.00
    Reference: PO-99823
    """
    extractor = PatternExtractor()
    extracted = extractor.extract_from_text(sample_invoice)

    assert "invoice_number" in extracted
    assert extracted["invoice_number"]["extracted_value"] == "INV-98421"
    assert extracted["invoice_number"]["confidence"] >= 0.9

    assert "email" in extracted
    assert extracted["email"]["normalized_value"] == "billing@acme.org"

    assert "total_amount" in extracted
    assert extracted["total_amount"]["normalized_value"] == "4500.00"

    assert "currency" in extracted
    assert extracted["currency"]["normalized_value"] == "USD"
