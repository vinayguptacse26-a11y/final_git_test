from pathlib import Path
import logging
import pdfplumber

logger = logging.getLogger(__name__)


def load_pdf(file_path: Path) -> list[str]:
  
    pages: list[str] = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    pages.append(text.strip())

        logger.info(
            "Loaded PDF file: %s with %d pages",
            file_path.name,
            len(pages),
        )
        return pages

    except Exception as exc:
        logger.exception("Failed to load PDF file: %s", file_path)
        raise RuntimeError("PDF loading failed") from exc
