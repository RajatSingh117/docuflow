# Application Workflow Documentation

## Workflow A: Upload & Process Document
1. User authenticates via `/api/auth/login`.
2. User uploads file via `/api/documents/upload`.
3. Backend validates MIME type, extension, size limit (20MB), and calculates SHA-256 checksum.
4. Document record created in `documents` table with randomized storage filename.
5. User initiates processing via `/api/processing/start`.
6. Processing job created with status `QUEUED` -> `PROCESSING`.
7. Pipeline routes by type:
   - Digital PDF -> PyMuPDF
   - Scanned PDF / Image -> Pillow + Tesseract OCR
   - CSV / Excel -> Pandas / OpenPyXL
8. Configured fields are extracted using pattern and regex extractors.
9. Validation engine executes rules (Required, Format, Duplicate, Consistency).
10. Records saved in `extracted_records` with status `NEEDS_REVIEW` or `COMPLETED`.
11. User reviews, edits values, and approves records.
12. Status moves to `COMPLETED`.

## Workflow B: Generate Reports
1. User requests Excel or PDF export for approved job.
2. Report generator builds formatted workbook / document.
3. Metadata saved in `generated_reports`.
4. Authorized user downloads report.

## Workflow C: Scheduled Processing
1. Admin / Manager creates schedule with cron/interval rules.
2. Background task triggers job execution.
3. Full audit and processing history recorded.

## Workflow D: Failed Job Recovery
1. Processing errors caught and logged in `processing_logs`.
2. Job marked `FAILED` with detailed error summary.
3. Authorized manager can inspect error and trigger retry.
