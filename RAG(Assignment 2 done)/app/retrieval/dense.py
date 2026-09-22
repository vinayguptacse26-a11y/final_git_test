from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def dense_retrieve(
    vector_store,
    query_embedding: List[float],
    top_k: int = 5,
    metadata_filter: Dict[str, Any] | None = None
) -> List[Dict[str, Any]]:
    results = vector_store.search(
        query_embedding=query_embedding,
        top_k=top_k,
        metadata_filter=metadata_filter
    )

    logger.debug("Dense retrieval returned %d results", len(results))
    return results
