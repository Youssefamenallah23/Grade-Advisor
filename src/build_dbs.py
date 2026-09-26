"""
Database construction script for Grade Advisor.
Builds the relational store (DuckDB) and vector store (ChromaDB) from data/extracted.json.
Ensures exact primary key linkage between DuckDB 'name' and ChromaDB metadata 'grade_name'.
"""

import os
import json
import logging
import duckdb
import chromadb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_dbs")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

DATA_PATH = os.path.join(project_root, "data", "extracted.json")
DUCKDB_PATH = os.path.join(project_root, "data", "grades.db")
CHROMA_PATH = os.path.join(project_root, "data", "chroma_db")


def build_databases():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Extracted dataset not found at {DATA_PATH}. Run extract.py first.")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        grades = json.load(f)

    logger.info(f"Loaded {len(grades)} grade records from {DATA_PATH}")

    # ==========================================
    # 1. DuckDB Setup (Structured Data)
    # ==========================================
    logger.info(f"Populating DuckDB at {DUCKDB_PATH}...")
    if os.path.exists(DUCKDB_PATH):
        try:
            os.remove(DUCKDB_PATH)
        except Exception:
            pass

    conn = duckdb.connect(DUCKDB_PATH)
    conn.execute("DROP TABLE IF EXISTS steel_grades")
    conn.execute("""
        CREATE TABLE steel_grades (
            name VARCHAR PRIMARY KEY,
            family VARCHAR,
            hardness_min FLOAT,
            hardness_max FLOAT,
            c_pct FLOAT,
            cr_pct FLOAT,
            mo_pct FLOAT,
            w_pct FLOAT,
            v_pct FLOAT,
            co_pct FLOAT,
            machinability FLOAT,
            wear_resistance FLOAT,
            toughness FLOAT,
            hot_hardness FLOAT,
            grindability FLOAT,
            standards VARCHAR,
            raw_json VARCHAR
        )
    """)

    for g in grades:
        conn.execute("""
            INSERT INTO steel_grades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            g["name"],
            g["family"],
            float(g["hardness_min"]),
            float(g["hardness_max"]),
            float(g["c_pct"]),
            float(g["cr_pct"]),
            float(g["mo_pct"]),
            float(g["w_pct"]),
            float(g["v_pct"]),
            float(g["co_pct"]),
            float(g.get("machinability", 5.0)),
            float(g.get("wear_resistance", 5.0)),
            float(g.get("toughness", 5.0)),
            float(g.get("hot_hardness", 5.0)),
            float(g.get("grindability", 5.0)),
            g.get("standards", ""),
            json.dumps(g, ensure_ascii=False)
        ))

    total_duckdb = conn.execute("SELECT COUNT(*) FROM steel_grades").fetchone()[0]
    conn.close()
    logger.info(f"DuckDB populated with {total_duckdb} records.")

    # ==========================================
    # 2. ChromaDB Setup (Vector Search)
    # ==========================================
    logger.info(f"Populating ChromaDB at {CHROMA_PATH}...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Reset or get collection
    try:
        chroma_client.delete_collection("grade_descriptions")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name="grade_descriptions",
        metadata={"hnsw:space": "cosine"}
    )

    documents = []
    metadatas = []
    ids = []

    for g in grades:
        # Create semantic text document
        doc_text = (
            f"Grade Name: {g['name']}\n"
            f"Application Family: {g['family']}\n"
            f"Standards: {g.get('standards', 'N/A')}\n"
            f"Description: {g['description']}\n"
            f"Tooling Applications: {g['applications']}\n"
            f"Heat Treatment and Hardness: {g['heat_treatment']}. Hardness range: {g['hardness_min']} to {g['hardness_max']} HRC.\n"
            f"Properties profile: Machinability {g.get('machinability', '')}/10, "
            f"Wear resistance {g.get('wear_resistance', '')}/10, Toughness {g.get('toughness', '')}/10, "
            f"Hot hardness {g.get('hot_hardness', '')}/10, Grindability {g.get('grindability', '')}/10."
        )
        documents.append(doc_text)
        metadatas.append({
            "grade_name": g["name"],
            "family": g["family"]
        })
        ids.append(g["name"])

    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    logger.info(f"ChromaDB collection 'grade_descriptions' populated with {collection.count()} embeddings.")
    print("Databases successfully built!")


if __name__ == "__main__":
    build_databases()
