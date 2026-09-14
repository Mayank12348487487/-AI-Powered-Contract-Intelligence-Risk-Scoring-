import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    OCR fallback extractor for scanned image documents.
    Attempts to use pytesseract if installed, otherwise uses basic PIL image analysis.
    """
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))
        
        try:
            import pytesseract
            text = pytesseract.image_to_string(image)
            return text.strip()
        except (ImportError, Exception) as tesseract_err:
            logger.info("pytesseract not available or failed (%s). Image dimensions: %dx%d", tesseract_err, image.width, image.height)
            return f"[Scanned Image Document: {image.width}x{image.height}px. Tesseract engine not configured on system.]"
    except Exception as e:
        logger.error("OCR extraction failed: %s", str(e))
        return ""
