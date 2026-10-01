"""
Grade Advisor: Modern White-Box Inspection Dashboard (Production Build).

Designed for engineering presentations, executive demonstrations, and technical audits.
Exposes dual-stage retrieval internals:
- DuckDB Deterministic Relational Filters (SQL)
- ChromaDB Pre-Filtered Dense Vector Semantic Rankings ($in filter applied)
- Ground-truth Database Payloads & Metallurgical Synthesis with Citations.
"""

import os
import sys
import json
import html
import logging

import gradio as gr
import pandas as pd

# Add src directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from agent import GradeAdvisorAgent
from hybrid_search import execute_hybrid_search

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ui")

DATA_PATH = os.path.join(project_root, "data", "extracted.json")

agent = GradeAdvisorAgent()

# Single source of truth for the ranking table schema (prevents empty-state mismatches)
RANKING_COLUMNS = ["Rank", "Grade Name", "Cosine Distance", "Family", "Peak Hardness", "Cobalt %"]


def empty_ranking_df() -> pd.DataFrame:
    return pd.DataFrame(columns=RANKING_COLUMNS)


def load_catalog_df() -> pd.DataFrame:
    """Loads verified Erasteel catalog into a styled pandas DataFrame."""
    cols = [
        "name", "family", "c_pct", "cr_pct", "mo_pct", "w_pct",
        "v_pct", "co_pct", "hardness_min", "hardness_max", "standards"
    ]
    renamed = {
        "name": "Grade", "family": "Family", "c_pct": "C %", "cr_pct": "Cr %",
        "mo_pct": "Mo %", "w_pct": "W %", "v_pct": "V %", "co_pct": "Co %",
        "hardness_min": "HRC Min", "hardness_max": "HRC Max",
        "standards": "Standards / Spec"
    }
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            return df[cols].rename(columns=renamed)
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
    return pd.DataFrame(columns=[renamed[c] for c in cols])


def render_property_bar(name: str, score: float, color: str = "#0055a4") -> str:
    """Renders an animated property progress bar."""
    pct = min(max(score * 10, 0), 100)
    return f"""
    <div style="margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 600; color: #475569; margin-bottom: 3px;">
            <span>{name}</span>
            <span style="color: {color};">{score:.1f} / 10</span>
        </div>
        <div style="background: #e2e8f0; border-radius: 999px; height: 7px; overflow: hidden; width: 100%;">
            <div style="background: {color}; width: {pct}%; height: 100%; border-radius: 999px; transition: width 0.6s ease;"></div>
        </div>
    </div>
    """


def render_empty_state() -> str:
    return """
    <div style="text-align: center; padding: 48px 24px; color: #94a3b8; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px;">
        <div style="font-size: 2.5rem; margin-bottom: 8px;">⚙️</div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #475569;">Ready for Demonstration</div>
        <div style="font-size: 0.85rem;">Select a showcase scenario on the left or type your own tooling query.</div>
    </div>
    """


def render_error_state(message: str) -> str:
    safe_msg = html.escape(message)
    return f"""
    <div style="background: #fff7ed; border: 1.5px solid #fdba74; border-radius: 12px; padding: 24px; color: #9a3412;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 10px;">
            <span style="font-size: 1.8rem;">⚠️</span>
            <div>
                <h3 style="margin: 0; font-size: 1.2rem; font-weight: 700;">Processing Error</h3>
                <p style="margin: 2px 0 0 0; font-size: 0.85rem;">The query could not be completed. Please try again.</p>
            </div>
        </div>
        <div style="background: #ffffff; border: 1px solid #fed7aa; border-radius: 6px; padding: 10px 14px; font-family: monospace; font-size: 0.85rem; color: #c2410c;">
            {safe_msg}
        </div>
    </div>
    """



def format_html_recommendation(res: dict) -> str:
    """Renders an executive-grade visual card for the recommended grade."""
    matches = res.get("matches", [])
    if not matches:
        conds = res.get("sql_conditions", [])
        cond_str = html.escape(" AND ".join(conds)) if conds else "the specified constraints"
        return f"""
        <div style="background: #fff1f2; border: 1.5px solid #fda4af; border-radius: 12px; padding: 24px; color: #9f1239; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="font-size: 1.8rem;">🚫</span>
                <div>
                    <h3 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: #9f1239;">Zero Matching Catalog Grades</h3>
                    <p style="margin: 2px 0 0 0; font-size: 0.88rem; color: #be123c;">Physical &amp; Chemical Boundary Rejection</p>
                </div>
            </div>
            <p style="font-size: 0.95rem; line-height: 1.5; color: #881337; margin-bottom: 12px;">
                None of the 13 verified Erasteel catalog grades satisfy all specified physical/chemical constraints:
            </p>
            <div style="background: #ffffff; border: 1px solid #fecdd3; border-radius: 6px; padding: 10px 14px; font-family: monospace; font-size: 0.9rem; color: #b91c1c; margin-bottom: 12px;">
                {cond_str}
            </div>
            <div style="background: #ffe4e6; border-left: 4px solid #f43f5e; padding: 10px 14px; border-radius: 0 6px 6px 0; font-size: 0.85rem; color: #9f1239;">
                <strong>Zero-Tolerance Constraint Enforcement:</strong> Unlike naive vector search which hallucinates an invalid recommendation, Grade Advisor strictly rejects queries that violate physical metallurgy boundaries.
            </div>
        </div>
        """

    top = matches[0]
    data = top.get("data", {})
    name = html.escape(str(data.get("name", "Unknown Grade")))
    family = str(data.get("family", "Unknown Family"))
    dist = top.get("distance", 0.0)
    sim_score = max(0, 100 - (dist * 50))  # normalized visual match index

    c = data.get("c_pct", 0.0)
    cr = data.get("cr_pct", 0.0)
    mo = data.get("mo_pct", 0.0)
    w = data.get("w_pct", 0.0)
    v = data.get("v_pct", 0.0)
    co = data.get("co_pct", 0.0)
    h_min = data.get("hardness_min", 0.0)
    h_max = data.get("hardness_max", 0.0)
    standards = html.escape(str(data.get("standards", "Erasteel Proprietary Spec")))

    fam_color = {"Cold work": "#059669", "Specialties": "#7c3aed"}.get(family, "#0055a4")

    # Secondary candidates
    alt_html = ""
    if len(matches) > 1:
        alt_badges = []
        for alt in matches[1:]:
            alt_name = html.escape(str(alt.get("name", "")))
            alt_dist = alt.get("distance", 0.0)
            alt_badges.append(
                f'<span style="background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 10px; font-size: 0.82rem; font-weight: 600; color: #334155;">'
                f'{alt_name} <span style="color: #64748b; font-weight: 400;">(dist: {alt_dist:.3f})</span></span>'
            )
        alt_html = f"""
        <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid #e2e8f0;">
            <div style="font-size: 0.8rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                Secondary Screened Candidates ($in survivors):
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                {' '.join(alt_badges)}
            </div>
        </div>
        """

    # Property bars
    props = [
        ("Machinability", data.get("machinability", 0.0), "#0055a4"),
        ("Wear Resistance", data.get("wear_resistance", 0.0), "#0891b2"),
        ("Toughness", data.get("toughness", 0.0), "#059669"),
        ("Hot Hardness", data.get("hot_hardness", 0.0), "#d97706"),
        ("Grindability", data.get("grindability", 0.0), "#7c3aed"),
    ]
    bars_html = "".join(render_property_bar(n, float(s or 0.0), col) for n, s, col in props)

    description = html.escape(str(data.get("description", ""))).replace("\n", "<br>")
    applications = html.escape(str(data.get("applications", ""))).replace("\n", "<br>")
    heat_treatment = html.escape(str(data.get("heat_treatment", ""))).replace("\n", "<br>")

    def chem_cell(label, val):
        return f"""
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 2px;">
            <div style="font-size: 0.7rem; color: #64748b; font-weight: 600;">{label}</div>
            <div style="font-size: 0.95rem; font-weight: 800; color: #0f172a;">{val}%</div>
        </div>"""

    chem_html = (
        chem_cell("Carbon", c) + chem_cell("Chromium", cr) + chem_cell("Moly", mo)
        + chem_cell("Tungsten", w) + chem_cell("Vanadium", v) + chem_cell("Cobalt", co)
    )

    return f"""
    <div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 14px; padding: 24px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -2px rgba(0,0,0,0.025);">
        <!-- Header Banner -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
            <div>
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px; flex-wrap: wrap;">
                    <h2 style="margin: 0; font-size: 1.7rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">{name}</h2>
                    <span style="background: {fam_color}18; color: {fam_color}; border: 1px solid {fam_color}40; border-radius: 999px; padding: 3px 12px; font-size: 0.78rem; font-weight: 700; text-transform: uppercase;">
                        {html.escape(family)}
                    </span>
                    <span style="background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 999px; padding: 3px 10px; font-size: 0.78rem; font-weight: 600;">
                        {standards}
                    </span>
                </div>
                <div style="font-size: 0.88rem; color: #64748b;">
                    Erasteel Powder Metallurgy (ASP®) Technical Datasheet Reference
                </div>
            </div>
            <div style="text-align: right; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 12px;">
                <div style="font-size: 0.7rem; text-transform: uppercase; color: #64748b; font-weight: 700;">Vector Proximity</div>
                <div style="font-size: 1.1rem; font-weight: 800; color: #0055a4;">{sim_score:.0f}% <span style="font-size: 0.75rem; color: #64748b; font-weight: 400;">(d={dist:.3f})</span></div>
            </div>
        </div>

        <!-- Chemistry & Hardness -->
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
                <span style="font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.05em;">Nominal Chemical Composition (wt. %)</span>
                <span style="font-size: 0.78rem; font-weight: 700; background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 6px;">
                    Hardness: {h_min:.0f} – {h_max:.0f} HRC (Peak: {h_max:.0f} HRC)
                </span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; text-align: center;">
                {chem_html}
            </div>
        </div>

        <!-- Engineering Property Ratings -->
        <div style="margin-bottom: 18px;">
            <div style="font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                Engineering Property Ratings
            </div>
            {bars_html}
        </div>

        <!-- Metallurgical Detail -->
        <div style="font-size: 0.88rem; line-height: 1.6; color: #334155;">
            <div style="margin-bottom: 10px;"><strong style="color: #0f172a;">Metallurgical Rationale:</strong><br>{description}</div>
            <div style="margin-bottom: 10px;"><strong style="color: #0f172a;">Recommended Applications:</strong><br>{applications}</div>
            <div><strong style="color: #0f172a;">Heat Treatment:</strong><br>{heat_treatment}</div>
        </div>
        {alt_html}
    </div>
    """



# --------------------------------------------------------------------------- #
# Query Pipeline
# --------------------------------------------------------------------------- #
def process_query(user_query: str):
    """Runs the agent and renders all white-box outputs. Never raises."""
    if not user_query or not user_query.strip():
        return (
            render_empty_state(),
            "-- Awaiting query submission...",
            "N/A",
            empty_ranking_df(),
            "{}"
        )

    try:
        res = agent.run(user_query.strip())
    except Exception as e:
        logger.exception("Agent run failed")
        return (
            render_error_state(str(e)),
            "-- Error: query did not execute --",
            "N/A",
            empty_ranking_df(),
            "{}"
        )

    # 1. HTML Recommendation Card
    card_html = format_html_recommendation(res)

    # 2. SQL Details
    sql_clauses = res.get("sql_conditions", [])
    sql_text = "-- Step 1: DuckDB Relational Gatekeeper Execution\n"
    if sql_clauses:
        sql_text += "SELECT name, family, c_pct, cr_pct, mo_pct, w_pct, v_pct, co_pct, hardness_min, hardness_max\nFROM steel_grades\n"
        sql_text += "\n".join([f"  AND {c}" if i > 0 else f"WHERE {c}" for i, c in enumerate(sql_clauses)])
    else:
        sql_text += "SELECT * FROM steel_grades -- (No strict numeric inequality extracted)"

    matched_names = res.get("sql_matched_names", [])
    sql_text += f"\n\n-- Surviving Candidate Pool ({len(matched_names)} grades passed hard bounds):\n"
    sql_text += f"-- {', '.join(matched_names) if matched_names else 'ZERO candidates matched (Constraint Violated)'}"

    # 3. Semantic Query
    sem_text = res.get("semantic_query", "N/A") or "N/A"

    # 4. ChromaDB Ranking Table
    rank_rows = []
    for idx, m in enumerate(res.get("matches", []), 1):
        gdata = m.get("data", {})
        dist = m.get("distance", 0.0)
        rank_rows.append({
            "Rank": f"#{idx}",
            "Grade Name": m.get("name", "N/A"),
            "Cosine Distance": f"{dist:.4f}",
            "Family": gdata.get("family", "N/A"),
            "Peak Hardness": f"{gdata.get('hardness_max', 0.0):.0f} HRC",
            "Cobalt %": f"{gdata.get('co_pct', 0.0)}%"
        })
    rank_df = pd.DataFrame(rank_rows, columns=RANKING_COLUMNS) if rank_rows else empty_ranking_df()

    # 5. Raw JSON Payload
    raw_json_str = json.dumps([m.get("data", {}) for m in res.get("matches", [])], indent=2, ensure_ascii=False)

    return card_html, sql_text, sem_text, rank_df, raw_json_str


def reset_outputs():
    return (
        render_empty_state(),
        "-- Awaiting query submission...",
        "N/A",
        empty_ranking_df(),
        "{}"
    )



# --------------------------------------------------------------------------- #
# Custom CSS (must live in gr.Blocks(css=...), NOT in launch())
# --------------------------------------------------------------------------- #
custom_css = """
body, .gradio-container {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
}
.header-container {
    background: linear-gradient(135deg, #0b1f3a 0%, #0055a4 100%);
    border-radius: 12px;
    padding: 24px 30px;
    color: #ffffff;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.header-title {
    font-size: 2rem;
    font-weight: 800;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    letter-spacing: -0.02em;
}
.header-subtitle {
    font-size: 0.95rem;
    color: #cbd5e1;
    margin-top: 6px;
    margin-bottom: 12px;
}
.badge-bar {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}
.badge-pill {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #e2e8f0;
}
.demo-btn-row button {
    font-size: 0.85rem !important;
    padding: 6px 12px !important;
    width: 100%;
    text-align: left !important;
    transition: transform 0.1s ease, box-shadow 0.2s ease;
}
.demo-btn-row button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px -2px rgba(0, 85, 164, 0.3);
}
.footer-note {
    text-align: center;
    font-size: 0.8rem;
    color: #94a3b8;
    padding: 18px 0 6px 0;
    border-top: 1px solid #e2e8f0;
    margin-top: 24px;
}
"""

# Consistent Gradio theme aligned with the Erasteel blue brand
theme = gr.themes.Soft(
    primary_hue=gr.themes.colors.blue,
    neutral_hue=gr.themes.colors.slate,
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
)



# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #
# Gradio 6+ moved `theme` and `css` from the Blocks constructor to launch().
_GRADIO_MAJOR = int(gr.__version__.split(".")[0])
_BLOCKS_KWARGS = {"title": "Grade Advisor: Dual-Stage Hybrid RAG"}
if _GRADIO_MAJOR < 6:
    _BLOCKS_KWARGS.update({"theme": theme, "css": custom_css})

with gr.Blocks(**_BLOCKS_KWARGS) as demo:
    # Top Executive Banner
    gr.HTML(
        """
        <div class="header-container">
            <div class="header-title">
                <span>⚡</span> Grade Advisor: Hybrid RAG for HSS Grade Selection
            </div>
            <div class="header-subtitle">
                Two-Stage Metallurgical Decision Engine: Deterministic SQL Filtering (DuckDB) + Dense Vector Semantic Ranking (ChromaDB)
            </div>
            <div class="badge-bar">
                <span class="badge-pill">🛡️ Zero Hallucination Guarantee</span>
                <span class="badge-pill">🗄️ DuckDB SQL Gatekeeper</span>
                <span class="badge-pill">🎯 ChromaDB Pre-Filter ($in)</span>
                <span class="badge-pill">🔬 13 Authentic Erasteel Grades</span>
                <span class="badge-pill">🧪 100% Benchmark Accuracy</span>
            </div>
        </div>
        """
    )

    # Main Workbench Grid
    with gr.Row():
        # Left Control Panel (Query & Showcase Scenarios)
        with gr.Column(scale=5):
            gr.Markdown("### 🔍 Query & Engineering Requirements")
            query_input = gr.Textbox(
                label="Enter Tooling Intent or Specific Metallurgical Constraints",
                placeholder="e.g. Cold work tooling, max toughness, HRC around 60, zero cobalt.",
                lines=3
            )
            with gr.Row():
                submit_btn = gr.Button("⚡ Run Dual-Stage Selection", variant="primary", scale=2)
                clear_btn = gr.Button("Clear", scale=1)

            with gr.Accordion("🎬 Showcase Demo Scenarios (Click to Run)", open=True):
                gr.Markdown("*Pre-configured queries demonstrating specific architectural capabilities:*")
                with gr.Column(elem_classes="demo-btn-row"):
                    scenario_a = gr.Button("🔴 Scenario 1: Cold Work Shock Punch (Zero Cobalt, Toughness)", size="sm")
                    scenario_b = gr.Button("🔵 Scenario 2: Dry High-Speed Gear Skiving (29% Co, Hot Hardness)", size="sm")
                    scenario_c = gr.Button("🟢 Scenario 3: Corrosive Plastic Tooling (Stainless PM APZ10)", size="sm")
                    scenario_d = gr.Button("🟣 Scenario 4: Threading Machine Taps (Grindability & Toughness)", size="sm")
                    scenario_e = gr.Button("⚠️ Scenario 5: Boundary Failure Stress Test (>35% Co, >75 HRC)", size="sm")

        # Right Output Panel (Rich Presentation Card)
        with gr.Column(scale=6):
            gr.Markdown("### 📋 Primary Recommendation & Physical Profile")
            rec_html_output = gr.HTML(value=render_empty_state())

    gr.Markdown("---")


    # Lower Section: White-Box Inspection Audit Trail
    gr.Markdown("### 🔬 White-Box Retrieval Internals (Audit Trail)")
    gr.Markdown("*Proves this is an engineering-grade hybrid retrieval system, not a black-box chatbot wrapper.*")

    with gr.Tabs():
        with gr.TabItem("🗂️ Step 1: DuckDB SQL Gatekeeper"):
            sql_output = gr.Code(
                label="Executed SQL Query & Surviving Candidate Pool",
                language="sql",
                lines=7
            )
        with gr.TabItem("🎯 Step 2: ChromaDB Dense Vector Ranking"):
            with gr.Row():
                with gr.Column(scale=2):
                    semantic_output = gr.Textbox(
                        label="Extracted Semantic Search Vector String",
                        lines=2
                    )
                with gr.Column(scale=3):
                    ranking_output = gr.Dataframe(
                        label="ChromaDB Ranked Candidates ($in metadata filter applied)",
                        headers=RANKING_COLUMNS
                    )
        with gr.TabItem("📦 Step 3: Raw Database JSON Payloads"):
            json_output = gr.Code(
                label="Ground-Truth Datasheet Specifications Retrieved from Disk",
                language="json",
                lines=12
            )
        with gr.TabItem("📚 Erasteel Catalog Explorer (13 Verified Grades)"):
            gr.Dataframe(
                value=load_catalog_df(),
                label="Full Ingested Erasteel Datasheet Catalog",
                interactive=False
            )

    gr.HTML(
        """
        <div class="footer-note">
            Grade Advisor · Hybrid RAG (DuckDB + ChromaDB + Gemini) · Built on authentic Erasteel ASP® technical datasheets ·
            Always verify against official Erasteel datasheets before production tooling decisions.
        </div>
        """
    )


    # ------------------------------------------------------------------ #
    # Event Wiring
    # ------------------------------------------------------------------ #
    submit_btn.click(
        fn=process_query,
        inputs=[query_input],
        outputs=[rec_html_output, sql_output, semantic_output, ranking_output, json_output]
    )
    query_input.submit(
        fn=process_query,
        inputs=[query_input],
        outputs=[rec_html_output, sql_output, semantic_output, ranking_output, json_output]
    )
    clear_btn.click(
        fn=reset_outputs,
        inputs=None,
        outputs=[rec_html_output, sql_output, semantic_output, ranking_output, json_output]
    ).then(fn=lambda: "", outputs=[query_input])

    def set_and_run(query: str):
        card, sql, sem, rank, jsn = process_query(query)
        return query, card, sql, sem, rank, jsn

    ALL_OUTPUTS = [query_input, rec_html_output, sql_output, semantic_output, ranking_output, json_output]
    for btn, query in [
        (scenario_a, "Cold work tooling, max toughness, HRC around 60, zero cobalt."),
        (scenario_b, "Dry high-speed gear skiving requiring extreme hot hardness and ultra-high cobalt (>20% cobalt)."),
        (scenario_c, "Plastic injection molds in corrosive environment, stainless high chromium PM tool steel."),
        (scenario_d, "Dedicated steel for manufacturing machine taps, balanced grindability and toughness."),
        (scenario_e, "Impossible constraint: tool steel with > 35% cobalt and hardness > 75 HRC."),
    ]:
        btn.click(fn=lambda q=query: set_and_run(q), outputs=ALL_OUTPUTS)


if __name__ == "__main__":
    demo.queue(max_size=20, default_concurrency_limit=1)
    launch_kwargs = {
        "server_name": "127.0.0.1",
        "server_port": 7860,
        "share": False,
        "show_error": True,
    }
    if _GRADIO_MAJOR >= 6:
        # Gradio 6+: theme & css are passed at launch time
        launch_kwargs.update({"theme": theme, "css": custom_css})
    demo.launch(**launch_kwargs)

