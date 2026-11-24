# M4 — Data Validation & Edge Case Auditing

## Responsibilities & Scope
The M4 team member is responsible for evaluating the validation engine, testing duplicate detection, verifying boundary values, and ensuring corrupt/malformed records are accurately flagged.

### Core Deliverables
1. `validation_test_cases.xlsx`: Test cases covering:
   - Missing required fields (email, total amount, dates).
   - Format errors (malformed dates, invalid emails, negative numbers).
   - Data consistency issues (invoice total mismatch, end date before start date).
2. `sample_invalid_data/`: Intentionally corrupted and boundary test files.
3. `duplicate_detection_tests.md`: Test records and results for document-level SHA-256 checks and record-level duplicates (duplicate invoice IDs).
4. `validation_report.md`: Measured validation detection rate:
   - $\text{Validation Detection Rate} = \frac{\text{Correctly Detected Invalid Values}}{\text{Total Known Invalid Values}} \times 100$

### Submission Instructions
1. Branch from `main`: `git checkout -b feature/m4-validation-audit`.
2. Keep all test artifacts within `team_contributions/M4_validation/`.
3. Do not modify core validator rules in `app/validators/` without PR review by M1.
