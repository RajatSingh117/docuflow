from typing import Dict, Any, List
from pathlib import Path
import pandas as pd
from app.processors.base import BaseProcessor


class CSVProcessor(BaseProcessor):
    """Processes tabular CSV files using pandas with column mapping support."""

    def process(self, file_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # Attempt utf-8, fallback to latin-1
        try:
            df = pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding="latin-1")

        # Strip whitespace from headers
        df.columns = [str(c).strip() for c in df.columns]

        # Convert NaN to None for clean JSON serialization
        df = df.where(pd.notnull(df), None)

        records = df.to_dict(orient="records")

        # Generate readable raw_text summary
        raw_text = f"CSV Dataset: {len(records)} records, Columns: {', '.join(df.columns)}\n"
        preview_rows = records[:5]
        for idx, row in enumerate(preview_rows, 1):
            raw_text += f"Row {idx}: {row}\n"

        return {
            "raw_text": raw_text,
            "pages": [],
            "records": records,
            "metadata": {
                "columns": list(df.columns),
                "total_rows": len(records),
                "processor": "CSVProcessor (Pandas)"
            }
        }
