"""
app/src/intent_router.py

Classifies a user question as SQL, VECTOR, or GREETING.
Only used when pipeline mode == "both".
"""

import re
import logging
import sqlite3
from pathlib import Path
from typing import Callable

from langfuse import observe

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_sql_schema_summary(sql_db_path: Path) -> str:
    """Returns full table+column schema string from the SQLite DB."""

    if not sql_db_path or not sql_db_path.exists():
        return ""

    try:
        conn = sqlite3.connect(str(sql_db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]

        lines = []
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [f"{col[1]} ({col[2]})" for col in cursor.fetchall()]
            lines.append(f"Table '{table}': {', '.join(cols)}")

        conn.close()
        return "\n".join(lines)

    except Exception as e:
        logger.warning("Could not read SQL schema: %s", e)
        return ""



@observe(name="Identify_Intent", as_type="span")
def identify_intent(
    question: str,
    sql_db_path: Path,
    has_vector: bool,
    llm_sync_fn: Callable[[str], str],
) -> str:
    """
    Returns 'SQL' or 'VECTOR'.
    Uses LLM first.
    Falls back to keyword heuristic if ambiguous.
    """

    sql_schema = get_sql_schema_summary(sql_db_path)

    sql_block = (
        "=== SQL DATABASE (tabular/structured data) ===\n"
        f"{sql_schema}\n"
        "Choose SQL for: counts, sums, averages, specific IDs, filters,\n"
        "table/column names listed above, or any structured data lookup.\n\n"
    ) if sql_schema else "No SQL database available. Do NOT choose SQL.\n\n"

    vector_block = (
        "=== DOCUMENT INDEX (text/unstructured data) ===\n"
        "Choose VECTOR for: definitions, summaries, explanations,\n"
        "policies, 'what is', 'how does', or conceptual questions.\n\n"
    ) if has_vector else "No document index available. Do NOT choose VECTOR.\n\n"

    prompt = (
        "You are a query router. Output EXACTLY one word: SQL or VECTOR.\n"
        "Do not explain. Do not punctuate. Just the single word.\n\n"
        f"{sql_block}"
        f"{vector_block}"
        f'Question: "{question}"\n\n'
        "Answer (one word — SQL or VECTOR):"
    )

    raw = ""
    try:
        raw = llm_sync_fn(prompt).strip()
        logger.info("[Intent] LLM raw response: '%s'", raw)
    except Exception as e:
        logger.error("[Intent] LLM call failed: %s", e)

    upper = raw.upper()

    if "SQL" in upper:
        intent = "SQL"
    elif "VECTOR" in upper:
        intent = "VECTOR"
    else:
        intent = _heuristic_intent(question, sql_schema)
        logger.warning(
            "[Intent] Ambiguous LLM response '%s' → heuristic chose '%s'",
            raw,
            intent,
        )

    logger.info("[Intent] Final: '%s'", intent)
    return intent



def _heuristic_intent(question: str, sql_schema: str) -> str:
    """
    Keyword-based fallback.
    SQL wins if: analytics keywords match OR table/column names appear.
    """

    q = question.lower()

    sql_keywords = {
        "how many", "count", "total", "sum", "average", "avg",
        "maximum", "minimum", "max", "min", "list all", "show all",
        "find all", "filter", "sort", "order by", "group by",
        "top ", "bottom ", "between", "greater than", "less than",
        "equals", "compare", "per ", "each ",
    }

    if any(kw in q for kw in sql_keywords):
        logger.info("[Intent] Heuristic matched SQL keyword")
        return "SQL"

    if sql_schema:
        for line in sql_schema.splitlines():
            m = re.match(r"Table '(\w+)':\s*(.*)", line)
            if m:
                table_name = m.group(1).lower()
                col_names = [
                    c.split("(")[0].strip().lower()
                    for c in m.group(2).split(",")
                ]

                if table_name in q:
                    logger.info("[Intent] Heuristic matched table '%s'", table_name)
                    return "SQL"

                if any(col in q for col in col_names if len(col) > 3):
                    logger.info(
                        "[Intent] Heuristic matched column in '%s'",
                        table_name,
                    )
                    return "SQL"

    return "VECTOR"

def is_greeting(text: str) -> bool:
    return bool(
        re.search(r"\b(hi|hello|hey|greetings|help)\b", text.lower())
    )
