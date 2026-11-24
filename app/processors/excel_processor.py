from typing import Dict, Any, List
from pathlib import Path
import pandas as pd
from app.processors.base import BaseProcessor


class ExcelProcessor(BaseProcessor):
    """Processes Excel workbooks (.xlsx) using pandas and openpyxl."""

    def process(self, file_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        # Read all sheets or primary sheet
        excel_file = pd.ExcelFile(file_path, engine="openpyxl")
        sheet_names = excel_file.sheet_names

        all_records = []
        raw_text_parts = [f"Excel Workbook: {len(sheet_names)} sheet(s): {', '.join(sheet_names)}"]

        for sheet in sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet)
            df.columns = [str(c).strip() for c in df.columns]
            df = df.where(pd.notnull(df), None)

            sheet_records = df.to_dict(orient="records")
            for r in sheet_records:
                r["_sheet_name"] = sheet
                all_records.append(r)

            raw_text_parts.append(f"Sheet '{sheet}': {len(sheet_records)} rows, Columns: {', '.join(df.columns)}")

        return {
            "raw_text": "\n".join(raw_text_parts),
            "pages": [],
            "records": all_records,
            "metadata": {
                "sheet_names": sheet_names,
                "total_rows": len(all_records),
                "processor": "ExcelProcessor (Pandas + OpenPyXL)"
            }
        }
