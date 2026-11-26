# DocuFlow M3: OCR Evaluation Methodology & Pipeline Architecture

**Document Version:** 1.1.0 (Audited & Verified)  
**Author:** Assigned M3 Specialist — OCR Evaluation & Document Extraction  
**Date:** November 2026  
**Repository Branch:** `feature/m3-ocr-evaluation`  
**Contribution Scope:** `team_contributions/M3_ocr_evaluation/`  

---

## 1. Project Overview & Scope Context

DocuFlow is an intelligent document processing application designed to extract structured information from business documents into validated database records and downloadable reports.

Role **M3** is responsible for an empirical, evidence-based evaluation of DocuFlow's existing OCR and document extraction pipeline under diverse document quality conditions.

### Strict Non-Negotiable Operational Constraints
- All work is strictly quarantined within `team_contributions/M3_ocr_evaluation/`.
- Zero modifications have been made to application code inside `app/`, shared project configurations, or other team members' contribution folders.
- Evaluation runs directly against the genuine application service functions (`app.processors.extract` and `app.processors.validate`).
- Results represent the specific 30-document synthetic dataset evaluated and do not establish universal or production-scale OCR performance claims.

---

## 2. Existing DocuFlow Extraction Architecture

Inspection of `app/processors.py`, `app/jobs.py`, and `app/main.py` confirms the concrete document extraction workflow:

```mermaid
flowchart TD
    A["Input File Buffer"] --> BFile Extension
    B -->|".pdf"| C["PyMuPDF (fitz) Document Open"]
    B -->|".png / .jpg / .jpeg"| D["Tesseract CLI Subprocess"]
    B -->|".csv / .xlsx"| E["Pandas Structured Reader"]
    
    C --> FPage Native Text Length >= 20 chars?
    F -->|"Yes (Digital PDF)"| G["Native PDF Text Extraction (page.get_text())"]
    F -->|"No (Scanned PDF)"| H["Render Page Pixmap (scale factor <= 2.5)"]
    H --> I["Pipe Pixmap PNG to Tesseract CLI"]
    
    G --> J["Consolidated Text Stream"]
    I --> J
    D --> J
    
    J --> K["Regex Field Extraction (ALIASES)"]
    K --> L["Structured Record: (name, date, invoice_number, total)"]
    L --> M["Validation Engine (app.processors.validate)"]
    M --> N["Storage & Human Review Queue"]
```

### Verified Code Components
- **Extraction Dispatcher (`app/processors.py:extract`):**
  - **Text-based PDFs:** Extracted via `page.get_text().strip()`. Bypasses OCR when character count $\ge 20$.
  - **Scanned PDFs:** When `len(text) < 20`, page is rendered to PNG pixmap (`matrix=fitz.Matrix(scale, scale)`) and piped to Tesseract.
  - **Image Files:** PNG and JPEG files are passed directly to `ocr(data)`.
- **OCR Engine Subprocess (`app/processors.py:ocr`):**
  - Executes: `subprocess.run(["tesseract", "stdin", "stdout", "-l", "eng"], input=data, capture_output=True, timeout=35, check=True)`.
  - Configured for English (`-l eng`) using Tesseract default Page Segmentation Mode (PSM 3). No deskewing, rotation correction, or image preprocessing is applied before invoking Tesseract.
- **Field Extraction Logic (`app/processors.py:81-86`):**
  - Matches 4 supported fields using:
    `re.search(rf"^\s*(?:{labels})\s*[:#]\s*([^\r\n]+)", text, re.I | re.M)`
  - Target fields: `name`, `date`, `invoice_number`, `total`.

---

## 3. Synthetic Evaluation Dataset

A 30-document synthetic dataset was programmatically generated from 5 realistic base documents containing structured commercial fields.

| Document Category | Document Count | Format | Native Text Stream | Processing Pipeline | Quality Transformation Applied |
|---|---:|---|---|---|---|
| **Text-based PDFs** | 5 | PDF | Yes | PyMuPDF Native Text | Clean digital vector PDF with selectable text stream |
| **Scanned PDFs** | 5 | PDF | No | PyMuPDF Pixmap + OCR | 150 DPI raster image-only PDF (no text stream) |
| **Clear Images** | 5 | PNG | No | Direct Tesseract OCR | 1200x1600 px high-contrast, clean PNG |
| **Blurry Images** | 5 | PNG | No | Direct Tesseract OCR | Gaussian blur degradation (radii: 1.5, 2.5, 3.5, 4.5, 5.5) |
| **Rotated Images** | 5 | PNG | No | Direct Tesseract OCR | Rotation angles: 5°, 15°, 30°, 90°, 180° with white fill |
| **Low-quality Images** | 5 | PNG/JPG | No | Direct Tesseract OCR | JPEG quality 20, downsampling (3x, 2x), salt & pepper noise, contrast/brightness reduction |
| **Total Dataset** | **30** | — | — | — | **5 Matched Base Documents across 6 Categories** |

---

## 4. Evaluation & Comparison Methodology

1. **Ground Truth:** Predefined in `sample_dataset/ground_truth.json` prior to execution.
2. **Execution:** Each document was evaluated by calling DocuFlow's genuine `app.processors.extract` function.
3. **Evidence Archival:** Full execution payloads, raw extracted dictionaries, durations, and flags are saved in `raw_results/<DOC_ID>_raw.json`.
4. **Field Comparison Categorization:**
   - **Correct:** Exact match or non-masking normalized match (e.g., whitespace trim, currency decimal standardizing `1250.00` vs `1250`).
   - **Incorrect:** Includes explicit missing blanks, processing failures, character mismatches, and partial captures.
   - **Unsupported:** Fields present in the document but unsupported by DocuFlow's schema (`due_date`, `email`, `phone`, `tax`, `currency`). Evaluated separately.
5. **Accuracy Metric Formula:**
   $$\text{Accuracy (\%)} = \left( \frac{\text{Correctly Extracted Supported Fields}}{\text{Total Evaluated Supported Fields}} \right) \times 100$$
