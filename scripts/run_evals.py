"""
Run eval cases through the SAFE detection pipeline and report metrics.

Usage:
    cd /Users/manan/Desktop/PerniciaAI/TrainingTopics/ResponsibleAI/tool
    python scripts/run_evals.py

Metrics computed:
- Category recall: fraction of expected_categories that the detector flagged
- Risk score gap: abs(detected_risk_score - expected_risk_score)

Scaffold scope: 3 cases, 2 metrics, no CI integration.
Expansion to 20+ cases and additional metrics is later sprint work.
"""

import os
import sys
from pathlib import Path

# Load .env.local for OPENAI_API_KEY when running outside vercel's runtime.
# Vercel auto-loads .env.local; bare `python3` does not.
_env_file = Path(__file__).parent.parent / ".env.local"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if "=" in _line and not _line.startswith("#"):
            _key, _, _value = _line.partition("=")
            os.environ.setdefault(_key.strip(), _value.strip().strip('"').strip("'"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from _lib.llm_service import analyse_prompt
from _lib.prompts import DETECTION_PROMPT_V1_2

# Import after sys.path setup
sys.path.insert(0, os.path.dirname(__file__))
from eval_cases import EVAL_CASES


def category_recall(expected: set, detected: set) -> float:
    """Fraction of expected categories that appeared in detected categories."""
    if not expected:
        return 1.0  # vacuous case
    return len(expected & detected) / len(expected)


def risk_score_gap(expected: int, detected: int) -> int:
    """Absolute difference between expected and detected risk scores."""
    return abs(expected - detected)


def run_one_case(case: dict) -> dict:
    """Run a single eval case and return a result dict."""
    result = analyse_prompt(case["prompt"], DETECTION_PROMPT_V1_2)

    if "error" in result:
        return {
            "id": case["id"],
            "name": case["name"],
            "error": result["error"],
            "category_recall": None,
            "risk_score_gap": None,
        }

    detected_categories = {item["category"] for item in result.get("items", [])}
    detected_risk_score = result.get("overall_risk_score", 0)

    return {
        "id": case["id"],
        "name": case["name"],
        "expected_categories": case["expected_categories"],
        "detected_categories": detected_categories,
        "expected_risk_score": case["expected_risk_score"],
        "detected_risk_score": detected_risk_score,
        "category_recall": category_recall(
            case["expected_categories"], detected_categories
        ),
        "risk_score_gap": risk_score_gap(
            case["expected_risk_score"], detected_risk_score
        ),
        "items_flagged": len(result.get("items", [])),
    }


def print_results(results: list) -> None:
    """Print a simple results table to stdout."""
    print()
    print("=" * 78)
    print("SAFE Eval Scaffold — Results")
    print(f"Model: gpt-4.1-mini | Prompt version: DETECTION_PROMPT_V1_2")
    print("=" * 78)
    print()

    for r in results:
        print(f"[{r['id']}] {r['name']}")
        if "error" in r:
            print(f"  ERROR: {r['error']}")
            print()
            continue

        print(f"  Expected categories: {sorted(r['expected_categories'])}")
        print(f"  Detected categories: {sorted(r['detected_categories'])}")
        print(f"  Category recall:     {r['category_recall']:.2f}")
        print(f"  Expected risk:       {r['expected_risk_score']}")
        print(f"  Detected risk:       {r['detected_risk_score']}")
        print(f"  Risk score gap:      {r['risk_score_gap']}")
        print(f"  Items flagged:       {r['items_flagged']}")
        print()

    valid = [r for r in results if "error" not in r]
    if valid:
        avg_recall = sum(r["category_recall"] for r in valid) / len(valid)
        avg_gap = sum(r["risk_score_gap"] for r in valid) / len(valid)
        print("-" * 78)
        print(f"Summary ({len(valid)}/{len(results)} cases ran successfully):")
        print(f"  Mean category recall: {avg_recall:.2f}")
        print(f"  Mean risk score gap:  {avg_gap:.2f}")
        print("=" * 78)


def main():
    print(f"Running {len(EVAL_CASES)} eval case(s)...")
    results = []
    for case in EVAL_CASES:
        print(f"  Running {case['id']}...")
        result = run_one_case(case)
        results.append(result)

    print_results(results)


if __name__ == "__main__":
    main()