from pathlib import Path

from app.ingestion.loaders.pdf_loader import load_pdf
from app.ingestion.loaders.ppt_loader import load_ppt
from app.ingestion.loaders.docx_loader import load_docx


class LoaderFactory:
    """
    Returns correct loader based on file extension.
    """

    @staticmethod
    def get_loader(path: Path):
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return PDFLoader()

        if suffix in {".ppt", ".pptx"}:
            return PPTLoader()

        if suffix == ".docx":
            return DOCXLoader()

        raise ValueError(f"Unsupported file type: {suffix}")


class PDFLoader:
    def load(self, path: Path):
        pages = load_pdf(path)

        blocks = []
        for page_number, page_text in enumerate(pages, start=1):
            blocks.append(
                {
                    "text": page_text,
                    "metadata": {
                        "file_type": "pdf",
                        "page_number": page_number,
                    },
                }
            )
        return blocks


class PPTLoader:
    def load(self, path: Path):
        slides = load_ppt(path)

        blocks = []
        for slide in slides:
            blocks.append(
                {
                    "text": slide["text"],
                    "metadata": {
                        "file_type": "pptx",
                        "slide_number": slide["slide_number"],
                        "slide_title": slide.get("title"),
                        "has_image": slide.get("has_image", False),
                    },
                }
            )
        return blocks


class DOCXLoader:
    def load(self, path: Path):
        return load_docx(path)
