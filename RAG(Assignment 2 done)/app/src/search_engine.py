from typing import List, Dict, Any, Optional, Literal
import logging
import numpy as np
import faiss

from pydantic import BaseModel, ValidationError, Field

from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import hybrid_retrieve
from app.src.embedder import Embedder

logger = logging.getLogger(__name__)

class SearchInput(BaseModel):
    query: str
    search_type: Literal["bm25", "dense", "hybrid"] = "hybrid"
    top_k: int = Field(default=10, ge=1, le=100)
    
    source: Optional[str] = None 

class SearchEngine:
    """
    Unified search engine supporting BM25, Dense, and Hybrid search.
    """

    def __init__(
        self,
        index: faiss.Index,
        metadata: List[Dict[str, Any]],
    ) -> None:
        self.index = index
        self.metadata = metadata

        self.embedder = Embedder()
        self.bm25 = BM25Retriever(documents=metadata)

        logger.info("SearchEngine initialized with %d chunks", len(metadata))

    def search(
        self,
        query: str,
        search_type: str = "hybrid",
        top_k: int = 10,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        try:
         
            validated = SearchInput(
                query=query,
                search_type=search_type,
                top_k=top_k,
                source=source,
            )

            query = validated.query.strip().lower()
            search_type = validated.search_type
            top_k = validated.top_k
            source = validated.source

            logger.info(
                "Search Execution | type=%s | top_k=%d | source=%s",
                search_type,
                top_k,
                source,
            )

            if search_type == "bm25":
                results = self._bm25_search(query, top_k)
            elif search_type == "dense":
                results = self._dense_search(query, top_k)
            else: # hybrid
                results = self._hybrid_search(query, top_k)

           
            return results[:top_k]

        except ValidationError as ve:
            logger.error("Invalid search input: %s", ve)
            raise

        except Exception:
            logger.exception("Search failed")
            raise

    def _bm25_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        results = self.bm25.search(query, top_k=top_k)
        for r in results:
            r.setdefault("score", 1.0)
        return results

    def _dense_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        query_embedding = np.array(
            self.embedder.embed([query])[0],
            dtype="float32"
        )
        distances, indices = self.index.search(np.array([query_embedding]), top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                chunk = self.metadata[idx]
                results.append({**chunk, "score": float(-dist)})
        return results

    def _hybrid_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        query_embedding = np.array(
            self.embedder.embed([query])[0],
            dtype="float32"
        )
        _, dense_indices = self.index.search(np.array([query_embedding]), top_k * 2)
        dense_results = [self.metadata[i] for i in dense_indices[0] if i < len(self.metadata)]
        sparse_results = self.bm25.search(query, top_k=top_k * 2)

        return hybrid_retrieve(
            dense_results=dense_results,
            sparse_results=sparse_results,
            top_k=top_k,
        )