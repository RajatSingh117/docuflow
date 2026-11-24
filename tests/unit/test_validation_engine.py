from app.validators.engine import ValidationEngine
from app.models.extraction import ValidationStatus


def test_required_field_validation():
    engine = ValidationEngine()
    # Missing total_amount and invoice_number
    bad_record = {"email": "test@domain.com"}
    results = engine.validate_record(bad_record)

    missing_fields = [r["field_name"] for r in results if r["status"] == ValidationStatus.MISSING.value]
    assert "invoice_number" in missing_fields
    assert "total_amount" in missing_fields
    assert "invoice_date" in missing_fields

    overall_status = engine.compute_record_status(results)
    assert overall_status == ValidationStatus.MISSING


def test_format_validation():
    engine = ValidationEngine()
    record = {
        "invoice_number": "INV-100",
        "date": "2026-05-10",
        "total_amount": "invalid_number",
        "email": "not-an-email"
    }
    results = engine.validate_record(record)

    invalid_fields = [r["field_name"] for r in results if r["status"] == ValidationStatus.INVALID.value]
    assert "total_amount" in invalid_fields
    assert "email" in invalid_fields


def test_data_consistency_validation():
    engine = ValidationEngine()
    record = {
        "invoice_number": "INV-100",
        "invoice_date": "2026-05-15",
        "due_date": "2026-05-01",  # Due date before invoice date
        "total_amount": "100.00",
        "tax_amount": "150.00"     # Tax exceeds total
    }
    results = engine.validate_record(record)

    inconsistencies = [r["field_name"] for r in results if r["rule"] == "DATA_CONSISTENCY"]
    assert "due_date" in inconsistencies
    assert "tax_amount" in inconsistencies


def test_valid_record():
    engine = ValidationEngine()
    record = {
        "invoice_number": "INV-VALID-01",
        "invoice_date": "2026-04-01",
        "due_date": "2026-04-30",
        "total_amount": "1250.00",
        "tax_amount": "125.00",
        "email": "billing@company.com"
    }
    results = engine.validate_record(record)

    overall_status = engine.compute_record_status(results)
    assert overall_status == ValidationStatus.VALID
