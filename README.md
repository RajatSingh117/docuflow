# DocuFlow – Intelligent Document Processing & Workflow Automation

DocuFlow is a modern, enterprise-grade document processing platform that automates repetitive data extraction, validation, manual review workflows, and report generation from business documents (digital PDFs, scanned images, CSV files, and Excel spreadsheets).

---

## Key Features
- **Multi-Format Ingestion:** Drag-and-drop support for PDF, PNG, JPG, TIFF, CSV, and XLSX with SHA-256 deduplication and magic-byte MIME validation.
- **Intelligent Processing Pipelines:**
  - Digital PDF extraction via PyMuPDF.
  - Scanned PDF & image OCR via Tesseract and Pillow contrast/threshold preprocessing.
  - Tabular parsing via Pandas & OpenPyXL.
- **Configurable Field Extraction:** Automated pattern matching and normalization for Invoices, Names, Dates, Amounts, Tax, and Reference Numbers with mathematical confidence scoring.
- **Centralized Validation Engine:** Missing field detection, format checks (email, date, phone), duplicate checks, and business consistency rules (e.g. Due Date &ge; Invoice Date, Total &ge; Subtotal).
- **Human-in-the-Loop Review:** Dedicated review and approvals screen with real-time editing, visual status indicators (Valid, Warning, Invalid, Needs Review), live re-validation, and comprehensive audit trails.
- **Multi-Format Reporting:** Downloadable formatted Excel (.xlsx) workbooks with KPI summaries and conditional formatting, plus ReportLab landscape PDF summaries.
- **Role-Based Access Control:** Strict RBAC separating Administrator, Processing Manager, and Viewer permissions.
- **Async & Scheduled Processing:** Background queuing with retry logic and scheduled task automation (Daily, Weekly, Monthly recurring runs).
- **Executive Analytics:** Live database-calculated KPIs, throughput metrics, format-specific success rates, confidence score distributions, and export coverage.

---

## Tech Stack
- **Backend:** FastAPI, Python 3.11+, SQLAlchemy 2.0, Alembic, Pydantic v2
- **Database:** PostgreSQL (with SQLite support for zero-dependency local dev/testing)
- **Frontend:** Jinja2 templates, Linear/Stripe-inspired custom CSS design system
- **Workers & Queues:** Celery, Redis
- **Document Processing:** PyMuPDF, pytesseract, Pillow, Pandas, OpenPyXL, ReportLab
- **Testing:** pytest, pytest-asyncio, httpx

---

## Documentation
- [System Architecture & Workflow Design](docs/architecture.md)
- [Database Schema Reference](docs/database_schema.md)
- [RESTful API Endpoint Reference](docs/api_reference.md)

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

### 3. Initialize Database & Seed Users
```bash
python scripts/init_db.py
```
Default seeded accounts:
- **Administrator:** `admin@docuflow.com` / `Admin@123456`
- **Processing Manager:** `manager@docuflow.com` / `Manager@123456`
- **Viewer:** `viewer@docuflow.com` / `Viewer@123456`

### 4. Database Migrations (Alembic)
```bash
alembic upgrade head
```

### 5. Generate Synthetic Test Documents & Demo Data (Optional)
```bash
python scripts/seed_synthetic_data.py
```
Populates `samples/pdfs`, `samples/csv`, `samples/excel`, and `samples/images`, and uploads live sample records into the database.

### 6. Run Background Worker (Optional for Async Queues)
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

### 7. Run Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Running the Test Suite
The complete test suite includes unit, integration, RBAC authorization, and edge-case tests:
```bash
pytest -v
```
To run specific suites:
```bash
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/authorization/ -v
pytest tests/edge_cases/ -v
```

---

## Team Contributions Structure (M1–M6)
- **`app/`**: Core application development owned by M1.
- **`team_contributions/`**: Isolated contribution workspaces:
  - `M2_testing/`: Test cases, defect logs, test execution results.
  - `M3_ocr_evaluation/`: Sample ground-truth documents and CER/WER accuracy benchmarking.
  - `M4_validation/`: Boundary tests, corrupt files, and validation detection rate audits.
  - `M5_reports_analytics/`: Export format audits, KPI calculation verification.
  - `M6_documentation_security/`: User manuals, workflow documentation, and security audit checklists.
