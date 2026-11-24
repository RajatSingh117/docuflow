# DocuFlow RESTful API Reference

DocuFlow exposes an OpenAPI 3.0-compliant RESTful interface for document ingestion, processing automation, human validation, report generation, and system analytics.

All authenticated requests must include either:
- **Authorization header:** `Authorization: Bearer <jwt_token>`
- **HTTP-only cookie:** `access_token=<jwt_token>`

---

## 1. Authentication & User Management

### `POST /api/auth/login`
Authenticate credentials and issue JWT access token.
- **Access:** Public
- **Request Body:**
  ```json
  {
    "email": "manager@docuflow.com",
    "password": "Manager@123456"
  }
  ```
- **Response 200 OK:**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": 2,
      "email": "manager@docuflow.com",
      "name": "Processing Manager",
      "role": "processing_manager"
    }
  }
  ```

### `POST /api/auth/logout`
Revoke session cookie.
- **Access:** Authenticated

### `GET /api/auth/me`
Retrieve profile of currently authenticated user.
- **Access:** Authenticated

### `GET /api/users`
List system users.
- **Access:** Admin only

### `POST /api/users`
Create new user account with assigned role.
- **Access:** Admin only
- **Roles:** `admin`, `processing_manager`, `viewer`

---

## 2. Document Management

### `POST /api/documents/upload`
Upload and validate a business document (PDF, CSV, XLSX, JPG, PNG, TIFF).
- **Access:** `admin`, `processing_manager`
- **Request:** `multipart/form-data` with `file`
- **Validations:** Magic byte verification, max size 20MB, SHA-256 deduplication
- **Response 201 Created:**
  ```json
  {
    "id": 14,
    "original_filename": "invoice_march.pdf",
    "file_type": "pdf",
    "file_size": 184520,
    "checksum": "a8f5c9...",
    "uploaded_at": "2026-03-15T10:30:00Z",
    "status": "STORED"
  }
  ```

### `GET /api/documents`
List documents with search and format filtering.
- **Access:** All authenticated users (`admin`, `manager`, `viewer`)
- **Query Params:** `search`, `file_type`, `skip`, `limit`

### `GET /api/documents/{document_id}`
Retrieve document metadata.
- **Access:** All authenticated users

### `GET /api/documents/{document_id}/download`
Download stored file (with path traversal protection).
- **Access:** All authenticated users

### `DELETE /api/documents/{document_id}`
Delete document and cascade associated jobs.
- **Access:** `admin`, `processing_manager`

---

## 3. Processing & OCR Pipelines

### `POST /api/processing/jobs`
Trigger extraction job for an uploaded document.
- **Access:** `admin`, `processing_manager`
- **Request Body:**
  ```json
  {
    "document_id": 14,
    "processing_type": "auto"
  }
  ```
- **Response 201 Created:** Returns job with current status (`NEEDS_REVIEW`, `EXTRACTED`, etc.)

### `GET /api/processing/jobs`
List processing jobs with status filters.
- **Access:** All authenticated users

### `GET /api/processing/jobs/{job_id}`
Retrieve full job details, execution duration, and audit logs.
- **Access:** All authenticated users

### `POST /api/processing/jobs/{job_id}/retry`
Retry a failed processing job.
- **Access:** `admin`, `processing_manager`

---

## 4. Human-in-the-Loop Review & Approvals

### `GET /api/reviews/{job_id}`
Get records and extracted fields with confidence scores for verification.
- **Access:** All authenticated users
- **Response:**
  ```json
  {
    "job_id": 4,
    "document_name": "invoice.pdf",
    "status": "NEEDS_REVIEW",
    "records": [
      {
        "id": 1,
        "record_number": 1,
        "is_approved": false,
        "fields": [
          {
            "id": 12,
            "field_name": "total_amount",
            "raw_value": "$8,305.00",
            "normalized_value": "8305.00",
            "confidence_score": 0.98,
            "validation_status": "VALID"
          }
        ]
      }
    ]
  }
  ```

### `PUT /api/reviews/fields/{field_id}`
Manually correct an extracted field value. Automatically re-evaluates validation rules and logs audit entry.
- **Access:** `admin`, `processing_manager`
- **Request Body:**
  ```json
  {
    "new_value": "8305.00"
  }
  ```

### `POST /api/reviews/records/{record_id}/approve`
Approve an individual record. Blocked if record contains unresolved `INVALID` fields.
- **Access:** `admin`, `processing_manager`

### `POST /api/reviews/jobs/{job_id}/approve-all`
Bulk-approve all valid records in a job and mark job `COMPLETED`.
- **Access:** `admin`, `processing_manager`

---

## 5. Report Export

### `POST /api/reports/generate`
Generate formatted Excel workbook or PDF report for a processed job.
- **Access:** `admin`, `processing_manager`
- **Request Body:**
  ```json
  {
    "processing_job_id": 4,
    "report_type": "excel"
  }
  ```

### `GET /api/reports`
List generated reports.
- **Access:** All authenticated users

### `GET /api/reports/{report_id}/download`
Download generated Excel or PDF file.
- **Access:** All authenticated users

---

## 6. Scheduled Automation

### `GET /api/schedules`
List recurring scheduled processing jobs and execution history.
- **Access:** All authenticated users

### `POST /api/schedules`
Create recurring automation schedule.
- **Access:** `admin`, `processing_manager`
- **Schedule Types:** `daily`, `weekly`, `monthly`

### `PUT /api/schedules/{schedule_id}/toggle`
Pause or resume scheduled automation.
- **Access:** `admin`, `processing_manager`

### `POST /api/schedules/{schedule_id}/run`
Trigger immediate manual execution of a schedule.
- **Access:** `admin`, `processing_manager`

### `DELETE /api/schedules/{schedule_id}`
Delete automation schedule.
- **Access:** `admin`, `processing_manager`

---

## 7. Analytics & Dashboard

### `GET /api/analytics/dashboard`
Live executive KPIs (total documents, success rate, failure rate, average duration, recent files).
- **Access:** All authenticated users

### `GET /api/analytics/detailed`
Detailed analytics breakdown: performance by file type, confidence distribution, accuracy rate, and report metrics.
- **Access:** All authenticated users
