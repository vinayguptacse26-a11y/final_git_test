from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def hybrid_retrieve(
    dense_results: List[Dict],
    sparse_results: List[Dict],
    top_k: int = 20
) -> List[Dict]:
    
    combined: Dict[str, Dict] = {}

    
    DENSE_WEIGHT = 0.6
    SPARSE_WEIGHT = 0.4


    for rank, result in enumerate(dense_results):
        key = result["text"]
        score = 1 / (rank + 1)

        if key not in combined:
            combined[key] = result.copy()
            combined[key]["hybrid_score"] = DENSE_WEIGHT * score
        else:
            combined[key]["hybrid_score"] += DENSE_WEIGHT * score


    for rank, result in enumerate(sparse_results):
        key = result["text"]
        score = 1 / (rank + 1)

        if key not in combined:
            combined[key] = result.copy()
            combined[key]["hybrid_score"] = SPARSE_WEIGHT * score
        else:
            combined[key]["hybrid_score"] += SPARSE_WEIGHT * score


    final_results = sorted(
        combined.values(),
        key=lambda x: x["hybrid_score"],
        reverse=True
    )[:top_k]

    logger.info("Hybrid retrieval returned %d results", len(final_results))
    return final_results
