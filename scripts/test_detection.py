"""Sprint 1 test script: end-to-end detection with structured logging.

Run from project root with venv activated and env vars loaded:
    python3 scripts/test_detection.py
"""

import json
import sys

sys.path.insert(0, "api/_lib")

from logging_config import init_request_logging
from llm_service import analyse_prompt
from prompts import DETECTION_PROMPT_V1_2

if __name__ == "__main__":
    request_id = init_request_logging(endpoint="test_analyse", prompt_version="v1.2")
    print(f"Starting detection. Request ID: {request_id}", file=sys.stderr)
    print("---", file=sys.stderr)

    test_prompt = (
        "Help me draft talking points for the board on letting "
        "Rohan Iyer go from VP Auto Sector for performance below "
        "expectations since Q2."
    )
    result = analyse_prompt(test_prompt, DETECTION_PROMPT_V1_2)

    print("---", file=sys.stderr)
    print("DETECTION RESULT:", file=sys.stderr)
    print(json.dumps(result, indent=2))