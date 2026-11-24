import tempfile
import pandas as pd
from app.processors.csv_processor import CSVProcessor
from app.processors.excel_processor import ExcelProcessor


def test_csv_processor():
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, newline="") as f:
        f.write("invoice_number,date,total_amount,email\n")
        f.write("INV-101,2026-01-10,500.00,client1@test.com\n")
        f.write("INV-102,2026-01-11,750.50,client2@test.com\n")
        temp_csv = f.name

    processor = CSVProcessor()
    result = processor.process(temp_csv)

    assert result["metadata"]["total_rows"] == 2
    assert len(result["records"]) == 2
    assert result["records"][0]["invoice_number"] == "INV-101"
    assert result["records"][1]["total_amount"] == 750.50


def test_excel_processor():
    df = pd.DataFrame({
        "invoice_number": ["INV-EXCEL-01", "INV-EXCEL-02"],
        "date": ["2026-02-01", "2026-02-02"],
        "amount": [1200.00, 2400.00]
    })
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        temp_excel = f.name
        df.to_excel(temp_excel, index=False, engine="openpyxl")

    processor = ExcelProcessor()
    result = processor.process(temp_excel)

    assert result["metadata"]["total_rows"] == 2
    assert result["records"][0]["invoice_number"] == "INV-EXCEL-01"
    assert result["records"][1]["amount"] == 2400.00
