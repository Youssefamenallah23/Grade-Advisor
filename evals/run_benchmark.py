"""
Deterministic Evaluation Benchmark Suite for Grade Advisor.
Executes test cases from data/eval_cases.json.
Enforces:
1. Zero-tolerance constraint check: immediate score=0 if any recommendation violates SQL bounds.
2. Precision@3: checks if human-determined optimal grade is in top 3 results.
Can be executed via pytest or directly as a CLI script.
"""

import os
import sys
import json
import logging
import pytest

# Ensure src is on python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from agent import GradeAdvisorAgent

logging.basicConfig(level=logging.WARNING)

CASES_PATH = os.path.join(project_root, "data", "eval_cases.json")


def load_eval_cases():
    with open(CASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


EVAL_CASES = load_eval_cases()


def evaluate_numeric_rule(val: float, op: str, threshold: float) -> bool:
    """Evaluates strict numeric bounds."""
    eps = 1e-4
    if op == "==":
        return abs(val - threshold) < eps
    elif op == ">":
        return val > (threshold - eps)
    elif op == ">=":
        return val >= (threshold - eps)
    elif op == "<":
        return val < (threshold + eps)
    elif op == "<=":
        return val <= (threshold + eps)
    return False


def run_single_eval(case: dict, agent: GradeAdvisorAgent) -> dict:
    """Runs a single test case and returns structured scoring metrics."""
    query = case["query"]
    result = agent.run(query)
    matches = result.get("matches", [])
    returned_names = [m["name"] for m in matches]
    
    numeric_rules = case.get("numeric_rules", {})
    expected_top_3 = set(case.get("expected_top_3", []))
    allow_no_match = case.get("allow_no_match", False)

    # 1. Zero-tolerance constraint validation
    constraint_pass = True
    constraint_violation = None

    if allow_no_match:
        # If no valid match should exist, any returned candidate is a zero-tolerance failure!
        if len(matches) > 0:
            constraint_pass = False
            constraint_violation = f"Expected 0 matches for impossible query, but got {returned_names}"
    else:
        if len(matches) == 0:
            constraint_pass = False
            constraint_violation = "No candidates returned for valid query"
        else:
            for m in matches:
                data = m.get("data", {})
                for field, (op, threshold) in numeric_rules.items():
                    val = float(data.get(field, 0.0))
                    if not evaluate_numeric_rule(val, op, float(threshold)):
                        constraint_pass = False
                        constraint_violation = (
                            f"Grade {m['name']} violated rule {field} {op} {threshold} (actual={val})"
                        )
                        break
                if not constraint_pass:
                    break

    # 2. Precision@3 evaluation
    precision_at_3 = 0.0
    if allow_no_match:
        precision_at_3 = 1.0 if len(matches) == 0 else 0.0
    else:
        top_3_names = set(returned_names[:3])
        if top_3_names.intersection(expected_top_3):
            precision_at_3 = 1.0
        else:
            precision_at_3 = 0.0

    return {
        "id": case["id"],
        "query": query,
        "returned_names": returned_names,
        "constraint_pass": constraint_pass,
        "constraint_violation": constraint_violation,
        "precision_at_3": precision_at_3,
        "score": precision_at_3 if constraint_pass else 0.0
    }


@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_grade_advisor_case(case):
    agent = GradeAdvisorAgent()
    eval_res = run_single_eval(case, agent)
    
    assert eval_res["constraint_pass"], (
        f"ZERO-TOLERANCE CONSTRAINT FAILURE on {case['id']}: {eval_res['constraint_violation']}"
    )
    assert eval_res["precision_at_3"] == 1.0, (
        f"PRECISION@3 FAILURE on {case['id']}: Expected one of {case['expected_top_3']}, "
        f"got {eval_res['returned_names'][:3]}"
    )


def print_benchmark_summary():
    """Runs all cases and prints a professional benchmark scorecard."""
    agent = GradeAdvisorAgent()
    results = []

    print("\n" + "=" * 90)
    print("GRADE ADVISOR: DETERMINISTIC EVALUATION BENCHMARK SCORECARD")
    print("=" * 90)
    print(f"{'ID':<9} | {'Constraint Check':<18} | {'Precision@3':<12} | {'Top Match':<15} | {'Status'}")
    print("-" * 90)

    for case in EVAL_CASES:
        res = run_single_eval(case, agent)
        results.append(res)
        c_status = "PASS (100%)" if res["constraint_pass"] else "FAIL (0%)"
        p_status = "1.0" if res["precision_at_3"] == 1.0 else "0.0"
        top_name = res["returned_names"][0] if res["returned_names"] else "None (Correct)"
        overall = "SUCCESS" if res["score"] == 1.0 else "FAILED"
        print(f"{res['id']:<9} | {c_status:<18} | {p_status:<12} | {top_name:<15} | {overall}")

    total = len(results)
    passed_constraints = sum(1 for r in results if r["constraint_pass"])
    passed_precision = sum(1 for r in results if r["precision_at_3"] == 1.0)
    total_passed = sum(1 for r in results if r["score"] == 1.0)

    print("-" * 90)
    print(f"Total Cases: {total}")
    print(f"Zero-Tolerance Constraint Pass Rate: {passed_constraints}/{total} ({passed_constraints/total*100:.1f}%)")
    print(f"Precision@3 Retrieval Rate:          {passed_precision}/{total} ({passed_precision/total*100:.1f}%)")
    print(f"Overall Benchmark Accuracy:          {total_passed}/{total} ({total_passed/total*100:.1f}%)")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    print_benchmark_summary()
