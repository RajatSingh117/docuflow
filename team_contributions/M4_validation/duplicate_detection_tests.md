# Duplicate Detection Test Logs

## 1. Document-Level Checksum Deduplication
- **Algorithm:** SHA-256
- **Test Case:** Re-upload exact same document with identical content under a different filename.
- **Expected Result:** Application identifies identical checksum and flags duplicate upload.

| Test ID | File 1 Name | File 2 Name | Expected Action | Actual Status |
|---|---|---|---|---|
| DUP-DOC-01 | invoice_01.pdf | invoice_01_copy.pdf | Block / Flag Duplicate | Passed |

## 2. Record-Level Deduplication
- **Field:** Invoice Number
- **Test Case:** Process two distinct files containing duplicate invoice numbers.
- **Expected Result:** Record flagged with `DUPLICATE` warning.
