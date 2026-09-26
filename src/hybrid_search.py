"""
Core Hybrid Retrieval Module (SQL + Vector Pre-filtering).
Executes structured numerical/elemental filtering on DuckDB,
then restricts ChromaDB semantic search to the matching candidate set using $in metadata filtering.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import duckdb
import chromadb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hybrid_search")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

DEFAULT_DUCKDB_PATH = os.path.join(project_root, "data", "grades.db")
DEFAULT_CHROMA_PATH = os.path.join(project_root, "data", "chroma_db")

ALLOWED_COLUMNS = {
    "name", "family", "hardness_min", "hardness_max",
    "c_pct", "cr_pct", "mo_pct", "w_pct", "v_pct", "co_pct",
    "machinability", "wear_resistance", "toughness", "hot_hardness",
    "grindability", "standards"
}


def sanitize_condition(cond: str) -> str:
    """Sanitizes and normalizes common syntax like '==' to '='."""
    cleaned = cond.strip()
    if "==" in cleaned:
        cleaned = cleaned.replace("==", "=")
    return cleaned


def execute_hybrid_search(
    sql_conditions: Optional[List[str]] = None,
    semantic_query: str = "",
    top_k: int = 3,
    duckdb_path: str = DEFAULT_DUCKDB_PATH,
    chroma_path: str = DEFAULT_CHROMA_PATH
) -> Dict[str, Any]:
    """
    Executes the two-step hybrid retrieval:
    1. Filter candidates via DuckDB SQL WHERE clauses.
    2. Rank surviving candidates using ChromaDB semantic search with metadata filter.
    """
    if not os.path.exists(duckdb_path):
        raise FileNotFoundError(f"DuckDB not found at {duckdb_path}. Run build_dbs.py first.")

    # 1. DuckDB Query Execution
    conn = duckdb.connect(duckdb_path, read_only=True)
    base_sql = "SELECT name, raw_json FROM steel_grades"
    where_clauses = []

    if sql_conditions:
        for c in sql_conditions:
            c_clean = sanitize_condition(c)
            if c_clean:
                where_clauses.append(c_clean)

    if where_clauses:
        sql_query = f"{base_sql} WHERE {' AND '.join(where_clauses)}"
    else:
        sql_query = base_sql

    logger.info(f"Executing DuckDB query: {sql_query}")
    try:
        rows = conn.execute(sql_query).fetchall()
    except Exception as e:
        logger.error(f"DuckDB SQL execution error: {e}")
        conn.close()
        return {
            "success": False,
            "error": f"Invalid SQL condition: {e}",
            "sql_query": sql_query,
            "sql_conditions": sql_conditions,
            "sql_matched_names": [],
            "matches": []
        }
    conn.close()

    matched_names = [r[0] for r in rows]
    grade_data_map = {r[0]: json.loads(r[1]) for r in rows}
    logger.info(f"DuckDB matched {len(matched_names)} grades: {matched_names}")

    # If zero candidates meet SQL conditions, return immediately
    if not matched_names:
        return {
            "success": True,
            "sql_query": sql_query,
            "sql_conditions": sql_conditions,
            "sql_matched_names": [],
            "semantic_query": semantic_query,
            "matches": [],
            "message": "No steel grades satisfy all specified physical/chemical SQL constraints."
        }

    # 2. ChromaDB Semantic Vector Search with Pre-Filter
    if not os.path.exists(chroma_path):
        raise FileNotFoundError(f"ChromaDB not found at {chroma_path}. Run build_dbs.py first.")

    chroma_client = chromadb.PersistentClient(path=chroma_path)
    collection = chroma_client.get_collection(name="grade_descriptions")

    # If no semantic query provided, return matching items sorted by name
    if not semantic_query.strip():
        matches = []
        for name in matched_names[:top_k]:
            matches.append({
                "name": name,
                "distance": 0.0,
                "data": grade_data_map[name]
            })
        return {
            "success": True,
            "sql_query": sql_query,
            "sql_conditions": sql_conditions,
            "sql_matched_names": matched_names,
            "semantic_query": "",
            "matches": matches
        }

    # Filter Chroma query to only the names that passed SQL filtering
    if len(matched_names) == 1:
        where_filter = {"grade_name": matched_names[0]}
    else:
        where_filter = {"grade_name": {"$in": matched_names}}

    n_results = min(top_k, len(matched_names))
    query_result = collection.query(
        query_texts=[semantic_query],
        n_results=n_results,
        where=where_filter
    )

    matches = []
    if query_result and query_result["ids"] and query_result["ids"][0]:
        retrieved_ids = query_result["ids"][0]
        distances = query_result["distances"][0] if "distances" in query_result and query_result["distances"] else [0.0] * len(retrieved_ids)
        
        for grade_id, dist in zip(retrieved_ids, distances):
            matches.append({
                "name": grade_id,
                "distance": round(float(dist), 4),
                "data": grade_data_map.get(grade_id, {})
            })

    return {
        "success": True,
        "sql_query": sql_query,
        "sql_conditions": sql_conditions,
        "sql_matched_names": matched_names,
        "semantic_query": semantic_query,
        "matches": matches
    }


if __name__ == "__main__":
    # Test sample hybrid query
    res = execute_hybrid_search(
        sql_conditions=["co_pct >= 8.0", "hardness_max >= 66"],
        semantic_query="high wear resistance drill grade",
        top_k=3
    )
    print(json.dumps(res, indent=2))
