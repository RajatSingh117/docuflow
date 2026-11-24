# Final Technical Documentation & Project Summary

## System Architecture
DocuFlow is built using:
- **Backend:** FastAPI (Python 3.11+) with asynchronous routing.
- **ORM & Database:** SQLAlchemy 2.0 with PostgreSQL (and local SQLite fallback for dev/testing).
- **Processing Pipelines:** PyMuPDF (digital PDFs), Tesseract OCR & Pillow (scans/images), Pandas & OpenPyXL (CSV/Excel).
- **Validation Engine:** Multi-rule validator calculating mathematical confidence scores.
- **Report Generation:** OpenPyXL (Excel) and ReportLab (PDF) with styled layouts.
- **Frontend:** Jinja2 templates, Chart.js, modern Tailwind-inspired SaaS stylesheet (Linear/Stripe aesthetic).
- **Security:** Strict RBAC, bcrypt password hashing, path traversal protection, SHA-256 deduplication.
