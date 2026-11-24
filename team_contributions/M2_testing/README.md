# M2 — Testing & Quality Assurance

## Responsibilities & Scope
The M2 team member is responsible for end-to-end testing, quality assurance, defect reporting, and test coverage tracking for the DocuFlow platform.

### Core Deliverables
1. `test_cases.xlsx`: Comprehensive test case spreadsheet covering:
   - Authentication & Role-Based Access Control (Admin, Processing Manager, Viewer).
   - Document upload validation (supported formats, corrupt files, size limits, duplicate checksums).
   - Extraction pipelines (PDF, OCR, CSV, Excel).
   - Data validation rules (required fields, format checks, consistency).
   - Review and manual approval workflows.
   - Report generation and authorization checks.
2. `bug_reports.md`: Documented defect logs with reproduction steps, severity, and status.
3. `test_results.md`: Formal test execution summaries and pass rate logs.

### Submission Instructions
1. Fork or branch from `main`: `git checkout -b feature/m2-testing-qa`.
2. Keep all testing artifacts, matrices, and defect reports within `team_contributions/M2_testing/`.
3. Do not modify core application files in `app/` without M1 approval.
4. Submit a Pull Request targeting `main` with detailed notes on tests executed.
