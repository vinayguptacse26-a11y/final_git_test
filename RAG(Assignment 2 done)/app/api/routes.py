import re
import uuid
import json
import logging
import shutil
import io
import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from app.src.ingest_document import IngestionService
from app.pipeline.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

router = APIRouter()

BASE_INDEX_PATH = Path("app/indexes")
TMP_UPLOAD_DIR  = Path("app/data/uploads")

BASE_INDEX_PATH.mkdir(parents=True, exist_ok=True)
TMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


_pipeline: Optional[RAGPipeline] = None

def get_pipeline() -> RAGPipeline:
    """Return (or lazily create) the shared pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline(base_index_path=BASE_INDEX_PATH)
        logger.info(f"Pipeline created: mode={_pipeline.mode}")
    return _pipeline

def refresh_pipeline():
    """Force the next request to reload the pipeline from disk."""
    global _pipeline
    _pipeline = None
    logger.info("Pipeline cache invalidated – will reload on next request")


@router.get("/indices", response_model=List[str])
async def list_indices():
    """Returns vector indices (folders) and SQL indices (files)."""
    try:
        if not BASE_INDEX_PATH.exists():
            return ["general"]

        vector_indices = [d.name for d in BASE_INDEX_PATH.iterdir() if d.is_dir()]
        sql_indices    = [f.stem for f in BASE_INDEX_PATH.glob("*.db")]

        all_indices = list(set(vector_indices + sql_indices))
        return all_indices if all_indices else ["general"]
    except Exception as e:
        logger.error(f"Failed to list indices: {e}")
        return ["general"]



@router.post("/ingest")
async def ingest(
    file:               UploadFile = File(...),
    index_type:         str        = Form(...),
    chunking_strategy:  str        = Form("fixed"),
    max_chars:          int        = Form(500),
):
    """Handles multi-part form data for document ingestion."""
    try:
        safe_index_name = re.sub(r"[^\w-]", "_", index_type)
        file_ext        = Path(file.filename).suffix.lower()

        # ── A. SQL INGESTION (Excel / CSV) ──────────────────────────────────
        if file_ext in (".csv", ".xlsx", ".xls"):
            db_name = "sql_index.db" if ("sql" in safe_index_name or "auto" in safe_index_name) else f"{safe_index_name}.db"
            db_path = BASE_INDEX_PATH / db_name

            content = await file.read()
            df      = pd.read_csv(io.BytesIO(content)) if file_ext == ".csv" else pd.read_excel(io.BytesIO(content))

            # Sanitise column names
            df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]

            table_name = re.sub(r"[^\w]", "_", Path(file.filename).stem).lower()
            conn       = sqlite3.connect(str(db_path))
            df.to_sql(table_name, conn, index=False, if_exists="replace")
            conn.close()

            refresh_pipeline()   # ← invalidate singleton so it sees new DB
            return {"status": "success", "index": db_name, "type": "sql", "table": table_name}

        # ── B. VECTOR INGESTION (PDF / DOCX / …) ────────────────────────────
        else:
            if "vector" in safe_index_name or "auto" in safe_index_name:
                safe_index_name = "vector_index"

            session_id        = str(uuid.uuid4())
            upload_session_dir = TMP_UPLOAD_DIR / session_id
            upload_session_dir.mkdir(parents=True, exist_ok=True)

            file_path = upload_session_dir / file.filename
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            service = IngestionService(index_base_dir=BASE_INDEX_PATH)
            service.ingest(
                document_path=file_path,
                chunking_strategy=chunking_strategy,
                index_type=safe_index_name,
                max_chars=max_chars,
            )

            refresh_pipeline()   # ← invalidate singleton so it sees new index
            return {"status": "success", "index": safe_index_name, "filename": file.filename}

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query-stream")
async def query_stream(req: dict):
    """Receives JSON and returns a text/event-stream."""
    try:
        question   = req.get("question", "").strip()
        index_type = req.get("index_type", "auto")

        if not question:
            raise HTTPException(status_code=400, detail="'question' field is required.")

        # ── AUTO mode: use the shared singleton (has both indexes) ────────────
        if index_type == "auto":
            pipeline = get_pipeline()

        # ── EXPLICIT index selection (legacy / advanced use) ─────────────────
        else:
            safe_index_name = re.sub(r"[^\w-]", "_", index_type)
            possible_db     = BASE_INDEX_PATH / f"{safe_index_name}.db"
            possible_dir    = BASE_INDEX_PATH / safe_index_name

            if possible_db.exists():
                pipeline = RAGPipeline(index_path=possible_db)
            elif possible_dir.exists():
                pipeline = RAGPipeline(index_path=possible_dir)
            else:
                logger.warning(f"Index '{safe_index_name}' not found – falling back to auto.")
                pipeline = get_pipeline()

        return StreamingResponse(
            pipeline.query_stream_auto(
                question=question,
                search_type=req.get("search_type", "hybrid").lower(),
                top_k=int(req.get("top_k", 10)),
            ),
            media_type="text/event-stream",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/query-visual")
async def query_visual(
    index_type: str        = Form(...),
    question:   str        = Form(...),
    image:      UploadFile = File(...),
):
    """Query context using an uploaded image + text."""
    try:
        image_data = await image.read()

        pipeline = (
            get_pipeline()
            if index_type == "auto"
            else RAGPipeline(
                index_path=BASE_INDEX_PATH / re.sub(r"[^\w-]", "_", index_type)
                if (BASE_INDEX_PATH / re.sub(r"[^\w-]", "_", index_type)).exists()
                else None
            )
        )

        return StreamingResponse(
            pipeline.query_visual(
                question=question,
                image_bytes=image_data,
                source="vector_index",
            ),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"Visual query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/query-data")
async def query_data(
    question: str               = Form(...),
    files:    List[UploadFile]  = File(...),
):
    """Query tabular data (Excel / CSV) using Text-to-SQL (no pre-ingestion needed)."""
    try:
        loaded_files = []
        for f in files:
            content = await f.read()
            loaded_files.append((f.filename, content))

        pipeline = RAGPipeline(index_path=None)   # ad-hoc, no stored index needed

        return StreamingResponse(
            pipeline.query_excel_sql(
                question=question,
                file_list=loaded_files,
            ),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"Data query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-cache")
async def clear_cache():
    """Clears the semantic query cache."""
    try:
        pipeline = get_pipeline()
        if pipeline.clear_cache():
            return {"status": "success", "message": "Cache cleared."}
        raise HTTPException(status_code=500, detail="Failed to clear cache.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache clear failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))