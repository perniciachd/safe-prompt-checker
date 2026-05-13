import os
import sys
import json
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
from _lib.llm_service import rewrite_prompt
from _lib.rewriter_prompts import CRAFT_REWRITER_V1_0


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length else b""

        try:
            data = json.loads(raw_body) if raw_body else None
        except json.JSONDecodeError:
            return self._send_json({"error": "Invalid JSON in request body"}, 400)

        if not data or "prompt" not in data:
            return self._send_json({"error": "Missing 'prompt' field in request body"}, 400)

        if "detection_result" not in data:
            return self._send_json({"error": "Missing 'detection_result' field in request body"}, 400)

        user_prompt = data["prompt"].strip()
        if not user_prompt:
            return self._send_json({"error": "Prompt is empty"}, 400)

        if len(user_prompt) > 10000:
            return self._send_json({"error": "Prompt exceeds maximum length of 10000 characters"}, 400)

        detection_result = data["detection_result"]
        if not isinstance(detection_result, dict):
            return self._send_json({"error": "detection_result must be an object"}, 400)

        if detection_result.get("total_items_flagged", 0) == 0 and not detection_result.get("combinatorial_notes"):
            return self._send_json(
                {"error": "Detection result has nothing to sanitise. Use the original prompt as-is."},
                400,
            )

        result = rewrite_prompt(user_prompt, detection_result, CRAFT_REWRITER_V1_0)
        status = 500 if "error" in result else 200
        return self._send_json(result, status)

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
