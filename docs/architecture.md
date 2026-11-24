# DocuFlow Architecture & System Design

## 1. System Overview

**DocuFlow** is an enterprise-grade, end-to-end Intelligent Document Processing (IDP) and Workflow Automation platform. It ingests semi-structured and unstructured business documents (PDFs, scanned images, Excel workbooks, and CSV files), extracts target financial and identity fields using OCR and regex pattern extraction, calculates mathematical confidence scores, applies multi-layer validation rules, provides a human-in-the-loop review interface, and exports standardized reports.

---

## 2. High-Level Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                                  CLIENT TIER                                      |
|  - Modern Linear / Stripe-styled responsive UI (Jinja2 + Vanilla JS + CSS)        |
|  - RESTful API Clients (Mobile / External Microservices / Integrations)           |
+-----------------------------------------------------------------------------------+
                                         |
                                         | HTTPS (Session Cookie / JWT Bearer)
                                         v
+-----------------------------------------------------------------------------------+
|                                FASTAPI GATEWAY                                    |
|  - Security Middleware (CSP, X-Frame-Options, X-Content-Type-Options)             |
|  - RBAC & JWT Authentication (Admin, Processing Manager, Viewer)                  |
|  - Request Validation & Serialization (Pydantic v2)                               |
+-----------------------------------------------------------------------------------+
      |                      |                       |                       |
      v                      v                       v                       v
+---------------+     +---------------+       +---------------+      +---------------+
| Documents API |     |  Reviews API  |       |  Reports API  |      | Schedules API |
+---------------+     +---------------+       +---------------+      +---------------+
      |                      |                       |                       |
      v                      v                       v                       v
+-----------------------------------------------------------------------------------+
|                                 CORE SERVICES                                     |
|  - DocumentService: Magic-byte inspection, SHA-256 deduplication, safe storage    |
|  - ProcessingService: Pipeline dispatcher, execution logger                       |
|  - ValidationEngine: Mandatory, format, business consistency, uniqueness rules     |
|  - ReviewService: Human-in-the-loop field edits, audit logging, approvals         |
|  - AnalyticsService: Real-time SQL aggregations for KPIs and format breakdowns    |
+-----------------------------------------------------------------------------------+
      |                                              |
      v                                              v
+-----------------------------+        +--------------------------------------------+
|     PROCESSING PIPELINES    |        |             REPORT GENERATORS              |
| - PDFProcessor (PyMuPDF)    |        | - ExcelGenerator (OpenPyXL styled sheets)  |
| - ImageProcessor (Tesseract)|        | - PDFGenerator (ReportLab landscape tables)|
| - CSVProcessor (Pandas)     |        +--------------------------------------------+
| - ExcelProcessor (OpenPyXL) |
+-----------------------------+
      |
      v
+-----------------------------------------------------------------------------------+
|                             ASYNC WORKER & AUTOMATION                             |
|  - Celery Worker (Redis broker / Result backend)                                  |
|  - Celery Beat / Cron Automation for recurring document batch runs                |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                               PERSISTENCE & STORAGE                               |
|  - Relational DB: SQLite (Development) / PostgreSQL (Production) with SQLAlchemy  |
|  - File Storage: Local UUID-randomized storage / S3-compatible cloud storage      |
|  - Migrations: Alembic auto-generating schema version tracking                     |
+-----------------------------------------------------------------------------------+
```

---

## 3. End-to-End Processing Workflow

```
[Upload Document]
       │
       ▼
[Magic Byte & Size Validation] ──► Fails ──► Reject 400 Bad Request
       │ Passes
       ▼
[SHA-256 Hash Generation & UUID Storage]
       │
       ▼
[Create Processing Job (Queued)]
       │
       ▼
[Processor Dispatch]
  ├── PDF  ──► PyMuPDF digital extract + Tesseract fallback
  ├── PNG/JPG ──► Image contrast & threshold preprocessing + Tesseract OCR
  ├── CSV  ──► Pandas encoding-safe parser
  └── XLSX ──► OpenPyXL multi-sheet reader
       │
       ▼
[Pattern Extractor & Normalizers]
  Extracts: invoice_number, dates, currency, amounts, taxes, emails, phones, vendor
       │
       ▼
[Mathematical Confidence Engine]
  Confidence = 0.40 * S_pattern + 0.40 * S_format + 0.20 * S_source
       │
       ▼
[Validation Engine]
  ├── Required field checks (invoice_number, total_amount, date)
  ├── Format checks (RFC-5322 email, ISO-8601 date, float amounts)
  ├── Business consistency (due_date >= invoice_date, total >= subtotal)
  └── Duplicate invoice number detection across database records
       │
       ├── All Valid & High Confidence ──► Status: EXTRACTED / COMPLETED
       └── Has Warnings, Invalids, or Low Confidence ──► Status: NEEDS_REVIEW
                                                                 │
                                                                 ▼
                                                    [Human-in-the-Loop Review]
                                                    - Edit fields with audit log
                                                    - Re-run live validation
                                                    - Single / Bulk Record Approval
                                                                 │
                                                                 ▼
                                                    [Status: COMPLETED]
                                                                 │
                                                                 ▼
                                                    [Generate Excel / PDF Report]
```

---

## 4. Key Architectural Guarantees

1. **Role-Based Access Control (RBAC):**
   - `admin`: Full system control, user provisioning, role adjustments, all document actions.
   - `processing_manager`: Document upload, job execution, review approvals, reports, and scheduling.
   - `viewer`: Read-only access to documents, jobs, review data, reports, and dashboards.

2. **Security Hardening:**
   - **Path Traversal Protection:** All uploaded documents and generated reports use cryptographically randomized UUID filenames. Absolute paths are resolved and validated within application boundaries.
   - **MIME & Magic Byte Validation:** File extensions are cross-checked against actual initial binary byte sequences (e.g. `%PDF-` for PDFs, `\x89PNG` for PNGs, `PK\x03\x04` for OpenXML Excel).
   - **Security Headers:** Enforced via middleware (`Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`).
   - **PBKDF2 Password Hashing:** 100,000 rounds of PBKDF2-HMAC-SHA256 with unique 16-byte random salts.

3. **Production Database Compatibility:**
   - Designed for standard SQLAlchemy 2.0 ORM, operating seamlessly on SQLite (for zero-dependency local dev/tests) and PostgreSQL (for scalable enterprise production).
