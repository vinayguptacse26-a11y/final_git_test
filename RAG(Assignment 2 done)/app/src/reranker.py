from typing import List, Dict, Any
import numpy as np
import logging

logger = logging.getLogger(__name__)


class Reranker:
  

    def rerank(
        self,
        query_embedding: List[float],
        retrieved_chunks: List[Dict[str, Any]],    
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        if not retrieved_chunks:
            return []

        query_vec = np.array(query_embedding, dtype=float)
        scored_chunks: list[tuple[float, Dict[str, Any]]] = []

        for chunk in retrieved_chunks:
            chunk_vec = np.array(chunk.get("embedding", []), dtype=float)

           
            if chunk_vec.size == 0:
                continue

            score = self._cosine_similarity(query_vec, chunk_vec)

            text_lower = chunk["text"].lower()

           
            if text_lower.startswith("what is"):
                score += 0.25                   #to  boost the results from pdf 

            scored_chunks.append((score, chunk))

        
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        logger.info(
            "Reranked %d chunks, returning top %d",
            len(scored_chunks),
            top_k,
        )

        return [chunk for _, chunk in scored_chunks[:top_k]]

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
