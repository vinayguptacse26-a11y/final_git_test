from typing import List, Dict
from rank_bm25 import BM25Okapi
import logging
import re

logger = logging.getLogger(__name__)


def tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)   #remove puctuations
    return text.split()


class BM25Retriever:
   

    def __init__(self, documents: List[Dict[str, str]]) -> None:
        self.documents = documents
        self.tokenized_corpus = [
            tokenize(doc["text"]) for doc in documents
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        logger.info("Initialized BM25 with %d documents", len(documents))

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, str]]:
        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

        results = []
        for i in ranked_indices:
            doc = dict(self.documents[i])
            doc["bm25_score"] = scores[i]
            results.append(doc)

        logger.debug("BM25 returned %d results", len(results))
        return results
