from pydantic import BaseModel, Field
from typing import Optional, List


class IngestRequest(BaseModel):
    document_path: str
    chunking_strategy: str = "Fixed" 
    index_type: str
    token_limit: int = 512
    max_chars: int = 500

class QueryRequest(BaseModel):
    """
    Standardized to match the JSON sent by script.js:
    JSON: { "question": "...", "index_type": "...", "search_type": "...", "top_k": 10 }
    """
    question: str = Field(..., alias="question")
    search_type: str = Field("Hybrid", alias="search_type")
    index_type: str = Field(..., alias="index_type")
    top_k: int = Field(10, alias="top_k")

    class Config:
        populate_by_name = True
        
        json_schema_extra = {
            "example": {
                "question": "What is the maintenance schedule?",
                "search_type": "Hybrid",
                "index_type": "manuals_v1",
                "top_k": 5
            }
        }

class Citation(BaseModel):
    source: str
    page: Optional[int] = None
    content: Optional[str] = None
    score: Optional[float] = None 

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    transcript: Optional[str] = None 