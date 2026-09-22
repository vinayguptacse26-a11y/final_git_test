from pathlib import Path
import logging
from typing import Any, Dict, List, Optional

from app.ingestion.loaders.loader_factory import LoaderFactory
from app.ingestion.chunking.chunker import Chunker
from app.src.embedder import Embedder
from app.src.index_writer import IndexWriter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IngestionService:
    """
    Handles full ingestion lifecycle:
    load → chunk → enrich metadata → embed → index
    """

    def __init__(self, index_base_dir: Path) -> None:
        self.chunker: Chunker = Chunker()
        self.embedder: Embedder = Embedder()
        self.index_writer: IndexWriter = IndexWriter(base_dir=index_base_dir)


    def ingest(
        self,
        document_path: Path,
        chunking_strategy: str,
        index_type: str,
        token_limit: int = 512,
        max_chars: int = 500,
    ) -> None:
        """
        Ingest a document into vector index.

        Ensures every chunk has a valid 1-based page_number.
        """

        logger.info("Starting ingestion | file=%s | index=%s",
                    document_path.name, index_type)

        # 1. Load
        loader = LoaderFactory.get_loader(document_path)
        blocks: List[Dict[str, Any]] = loader.load(document_path)

        if not blocks:
            logger.warning("No content loaded from '%s'", document_path.name)
            return

        logger.info("Loaded %d block(s)", len(blocks))

        # 2. Chunk
        chunks: List[Dict[str, Any]] = self.chunker.chunk(
            blocks=blocks,
            strategy=chunking_strategy,
            token_limit=token_limit,
            max_chars=max_chars,
        )

        if not chunks:
            logger.warning("Chunking produced zero chunks for '%s'",
                           document_path.name)
            return

        # 3. Enrich metadata (page_number propagation)
        self._propagate_page_numbers(
            document_path=document_path,
            blocks=blocks,
            chunks=chunks,
        )

        # 4. Embed
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedder.embed(texts)

        # 5. Write index
        self.index_writer.write(
            chunks=chunks,
            embeddings=embeddings,
            index_name=index_type,
        )

        logger.info(
            "Ingestion complete | file=%s | chunks=%d | index=%s",
            document_path.name,
            len(chunks),
            index_type,
        )

    def _propagate_page_numbers(
        self,
        document_path: Path,
        blocks: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]],
    ) -> None:
        """
        Ensure each chunk has a valid 1-based page_number.

        Fallback order:
        1) chunk["page_number"]
        2) chunk["metadata"]["page_number"]
        3) source_block["page_number"]
        4) source_block["metadata"]["page_number"]
        5) 0-based "page" (+1)
        6) chunk position (last resort)
        """

        for i, chunk in enumerate(chunks):

            chunk["filename"] = document_path.name

            # 1. Already valid
            if self._valid_page(chunk.get("page_number")):
                continue

            chunk_meta = chunk.get("metadata") or {}

            # 2. Chunk metadata
            if self._valid_page(chunk_meta.get("page_number")):
                chunk["page_number"] = int(chunk_meta["page_number"])
                continue

            # 3. Trace back to source block
            block_index = (
                chunk.get("block_index")
                or chunk.get("source_block_index")
                or chunk_meta.get("block_index")
            )

            src_block: Optional[Dict[str, Any]] = (
                blocks[block_index]
                if isinstance(block_index, int)
                and 0 <= block_index < len(blocks)
                else None
            )

            if src_block:
                src_meta = src_block.get("metadata") or {}

                # Loader-provided 1-based page_number
                if self._valid_page(src_block.get("page_number")):
                    chunk["page_number"] = int(src_block["page_number"])
                    continue

                if self._valid_page(src_meta.get("page_number")):
                    chunk["page_number"] = int(src_meta["page_number"])
                    continue

                # 0-based "page"
                if src_block.get("page") is not None:
                    chunk["page_number"] = int(src_block["page"]) + 1
                    continue

                if src_meta.get("page") is not None:
                    chunk["page_number"] = int(src_meta["page"]) + 1
                    continue

            # 4. 0-based page on chunk itself
            if chunk.get("page") is not None:
                chunk["page_number"] = int(chunk["page"]) + 1
                continue

            if chunk_meta.get("page") is not None:
                chunk["page_number"] = int(chunk_meta["page"]) + 1
                continue

            # 5. Final fallback: chunk position
            chunk["page_number"] = i + 1
            logger.debug(
                "Fallback page_number used | file=%s | chunk=%d | page=%d",
                document_path.name,
                i,
                i + 1,
            )

    @staticmethod
    def _valid_page(value: Any) -> bool:
        """Return True if value is a valid 1-based page number."""
        if value is None:
            return False

        try:
            return int(float(str(value))) > 0
        except (ValueError, TypeError):
            return False
