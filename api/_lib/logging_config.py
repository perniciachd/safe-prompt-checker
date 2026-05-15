"""
Structured logging configuration for the SAFE tool.

USAGE:
    from _lib.logging_config import init_request_logging
    from structlog import get_logger

    # At the start of each request handler:
    request_id = init_request_logging(endpoint="analyse")

    # Anywhere in code (gets request_id automatically):
    log = get_logger()
    log.info("llm.call.started", provider="openai", model="gpt-4.1-mini")

OUTPUT FORMAT:
    JSON lines, one per log event, with these standard fields:
    - timestamp (ISO 8601 UTC)
    - level (info, warning, error)
    - event (the name passed to log.info/warning/error)
    - request_id (auto-injected from context)
    - any extra kwargs passed to the log call

WHY STRUCTURED:
    Lets us filter by request_id, aggregate by event type, ingest into
    CloudWatch/Datadog/Langfuse without custom parsing. See
    docs/dependencies/structlog.md for the full rationale.
"""

import logging
import sys
import uuid
from typing import Any

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

# Module-level flag to ensure structlog is configured exactly once.
# Vercel serverless functions may invoke the handler multiple times
# in the same warm process, so we don't want to reconfigure on every call.
_CONFIGURED = False


def _configure_structlog() -> None:
    """One-time structlog configuration. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    # Set stdlib logging to write to stdout at INFO level.
    # Vercel/CloudWatch capture stdout automatically.
    logging.basicConfig(
        format="%(message)s",  # structlog renders the actual format
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            # Auto-include any contextvars bound for this request (request_id, etc.)
            structlog.contextvars.merge_contextvars,
            # Add the log level (info/warning/error) as a field
            structlog.processors.add_log_level,
            # Add an ISO 8601 timestamp
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Include traceback info when exceptions are logged
            structlog.processors.dict_tracebacks,
            # Render the final log entry as JSON
            structlog.processors.JSONRenderer(),
        ],
        # Filter logs by level. INFO and above will be emitted.
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        # Cache the logger per-name for performance.
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


def init_request_logging(endpoint: str, **extra_context: Any) -> str:
    """
    Initialize logging context for a single request.

    Call this once at the start of every request handler. It:
    1. Ensures structlog is configured (idempotent).
    2. Clears any stale context from a previous request (defensive).
    3. Generates a unique request_id and binds it to the context.
    4. Binds the endpoint name and any extra context provided.

    Returns the generated request_id so the handler can include it
    in the HTTP response headers (useful for support and debugging).

    Args:
        endpoint: Logical name of the endpoint, e.g. "analyse" or "rewrite".
        **extra_context: Any additional fields to bind for this request.

    Returns:
        The generated UUID4 request_id as a string.

    Example:
        request_id = init_request_logging(
            endpoint="analyse",
            prompt_version="v1.2",
        )
        log = structlog.get_logger()
        log.info("request.received")  # Will include request_id and prompt_version
    """
    _configure_structlog()
    # Defensive: clear any context bound by a previous invocation of this
    # process. Important because Vercel may reuse warm processes.
    clear_contextvars()

    request_id = str(uuid.uuid4())
    bind_contextvars(request_id=request_id, endpoint=endpoint, **extra_context)
    return request_id