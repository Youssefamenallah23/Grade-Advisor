"""
Grade Advisor: Production Web Server.

Serves the custom-built Metallurgical Datasheet UI and exposes a clean JSON API
over the existing hybrid retrieval agent (DuckDB + ChromaDB + Gemini).

FastAPI + Uvicorn ship as Gradio dependencies, so no new packages are required.

Run:
    python ui/server.py
Open:
    http://127.0.0.1:7860
"""

import os
import sys
import json
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

import agent as agent_module
from agent import GradeAdvisorAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("server")

STATIC_DIR = os.path.join(current_dir, "static")
DATA_PATH = os.path.join(project_root, "data", "extracted.json")

agent = GradeAdvisorAgent()

app = FastAPI(title="Grade Advisor API", docs_url=None, redoc_url=None)


class QueryRequest(BaseModel):
    query: str


@app.get("/api/health")
def health():
    """Reports active router mode and catalog size for the UI status chip."""
    router = "deterministic" if not (agent_module.GENAI_AVAILABLE and agent_module.GEMINI_API_KEY) else "gemini"
    model = agent_module.GEMINI_MODEL if router == "gemini" else "ast-pattern-router"
    catalog_size = 0
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            catalog_size = len(json.load(f))
    except Exception:
        pass
    return {"router": router, "model": model, "catalog_size": catalog_size}


@app.get("/api/catalog")
def catalog():
    """Full verified Erasteel catalog for the explorer table."""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return JSONResponse(json.load(f))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/query")
def run_query(req: QueryRequest):
    """Executes the dual-stage hybrid retrieval and returns raw structured data."""
    if not req.query or not req.query.strip():
        return JSONResponse({"error": "Empty query."}, status_code=400)
    try:
        res = agent.run(req.query.strip())
        # Serialise numpy/tuple types defensively
        return JSONResponse(json.loads(json.dumps(res, default=float, ensure_ascii=False)))
    except Exception as e:
        logger.exception("Query failed")
        return JSONResponse({"error": str(e)}, status_code=500)


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="warning")