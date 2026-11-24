import re
from typing import Dict, Any, List, Optional
from app.extractors.normalizers import (
    normalize_date,
    normalize_amount,
    normalize_currency,
    normalize_phone,
    normalize_text,
)
from app.extractors.confidence import calculate_field_confidence

PATTERNS = {
    "invoice_number": [
        (re.compile(r'(?i)(?:invoice\s*(?:no|number|#|id)?[:\s#]*)([A-Z0-9-]{3,24})'), True),
        (re.compile(r'(?i)(?:bill\s*(?:no|number|#)?[:\s#]*)([A-Z0-9-]{3,24})'), True),
        (re.compile(r'\b(INV-[0-9]{4,8})\b'), False),
    ],
    "email": [
        (re.compile(r'(?i)(?:email|e-mail)?[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)'), True),
        (re.compile(r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b'), False),
    ],
    "phone": [
        (re.compile(r'(?i)(?:phone|tel|mobile|cell)?[:\s]*(\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'), True),
        (re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), False),
    ],
    "invoice_date": [
        (re.compile(r'(?i)(?:invoice\s*date|bill\s*date|date\s*of\s*issue)[:\s]*([A-Za-z0-9,.\s/-]{6,25})'), True),
    ],
    "due_date": [
        (re.compile(r'(?i)(?:due\s*date|payment\s*due)[:\s]*([A-Za-z0-9,.\s/-]{6,25})'), True),
    ],
    "date": [
        (re.compile(r'(?i)(?:date)[:\s]*([A-Za-z0-9,.\s/-]{6,25})'), True),
        (re.compile(r'\b(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b'), False),
    ],
    "total_amount": [
        (re.compile(r'(?i)(?:total\s*amount|total\s*due|amount\s*due|grand\s*total|balance\s*due|total)[:\s]*([$€£₹]?\s*[\d,]+(?:\.\d{2})?)'), True),
        (re.compile(r'(?i)(?:amount|net\s*total)[:\s]*([$€£₹]?\s*[\d,]+(?:\.\d{2})?)'), True),
    ],
    "tax_amount": [
        (re.compile(r'(?i)(?:tax\s*amount|tax|vat|gst)[:\s]*([$€£₹]?\s*[\d,]+(?:\.\d{2})?)'), True),
    ],
    "currency": [
        (re.compile(r'\b(USD|EUR|GBP|INR|CAD|AUD)\b'), False),
        (re.compile(r'([$€£₹])'), False),
    ],
    "company_name": [
        (re.compile(r'(?i)(?:bill\s*to|sold\s*to|customer|client)[:\s]*([A-Za-z0-9\s,&.]{3,40})'), True),
        (re.compile(r'(?i)(?:vendor|company|from|payable\s*to)[:\s]*([A-Za-z0-9\s,&.]{3,40})'), True),
    ],
    "document_reference": [
        (re.compile(r'(?i)(?:reference|ref|order\s*#|po\s*#)[:\s#]*([A-Za-z0-9-]{4,24})'), True),
    ],
    "full_name": [
        (re.compile(r'(?i)(?:name|contact\s*name|attention|attn)[:\s]*([A-Z][a-z]+\s+[A-Z][a-z]+)'), True),
    ]
}


class PatternExtractor:
    """Extracts business entities from text using compiled pattern matching."""

    def extract_from_text(self, text: str, source: str = "regex") -> Dict[str, Dict[str, Any]]:
        """Extract configured fields from unstructured document text."""
        results = {}

        for field_name, pattern_list in PATTERNS.items():
            found_val = None
            has_anchor = False

            for pattern, is_anchored in pattern_list:
                match = pattern.search(text)
                if match:
                    # Prefer first group if captured
                    found_val = match.group(1).strip() if match.groups() else match.group(0).strip()
                    has_anchor = is_anchored
                    break

            if found_val:
                # Normalization
                norm_val = found_val
                if field_name in ["invoice_date", "due_date", "date"]:
                    norm_val = normalize_date(found_val)
                elif field_name in ["total_amount", "tax_amount"]:
                    norm_float = normalize_amount(found_val)
                    norm_val = f"{norm_float:.2f}" if norm_float is not None else found_val
                elif field_name == "currency":
                    norm_val = normalize_currency(found_val)
                elif field_name == "phone":
                    norm_val = normalize_phone(found_val)
                else:
                    norm_val = normalize_text(found_val)

                confidence = calculate_field_confidence(found_val, norm_val, has_anchor, source)

                results[field_name] = {
                    "extracted_value": found_val,
                    "normalized_value": norm_val,
                    "confidence": confidence,
                    "source": source
                }

        # Derive currency from total amount if not explicitly found
        if "total_amount" in results and "currency" not in results:
            raw_amt = results["total_amount"]["extracted_value"]
            curr = normalize_currency(raw_amt)
            results["currency"] = {
                "extracted_value": curr,
                "normalized_value": curr,
                "confidence": 0.92,
                "source": "derived"
            }

        return results

    def extract_from_row(self, row: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract and map configured fields from tabular rows (CSV / Excel)."""
        results = {}
        # Normalize column names in row for case-insensitive matching
        row_normalized = {str(k).lower().replace(" ", "_").replace("-", "_"): (k, v) for k, v in row.items()}

        field_mappings = {
            "invoice_number": ["invoice_number", "invoice_no", "inv_no", "invoice_id", "bill_no", "invoiceno", "invoice"],
            "invoice_date": ["invoice_date", "bill_date", "date_issued"],
            "due_date": ["due_date", "payment_due"],
            "date": ["date", "transaction_date", "created_date"],
            "total_amount": ["total_amount", "total", "amount", "total_due", "grand_total", "balance_due", "balance"],
            "tax_amount": ["tax_amount", "tax", "vat", "gst"],
            "currency": ["currency", "curr"],
            "email": ["email", "email_address", "contact_email"],
            "phone": ["phone", "phone_number", "telephone", "mobile"],
            "full_name": ["full_name", "name", "customer_name", "client_name"],
            "company_name": ["company_name", "company", "vendor", "client", "customer"],
            "document_reference": ["reference", "ref_no", "ref", "order_id", "po_number"]
        }

        for target_field, aliases in field_mappings.items():
            matched_key = None
            for alias in aliases:
                if alias in row_normalized:
                    matched_key = alias
                    break

            if matched_key:
                orig_key, orig_val = row_normalized[matched_key]
                val_str = str(orig_val).strip() if orig_val is not None else ""

                if val_str:
                    norm_val = val_str
                    if target_field in ["date", "invoice_date", "due_date"]:
                        norm_val = normalize_date(val_str)
                    elif target_field in ["total_amount", "tax_amount"]:
                        norm_float = normalize_amount(val_str)
                        norm_val = f"{norm_float:.2f}" if norm_float is not None else val_str
                    elif target_field == "currency":
                        norm_val = normalize_currency(val_str)
                    elif target_field == "phone":
                        norm_val = normalize_phone(val_str)

                    confidence = calculate_field_confidence(val_str, norm_val, has_anchor_match=True, source="table")

                    results[target_field] = {
                        "extracted_value": val_str,
                        "normalized_value": norm_val,
                        "confidence": confidence,
                        "source": "table"
                    }

        return results
