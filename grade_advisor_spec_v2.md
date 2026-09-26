# Grade Advisor: Implementation Spec v2

Hybrid RAG architecture (SQL + Vector) for HSS grade selection, built on Erasteel's
public datasheets. This is a portfolio demo, not a production system: scope is
deliberately small, but the eval discipline is not.

## Changelog from v1

- Single model instead of two: **Gemini 3.5 Flash-Lite** handles both extraction and
  agent routing (v1 split extraction/Flash-Lite vs agent/1.5-Pro). Reason: free-tier
  access. Compensate for weaker reasoning on the agent side with a higher `thinking`
  level on those calls only (see Phase 3).
- Scope cut from 60+ grades / 50 eval cases to **12-15 grades / 15-20 eval cases**.
  Nothing about the architecture, the hybrid retrieval split, or the eval metrics
  changed, only volume.
- Added rate-limit handling, required on the free tier (see Phase 1 and Phase 3).

## 1. Core Technology Stack

**AI Model**
- Gemini 3.5 Flash-Lite (`gemini-3.5-flash-lite`) for both extraction and agent
  routing. Supports PDF input, function calling, structured outputs (`response_schema`),
  and configurable thinking levels.
- Get a free API key from Google AI Studio (no billing enabled). This gives a real
  free quota, rate-limited (roughly 10-15 requests/minute, low hundreds to ~1000
  requests/day, check current numbers in AI Studio, they change). Enabling billing
  raises the limits but is not required for this scope.
- Free tier note: prompts/outputs may be used by Google to improve their models.
  Not an issue here, all input data is Erasteel's public datasheets.

**Database & Infrastructure**
- Relational / filters: DuckDB (in-memory or local file).
- Vector store: ChromaDB (local persistence).
- Orchestration: raw Python + API calls, no heavy agent framework.

## 2. System Architecture Flow

```
User Query: "High wear resistance drill grade, >8% Cobalt"
        |
Gemini 3.5 Flash-Lite (Agent Router, thinking level: high)
        |
   +---------------------------+
   |                           |
DuckDB (Structured)      ChromaDB (Semantic)
SELECT name FROM grades  Search: "wear resistant drill"
WHERE cobalt >= 8         Filter: name IN [DuckDB_Results]
   |                           |
   +------------+--------------+
                |
   Synthesis & Generation with Citations
```

## Phase 1: PDF Extraction Pipeline (12-15 grades)

**Grade selection.** Pick grades spanning Erasteel's 3 application families so the
demo shows breadth, not depth in one niche. Confirmed candidates from public pages:

- Cutting tools: ASP®2023, ASP®2030, ASP®2011, BlueTap®Max (taps specifically),
  Evoloop® M42
- Cold work: ASP®2012 (Erasteel publishes a dedicated Cold Work brochure for this
  grade), ASP®2042, ASP®2048, ASP®2078
- Specialties: ASP®2053, ASP®APZ10, ASP®2190

That's 12. Fill the remaining 0-3 slots by checking the live Grades and
Applications pages at erasteel.com/documents and picking whatever rounds out
under-represented families. Don't guess application mappings you haven't
verified on the actual site, pull the datasheet and confirm.

**Step 1: Multimodal ingestion.** Upload raw PDFs directly via the Gemini File
API. Do not pre-strip text, the multimodal path handles irregular table layouts
better than pdfplumber-style parsing.

**Step 2: Structured output enforcement.** Use `response_schema` (or Pydantic via
the `google-genai` SDK) to force strict JSON: grade name, family, composition
(C, Cr, Mo, W, V, Co), hardness range, the 5 qualitative property ratings
(machinability, wear resistance, toughness, hot hardness, grindability),
standards, applications, heat treatment.

**Step 3: Prompt engineering for edge cases.**
- Composition given as a range (e.g. 5.0-5.5% Mo) → extract the average.
- Extract the maximum reachable hardness in HRC from tempering curves.

**Step 4: Automated validation.** Load extracted JSON into a Pandas DataFrame,
check for physical impossibilities (total composition > 100%, hardness > 80 HRC).
Reject and flag failed parses for manual review.

**Step 5: Rate limiting.** 12-15 sequential extraction calls will likely stay
under free-tier RPM, but add a basic sleep/retry-with-backoff around the API
call anyway. Trivial to write, avoids a silent partial failure mid-batch.

## Phase 2: Hybrid Database Construction

Unchanged from v1. All exact values live in SQL, all descriptive text lives in
the vector DB.

```python
# 1. DuckDB setup (structured data)
import duckdb
conn = duckdb.connect('grades.db')
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
        co_pct FLOAT
    )
""")

# 2. ChromaDB setup (vector search)
import chromadb
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.create_collection(name="grade_descriptions")
# Store the DuckDB 'name' as metadata: {"grade_name": "ASP 2030"}
```

Crucial linkage: when embedding textual descriptions (applications, wear
resistance profiles) into ChromaDB, store the exact DuckDB primary key (grade
name) in the ChromaDB metadata payload.

## Phase 3: Gemini Agent Orchestration

The agent is a router. It translates user intent into database queries, it does
not answer from its own weights.

**Tool definition:**
```
query_database(sql_conditions: list[str], semantic_query: str)
```

**Model config:** `gemini-3.5-flash-lite`, thinking level set high for these
routing calls specifically (keep it minimal for Phase 1 extraction calls, that's
pure parsing). Higher thinking partially compensates for Flash-Lite's weaker
multi-constraint reasoning versus a Pro-tier model.

**Execution loop:**
1. Agent parses the prompt: "I need a tough punch material, at least 60 HRC, no
   cobalt."
2. Agent calls the tool: `sql_conditions = ["hardness_max >= 60", "co_pct = 0"]`,
   `semantic_query = "tough punch material"`.
3. Backend executes the SQL on DuckDB, gets matching grade names.
4. Backend queries ChromaDB with `semantic_query`, applying an `$in` metadata
   filter restricted to the DuckDB result names.
5. Agent formats the final answer, citing the specific database fields used.

**Rate limiting:** same as Phase 1, wrap the call in retry-with-backoff.

## Phase 4: Deterministic Evaluation Benchmark (15-20 cases)

Scaled down from v1's 50, metrics unchanged, do not water these down:

- **Zero-tolerance constraint check:** each test case has numeric rules. If the
  system recommends a grade violating the SQL bounds, the test fails instantly
  (score = 0). No partial credit.
- **Precision@3:** is the human-determined optimal grade present in the top 3
  results?

Build the 15-20 cases to cover all 3 application families and to include a few
queries with no valid match (to check the system says so instead of forcing a
bad recommendation).

Example:
```
Q: "Cold work tooling, max toughness, HRC around 60, zero cobalt."
Expected top result: ASP®2023 or ASP®2012 (confirm against actual extracted data)
```

## Repository Structure

```
grade-advisor/
├── data/
│   ├── raw_pdfs/          # 12-15 Erasteel datasheets
│   ├── extracted.json     # Output from Flash-Lite extraction pipeline
│   └── eval_cases.json    # 15-20 benchmark queries
├── src/
│   ├── extract.py         # Multimodal ingestion script
│   ├── build_dbs.py       # Populates DuckDB and ChromaDB
│   ├── hybrid_search.py   # Core logic: SQL execution + vector pre-filtering
│   ├── agent.py           # Flash-Lite function-calling loop
│   └── rate_limit.py      # Retry/backoff wrapper shared by extract.py and agent.py
├── evals/
│   └── run_benchmark.py   # pytest suite executing eval_cases.json
├── ui/
│   └── app.py             # Gradio frontend showing intermediate steps
├── requirements.txt
└── .env                   # GEMINI_API_KEY
```

## Frontend Design (Gradio)

Expose the agent's internal reasoning. On query submit, show (accordions or
text boxes):
- The extracted SQL WHERE clauses
- The extracted semantic vector query
- The raw JSON snippet retrieved from the database
- The final synthesized answer

Showing the retrieval internals, not just a chat answer, is what makes this
read as a research/engineering demo rather than a chatbot wrapper.
