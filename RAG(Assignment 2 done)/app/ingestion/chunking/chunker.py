from typing import List, Dict, Any, Optional
import logging
import tiktoken

logger = logging.getLogger(__name__)

class Chunker:
    """
    Unified chunker supporting multiple chunking strategies with 
    overflow protection and flexible parameter handling.
    """

    def chunk(
        self,
        blocks: List[Dict[str, Any]],
        strategy: str = "Fixed",
        **kwargs
    ) -> List[Dict[str, Any]]:
        logger.info("Chunking using strategy: %s", strategy)

        if strategy == "Fixed":
            return self._fixed_chunk(blocks, **kwargs)
        if strategy == "Paragraph":
            return self._paragraph_chunk(blocks, **kwargs)
        if strategy == "Section Aware":
            return self._section_aware_chunk(blocks, **kwargs)
        if strategy == "Slide Aware":
            return self._slide_aware_chunk(blocks, **kwargs)
        if strategy == "Image Aware":
            return self._image_aware_chunk(blocks, **kwargs)
        if strategy == "Token Based":
            return self._token_aware_chunk(blocks, **kwargs)

        raise ValueError(f"Unknown chunking strategy: {strategy}")

    def _token_aware_chunk(
        self, 
        blocks: List[Dict[str, Any]], 
        token_limit: int = 512,
        **kwargs
    ) -> List[Dict[str, Any]]:
        encoding = tiktoken.encoding_for_model("text-embedding-ada-002")
        chunks = []
        current_text = ""
        current_tokens = 0

        for block in blocks:
            text = block.get("text", "").strip()
            if not text: continue
            
            block_tokens = len(encoding.encode(text))
            
            if block_tokens > token_limit:
                if current_text:
                    chunks.append(self._make_chunk(current_text, block))
                    current_text = ""
                    current_tokens = 0
                
                tokens = encoding.encode(text)
                for i in range(0, len(tokens), token_limit):
                    sub_text = encoding.decode(tokens[i : i + token_limit])
                    chunks.append(self._make_chunk(sub_text, block))
                continue

            if current_tokens + block_tokens <= token_limit:
                current_text += text + "\n\n"
                current_tokens += block_tokens
            else:
                chunks.append(self._make_chunk(current_text, block))
                current_text = text + "\n\n"
                current_tokens = block_tokens

        if current_text.strip():
            chunks.append(self._make_chunk(current_text, blocks[-1]))
        return chunks

    def _fixed_chunk(
        self,
        blocks: List[Dict[str, Any]],
        max_chars: int = 500,
        **kwargs
    ) -> List[Dict[str, Any]]:
       
        limit = kwargs.get("max_chars", max_chars)
        chunks = []
        buffer = ""
        for block in blocks:
            text = block.get("text", "").strip()
            if not text: continue
            if len(buffer) + len(text) <= limit:
                buffer += text + "\n\n"
            else:
                chunks.append(self._make_chunk(buffer, block))
                buffer = text + "\n\n"
        if buffer.strip():
            chunks.append(self._make_chunk(buffer, blocks[-1]))
        return chunks

    def _paragraph_chunk(self, blocks, **kwargs):
        chunks = []
        for block in blocks:
            text = block.get("text", "").strip()
            if len(text) < 30: continue
            chunks.append(self._make_chunk(text, block))
        return chunks

    def _section_aware_chunk(self, blocks, **kwargs):
        chunks = []
        section_map = {}
        for block in blocks:
            section = block.get("metadata", {}).get("section_id", "unknown")
            section_map.setdefault(section, []).append(block)
        for section, items in section_map.items():
            combined_text = "\n\n".join(i["text"] for i in items if i.get("text"))
            if combined_text.strip():
                text_parts = self._split_text(combined_text)
                for part in text_parts:
                    chunks.append({
                        "text": part,
                        "metadata": {**items[0]["metadata"], "is_sub_chunk": len(text_parts) > 1},
                    })
        return chunks

    def _slide_aware_chunk(self, blocks, **kwargs):
        chunks = []
        slide_map = {}
        for block in blocks:
            slide = block.get("metadata", {}).get("slide_number")
            slide_map.setdefault(slide, []).append(block)
        for slide, items in slide_map.items():
            combined_text = "\n".join(i["text"] for i in items if i.get("text"))
            if combined_text.strip():
                text_parts = self._split_text(combined_text)
                for part in text_parts:
                    chunks.append({
                        "text": part,
                        "metadata": {**items[0]["metadata"], "is_sub_chunk": len(text_parts) > 1},
                    })
        return chunks

    def _image_aware_chunk(self, blocks, **kwargs):
        chunks = []
        for block in blocks:
            text = block.get("text", "").strip()
            meta = block.get("metadata", {})
            if meta.get("has_image") or meta.get("is_diagram"):
                title = meta.get("slide_title", "diagram")
                chunks.append({
                    "text": f"This slide contains a DIAGRAM related to '{title}'.",
                    "metadata": {**meta, "chunk_type": "diagram"},
                })
            if len(text) > 30:
                chunks.append(self._make_chunk(text, block))
        return chunks

    def _split_text(self, text: str, max_chars: int = 4000) -> List[str]:
        if len(text) <= max_chars: return [text]
        parts = text.split("\n\n")
        sub_chunks = []
        current_chunk = ""
        for part in parts:
            if len(current_chunk) + len(part) <= max_chars:
                current_chunk += part + "\n\n"
            else:
                if current_chunk: sub_chunks.append(current_chunk.strip())
                current_chunk = part + "\n\n"
        if current_chunk: sub_chunks.append(current_chunk.strip())
        return sub_chunks

    def _make_chunk(self, text: str, block: Dict[str, Any]) -> Dict[str, Any]:
        return {"text": text.strip(), "metadata": block.get("metadata", {})}