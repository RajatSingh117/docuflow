# DocuFlow M3: Document Extraction Accuracy & Performance Report

**Report Version:** 1.1.0 (Audited & Reconciled)  
**Evaluation Date:** November 2026  
**Branch:** `feature/m3-ocr-evaluation`  
**Total Documents Evaluated:** 30  
**Total Supported Fields Evaluated:** 120  

---

## 1. Executive Summary

An empirical evaluation was executed against DocuFlow's genuine processing pipeline across 30 synthetic documents. All metrics reported below are calculated directly from the raw execution results preserved in `raw_results/`.

### Reconciled Key Performance Indicators (KPIs)

| Metric | Measured Value | Methodology & Reconciliation Basis |
|---|---:|---|
| **Overall Field Extraction Accuracy** | **45.00%** | 54 correct out of 120 evaluated supported fields |
| **Document Processing Success Rate** | **96.7%** (29/30) | Documents parsed without fatal exception |
| **Document Fatal Failure Rate** | **3.3%** (1/30) | Document `DOC_023` (30° rotation: `"No readable text was found"`) |
| **Total Evaluated Supported Fields** | **120** | 4 core fields (`name`, `date`, `invoice_number`, `total`) × 30 documents |
| **Correctly Extracted Fields** | **54** | Exact matches against ground-truth values |
| **Incorrectly Extracted Fields** | **66** | Total extraction failures across all failure categories |
| **Explicit Missing Fields (Blank Output)** | **39** (32.5%) | Fields where the reader returned empty text `""` |
| **Processing Failure Fields (Fatal Error)** | **4** (3.3%) | Supported fields in `DOC_023` lost due to fatal reader crash |
| **Total Unextracted Fields** | **43** (35.8%) | Sum of explicit blank fields (39) and processing failure fields (4) |
| **Partial Extractions** | **18** (15.0%) | Fields with regex label leakage (17 in `name`, 1 in `total`) |
| **OCR Substitution / Mismatches** | **5** (4.2%) | Character substitution (1 in `total`) or layout association errors (4 in `name`) |
| **Overall Mean Latency (All 30 Documents)** | **0.582s** | Arithmetic mean across all 30 processed documents |
| **Successful Documents Mean Latency (29 Docs)** | **0.584s** | Arithmetic mean across the 29 successfully parsed documents |

---

## 2. Category-Wise Extraction Performance

| Document Category | Document Count | Total Fields | Correct | Incorrect | Category Accuracy (%) | Category Mean Latency (s) | Primary Quality Impact Observed |
|---|---:|---:|---:|---:|---:|---:|---|
| **Text-based PDFs** | 5 | 20 | 15 | 5 | **75.00%** | 0.018s | High accuracy; only `name` failed due to regex prefix leakage |
| **Scanned PDFs** | 5 | 20 | 13 | 7 | **65.00%** | 0.880s | Strong OCR text recovery on clean 150 DPI scans |
| **Clear Images** | 5 | 20 | 15 | 5 | **75.00%** | 0.559s | 100% accurate on `date`, `invoice_number`, and `total` |
| **Blurry Images** | 5 | 20 | 1 | 19 | **5.00%** | 0.495s | Severe degradation; only 1 field readable across blur radii 1.5–5.5 |
| **Rotated Images** | 5 | 20 | 3 | 17 | **15.00%** | 0.984s | Severe failure on angles $\ge 15^\circ$; fatal crash at 30° |
| **Low-quality Images** | 5 | 20 | 7 | 13 | **35.00%** | 0.557s | Compression and noise caused missing fields and digit substitution |
| **Overall Micro-Average** | **30** | **120** | **54** | **66** | **45.00%** | **0.582s** | Micro-average across all 30 documents |

> **Note on Latency Reconciliations:**
> - Category mean latencies: text PDFs (0.018s), scanned PDFs (0.880s), clear images (0.559s), blurry images (0.495s), rotated images (0.984s), low-quality images (0.557s).
> - The arithmetic mean across all 30 individual documents is **0.582s**. Excluding the failed document `DOC_023` (0.532s) yields **0.584s** across the 29 successful documents.

---

## 3. Reconciled Field-Wise Analysis

| Field Name | Supported in Schema | Evaluated | Correct | Incorrect | Explicit Missing (Blank) | Processing Failures | Partial Extractions | Mismatches | Field Accuracy (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **name** | Yes (`FIELDS`) | 30 | 0 | 30 | 8 | 1 | 17 | 4 | **0.00%** |
| **date** | Yes (`FIELDS`) | 30 | 17 | 13 | 12 | 1 | 0 | 0 | **56.67%** |
| **invoice_number** | Yes (`FIELDS`) | 30 | 17 | 13 | 12 | 1 | 0 | 0 | **56.67%** |
| **total** | Yes (`FIELDS`) | 30 | 20 | 10 | 7 | 1 | 1 | 1 | **66.67%** |
| **due_date** | No (Unsupported) | 30 | 0 | 30 | 30 | 0 | 0 | 0 | **0.00%** (N/A) |
| **email** | No (Unsupported) | 30 | 0 | 30 | 30 | 0 | 0 | 0 | **0.00%** (N/A) |
| **phone** | No (Unsupported) | 30 | 0 | 30 | 30 | 0 | 0 | 0 | **0.00%** (N/A) |
| **tax** | No (Unsupported) | 30 | 0 | 30 | 30 | 0 | 0 | 0 | **0.00%** (N/A) |
| **currency** | No (Unsupported) | 30 | 0 | 30 | 30 | 0 | 0 | 0 | **0.00%** (N/A) |

### Reconciliation of Missing Field Discrepancy
- **Explicit Blank Fields:** 39 occurrences across successful document extractions (8 `name`, 12 `date`, 12 `invoice_number`, 7 `total`).
- **Processing Failure Fields:** 4 occurrences in `DOC_023` where the entire document failed processing.
- **Combined Unextracted Total:** **43 fields** (or **35.8%** of evaluated supported fields).
- The remaining 23 incorrect fields consist of 18 partial extractions (17 `name`, 1 `total`) and 5 value mismatches (4 `name`, 1 `total`), totaling **66 incorrect fields**.

---

## 4. Evidence References
- Raw per-document execution JSON: `raw_results/<DOC_ID>_raw.json`
- Master multi-sheet workbook: `extraction_results.xlsx`
- Summary dataset manifest: `sample_dataset/dataset_manifest.csv`
