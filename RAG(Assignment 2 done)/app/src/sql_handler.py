import io
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import AsyncGenerator, Callable, List, Tuple

import pandas as pd
from langfuse import observe

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_SQL_CITATION = [{"source": "SQL Database", "page": "Query", "display": "SQL Database"}]
_CSV_CITATION = [{"source": "Uploaded Data", "display": "Uploaded Files"}]


def _clean_sql(raw: str) -> str:
    """Remove markdown formatting from LLM-generated SQL."""
    return raw.strip().replace("```sql", "").replace("```", "").strip()


def _build_schema(conn: sqlite3.Connection) -> List[str]:
    """Extract table schema information from SQLite connection."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    schema: List[str] = []

    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [f"{col[1]} ({col[2]})" for col in cursor.fetchall()]
        schema.append(f"Table '{table}': {', '.join(columns)}")

    return schema

@observe(name="Persistent_SQL_Query", as_type="span")
async def query_persistent_sql(
    question: str,
    sql_db_path: Path,
    llm_sync_fn: Callable[[str], str],
    llm_stream_fn: Callable[[str], AsyncGenerator[str, None]],
) -> AsyncGenerator[str, None]:
    """
    Query a pre-ingested SQLite database on disk.
    """

    logger.info("Executing persistent SQL query")
    yield f"metadata:{json.dumps({'cache': False, 'citations': _SQL_CITATION})}\n\n"

    conn: sqlite3.Connection | None = None

    try:
        conn = sqlite3.connect(str(sql_db_path))
        schema_info = _build_schema(conn)

        logger.info("Schema extracted. Tables found: %d", len(schema_info))

        sql_prompt = (
            f"Tables:\n{chr(10).join(schema_info)}\n\n"
            f"Question: {question}\n"
            "Write a valid SQLite SQL query. Return ONLY the SQL."
        )

        sql_query = _clean_sql(llm_sync_fn(sql_prompt))
        logger.info("Generated SQL query")

        try:
            result_df = pd.read_sql(sql_query, conn)
            result_str = (
                result_df.to_string()
                if not result_df.empty
                else "No results found."
            )
        except Exception as sql_error:
            logger.warning("SQL execution failed: %s", sql_error)
            result_str = f"SQL Error: {sql_error}"

        final_prompt = (
            "You are a data analyst. Summarise the SQL result below.\n"
            "Rules:\n"
            "- Use ONLY the provided result.\n"
            "- Do not invent values.\n"
            "- If empty, clearly state no records were found.\n\n"
            f"Question: {question}\n"
            f"SQL Result:\n{result_str}\n\n"
            "Summary:"
        )

        async for token in llm_stream_fn(final_prompt):
            yield f"data: {token}\n\n"

    except Exception as e:
        logger.exception("Persistent SQL query failed")
        yield f"data: Database error: {e}\n\n"

    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")


@observe(name="Excel_SQL_Query", as_type="span")
async def query_excel_sql(
    question: str,
    file_list: List[Tuple[str, bytes]],
    llm_sync_fn: Callable[[str], str],
    llm_stream_fn: Callable[[str], AsyncGenerator[str, None]],
) -> AsyncGenerator[str, None]:
    """
    Load CSV/Excel files into an in-memory SQLite DB and answer using Text-to-SQL.
    """

    logger.info("Executing in-memory SQL query from uploaded files")
    yield f"metadata:{json.dumps({'cache': False, 'citations': _CSV_CITATION})}\n\n"

    conn = sqlite3.connect(":memory:")
    loaded_tables: List[Tuple[str, List[str]]] = []

    try:
        # Load files
        for filename, content in file_list:
            ext = Path(filename).suffix.lower()

            try:
                if ext == ".csv":
                    df = pd.read_csv(io.BytesIO(content))
                else:
                    df = pd.read_excel(io.BytesIO(content))

                # Normalize column names
                df.columns = [
                    re.sub(r"[^\w]", "_", str(col).strip().lower())
                    for col in df.columns
                ]

                table_name = re.sub(
                    r"[^\w]", "_", Path(filename).stem.lower()
                )

                df.to_sql(table_name, conn, index=False, if_exists="replace")

                loaded_tables.append((table_name, list(df.columns)))

                logger.info("Loaded file '%s' as table '%s'", filename, table_name)
                yield f"data: Loaded `{filename}` as `{table_name}`\n\n"

            except Exception as file_error:
                logger.warning("Failed to load file %s: %s", filename, file_error)
                yield f"data: Could not load `{filename}`: {file_error}\n\n"

        if not loaded_tables:
            yield "data: No valid files were loaded.\n\n"
            return

        schema_info = [
            f"Table '{name}': {', '.join(cols)}"
            for name, cols in loaded_tables
        ]

        sql_prompt = (
            f"Tables:\n{chr(10).join(schema_info)}\n\n"
            f"Question: {question}\n"
            "Write a valid SQLite SQL query. Return ONLY the SQL."
        )

        sql_query = _clean_sql(llm_sync_fn(sql_prompt))
        logger.info("Generated SQL query for uploaded data")

        try:
            result_df = pd.read_sql(sql_query, conn)
            result_str = (
                result_df.to_string()
                if not result_df.empty
                else "No results found."
            )
        except Exception as sql_error:
            logger.warning("SQL execution failed: %s", sql_error)
            result_str = f"SQL Error: {sql_error}"

        final_prompt = (
            f"Question: {question}\n"
            f"Result:\n{result_str}\n\n"
            "Provide a clear summary based only on the result above."
        )

        async for token in llm_stream_fn(final_prompt):
            yield f"data: {token}\n\n"

    except Exception as e:
        logger.exception("Unexpected error in Excel SQL handler")
        yield f"data: Unexpected error: {e}\n\n"

    finally:
        conn.close()
        logger.info("In-memory database closed")
