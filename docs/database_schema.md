# DocuFlow Database Schema Reference

This document describes the complete relational database schema for DocuFlow, built with SQLAlchemy 2.0 and managed via Alembic migrations.

---

## Entity Relationship Overview

```
       +--------------------+
       |       users        |
       +--------------------+
         | 1        | 1    | 1
         |          |      +---------------------+
         | n        | n                          | n
+-----------------+ | +-----------------------+  | +-----------------------+
|    documents    | | |    processing_jobs    |  | |      audit_logs       |
+-----------------+ | +-----------------------+  | +-----------------------+
         | 1        |   | 1             | 1      |
         |          +---+               |        |
         | n                            | n      |
+-------------------+       +--------------------+
|  processing_jobs  |       | generated_reports  |
+-------------------+       +--------------------+
         | 1
         |
         | n
+-------------------+
| extracted_records |
+-------------------+
         | 1               | 1
         |                 |
         | n               | n
+-------------------+  +--------------------+
|  extracted_fields |  | validation_results |
+-------------------+  +--------------------+
```

---

## Table Schemas

### 1. `users`
Stores user identities, credentials, and access control roles.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Unique user identifier |
| `name` | String(120) | NOT NULL | User's full display name |
| `email` | String(255) | UNIQUE, NOT NULL, Index | Unique email address |
| `password_hash` | String(255) | NOT NULL | Salt and PBKDF2-HMAC-SHA256 hash |
| `role` | Enum | NOT NULL, Default: VIEWER | `admin`, `processing_manager`, `viewer` |
| `is_active` | Boolean | NOT NULL, Default: True | Account active status |
| `created_at` | DateTime | NOT NULL, UTC | Creation timestamp |
| `updated_at` | DateTime | NOT NULL, UTC | Last modification timestamp |
| `last_login` | DateTime | Nullable | Last successful login |

---

### 2. `documents`
Catalog of ingested business documents and files.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Unique document ID |
| `uploaded_by` | Integer | FK(`users.id`), Index | User who uploaded the file |
| `original_filename` | String(255) | NOT NULL, Index | Client filename |
| `stored_filename` | String(255) | UNIQUE, NOT NULL | Randomized UUID disk storage filename |
| `file_type` | String(20) | NOT NULL, Index | Canonical type (`pdf`, `csv`, `xlsx`, `png`, `jpg`, `tiff`) |
| `file_size` | Integer | NOT NULL | File size in bytes |
| `checksum` | String(64) | NOT NULL, Index | SHA-256 content hash |
| `storage_reference` | String(500) | NOT NULL | Absolute file system path |
| `upload_status` | Enum | NOT NULL, Default: STORED | `STORED`, `FAILED`, `ARCHIVED` |
| `uploaded_at` | DateTime | NOT NULL, UTC, Index | Upload timestamp |

---

### 3. `processing_jobs`
Lifecycle execution tracking for document processing and OCR.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Unique job ID |
| `document_id` | Integer | FK(`documents.id`, CASCADE), Index | Reference to source document |
| `created_by` | Integer | FK(`users.id`), Index | Initiating user |
| `processing_type` | String(50) | NOT NULL, Default: 'auto' | Pipeline type (`auto`, `pdf_digital`, `ocr_scanned`, `csv`, `excel`) |
| `status` | Enum | NOT NULL, Default: QUEUED, Index | `QUEUED`, `PROCESSING`, `EXTRACTED`, `NEEDS_REVIEW`, `COMPLETED`, `FAILED` |
| `retry_count` | Integer | NOT NULL, Default: 0 | Number of background retries |
| `error_summary` | Text | Nullable | Reason for failure |
| `started_at` | DateTime | Nullable | Processing start time |
| `completed_at` | DateTime | Nullable | Processing completion time |
| `processing_duration` | Float | Nullable | Execution wall time in seconds |
| `created_at` | DateTime | NOT NULL, UTC, Index | Job creation timestamp |

---

### 4. `processing_logs`
Chronological audit events recorded during pipeline execution.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Log entry ID |
| `processing_job_id` | Integer | FK(`processing_jobs.id`, CASCADE), Index | Target job |
| `log_level` | String(20) | NOT NULL | `INFO`, `WARNING`, `ERROR` |
| `stage` | String(50) | NOT NULL | Processing stage |
| `message` | Text | NOT NULL | Detailed event description |
| `created_at` | DateTime | NOT NULL, UTC | Timestamp |

---

### 5. `extracted_records`
Container for extracted business entities (e.g. invoice rows, table rows).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Record ID |
| `processing_job_id` | Integer | FK(`processing_jobs.id`, CASCADE), Index | Job reference |
| `record_number` | Integer | NOT NULL, Default: 1 | Sequential row index |
| `extracted_data` | JSON | NOT NULL | Key-value dictionary of extracted fields |
| `validation_status` | Enum | NOT NULL, Default: NEEDS_REVIEW, Index | `VALID`, `WARNING`, `INVALID`, `MISSING`, `NEEDS_REVIEW` |
| `confidence_score` | Float | NOT NULL, Default: 1.0 | Aggregated confidence score [0.0 - 1.0] |
| `is_approved` | Boolean | NOT NULL, Default: False | Approval flag |
| `created_at` | DateTime | NOT NULL, UTC | Timestamp |
| `updated_at` | DateTime | NOT NULL, UTC | Last modification timestamp |

---

### 6. `extracted_fields`
Granular attribute tracking for confidence scoring and human review.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Field ID |
| `record_id` | Integer | FK(`extracted_records.id`, CASCADE), Index | Parent record |
| `field_name` | String(100) | NOT NULL, Index | Name of field (e.g., `invoice_number`) |
| `raw_value` | Text | Nullable | Raw OCR/text extracted string |
| `normalized_value` | Text | Nullable | Standardized string (e.g., ISO date) |
| `confidence_score` | Float | NOT NULL, Default: 1.0 | Mathematical confidence [0.0 - 1.0] |
| `validation_status` | Enum | NOT NULL, Default: NEEDS_REVIEW | `VALID`, `WARNING`, `INVALID`, `MISSING`, `NEEDS_REVIEW` |
| `validation_message` | Text | Nullable | Descriptive validation note |
| `is_user_edited` | Boolean | NOT NULL, Default: False | Flag indicating human manual override |
| `previous_value` | Text | Nullable | Audit trail before edit |

---

### 7. `validation_results`
Rule-by-rule audit findings for compliance and data integrity.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Result ID |
| `record_id` | Integer | FK(`extracted_records.id`, CASCADE), Index | Target record |
| `field_name` | String(100) | NOT NULL, Index | Evaluated field |
| `rule_name` | String(100) | NOT NULL | Name of validation rule |
| `rule_category` | Enum | NOT NULL | `REQUIRED_FIELD`, `FORMAT`, `CONSISTENCY`, `DUPLICATE` |
| `status` | Enum | NOT NULL | `VALID`, `WARNING`, `INVALID`, `MISSING` |
| `message` | Text | NOT NULL | Human-readable explanation |
| `created_at` | DateTime | NOT NULL, UTC | Timestamp |

---

### 8. `generated_reports`
Exported audit summaries and analytical reports (Excel/PDF).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Report ID |
| `processing_job_id` | Integer | FK(`processing_jobs.id`, CASCADE), Index | Source job |
| `report_type` | String(20) | NOT NULL | `excel`, `pdf` |
| `filename` | String(255) | NOT NULL | Client-facing download filename |
| `storage_reference` | String(500) | NOT NULL | Safe disk storage path |
| `generated_by` | Integer | FK(`users.id`), Nullable | Requesting user |
| `created_at` | DateTime | NOT NULL, UTC, Index | Timestamp |

---

### 9. `scheduled_jobs` & `scheduled_job_executions`
Recurring cron and batch scheduling for automated pipeline runs.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Schedule ID |
| `name` | String(150) | NOT NULL | Human-friendly title |
| `schedule_type` | String(50) | NOT NULL | `daily`, `weekly`, `monthly` |
| `schedule_configuration` | JSON | Nullable | Targeted file types and filters |
| `is_active` | Boolean | NOT NULL, Default: True | Pause/Resume switch |
| `next_run_at` | DateTime | Nullable | Next scheduled trigger time |
| `created_by` | Integer | FK(`users.id`) | Creator user |
| `created_at` | DateTime | NOT NULL, UTC | Timestamp |
