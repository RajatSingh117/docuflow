# M3 — OCR Evaluation & Accuracy Benchmarking

## Responsibilities & Scope
The M3 team member is responsible for benchmarking Tesseract OCR and text extraction accuracy across scanned PDFs and images.

### Core Deliverables
1. `sample_documents/`: Curated synthetic scanned documents and receipts for OCR benchmarking.
2. `expected_extractions.xlsx`: Manually labeled ground-truth text corresponding to sample documents.
3. `ocr_accuracy_report.md`: Documented Character Error Rate (CER) and Word Error Rate (WER) evaluations:
   - $CER = \frac{\text{Substitutions} + \text{Deletions} + \text{Insertions}}{\text{Total Reference Characters}}$
   - $WER = \frac{\text{Substitutions} + \text{Deletions} + \text{Insertions}}{\text{Total Reference Words}}$
4. `extraction_test_results.md`: Detailed breakdown of field-level OCR accuracy.

### Submission Instructions
1. Branch from `main`: `git checkout -b feature/m3-ocr-evaluation`.
2. Place test documents inside `team_contributions/M3_ocr_evaluation/sample_documents/`.
3. Submit evaluations in this directory only without modifying core application code.
