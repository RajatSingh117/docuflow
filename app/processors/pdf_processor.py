import io
from typing import Dict, Any, List
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
from app.processors.base import BaseProcessor
from app.processors.image_processor import ImageProcessor


class PDFProcessor(BaseProcessor):
    """Processes digital PDFs using PyMuPDF and falls back to OCR for scanned pages."""

    def __init__(self):
        self.image_processor = ImageProcessor()

    def process(self, file_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        doc = fitz.open(file_path)
        full_text_parts = []
        pages_info = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text").strip()
            ocr_used = False
            confidence = 1.0

            # Detect if page has insufficient extractable text (e.g. scanned document or image PDF)
            if len(text) < 40:
                # Render page to high-res pixmap (DPI 300 equivalent)
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                processed_img = self.image_processor.preprocess_image(img)

                try:
                    import pytesseract
                    ocr_text = pytesseract.image_to_string(processed_img).strip()
                    if ocr_text:
                        text = ocr_text
                        ocr_used = True
                        confidence = 0.88
                except Exception:
                    pass

            full_text_parts.append(text)
            pages_info.append({
                "page_number": page_idx + 1,
                "text": text,
                "is_ocr": ocr_used,
                "confidence": confidence
            })

        doc.close()
        full_text = "\n\n".join(full_text_parts)

        return {
            "raw_text": full_text,
            "pages": pages_info,
            "records": [],
            "metadata": {
                "page_count": len(pages_info),
                "processor": "PDFProcessor (PyMuPDF + Tesseract fallback)"
            }
        }
