# DocuFlow M3: Actionable Improvement Recommendations

**Document Version:** 1.1.0 (Audited & Verified)  
**Assigned Working Directory:** `team_contributions/M3_ocr_evaluation/`  

---

## 1. Prioritized Technical Recommendations

Based strictly on empirical evaluation evidence and verified implementation defects, the following improvements are recommended for future application updates.

> [!IMPORTANT]
> In accordance with project non-negotiable rules, these recommendations are documented for team lead review and approval. No modifications have been made to files inside `app/`.

| Priority | Improvement Recommendation | Observed Problem Addressed | Expected Benefit | Implementation Complexity |
|---|---|---|---|---|
| **P0** | **Fix Regex Overcapture for Field Aliases** | `name` captured as `"Name: Sarah Jenkins"` (0% accuracy on clean docs) | Restores `name` accuracy from 0% to 100% on clean documents | Low (< 10 lines in `app/processors.py`) |
| **P0** | **Graceful Handling of Unreadable Documents** | `DOC_023` raised unhandled `ValueError`, crashing document processing | Prevents unhandled job worker crashes on unreadable documents | Low (Try-except block in `extract`) |
| **P0** | **Automated Deskew & Rotation Correction (OSD)** | 100% failure on tested images rotated 15°–180° | Restores document extraction across multi-angle scans | Medium (OpenCV / Tesseract OSD) |
| **P1** | **Pre-OCR Image Preprocessing Pipeline** | Severe failure on blurry documents, numeral substitution on low quality | Enhances OCR glyph segmentation on noisy mobile captures | Medium (Pillow / OpenCV filters) |
| **P1** | **Expand Supported Schema to Common Invoice Fields** | Critical fields (`due_date`, `email`, `phone`, `tax`, `currency`) completely ignored | Enables commercial invoice processing beyond basic 4-field stub | Low (Update `FIELDS` & `ALIASES` tuples) |
| **P2** | **Cross-Field Mathematical Verification** | `4890.50` misread as `4690.50` without detection | Automatically flags discrepancy when `subtotal + tax != total` | Low (Logic in `app.processors.validate`) |
| **P2** | **Confidence Score Extraction & Thresholding** | Application currently has zero confidence awareness (returns binary text) | Routes low-confidence extractions (< 70%) to human review automatically | Medium (`pytesseract.image_to_data`) |
| **P3** | **Tabular Line-Item Extraction Engine** | Line items (items, quantities, unit prices) discarded during extraction | Transforms DocuFlow into a complete end-to-end invoice automation system | High (Layout-aware model or PDF table parser) |

---

## 2. Technical Remediation Specifications

### P0.1: Regex Overcapture Fix
In `app/processors.py`, update line 84 to prevent crossing newlines and strip leading field key prefixes:
```python
# CURRENT: Greedily consumes newline into next line prefix
match = re.search(rf"^\s*(?:{labels})\s*[:#]\s*([^
]+)", text, re.I | re.M)

# PROPOSED: Strict single-line match with lookahead preventing subfield capture
match = re.search(rf"^[ 	]*(?:{labels})[ 	]*[:#][ 	]*(?!.*:)([^
]+)", text, re.I | re.M)
```

### P0.2: Automated Deskewing and Rotation Correction
In `app/processors.py:ocr(data)`:
```python
def preprocess_orientation(image: Image.Image) -> Image.Image:
    try:
        import pytesseract
        osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
        angle = osd.get("rotate", 0)
        if angle in (90, 180, 270):
            image = image.rotate(360 - angle, expand=True)
    except Exception:
        pass
    return image
```
