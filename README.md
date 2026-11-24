# DocuFlow – Intelligent Document Processing & Workflow Automation

DocuFlow is a modern, enterprise-grade document processing platform that automates repetitive data extraction, validation, manual review workflows, and report generation from business documents (digital PDFs, scanned images, CSV files, and Excel spreadsheets).

---

## Key Features
- **Multi-Format Ingestion:** Drag-and-drop support for PDF, PNG, JPG, TIFF, CSV, and XLSX with SHA-256 deduplication and MIME validation.
- **Intelligent Processing Pipelines:**
  - Digital PDF extraction via PyMuPDF.
  - Scanned PDF & image OCR via Tesseract and Pillow preprocessing.
  - Tabular parsing via Pandas & OpenPyXL.
- **Configurable Field Extraction:** Automated pattern matching and normalization for Invoices, Names, Dates, Amounts, Tax, and Reference Numbers with mathematical confidence scoring.
- **Centralized Validation Engine:** Missing field detection, format checks (email, date, phone), duplicate checks, and consistency validation.
- **Human-in-the-Loop Review:** Dedicated review and approvals screen with real-time editing, visual status indicators (Valid, Warning, Invalid), and comprehensive audit trails.
- **Multi-Format Reporting:** Downloadable formatted Excel (.xlsx) workbooks and ReportLab PDF summaries.
- **Role-Based Access Control:** Strict RBAC separating Administrator, Processing Manager, and Viewer permissions.
- **Async & Scheduled Processing:** Background queuing with retry logic and scheduled task automation.

---

## Tech Stack
- **Backend:** FastAPI, Python 3.11+, SQLAlchemy 2.0, Alembic, Pydantic v2
- **Database:** PostgreSQL (with SQLite support for local dev/testing)
- **Frontend:** Jinja2 templates, Chart.js, Linear/Stripe-inspired custom CSS
- **Workers & Queues:** Celery, Redis, Celery Beat
- **Document Processing:** PyMuPDF, pytesseract, Pillow, Pandas, OpenPyXL, ReportLab
- **Testing:** pytest, pytest-asyncio, httpx

---

## Quickstart

### 1. Setup Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure settings as desired:
```bash
cp .env.example .env
```

### 3. Initialize Database & Seed Default Admin
```bash
python scripts/init_db.py
```
Default accounts created:
- **Administrator:** `admin@docuflow.com` / `Admin@123456`
- **Processing Manager:** `manager@docuflow.com` / `Manager@123456`
- **Viewer:** `viewer@docuflow.com` / `Viewer@123456`

### 4. Run Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Team Contributions Structure (M1–M6)
- **`app/`**: Core application development owned by M1.
- **`team_contributions/`**: Isolated contribution workspaces:
  - `M2_testing/`: Test cases, defect logs, test execution results.
  - `M3_ocr_evaluation/`: Sample ground-truth documents and CER/WER accuracy benchmarking.
  - `M4_validation/`: Boundary tests, corrupt files, and validation detection rate audits.
  - `M5_reports_analytics/`: Export format audits, KPI calculation verification.
  - `M6_documentation_security/`: User manuals, workflow documentation, and security audit checklists.
