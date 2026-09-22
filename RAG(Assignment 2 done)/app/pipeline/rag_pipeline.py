import json
import logging
import faiss
import pickle
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv
from langfuse import observe

from app.src.search_engine import SearchEngine
from app.src.context_manager import ContextManager
from app.src.llm_client import LLMClient

from app.src.cache_manager import (
    clear_cache,
    check_semantic_cache,
    store_in_cache,
)
from app.src.citation_extractor import extract_citations
from app.src.evaluator import evaluate_response
from app.src.intent_router import identify_intent, is_greeting
from app.src.sql_handler import query_persistent_sql
from app.src.multimodal_intent_router import classify_multimodal_intent 

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RAGPipeline:
    def __init__(
        self,
        index_dir: Optional[Path] = None,
        base_index_path: Optional[Path] = None,
    ) -> None:

        self.llm_client = LLMClient()
        self.search_engine: Optional[SearchEngine] = None
        self.sql_db_path: Optional[Path] = None
        self.mode: str = "none"

        vector_dir: Optional[Path] = None
        sql_db: Optional[Path] = None

        if base_index_path:
            vector_dir = base_index_path / "vector_index"
            sql_db = base_index_path / "sql_index.db"

        elif index_dir:
            if index_dir.is_dir():
                vector_dir = index_dir
                potential_db = index_dir / "sql_index.db"
                if potential_db.exists():
                    sql_db = potential_db
            elif index_dir.suffix == ".db":
                sql_db = index_dir

        # Load Vector Index
        if vector_dir and vector_dir.exists():
            try:
                faiss_file = vector_dir / "index.faiss"
                if not faiss_file.exists():
                    faiss_file = vector_dir / "faiss.index"

                meta_file = vector_dir / "metadata.pkl"

                if faiss_file.exists() and meta_file.exists():
                    index = faiss.read_index(str(faiss_file))
                    with open(meta_file, "rb") as f:
                        metadata = pickle.load(f)

                    self.search_engine = SearchEngine(
                        index=index,
                        metadata=metadata,
                    )

                    logger.info("Vector index loaded successfully")

            except Exception as e:
                logger.error("Vector load error: %s", e)

        if sql_db and sql_db.exists():
            self.sql_db_path = sql_db

        vector_loaded = self.search_engine is not None
        sql_loaded = self.sql_db_path is not None

        if vector_loaded and sql_loaded:
            self.mode = "both"
        elif vector_loaded:
            self.mode = "rag"
        elif sql_loaded:
            self.mode = "sql"

        logger.info("Pipeline mode: %s", self.mode)

    async def _describe_image(self, question: str, image_bytes: bytes) -> str:
        """
        Extract search keywords from image for vector retrieval.
        Tries multiple LLMClient methods in order of preference.
        """
        prompt = (
            f"Based on this image and the question '{question}', "
            "provide 3-5 search keywords to find relevant technical documentation. "
            "Output keywords only, comma separated."
        )
        
        try:
            # Try method 1: describe_image_for_search
            if hasattr(self.llm_client, 'describe_image_for_search'):
                return await self.llm_client.describe_image_for_search(question, image_bytes)
            
            # Try method 2: generate_with_image
            if hasattr(self.llm_client, 'generate_with_image'):
                return await self.llm_client.generate_with_image(prompt, image_bytes)
            
            # Try method 3: generate_stream with image_bytes
            if hasattr(self.llm_client, 'generate_stream'):
                result = ""
                try:
                    async for token in self.llm_client.generate_stream(prompt, image_bytes=image_bytes):
                        result += token
                    return result.strip()
                except TypeError:
                    pass  # Doesn't support image_bytes
            
            # Fallback: No vision support
            logger.warning("LLMClient has no vision support - using question as keywords")
            return question
            
        except Exception as e:
            logger.error(f"Image description failed: {e}")
            return question

    @observe(name="LLM_Stream", as_type="generation")
    async def _llm_stream(
        self,
        prompt: str,
        image_bytes: bytes = None,
    ) -> AsyncGenerator[str, None]:

        try:
            if image_bytes is not None:
                async for token in self.llm_client.generate_stream(
                    prompt,
                    image_bytes=image_bytes,
                ):
                    yield token
            else:
                async for token in self.llm_client.generate_stream(prompt):
                    yield token

        except TypeError as e:
            if "image_bytes" in str(e):
                logger.warning(
                    "generate_stream doesn't support image_bytes — fallback to text"
                )
                async for token in self.llm_client.generate_stream(prompt):
                    yield token
            else:
                raise

    def _llm_sync(self, prompt: str) -> str:
        return self.llm_client.generate(prompt)

    def _retrieve(self, query: str, top_k: int = 5) -> List[dict]:
        if not self.search_engine:
            return []
        return list(self.search_engine.search(query=query, top_k=top_k))

    def clear_cache(self) -> bool:
        return clear_cache()

    @observe(name="Visual_Query")
    async def query_visual(
        self,
        question: str,
        image_bytes: bytes,
        source: str = "vector_index",
    ) -> AsyncGenerator[str, None]:
        """
        IMPROVED: Multi-modal query with intelligent data source selection.
        
        Now classifies queries into:
          - IMAGE_ONLY: Analyze image without searching documents
          - IMAGE_AND_VECTOR: Extract keywords from image, search docs, use both
        
        This prevents unrelated PDFs from appearing in citations when user
        just wants to analyze the image itself.
        """
        
        classification = classify_multimodal_intent(
            question=question,
            has_image=True,
            has_vector_index=self.search_engine is not None,
            has_sql_db=self.sql_db_path is not None,
            llm_sync_fn=self._llm_sync,
            sql_db_path=self.sql_db_path
        )
        
        logger.info(
            "Visual query classified | intent=%s | sources=%s | reasoning=%s",
            classification["intent"],
            classification["data_sources"],
            classification["reasoning"][:100]
        )
    
        
        if "IMAGE_ONLY" in classification["data_sources"]:
    
            logger.info("IMAGE_ONLY route: Analyzing image without vector search")
            
            # Send empty citations (no documents retrieved)
            yield f"metadata:{json.dumps({'citations': [], 'cache': False})}\n\n"
            
            # Generate answer using only the image
            prompt = (
                f"User Question: {question}\n\n"
                "Analyze the attached image and answer the question directly."
            )
            
            full_answer = ""
            async for token in self._llm_stream(prompt, image_bytes=image_bytes):
                full_answer += token
                yield f"data: {token}\n\n"
            
            # Evaluation (perfect scores since no retrieval involved)
            scores = {"faithfulness": 1.0, "relevance": 1.0, "groundedness": 1.0}
            yield f"evaluation:{json.dumps({k: f'{round(v*100,1)}%' for k,v in scores.items()})}\n\n"
            
        elif "IMAGE_AND_VECTOR" in classification["data_sources"]:
        
            logger.info("IMAGE_AND_VECTOR route: Extracting keywords and searching documents")
            
            # Extract search keywords from image
            search_keywords = await self._describe_image(question, image_bytes)
            logger.info(f"Extracted search keywords: {search_keywords}")
            
            # Retrieve relevant documents using keywords
            retrieved_chunks = self._retrieve(query=search_keywords, top_k=5)
            citations = extract_citations(retrieved_chunks)
            yield f"metadata:{json.dumps({'citations': citations, 'cache': False})}\n\n"
            
            # Generate answer using both image and retrieved documents
            context_text = ContextManager.format_context(retrieved_chunks)
            prompt = (
                f"Document Context:\n{context_text}\n\n"
                f"User Question about the attached image: {question}\n\n"
                "Answer using both the image and the document context provided."
            )
            
            full_answer = ""
            async for token in self._llm_stream(prompt, image_bytes=image_bytes):
                full_answer += token
                yield f"data: {token}\n\n"
            
            # Evaluation
            scores = evaluate_response(
                question,
                context_text,
                full_answer,
                self._llm_sync,
            )
            yield f"evaluation:{json.dumps({k: f'{round(v*100,1)}%' for k,v in scores.items()})}\n\n"
        
        else:
  
            logger.warning(
                "Unknown classification '%s', falling back to IMAGE_AND_VECTOR",
                classification["data_sources"]
            )
            
            # Use question as search keywords (original behavior)
            retrieved_chunks = self._retrieve(question, top_k=5)
            citations = extract_citations(retrieved_chunks)
            yield f"metadata:{json.dumps({'citations': citations, 'cache': False})}\n\n"
            
            context_text = ContextManager.format_context(retrieved_chunks)
            prompt = (
                f"Document Context:\n{context_text}\n\n"
                f"User Question about the attached image: {question}\nAnswer:"
            )
            
            full_answer = ""
            async for token in self._llm_stream(prompt, image_bytes=image_bytes):
                full_answer += token
                yield f"data: {token}\n\n"
            
            scores = evaluate_response(
                question,
                context_text,
                full_answer,
                self._llm_sync,
            )
            yield f"evaluation:{json.dumps({k: f'{round(v*100,1)}%' for k,v in scores.items()})}\n\n"

    @observe(name="RAG_Query_Stream")
    async def query_stream_auto(
        self,
        question: str,
        search_type: str = "hybrid",
        top_k: int = 5,
        source: str = "vector_index",
    ) -> AsyncGenerator[str, None]:

        if is_greeting(question):
            yield "metadata:{}\n\ndata: Hello! How can I help?\n\n"
            return

        intent = "VECTOR"

        if self.mode == "both":
            intent = identify_intent(
                question,
                self.sql_db_path,
                True,
                self._llm_sync,
            )
        elif self.mode == "sql":
            intent = "SQL"

      
        if intent == "SQL":
            async for token in query_persistent_sql(
                question,
                self.sql_db_path,
                self._llm_sync,
                self._llm_stream,
            ):
                yield token
            return

        embedder = (
            self.search_engine.embedder
            if self.search_engine else None
        )

        is_hit, payload = check_semantic_cache(
            question=question,
            source=source,
            embedder=embedder,
        )

        if is_hit:
            yield f"metadata:{json.dumps({'citations': payload['citations'], 'cache': True})}\n\n"
            yield f"data: {payload['answer']}\n\n"
            return

        new_embedding = payload  # may contain embedding

      
        retrieved_chunks = self._retrieve(question, top_k)
        citations = extract_citations(retrieved_chunks)

        yield f"metadata:{json.dumps({'citations': citations, 'cache': False})}\n\n"

        context_text = ContextManager.format_context(retrieved_chunks)
        prompt = f"Context:\n{context_text}\n\nQuestion: {question}\nAnswer:"

        full_answer = ""

        async for token in self._llm_stream(prompt):
            full_answer += token
            yield f"data: {token}\n\n"

        scores = evaluate_response(
            question,
            context_text,
            full_answer,
            self._llm_sync,
        )

        yield f"evaluation:{json.dumps({k: f'{round(v*100,1)}%' for k,v in scores.items()})}\n\n"

        threshold = 0.7

        if all(
            scores.get(metric, 0) >= threshold
            for metric in ("faithfulness", "relevance", "groundedness")
        ):
            try:
                if not new_embedding and embedder:
                    new_embedding = embedder.embed([question])[0]

                store_in_cache(
                    source=source,
                    question=question,
                    answer=full_answer,
                    citations=citations,
                    embedding=new_embedding,
                )

                logger.info("Answer cached (evaluation >= 70%%)")

            except Exception as e:
                logger.warning("Failed to store in cache: %s", e)