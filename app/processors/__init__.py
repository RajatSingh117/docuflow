from app.processors.base import BaseProcessor
from app.processors.pdf_processor import PDFProcessor
from app.processors.image_processor import ImageProcessor
from app.processors.csv_processor import CSVProcessor
from app.processors.excel_processor import ExcelProcessor


def get_processor(file_type: str) -> BaseProcessor:
    """Factory method to return the appropriate processor for a file type."""
    t = file_type.lower()
    if t == "pdf" or t == "pdf_digital":
        return PDFProcessor()
    elif t in ["png", "jpg", "jpeg", "tiff", "image", "ocr_scanned"]:
        return ImageProcessor()
    elif t == "csv":
        return CSVProcessor()
    elif t in ["xlsx", "excel"]:
        return ExcelProcessor()
    else:
        raise ValueError(f"No processor registered for file type: {file_type}")


__all__ = [
    "BaseProcessor",
    "PDFProcessor",
    "ImageProcessor",
    "CSVProcessor",
    "ExcelProcessor",
    "get_processor",
]
