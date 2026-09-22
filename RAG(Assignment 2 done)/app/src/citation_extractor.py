"""
app/src/citation_extractor.py

Extracts deduplicated citations from retrieved document chunks.

Supports:
- PDF (0-based and 1-based loaders)
- DOCX
- PPTX (slides)
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Set

from langfuse import observe

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



def _safe_get(meta: Dict[str, Any], chunk: Dict[str, Any], *keys: str) -> str:
    """Fetch first non-empty value from metadata or chunk."""
    for key in keys:
        value = meta.get(key) or chunk.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_filename(raw_source: str) -> str:
    """Strip UUID prefixes and return clean filename."""
    clean = Path(raw_source).name

    # Remove UUID4 prefix if present
    clean = re.sub(
        r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}[_\-.]',
        '',
        clean
    )

    return clean or raw_source


def _format_page_display(ext: str, meta: Dict[str, Any], chunk: Dict[str, Any]) -> str:
    """Return formatted page/slide string based on file type."""

    raw = ""

    # PPT / PPTX
    if ext in (".pptx", ".ppt"):
        raw = _safe_get(meta, chunk, "slide_number", "slide", "page_number", "page")
        if raw:
            try:
                return f"Slide {int(float(raw))}"
            except Exception:
                return f"Slide {raw}"
        return ""

    # PDF
    if ext == ".pdf":
        raw_label = _safe_get(meta, chunk, "page_label")
        raw_num   = _safe_get(meta, chunk, "page_number")  # 1-based
        raw_page  = _safe_get(meta, chunk, "page")         # 0-based

        if raw_label:
            return f"p. {raw_label}"

        if raw_num:
            try:
                return f"p. {int(float(raw_num))}"
            except Exception:
                return f"p. {raw_num}"

        if raw_page:
            try:
                return f"p. {int(float(raw_page)) + 1}"
            except Exception:
                return f"p. {raw_page}"

        return ""

    # DOCX and others
    raw_num  = _safe_get(meta, chunk, "page_number")  
    raw_page = _safe_get(meta, chunk, "page")        

    if raw_num:
        try:
            return f"p. {int(float(raw_num))}"
        except Exception:
            return f"p. {raw_num}"

    if raw_page:
        try:
            return f"p. {int(float(raw_page)) + 1}"
        except Exception:
            return f"p. {raw_page}"

    return ""


@observe(name="Extract_Citations", as_type="span")
def extract_citations(chunks: List[Any]) -> List[Dict[str, str]]:
    """
    Extract and deduplicate citations from retrieved chunks.

    Returns:
        [
            {
                "source": str,
                "page": str,
                "display": str
            }
        ]
    """

    unique_citations: List[Dict[str, str]] = []
    seen: Set[str] = set()

    for chunk in chunks:

        if isinstance(chunk, dict):
            chunk_dict = chunk
            meta = chunk.get("metadata") or {}
        elif hasattr(chunk, "__dict__"):
            chunk_dict = vars(chunk)
            meta = chunk_dict.get("metadata") or {}
        else:
            continue

        if not isinstance(meta, dict):
            meta = {}

        raw_source = _safe_get(
            meta,
            chunk_dict,
            "filename",
            "file_name",
            "source",
            "doc_name",
            "name",
        ) or "Document"

        clean_name = _normalize_filename(raw_source)
        ext = Path(clean_name).suffix.lower()

        page_display = _format_page_display(ext, meta, chunk_dict)

        citation_key = f"{clean_name}|{page_display}"
        if citation_key in seen:
            continue

        display = (
            f"{clean_name} ({page_display})"
            if page_display
            else clean_name
        )

        unique_citations.append(
            {
                "source": clean_name,
                "page": page_display,
                "display": display,
            }
        )

        seen.add(citation_key)

    logger.info("Extracted %d unique citations", len(unique_citations))

    return unique_citations
