import os
import sys
import json
import time
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
import structlog
from _lib.llm_service import analyse_prompt
from _lib.logging_config import init_request_logging
from _lib.prompts import DETECTION_PROMPT_V1_2


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        started_at = time.monotonic()
        request_id = init_request_logging("analyse")
        log = structlog.get_logger()
        log.info(
            "request.received",
            method="POST",
            path=self.path,
            content_length=int(self.headers.get("Content-Length", 0)),
        )

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length else b""

        try:
            data = json.loads(raw_body) if raw_body else None
        except json.JSONDecodeError:
            return self._send_json({"error": "Invalid JSON in request body"}, 400, request_id, started_at)

        if not data or "prompt" not in data:
            return self._send_json({"error": "Missing 'prompt' field in request body"}, 400, request_id, started_at)

        user_prompt = data["prompt"].strip()
        if not user_prompt:
            return self._send_json({"error": "Prompt is empty"}, 400, request_id, started_at)

        if len(user_prompt) > 10000:
            return self._send_json({"error": "Prompt exceeds maximum length of 10000 characters"}, 400, request_id, started_at)

        result = analyse_prompt(user_prompt, DETECTION_PROMPT_V1_2)
        status = 500 if "error" in result else 200
        return self._send_json(result, status, request_id, started_at)

    def _send_json(self, payload: dict, status: int = 200, request_id: str = "", started_at: float = None):
        if started_at is not None:
            elapsed_ms = round((time.monotonic() - started_at) * 1000, 2)
            structlog.get_logger().info(
                "request.completed",
                status_code=status,
                elapsed_ms=elapsed_ms,
            )

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if request_id:
            self.send_header("X-Request-ID", request_id)
        self.end_headers()
        self.wfile.write(body)