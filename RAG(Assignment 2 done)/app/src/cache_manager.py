"""
app/src/cache_manager.py
Persistent semantic query cache.
Imported by RAGPipeline — nothing else should write to QUERY_CACHE directly.
"""
import json
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR  = Path("app/data/cache")
CACHE_FILE = CACHE_DIR / "query_cache.json"

# Module-level singleton — loaded once at import time
QUERY_CACHE: dict = {}


def load_cache() -> None:
    """Populate QUERY_CACHE from disk. Call once at startup."""
    global QUERY_CACHE
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                QUERY_CACHE = json.load(f)
            logger.info(f"Cache loaded: {len(QUERY_CACHE)} entries")
        except Exception as e:
            logger.error(f"Cache load error: {e}")
            QUERY_CACHE = {}


def save_cache() -> None:
    """Flush QUERY_CACHE to disk."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(QUERY_CACHE, f, indent=4)
    except Exception as e:
        logger.error(f"Cache save error: {e}")


def clear_cache() -> bool:
    global QUERY_CACHE
    QUERY_CACHE.clear()
    save_cache()
    return True


def check_semantic_cache(
    question: str,
    source: str,
    embedder,
    threshold: float = 0.92,
):
    """
    Returns (hit: bool, payload_or_embedding).
    - hit=True  → payload is the cached dict {answer, citations, embedding}
    - hit=False → payload is the query embedding list (reuse for storing later)
                  or None if embedding failed
    """
    cache_key = f"{source}_{question.lower().strip()}"

    # Exact key hit
    if cache_key in QUERY_CACHE:
        return True, QUERY_CACHE[cache_key]

    if not embedder:
        return False, None

    try:
        raw            = embedder.embed([question])[0]
        query_emb      = np.array(raw, dtype=float)
        best_sim       = 0.0
        best_match     = None

        for key, data in QUERY_CACHE.items():
            if not key.startswith(f"{source}_"):
                continue
            cached = data.get("embedding")
            if not cached:
                continue
            cached_emb = np.array(cached, dtype=float)
            sim = np.dot(query_emb, cached_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(cached_emb) + 1e-9
            )
            if sim > best_sim:
                best_sim, best_match = sim, data

        if best_sim >= threshold:
            return True, best_match
        return False, query_emb.tolist()

    except Exception as e:
        logger.warning(f"Semantic cache check failed: {e}")
        return False, None


def store_in_cache(
    source: str,
    question: str,
    answer: str,
    citations: list,
    embedding,
) -> None:
    cache_key = f"{source}_{question.lower().strip()}"
    QUERY_CACHE[cache_key] = {
        "answer":    answer,
        "citations": citations,
        "embedding": embedding,
    }
    save_cache()


# Load on import
load_cache()