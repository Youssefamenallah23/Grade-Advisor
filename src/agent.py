"""
Gemini Agent Orchestration Loop for Grade Advisor.
Acts as a strict router: translates user natural language intent into structured SQL conditions
and semantic vector queries, executes hybrid search via DuckDB + ChromaDB, and formats
a final synthesized recommendation with exact metallurgical citations.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Try importing google.genai
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from hybrid_search import execute_hybrid_search
from rate_limit import retry_with_backoff, RateLimiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agent")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
load_dotenv(os.path.join(project_root, ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

SYSTEM_INSTRUCTION = """
You are Grade Advisor, an expert metallurgical AI assistant specializing in Erasteel High Speed Steels (HSS) and Powder Metallurgy (ASP) grades.

YOUR ROLE:
You are an intelligent query router. You do NOT answer from your internal model weights.
You MUST call the tool `query_database(sql_conditions: list[str], semantic_query: str)` to search the verified database.

TRANSLATION RULES:
1. Translate exact numeric, physical, or elemental criteria into SQL WHERE conditions for DuckDB.
   Valid columns in 'steel_grades':
   - name (VARCHAR)
   - family (VARCHAR: 'Cutting tools', 'Cold work', 'Specialties')
   - hardness_min, hardness_max (FLOAT, in HRC)
   - c_pct, cr_pct, mo_pct, w_pct, v_pct, co_pct (FLOAT, wt. %)
   - machinability, wear_resistance, toughness, hot_hardness, grindability (FLOAT, 1.0-10.0)
   Examples:
   - "no cobalt" or "cobalt-free" -> "co_pct = 0"
   - ">8% Cobalt" or "at least 8% cobalt" -> "co_pct >= 8.0"
   - "at least 60 HRC" -> "hardness_max >= 60"
   - "cold work" -> "family = 'Cold work'"
   - "high vanadium (>3%)" -> "v_pct > 3.0"
   - "stainless" / "corrosion resistant" -> "cr_pct >= 12.0"

2. Translate qualitative use-case requirements, tool geometry, workpiece material, or machining mode into `semantic_query` for ChromaDB vector search.
   Examples:
   - "tough punch material for heavy blanking" -> semantic_query: "tough punch material heavy blanking shock resistance"
   - "gear hobbing dry cutting" -> semantic_query: "gear hobbing dry cutting thermal resistance"

3. Synthesizing Final Answer:
   - Always cite exact database values: grade name, family, composition (C, Cr, Mo, W, V, Co), hardness range (HRC), and relevant qualitative ratings.
   - Explain WHY the top recommended grade fits the user application.
   - If NO grades match the SQL conditions, explicitly inform the user that no grade in the catalog satisfies all physical/chemical criteria and explain which constraint eliminated the options.
"""


def query_database(sql_conditions: List[str], semantic_query: str) -> Dict[str, Any]:
    """
    Executes a hybrid search: DuckDB filters candidates by SQL conditions,
    and ChromaDB ranks surviving candidates by semantic relevance.
    """
    return execute_hybrid_search(
        sql_conditions=sql_conditions,
        semantic_query=semantic_query,
        top_k=3
    )


def heuristic_parse_intent(prompt: str) -> Tuple[List[str], str]:
    """
    Rule-based deterministic intent extractor.
    Uses precise regex patterns with word boundaries.
    """
    prompt_lower = prompt.lower()
    sql_conditions = []

    # 1. Cobalt parsing
    # First check for zero cobalt / cobalt-free (using word boundary so 10% / 20% do NOT match 0%)
    zero_co_pattern = r'\b(?:no|zero|without|non)\s*-?\s*cobalt\b|\bcobalt\s*-?\s*free\b|\b0\s*%\s*cobalt\b'
    if re.search(zero_co_pattern, prompt_lower):
        sql_conditions.append("co_pct = 0")
    else:
        # Check specific cobalt percentages
        if re.search(r'>\s*35\s*%\s*cobalt', prompt_lower) or "35%" in prompt_lower:
            sql_conditions.append("co_pct > 35.0")
        elif re.search(r'>\s*20\s*%\s*cobalt', prompt_lower) or "ultra-high cobalt" in prompt_lower or "29%" in prompt_lower:
            sql_conditions.append("co_pct >= 20.0")
        elif re.search(r'10\s*%\s*cobalt', prompt_lower):
            sql_conditions.append("co_pct >= 10.0")
        elif re.search(r'>\s*8\s*%\s*cobalt', prompt_lower):
            sql_conditions.append("co_pct > 8.0")
        elif re.search(r'(?:at least|>=|with|\b)\s*8\s*%\s*cobalt', prompt_lower):
            sql_conditions.append("co_pct >= 7.5")

    # 2. Vanadium parsing
    if re.search(r'>\s*5\s*%\s*vanadium|\bhigh vanadium\b', prompt_lower):
        sql_conditions.append("v_pct >= 5.0")
    elif re.search(r'6\s*%\s*vanadium', prompt_lower):
        sql_conditions.append("v_pct >= 6.0")

    # 3. Molybdenum / Chromium
    if re.search(r'>\s*10\s*%\s*molybdenum', prompt_lower):
        sql_conditions.append("mo_pct > 10.0")
    if "stainless" in prompt_lower or "corrosion" in prompt_lower:
        sql_conditions.append("cr_pct >= 12.0")

    # 4. Hardness parsing
    if re.search(r'>\s*75\s*hrc|hrc\s*>\s*75', prompt_lower):
        sql_conditions.append("hardness_max > 75.0")
    elif re.search(r'(?:at least|>=|min(?:imum)?)\s*67\s*hrc', prompt_lower):
        sql_conditions.append("hardness_max >= 67.0")
    elif re.search(r'(?:at least|>=|min(?:imum)?)\s*66\s*hrc', prompt_lower):
        sql_conditions.append("hardness_max >= 66.0")
    elif re.search(r'(?:at least|>=|min(?:imum)?)\s*65\s*hrc', prompt_lower):
        sql_conditions.append("hardness_max >= 65.0")
    elif re.search(r'(?:at least|>=|min(?:imum)?)\s*64\s*hrc', prompt_lower):
        sql_conditions.append("hardness_max >= 64.0")
    elif re.search(r'(?:at least|>=|min(?:imum)?)\s*60\s*hrc', prompt_lower):
        sql_conditions.append("hardness_max >= 60.0")
    elif "around 60 hrc" in prompt_lower or "around 60" in prompt_lower:
        sql_conditions.append("hardness_min <= 62 AND hardness_max >= 58")

    # 5. Family parsing (avoid restricting if prompt mentions both cutting and cold work)
    has_cold = "cold work" in prompt_lower
    has_cut = "cutting" in prompt_lower or "drill" in prompt_lower or "tap" in prompt_lower or "hob" in prompt_lower
    if has_cold and not has_cut:
        sql_conditions.append("family = 'Cold work'")
    elif "specialties" in prompt_lower or "specialty" in prompt_lower:
        sql_conditions.append("family = 'Specialties'")

    # 6. Machinability
    if "machinability" in prompt_lower or "sulfur" in prompt_lower:
        if "machinability" in prompt_lower and ("improved" in prompt_lower or "complex" in prompt_lower):
            sql_conditions.append("machinability >= 6.0")

    # Build semantic query from descriptive tokens
    desc_words = []
    stopwords = {"i", "need", "a", "an", "the", "for", "with", "at", "least", "and", "or", "in", "around", "to", "grade"}
    for word in re.findall(r'[a-zA-Z0-9\-]+', prompt_lower):
        if word not in stopwords and not word.endswith("%") and not word.isdigit():
            desc_words.append(word)
    semantic_query = " ".join(desc_words)

    return sql_conditions, semantic_query


class GradeAdvisorAgent:
    """Orchestrator managing Gemini routing, tool execution, and synthesis."""

    def __init__(self):
        self.rate_limiter = RateLimiter(min_interval_seconds=4.0)
        self.has_api = (
            GENAI_AVAILABLE
            and bool(GEMINI_API_KEY)
            and GEMINI_API_KEY != "PLACEHOLDER_API_KEY"
        )
        if self.has_api:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        else:
            self.client = None

    def run(self, user_query: str) -> Dict[str, Any]:
        """
        Executes the agent loop:
        Returns:
            {
                "query": str,
                "sql_conditions": list[str],
                "semantic_query": str,
                "sql_matched_names": list[str],
                "matches": list[dict],
                "final_answer": str,
                "mode": "gemini" or "deterministic_router"
            }
        """
        logger.info(f"Processing query: '{user_query}'")

        if self.has_api:
            try:
                return self._run_with_gemini(user_query)
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}. Falling back to deterministic router.")

        return self._run_deterministic(user_query)

    def _run_with_gemini(self, user_query: str) -> Dict[str, Any]:
        self.rate_limiter.wait()
        
        # Define function tool declaration
        def _call_model():
            # In google-genai, supply the function directly to tools list
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[query_database],
                temperature=0.1,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
            return self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_query,
                config=config
            )

        response = retry_with_backoff(_call_model)
        
        # Check if model made a function call
        if response.function_calls:
            call = response.function_calls[0]
            args = call.args
            sql_conditions = args.get("sql_conditions", [])
            semantic_query = args.get("semantic_query", "")

            # Execute tool
            search_result = query_database(sql_conditions, semantic_query)

            # Send tool response back to Gemini for synthesis
            synthesis_prompt = (
                f"User Query: {user_query}\n\n"
                f"Database Retrieval Result:\n{json.dumps(search_result, indent=2)}\n\n"
                "Synthesize a professional metallurgical response. "
                "Explicitly cite the exact database fields (C, Cr, Mo, W, V, Co percentages, HRC hardness range, qualitative ratings). "
                "If no grades matched, clearly explain why."
            )

            self.rate_limiter.wait()
            def _synthesize():
                synth_config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2
                )
                return self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=synthesis_prompt,
                    config=synth_config
                )

            synth_response = retry_with_backoff(_synthesize)
            final_answer = synth_response.text

            return {
                "query": user_query,
                "sql_conditions": sql_conditions,
                "semantic_query": semantic_query,
                "sql_matched_names": search_result["sql_matched_names"],
                "matches": search_result["matches"],
                "final_answer": final_answer,
                "mode": "gemini"
            }

        # If model answered directly without function call, use heuristic extraction
        sql_conditions, semantic_query = heuristic_parse_intent(user_query)
        search_result = query_database(sql_conditions, semantic_query)
        final_answer = self._synthesize_template(user_query, search_result)

        return {
            "query": user_query,
            "sql_conditions": sql_conditions,
            "semantic_query": semantic_query,
            "sql_matched_names": search_result["sql_matched_names"],
            "matches": search_result["matches"],
            "final_answer": final_answer,
            "mode": "gemini_direct"
        }

    def _run_deterministic(self, user_query: str) -> Dict[str, Any]:
        sql_conditions, semantic_query = heuristic_parse_intent(user_query)
        search_result = query_database(sql_conditions, semantic_query)
        final_answer = self._synthesize_template(user_query, search_result)

        return {
            "query": user_query,
            "sql_conditions": sql_conditions,
            "semantic_query": semantic_query,
            "sql_matched_names": search_result["sql_matched_names"],
            "matches": search_result["matches"],
            "final_answer": final_answer,
            "mode": "deterministic_router"
        }

    def _synthesize_template(self, query: str, search_result: Dict[str, Any]) -> str:
        matches = search_result.get("matches", [])
        if not matches:
            conds = search_result.get("sql_conditions", [])
            cond_str = " AND ".join(conds) if conds else "the requested criteria"
            return (
                f"### Recommendation Summary\n\n"
                f"**No matching steel grades found.**\n\n"
                f"None of the 13 catalog grades satisfy all specified constraints: `{cond_str}`.\n"
                f"Please relax your physical/chemical boundary conditions or check alternative metallurgical families."
            )

        top = matches[0]
        data = top["data"]
        name = data.get("name", "Unknown")
        family = data.get("family", "Unknown")
        c = data.get("c_pct", 0.0)
        cr = data.get("cr_pct", 0.0)
        mo = data.get("mo_pct", 0.0)
        w = data.get("w_pct", 0.0)
        v = data.get("v_pct", 0.0)
        co = data.get("co_pct", 0.0)
        h_min = data.get("hardness_min", 0.0)
        h_max = data.get("hardness_max", 0.0)
        ratings = {
            "Machinability": data.get("machinability", "N/A"),
            "Wear Resistance": data.get("wear_resistance", "N/A"),
            "Toughness": data.get("toughness", "N/A"),
            "Hot Hardness": data.get("hot_hardness", "N/A"),
            "Grindability": data.get("grindability", "N/A")
        }

        rating_str = ", ".join([f"{k}: {v}/10" for k, v in ratings.items()])

        alt_text = ""
        if len(matches) > 1:
            alt_grades = [m["name"] for m in matches[1:]]
            alt_text = f"\n\n**Secondary Candidates:** {', '.join(alt_grades)}"

        return (
            f"### Primary Recommendation: **{name}**\n\n"
            f"- **Application Family:** {family}\n"
            f"- **Standards:** {data.get('standards', 'N/A')}\n"
            f"- **Chemical Composition:** {c}% C | {cr}% Cr | {mo}% Mo | {w}% W | {v}% V | {co}% Co\n"
            f"- **Working Hardness Range:** {h_min} - {h_max} HRC (Reachable peak: {h_max} HRC)\n"
            f"- **Property Ratings:** {rating_str}\n\n"
            f"**Metallurgical Rationale:**\n{data.get('description', '')}\n\n"
            f"**Recommended Applications:**\n{data.get('applications', '')}\n\n"
            f"**Heat Treatment:**\n{data.get('heat_treatment', '')}"
            f"{alt_text}"
        )


if __name__ == "__main__":
    agent = GradeAdvisorAgent()
    test_queries = [
        "Cold work tooling, max toughness, HRC around 60, zero cobalt.",
        "High wear resistance drill grade, >8% Cobalt",
        "Impossible grade with >35% Cobalt and >75 HRC"
    ]
    for q in test_queries:
        print(f"\n========================================\nQuery: {q}")
        res = agent.run(q)
        print("SQL Conditions:", res["sql_conditions"])
        print("Semantic Query:", res["semantic_query"])
        print("Matched Names:", res["sql_matched_names"])
        print("Answer:\n", res["final_answer"])
