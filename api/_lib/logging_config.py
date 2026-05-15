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

WHY WE ALSO CONFIGURE STDLIB LOGGING:
    Third-party libraries (tenacity, openai SDK, httpx, urllib3) use
    Python's stdlib logging module — they don't know structlog exists.
    Without configuration, their logs would come out as plain text
    without our request_id context, breaking log consistency.

    We route stdlib logging through structlog so that ALL log output —
    ours and the libraries' — produces the same JSON format with the
    same context fields. One unified log stream.

    The mechanism: structlog's stdlib.ProcessorFormatter is installed
    as the formatter on the root stdlib logger. Anything written via
    stdlib logging.getLogger(...).info(...) gets passed through the
    same processor chain as our structlog calls.
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


def _configure_logging() -> None:
    """One-time logging configuration. Idempotent.

    Configures BOTH structlog and stdlib logging so they share a single
    processor chain and output as JSON to stdout.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    # Processors that run for BOTH structlog calls and stdlib logging calls.
    # The order matters — each processor receives the output of the previous.
    shared_processors: list[Any] = [
        # Auto-include any contextvars bound for this request (request_id, etc.)
        structlog.contextvars.merge_contextvars,
        # Add the log level (info/warning/error) as a field
        structlog.processors.add_log_level,
        # Add an ISO 8601 timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    # Configure structlog itself.
    # Last processor (`ProcessorFormatter.wrap_for_formatter`) hands the
    # event off to the stdlib root handler's formatter, which finishes
    # the chain by rendering as JSON. This is what unifies both paths.
    structlog.configure(
        processors=shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use a structlog-aware formatter.
    # The `foreign_pre_chain` runs the same shared_processors against
    # logs that arrive via stdlib (e.g. tenacity, openai SDK) so they
    # get request_id, timestamp, and level just like our own logs.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # Replace any existing handlers to ensure clean state (idempotency).
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    _CONFIGURED = True


def init_request_logging(endpoint: str, **extra_context: Any) -> str:
    """
    Initialize logging context for a single request.

    Call this once at the start of every request handler. It:
    1. Ensures logging is configured (idempotent).
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
    _configure_logging()
    # Defensive: clear any context bound by a previous invocation of this
    # process. Important because Vercel may reuse warm processes.
    clear_contextvars()

    request_id = str(uuid.uuid4())
    bind_contextvars(request_id=request_id, endpoint=endpoint, **extra_context)
    return request_id