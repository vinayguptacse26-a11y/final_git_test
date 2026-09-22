from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    return len(text.split())


class ContextManager:
    """
    Handles context selection and truncation.
    """

    def __init__(self, max_tokens: int = 7500) -> None:
        self.max_tokens = max_tokens

    def build_context(
        self,
        reranked_chunks: List[Dict]
    ) -> List[Dict]:
        """
        Preserve reranker order and apply token limit.
        """
        selected_chunks: List[Dict] = []
        current_tokens = 0

        for chunk in reranked_chunks:
            text = chunk.get("text", "")
            tokens = estimate_tokens(text)

            if current_tokens + tokens > self.max_tokens:
                logger.warning(
                    "Context token limit reached (%d tokens)",
                    self.max_tokens
                )
                break

            selected_chunks.append(chunk)
            current_tokens += tokens

        logger.info(
            "Selected %d chunks using %d tokens",
            len(selected_chunks),
            current_tokens
        )

        return selected_chunks

    @staticmethod
    def format_context(chunks: List[Dict]) -> str:
        formatted = []

        for chunk in chunks:
            meta = chunk.get("metadata", {})
            label = meta.get("section_id") or meta.get("file_type", "context")
            formatted.append(
                f"[{label}]\n{chunk.get('text', '').strip()}"
            )

        return "\n\n".join(formatted)
