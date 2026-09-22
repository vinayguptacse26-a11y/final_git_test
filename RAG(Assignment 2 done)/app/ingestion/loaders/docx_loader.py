from pathlib import Path
import logging
from docx import Document

logger = logging.getLogger(__name__)


def load_docx(file_path: Path) -> list[dict]:
    """
    Load DOCX file and return blocks with text + metadata.
    """
    document = Document(file_path)
    blocks = []

    for i, para in enumerate(document.paragraphs, start=1):
        text = para.text.strip()
        if not text:
            continue

        blocks.append(
            {
                "text": text,
                "metadata": {
                    "file_type": "docx",
                    "paragraph_number": i,
                },
            }
        )

    logger.info(
        "Loaded DOCX file: %s with %d paragraphs",
        file_path.name,
        len(blocks),
    )

    return blocks
