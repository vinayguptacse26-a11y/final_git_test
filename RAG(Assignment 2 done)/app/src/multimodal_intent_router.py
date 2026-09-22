import re
import logging
from typing import Dict, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


def classify_multimodal_intent(
    question: str,
    
    has_image: bool,
    has_vector_index: bool,
    has_sql_db: bool,
    llm_sync_fn: Callable[[str], str],
    sql_db_path: Optional[Path] = None,
) -> Dict[str, any]:
    """
    Classify user intent and determine which data sources to use.
    
    Args:
        question: User's natural language question
        has_image: Whether an image was uploaded with this query
        has_vector_index: Whether vector search is available
        has_sql_db: Whether SQL database is available
        llm_sync_fn: Function to call LLM synchronously
        sql_db_path: Path to SQL database (for schema extraction)
        
    Returns:
        Dict with keys:
          - intent: "TEXT", "SQL", "VISUAL", or "HYBRID"
          - data_sources: List of sources to query (e.g., ["IMAGE_ONLY"])
          - requires_image: bool
          - requires_vector: bool
          - requires_sql: bool
          - reasoning: str (explanation of the decision)
    """
    logger.info(
        "classify_multimodal_intent | question='%s' | has_image=%s | has_vector=%s | has_sql=%s",
        question[:80], has_image, has_vector_index, has_sql_db
    )
    
    # Step 1: Quick heuristic checks (fast path)
    heuristic_result = _heuristic_classification(
        question, has_image, has_vector_index, has_sql_db
    )
    
    if heuristic_result:
        logger.info(
            "Intent classified (heuristic) | intent=%s | sources=%s",
            heuristic_result["intent"], heuristic_result["data_sources"]
        )
        return heuristic_result
    
    # Step 2: LLM-based classification (for ambiguous cases)
    llm_result = _llm_classification(
        question, has_image, has_vector_index, has_sql_db, 
        llm_sync_fn, sql_db_path
    )
    
    logger.info(
        "Intent classified (LLM) | intent=%s | sources=%s | reasoning=%s",
        llm_result["intent"], llm_result["data_sources"], 
        llm_result["reasoning"][:100]
    )
    
    return llm_result


def _heuristic_classification(
    question: str,
    has_image: bool,
    has_vector_index: bool,
    has_sql_db: bool,
) -> Optional[Dict]:
    """
    Fast heuristic classification based on keywords.
    Returns None if ambiguous (requires LLM).
    """
    q = question.lower()
    
  
    image_only_patterns = [
        r"\banalyze\s+(this\s+)?image\b",
        r"\bwhat\s+(is|are)\s+(in\s+)?(this\s+)?image\b",
        r"\bdescribe\s+(this\s+)?image\b",
        r"\bwhat\s+do(es)?\s+you\s+see\b",
        r"\btranscribe\s+(this\s+)?image\b",
        r"\bread\s+(this\s+)?image\b",
        r"\bextract\s+text\s+from\s+(this\s+)?image\b",
        r"\bwhat'?s\s+in\s+(this\s+)?(picture|photo|screenshot)\b",
        r"\bidentify\s+(what'?s\s+)?in\s+(this\s+)?image\b",
    ]
    
    if has_image:
        for pattern in image_only_patterns:
            if re.search(pattern, q):
                return {
                    "intent": "VISUAL",
                    "data_sources": ["IMAGE_ONLY"],
                    "requires_image": True,
                    "requires_vector": False,
                    "requires_sql": False,
                    "reasoning": f"Heuristic match: '{pattern}' indicates image analysis only"
                }
    

    image_and_vector_patterns = [
        r"\b(find|show|get|retrieve)\s+(related|relevant|similar)\s+document",
        r"\bdocument.*related\s+to\s+(this\s+)?image\b",
        r"\bimage.*compare.*document",
        r"\b(match|find)\s+.*in\s+(the\s+)?document",
        r"\bprovide.*document.*about.*image\b",
    ]
    
    if has_image and has_vector_index:
        for pattern in image_and_vector_patterns:
            if re.search(pattern, q):
                return {
                    "intent": "HYBRID",
                    "data_sources": ["IMAGE_AND_VECTOR"],
                    "requires_image": True,
                    "requires_vector": True,
                    "requires_sql": False,
                    "reasoning": f"Heuristic match: '{pattern}' requires both image and documents"
                }
    
    sql_patterns = [
        r"\bhow\s+many\b",
        r"\bcount\b",
        r"\btotal\b",
        r"\baverage\b",
        r"\bsum\b",
        r"\bmaximum\b",
        r"\bminimum\b",
        r"\blist\s+all\b",
        r"\bshow\s+all\b",
        r"\bfilter\b",
        r"\bgroup\s+by\b",
    ]
    
    if has_sql_db:
        for pattern in sql_patterns:
            if re.search(pattern, q):
                return {
                    "intent": "SQL",
                    "data_sources": ["SQL_ONLY"],
                    "requires_image": False,
                    "requires_vector": False,
                    "requires_sql": True,
                    "reasoning": f"Heuristic match: '{pattern}' indicates SQL query"
                }
    

    return None


def _llm_classification(
    question: str,
    has_image: bool,
    has_vector_index: bool,
    has_sql_db: bool,
    llm_sync_fn: Callable[[str], str],
    sql_db_path: Optional[Path],
) -> Dict:
    """
    Use LLM to classify ambiguous queries.
    """
    # Build available data sources description
    sources_description = []
    if has_image:
        sources_description.append("IMAGE: An uploaded image (analyze visual content)")
    if has_vector_index:
        sources_description.append("VECTOR: Document collection (text search, definitions, policies)")
    if has_sql_db:
        schema = _get_sql_schema_summary(sql_db_path) if sql_db_path else ""
        sources_description.append(f"SQL: Structured database\n{schema}")
    
    sources_text = "\n".join(sources_description)
    
    prompt = f"""You are a query intent classifier. Analyze the user's question and determine which data sources to use.

AVAILABLE DATA SOURCES:
{sources_text}

USER QUESTION:
"{question}"

CLASSIFICATION RULES:
1. IMAGE_ONLY: User wants to analyze/describe/transcribe the uploaded image itself
   Examples: "What's in this image?", "Describe this diagram", "Read this text"

2. VECTOR_ONLY: User wants text information from documents (no image needed)
   Examples: "What is a CTE?", "Explain window functions", "Company policy on X"

3. SQL_ONLY: User wants statistics/counts/aggregations from structured data
   Examples: "How many orders?", "Average revenue?", "List all customers"

4. IMAGE_AND_VECTOR: User wants to analyze image AND find related documents
   Examples: "Find documents related to this diagram", "Show me policies about this equipment"

5. IMAGE_AND_SQL: User wants to analyze image AND query structured data (rare)
   Examples: "How many of these items are in stock?" (with product image)

OUTPUT FORMAT (return ONLY this JSON):
{{
  "intent": "<VISUAL|TEXT|SQL|HYBRID>",
  "data_sources": ["<IMAGE_ONLY|VECTOR_ONLY|SQL_ONLY|IMAGE_AND_VECTOR|IMAGE_AND_SQL>"],
  "reasoning": "<1-2 sentence explanation>"
}}"""

    try:
        raw_response = llm_sync_fn(prompt)
        logger.debug("LLM classification response: %s", raw_response[:200])
        
        # Parse JSON response
        import json
        # Extract JSON from response (may have markdown fences)
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
            
            # Map intent and data_sources to boolean flags
            intent = result.get("intent", "TEXT")
            data_sources = result.get("data_sources", ["VECTOR_ONLY"])
            reasoning = result.get("reasoning", "LLM classification")
            
            requires_image = any("IMAGE" in src for src in data_sources)
            requires_vector = any("VECTOR" in src for src in data_sources)
            requires_sql = any("SQL" in src for src in data_sources)
            
            return {
                "intent": intent,
                "data_sources": data_sources,
                "requires_image": requires_image,
                "requires_vector": requires_vector,
                "requires_sql": requires_sql,
                "reasoning": reasoning
            }
        
    except Exception as e:
        logger.error("LLM classification failed: %s", e)
    
    # Fallback: Use simple defaults based on what's available
    if has_image:
        return {
            "intent": "VISUAL",
            "data_sources": ["IMAGE_ONLY"],
            "requires_image": True,
            "requires_vector": False,
            "requires_sql": False,
            "reasoning": "Fallback: Image provided, defaulting to image analysis"
        }
    elif has_vector_index:
        return {
            "intent": "TEXT",
            "data_sources": ["VECTOR_ONLY"],
            "requires_image": False,
            "requires_vector": True,
            "requires_sql": False,
            "reasoning": "Fallback: No image, defaulting to vector search"
        }
    else:
        return {
            "intent": "TEXT",
            "data_sources": ["VECTOR_ONLY"],
            "requires_image": False,
            "requires_vector": False,
            "requires_sql": False,
            "reasoning": "Fallback: No data sources available"
        }


def _get_sql_schema_summary(sql_db_path: Path) -> str:
    """Extract SQL schema for the LLM prompt."""
    if not sql_db_path or not sql_db_path.exists():
        return ""
    try:
        import sqlite3
        conn = sqlite3.connect(str(sql_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        lines = []
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [f"{col[1]} ({col[2]})" for col in cursor.fetchall()]
            lines.append(f"  Table '{table}': {', '.join(cols)}")
        conn.close()
        return "\n".join(lines)
    except Exception as e:
        logger.warning("Could not read SQL schema: %s", e)
        return ""


if __name__ == "__main__":
    def mock_llm(prompt):
        return '{"intent": "VISUAL", "data_sources": ["IMAGE_ONLY"], "reasoning": "User wants image analysis"}'
    
    # Test case 1: Image-only query
    result = classify_multimodal_intent(
        question="Analyze this circuit diagram",
        has_image=True,
        has_vector_index=True,
        has_sql_db=False,
        llm_sync_fn=mock_llm
    )
    print("Test 1:", result)
    
    # Test case 2: Image + Vector query
    result = classify_multimodal_intent(
        question="Find documents related to this image",
        has_image=True,
        has_vector_index=True,
        has_sql_db=False,
        llm_sync_fn=mock_llm
    )
    print("Test 2:", result)
    
    # Test case 3: Text-only query
    result = classify_multimodal_intent(
        question="What is a window function?",
        has_image=False,
        has_vector_index=True,
        has_sql_db=True,
        llm_sync_fn=mock_llm
    )
    print("Test 3:", result)