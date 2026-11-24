import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.extraction import ValidationStatus, ExtractedRecord, ExtractedField
from app.extractors.normalizers import normalize_date, normalize_amount


class ValidationEngine:
    """Centralized multi-category validation engine (PRD Section 3.6)."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def validate_record(
        self,
        record_data: Dict[str, Any],
        current_record_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Run all validation categories against record fields."""
        results = []

        # --- 1. Required Field Validation ---
        required_fields = ["invoice_number", "total_amount"]
        # Check either date or invoice_date
        has_date = bool(record_data.get("invoice_date") or record_data.get("date"))
        if not has_date:
            results.append({
                "field_name": "invoice_date",
                "rule": "REQUIRED_FIELD",
                "status": ValidationStatus.MISSING.value,
                "message": "Mandatory invoice date is missing from document."
            })

        for req in required_fields:
            val = record_data.get(req)
            if not val or not str(val).strip():
                results.append({
                    "field_name": req,
                    "rule": "REQUIRED_FIELD",
                    "status": ValidationStatus.MISSING.value,
                    "message": f"Mandatory field '{req}' is missing or empty."
                })

        # --- 2. Format Validation ---
        # Email format
        if "email" in record_data and record_data["email"]:
            email_val = str(record_data["email"]).strip()
            if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email_val):
                results.append({
                    "field_name": "email",
                    "rule": "FORMAT_EMAIL",
                    "status": ValidationStatus.INVALID.value,
                    "message": f"Malformed email address format: '{email_val}'."
                })
            else:
                results.append({
                    "field_name": "email",
                    "rule": "FORMAT_EMAIL",
                    "status": ValidationStatus.VALID.value,
                    "message": "Valid email address format."
                })

        # Dates format
        for date_key in ["invoice_date", "due_date", "date"]:
            if date_key in record_data and record_data[date_key]:
                d_val = str(record_data[date_key]).strip()
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', d_val):
                    results.append({
                        "field_name": date_key,
                        "rule": "FORMAT_DATE",
                        "status": ValidationStatus.WARNING.value,
                        "message": f"Date '{d_val}' is not in standard ISO YYYY-MM-DD format."
                    })
                else:
                    results.append({
                        "field_name": date_key,
                        "rule": "FORMAT_DATE",
                        "status": ValidationStatus.VALID.value,
                        "message": "Standard ISO 8601 date."
                    })

        # Total Amount format
        if "total_amount" in record_data and record_data["total_amount"]:
            amt = normalize_amount(record_data["total_amount"])
            if amt is None:
                results.append({
                    "field_name": "total_amount",
                    "rule": "FORMAT_NUMERIC",
                    "status": ValidationStatus.INVALID.value,
                    "message": f"Total amount '{record_data['total_amount']}' cannot be parsed as a numeric value."
                })
            elif amt <= 0:
                results.append({
                    "field_name": "total_amount",
                    "rule": "DATA_CONSISTENCY",
                    "status": ValidationStatus.INVALID.value,
                    "message": f"Total amount must be greater than zero. Found: {amt}."
                })
            else:
                results.append({
                    "field_name": "total_amount",
                    "rule": "FORMAT_NUMERIC",
                    "status": ValidationStatus.VALID.value,
                    "message": "Valid positive numeric amount."
                })

        # Tax Amount format
        if "tax_amount" in record_data and record_data["tax_amount"]:
            tax = normalize_amount(record_data["tax_amount"])
            if tax is None or tax < 0:
                results.append({
                    "field_name": "tax_amount",
                    "rule": "FORMAT_NUMERIC",
                    "status": ValidationStatus.INVALID.value,
                    "message": "Tax amount must be a non-negative numeric value."
                })

        # --- 3. Data Consistency ---
        # Total vs Tax
        tot_amt = normalize_amount(record_data.get("total_amount"))
        tax_amt = normalize_amount(record_data.get("tax_amount"))
        if tot_amt is not None and tax_amt is not None:
            if tax_amt > tot_amt:
                results.append({
                    "field_name": "tax_amount",
                    "rule": "DATA_CONSISTENCY",
                    "status": ValidationStatus.INVALID.value,
                    "message": f"Inconsistent amounts: Tax ({tax_amt}) exceeds Total Amount ({tot_amt})."
                })

        # Due Date vs Invoice Date
        inv_d_str = record_data.get("invoice_date") or record_data.get("date")
        due_d_str = record_data.get("due_date")
        if inv_d_str and due_d_str:
            try:
                inv_dt = datetime.strptime(str(inv_d_str)[:10], "%Y-%m-%d")
                due_dt = datetime.strptime(str(due_d_str)[:10], "%Y-%m-%d")
                if due_dt < inv_dt:
                    results.append({
                        "field_name": "due_date",
                        "rule": "DATA_CONSISTENCY",
                        "status": ValidationStatus.INVALID.value,
                        "message": f"Due date ({due_d_str}) cannot precede invoice date ({inv_d_str})."
                    })
            except Exception:
                pass

        # --- 4. Duplicate Validation ---
        inv_no = record_data.get("invoice_number")
        if inv_no and self.db:
            inv_str = str(inv_no).strip()
            # Query for duplicate invoice numbers in database
            dup_query = self.db.query(ExtractedField).filter(
                ExtractedField.field_name == "invoice_number",
                ExtractedField.normalized_value == inv_str
            )
            if current_record_id:
                dup_query = dup_query.filter(ExtractedField.extracted_record_id != current_record_id)
            duplicate_exists = dup_query.first()

            if duplicate_exists:
                results.append({
                    "field_name": "invoice_number",
                    "rule": "DUPLICATE_DETECTION",
                    "status": ValidationStatus.WARNING.value,
                    "message": f"Invoice number '{inv_str}' already exists in another extracted record."
                })
            else:
                results.append({
                    "field_name": "invoice_number",
                    "rule": "DUPLICATE_DETECTION",
                    "status": ValidationStatus.VALID.value,
                    "message": "Unique invoice identifier."
                })

        return results

    def compute_record_status(self, validation_results: List[Dict[str, Any]]) -> ValidationStatus:
        """Derive overall record status based on validation items."""
        statuses = [r["status"] for r in validation_results]
        if ValidationStatus.INVALID.value in statuses:
            return ValidationStatus.INVALID
        if ValidationStatus.MISSING.value in statuses:
            return ValidationStatus.MISSING
        if ValidationStatus.WARNING.value in statuses:
            return ValidationStatus.WARNING
        return ValidationStatus.VALID
