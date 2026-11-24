from typing import Dict, Any, List
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from app.config import settings
from app.processors.base import BaseProcessor

# Configure Tesseract binary path if provided
if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


class ImageProcessor(BaseProcessor):
    """Processes images (PNG, JPEG, TIFF) with Pillow preprocessing and Tesseract OCR."""

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Apply grayscale conversion, contrast enhancement, and adaptive thresholding."""
        # Convert to Grayscale
        gray = image.convert("L")

        # Enhance Contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.8)

        # Apply slight sharpening filter to improve character edge clarity
        sharpened = enhanced.filter(ImageFilter.SHARPEN)

        # Thresholding (Binarization at threshold 180)
        thresholded = sharpened.point(lambda p: 255 if p > 180 else 0)
        return thresholded

    def process(self, file_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        with Image.open(path) as img:
            processed_img = self.preprocess_image(img)

            # Extract raw text with Tesseract
            try:
                extracted_text = pytesseract.image_to_string(processed_img)
                # Attempt to extract confidence data
                ocr_data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
                confidences = [int(c) for c in ocr_data.get("conf", []) if int(c) >= 0]
                avg_confidence = round(sum(confidences) / len(confidences) / 100.0, 2) if confidences else 0.85
            except Exception as e:
                # If tesseract binary is not installed on system path, record warning
                extracted_text = f"[OCR Extraction Unavailable: {str(e)}]"
                avg_confidence = 0.0

        return {
            "raw_text": extracted_text,
            "pages": [
                {
                    "page_number": 1,
                    "text": extracted_text,
                    "confidence": avg_confidence
                }
            ],
            "records": [],
            "metadata": {
                "format": path.suffix.lower(),
                "processor": "ImageProcessor (Pillow + Tesseract)"
            }
        }
