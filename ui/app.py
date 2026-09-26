"""
Grade Advisor: Gradio Web Frontend.
Exposes intermediate retrieval internals (SQL clauses, semantic vector query,
database JSON snippets) alongside the synthesized metallurgical answer.
"""

import os
import sys
import json
import gradio as gr
import pandas as pd

# Add src to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from agent import GradeAdvisorAgent
from hybrid_search import execute_hybrid_search

DATA_PATH = os.path.join(project_root, "data", "extracted.json")

agent = GradeAdvisorAgent()

def load_catalog_df():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        cols = ["name", "family", "c_pct", "cr_pct", "mo_pct", "w_pct", "v_pct", "co_pct", "hardness_min", "hardness_max", "standards"]
        return df[cols]
    return pd.DataFrame()


def process_query(user_query: str):
    if not user_query or not user_query.strip():
        return (
            "Please enter a valid query or click one of the example queries below.",
            "",
            "",
            pd.DataFrame(columns=["Rank", "Grade", "Distance", "Family"]),
            "{}"
        )

    res = agent.run(user_query.strip())
    
    # 1. SQL Details
    sql_clauses = res.get("sql_conditions", [])
    sql_text = f"-- Extracted SQL Conditions:\n"
    if sql_clauses:
        sql_text += "\n".join([f"AND {c}" if i > 0 else f"WHERE {c}" for i, c in enumerate(sql_clauses)])
    else:
        sql_text += "-- No strict numeric filters extracted (querying all catalog grades)"
    
    matched_names = res.get("sql_matched_names", [])
    sql_text += f"\n\n-- DuckDB Candidates Matched ({len(matched_names)}):\n"
    sql_text += ", ".join(matched_names) if matched_names else "None (Constraint check failed)"

    # 2. Semantic Query
    sem_text = res.get("semantic_query", "N/A")

    # 3. ChromaDB Ranking Table
    matches = res.get("matches", [])
    rank_rows = []
    for idx, m in enumerate(matches, 1):
        gdata = m.get("data", {})
        rank_rows.append({
            "Rank": idx,
            "Grade": m["name"],
            "Distance": m.get("distance", 0.0),
            "Family": gdata.get("family", "N/A")
        })
    rank_df = pd.DataFrame(rank_rows) if rank_rows else pd.DataFrame(columns=["Rank", "Grade", "Distance", "Family"])

    # 4. Raw JSON Snippet
    raw_json_str = json.dumps([m.get("data", {}) for m in matches], indent=2, ensure_ascii=False)

    # 5. Final Answer
    final_answer = res.get("final_answer", "")

    return final_answer, sql_text, sem_text, rank_df, raw_json_str


# Build Gradio UI
custom_css = """
.title-banner { text-align: center; margin-bottom: 20px; }
.output-card { border-radius: 8px; border: 1px solid #e2e8f0; padding: 15px; }
"""

with gr.Blocks(title="Grade Advisor - Erasteel HSS Hybrid RAG") as demo:
    gr.Markdown(
        """
        # ⚙️ Grade Advisor: Hybrid RAG for HSS Grade Selection
        ### Multi-modal PDF Ingestion • DuckDB Relational Filters • ChromaDB Vector Search • Gemini Agent Router
        *Built on Erasteel's public technical datasheets for Powder Metallurgy (ASP®) and Conventional High-Speed Steels.*
        """
    )

    with gr.Row():
        with gr.Column(scale=4):
            query_input = gr.Textbox(
                label="Tooling & Application Query",
                placeholder="e.g. High wear resistance drill grade, >8% Cobalt",
                lines=2
            )
            with gr.Row():
                submit_btn = gr.Button("🔍 Recommend Grade", variant="primary")
                clear_btn = gr.Button("Clear")

            gr.Markdown("#### Example Queries (Click to test)")
            example_queries = [
                "Cold work tooling, max toughness, HRC around 60, zero cobalt.",
                "High wear resistance drill grade, >8% Cobalt",
                "Dedicated steel for manufacturing machine taps, balanced grindability and toughness.",
                "Plastic injection molds in corrosive environment, stainless high chromium PM tool steel.",
                "Dry high-speed gear skiving requiring extreme hot hardness and ultra-high cobalt (>20% cobalt).",
                "Extreme wear resistance industrial granulator knives, non-cobalt, high vanadium (>5% vanadium).",
                "Impossible constraint: tool steel with > 35% cobalt and hardness > 75 HRC."
            ]
            gr.Examples(
                examples=example_queries,
                inputs=query_input
            )

        with gr.Column(scale=5):
            gr.Markdown("### 📋 Final Recommendation & Metallurgical Citations")
            final_output = gr.Markdown(label="Recommendation")

    gr.Markdown("---")
    gr.Markdown("### 🔬 Retrieval Internals (Inspection & Audit Trail)")
    
    with gr.Row():
        with gr.Column(scale=1):
            sql_output = gr.Code(
                label="DuckDB Executed SQL & Filtered Candidates",
                language="sql",
                lines=6
            )
        with gr.Column(scale=1):
            semantic_output = gr.Textbox(
                label="ChromaDB Semantic Vector Query",
                lines=2
            )
            ranking_output = gr.Dataframe(
                label="ChromaDB Filtered Vector Rankings ($in filter applied)",
                headers=["Rank", "Grade", "Distance", "Family"]
            )

    with gr.Accordion("📦 Raw Database JSON Snippets (Surviving Candidates)", open=False):
        json_output = gr.Code(
            label="Retrieved Grade Specifications",
            language="json",
            lines=12
        )

    with gr.Accordion("📚 Erasteel Catalog Browser (13 Verified Grades)", open=False):
        catalog_df = load_catalog_df()
        gr.Dataframe(catalog_df, label="Verified Erasteel Grade Catalog")

    # Wire events
    submit_btn.click(
        fn=process_query,
        inputs=[query_input],
        outputs=[final_output, sql_output, semantic_output, ranking_output, json_output]
    )
    query_input.submit(
        fn=process_query,
        inputs=[query_input],
        outputs=[final_output, sql_output, semantic_output, ranking_output, json_output]
    )
    clear_btn.click(
        fn=lambda: ("", "", "", pd.DataFrame(columns=["Rank", "Grade", "Distance", "Family"]), "{}"),
        outputs=[final_output, sql_output, semantic_output, ranking_output, json_output]
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False, css=custom_css)
