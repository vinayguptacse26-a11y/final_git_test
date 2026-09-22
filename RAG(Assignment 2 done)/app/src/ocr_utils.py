from PIL import Image
import pytesseract
import io
import logging

logger = logging.getLogger(__name__)


def extract_text_from_image(image_bytes: bytes) -> str:

    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.warning("OCR failed: %s", e)
        return ""
