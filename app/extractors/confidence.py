from typing import Optional


def calculate_field_confidence(
    extracted_value: Optional[str],
    normalized_value: Optional[str],
    has_anchor_match: bool,
    source: str = "regex"
) -> float:
    """
    Documented Mathematical Confidence Calculation:
    C = (w_pattern * S_pattern) + (w_format * S_format) + (w_source * S_source)
    
    Weights:
      w_pattern = 0.4 (Anchor label match strength)
      w_format  = 0.4 (Data format adherence after normalization)
      w_source  = 0.2 (Extraction origin fidelity)
    """
    if not extracted_value or not str(extracted_value).strip():
        return 0.0

    # Pattern specificity score (0.0 to 1.0)
    s_pattern = 1.0 if has_anchor_match else 0.7

    # Format verification score (0.0 to 1.0)
    s_format = 1.0 if normalized_value is not None else 0.4

    # Source score (0.0 to 1.0)
    if source in ["digital_pdf", "table", "csv", "excel"]:
        s_source = 1.0
    elif source == "ocr":
        s_source = 0.82
    elif source == "manual":
        s_source = 1.0
    else:
        s_source = 0.9

    confidence = (0.4 * s_pattern) + (0.4 * s_format) + (0.2 * s_source)
    return round(confidence, 2)
