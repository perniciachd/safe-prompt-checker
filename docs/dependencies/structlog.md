# structlog

**Version:** `24.4.0`
**Added:** Sprint 1, Day 1 (May 2026)
**Used in:** `api/_lib/logging_config.py`, `api/_lib/llm_service.py`, `api/analyse.py`

## What problem it solves

In production, we need to debug what happened on a specific request. With `print()` statements or basic `logging.info()`, log lines look like:

```
INFO: Called LLM
INFO: Got response in 1.4s
ERROR: JSON parse failed
```

When a user reports "my detection returned a weird error at 3:47pm", we have no way to correlate which logs belong to their request. Did the LLM call succeed? How long did it take? Which prompt version was used? How many tokens?

Structured logging produces JSON instead:

```json
{"timestamp": "2026-05-15T15:47:23Z", "level": "info", "request_id": "abc123", "event": "llm.call.started", "provider": "openai", "model": "gpt-4.1-mini"}
{"timestamp": "2026-05-15T15:47:24Z", "level": "info", "request_id": "abc123", "event": "llm.call.completed", "latency_ms": 1422, "tokens_used": 847}
{"timestamp": "2026-05-15T15:47:24Z", "level": "error", "request_id": "abc123", "event": "json.parse.failed", "raw_response_preview": "..."}
```

Now we can filter logs by `request_id`, search by `event`, aggregate by `latency_ms`. CloudWatch, Datadog, Langfuse — all of them ingest JSON logs natively. Without this, every analytics tool requires custom parsing.

## Why this package vs alternatives

| Option | Pros | Cons | Why not chosen |
|--------|------|------|----------------|
| `structlog` (chosen) | Designed for structured logging from day one, clean API, context binding, async-safe, popular in Python ecosystem | One more dependency | — |
| Stdlib `logging` with JSON formatter | No new dependency | Verbose to configure, no context binding (every log line repeats request_id manually), hostile to async | We'd write custom wrappers around it that approximate structlog; better to just use structlog |
| `loguru` | Easy API, popular | Less standard for structured logging specifically; opinionated about format | Strong choice but structlog is more "neutral" infrastructure |
| `print()` with `json.dumps()` | Zero dependencies | Manual, easy to forget fields, no context binding, no log levels | Junior pattern; doesn't scale |

## How we use it

**Configuration (one-time, in `api/_lib/logging_config.py`):**

```python
import structlog
import logging

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # auto-include request_id
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    cache_logger_on_first_use=True,
)
```

**Binding request context (at start of each request, in `api/analyse.py`):**

```python
import structlog
from structlog.contextvars import bind_contextvars
import uuid

request_id = str(uuid.uuid4())
bind_contextvars(request_id=request_id)

log = structlog.get_logger()
log.info("request.received", endpoint="analyse", prompt_length=len(user_prompt))
```

**Logging an LLM call (in `llm_service.py`):**

```python
log = structlog.get_logger()
log.info("llm.call.started", provider="openai", model="gpt-4.1-mini")
# ... make the call ...
log.info("llm.call.completed", latency_ms=1422, tokens_used=847, prompt_version="v1.2")
```

The `request_id` automatically appears in every log line for the duration of the request. We don't pass it manually.

## Gotchas and lessons learned

- **`contextvars.merge_contextvars` is essential.** Without it, the request_id you bound at the request handler doesn't propagate to logger calls in helper functions. This was confusing the first time I encountered it.

- **`bind_contextvars` is request-scoped automatically in async, but in sync code (our case with `BaseHTTPRequestHandler`) you should `clear_contextvars()` at the start of each request** to avoid context bleed between requests (unlikely with serverless functions which get fresh process state, but good hygiene).

- **Event names: use dot-separated, past-tense, lowercase.** `llm.call.completed` not `LLM Call Done`. Makes filtering and aggregation work cleanly downstream.

- **Log fields you'll want later:** Even if you don't have a dashboard yet, log `latency_ms`, `tokens_used`, `provider`, `model`, `prompt_version`. Free to add; expensive to backfill.

- **Don't log secrets.** Tempting to dump raw request body when debugging. Don't. Especially for SAFE — the whole point is the input contains sensitive content. We never log the actual user_prompt content.

## When to revisit this choice

- If we adopt OpenTelemetry for tracing (likely in Sprint 6 alongside Langfuse), structlog can emit OTel-compatible logs but we may also want OTel-specific integration.
- If logs become a perf bottleneck (unlikely at our scale), would profile structlog vs alternatives.

For now, structlog is the right call.

## Resources

- Official docs: https://www.structlog.org/
- Why structured logging matters: https://www.honeycomb.io/blog/structured-logs-best-friend-developers
- Stripe's logging philosophy (the canonical reference): https://stripe.com/blog/canonical-log-lines