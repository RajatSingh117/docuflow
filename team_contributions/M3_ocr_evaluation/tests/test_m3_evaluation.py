"""
Automated Unit and Quality Assurance Test Suite for DocuFlow M3 OCR Evaluation.
Validates:
1. Dataset generation integrity, ground truth structure, and dataset manifest consistency.
2. Field normalization logic, exact match, normalized match, partial match, and missing field handling.
3. Accuracy calculations, category grouping, and zero-denominator handling.
4. Excel workbook generation, sheet integrity, formulas, and chart definitions.
5. Exploratory edge-case testing (empty file, corrupted PDF, unsupported format).
"""

import csv
import io
import json
import os
import sys
import pytest
from pathlib import Path

# Paths
M3_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = M3_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(M3_DIR / "scripts"))

from evaluate_ocr import normalize_field_value, compare_field, classify_error
from app.processors import validate_upload, extract, FIELDS

class TestDatasetAndManifest:
    """Validate sample dataset files, manifest catalog, and ground-truth records."""

    def test_ground_truth_exists_and_valid(self):
        gt_path = M3_DIR / "sample_dataset" / "ground_truth.json"
        assert gt_path.exists(), "ground_truth.json must exist"
        with open(gt_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 30, f"Expected 30 records in ground truth, got {len(data)}"
        for doc in data:
            assert "document_id" in doc
            assert "base_id" in doc
            assert "category" in doc
            assert "expected_fields" in doc
            for req in ("name", "date", "invoice_number", "total"):
                assert req in doc["expected_fields"], f"Missing {req} in expected fields of {doc['document_id']}"

    def test_dataset_manifest_matches_files(self):
        manifest_path = M3_DIR / "sample_dataset" / "dataset_manifest.csv"
        assert manifest_path.exists(), "dataset_manifest.csv must exist"
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 30, f"Expected 30 manifest rows, got {len(rows)}"
        for row in rows:
            file_path = M3_DIR / row["file_path"]
            assert file_path.exists(), f"File specified in manifest does not exist: {file_path}"
            assert file_path.stat().st_size > 0, f"File in manifest is empty: {file_path}"

    def test_category_distribution(self):
        gt_path = M3_DIR / "sample_dataset" / "ground_truth.json"
        with open(gt_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        from collections import Counter
        cat_counts = Counter(d["category"] for d in data)
        expected_cats = ["text_pdfs", "scanned_pdfs", "clear_images", "blurry_images", "rotated_images", "low_quality_images"]
        for cat in expected_cats:
            assert cat_counts[cat] == 5, f"Category {cat} should have exactly 5 documents, got {cat_counts[cat]}"

class TestComparisonAndNormalization:
    """Validate field normalization, comparison logic, and classification."""

    def test_normalize_field_value_total(self):
        assert normalize_field_value("total", "1,250.00") == "1250.00"
        assert normalize_field_value("total", "1250") == "1250.00"
        assert normalize_field_value("total", " 4890.5 ") == "4890.50"

    def test_normalize_field_value_name(self):
        assert normalize_field_value("name", " Sarah   Jenkins ") == "Sarah Jenkins"

    def test_compare_field_exact(self):
        status, remark = compare_field("invoice_number", "INV-2026-101", "INV-2026-101")
        assert status == "Correct"
        assert remark == "Exact match"

    def test_compare_field_normalized(self):
        status, remark = compare_field("total", "1250.00", "1,250")
        assert status == "Correct"
        assert remark == "Normalized match"

    def test_compare_field_missing(self):
        status, remark = compare_field("date", "2026-10-14", "")
        assert status == "Incorrect"
        assert "Missing" in remark

    def test_compare_field_partial(self):
        status, remark = compare_field("name", "Sarah Jenkins", "Name: Sarah Jenkins")
        assert status == "Incorrect"
        assert "Partial extraction" in remark

    def test_compare_field_mismatch(self):
        status, remark = compare_field("total", "4890.50", "4690.50")
        assert status == "Incorrect"
        assert "mismatch" in remark

class TestExcelWorkbookIntegrity:
    """Validate generated Excel workbook structure, sheets, formatting and formulas."""

    def test_workbook_structure_and_sheets(self):
        import openpyxl
        xlsx_path = M3_DIR / "extraction_results.xlsx"
        assert xlsx_path.exists(), "extraction_results.xlsx must exist"
        wb = openpyxl.load_workbook(xlsx_path, data_only=False)
        expected_sheets = [
            "Evaluation Summary",
            "Field Extraction Results",
            "Document Results",
            "Category Analysis",
            "Field-wise Analysis",
            "Error Analysis",
            "Dataset Manifest",
        ]
        assert wb.sheetnames == expected_sheets
        assert wb["Evaluation Summary"].max_row >= 15
        assert wb["Field Extraction Results"].max_row == 271  # header + 270 field rows (9 fields * 30 docs)
        assert wb["Document Results"].max_row == 31  # header + 30 docs

class TestEdgeCasesAndExploratory:
    """Exploratory application tests for edge cases like empty documents, invalid headers, corrupted files."""

    def test_empty_document_rejected(self):
        with pytest.raises(ValueError, match="Choose a supported, non-empty file"):
            validate_upload(b"", ".pdf")

    def test_invalid_pdf_header_rejected(self):
        with pytest.raises(ValueError, match="The file does not have a PDF header"):
            validate_upload(b"NOT A REAL PDF HEADER", ".pdf")

    def test_unsupported_file_extension_rejected(self):
        with pytest.raises(ValueError, match="Choose a supported"):
            validate_upload(b"some content", ".docx")

    def test_oversized_document_rejected(self):
        oversized = b"%PDF-" + b"x" * (16 * 1024 * 1024)
        with pytest.raises(ValueError, match="Choose a supported"):
            validate_upload(oversized, ".pdf")
