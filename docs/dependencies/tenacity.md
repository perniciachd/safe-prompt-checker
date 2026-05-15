# tenacity

**Version:** `9.0.0`
**Added:** Sprint 1, Day 1 (May 2026)
**Used in:** `api/_lib/llm_service.py`

## What problem it solves

LLM API calls fail. Rate limits, timeouts, transient 5xx errors, network blips. Without retry logic, every failure propagates to the user as a 500 error. The tool becomes flaky.

The naive solution is `try/except` with `time.sleep()` and a counter. This works but quickly becomes complex when you need:
- Different behaviour for different error types (retry 429, don't retry 400)
- Exponential backoff with jitter
- Max attempts AND max total duration
- Logging of retry attempts
- Async support

Tenacity gives all of this declaratively, via decorators.

## Why this package vs alternatives

| Option | Pros | Cons | Why not chosen |
|--------|------|------|----------------|
| `tenacity` (chosen) | Battle-tested, declarative API, async support, fine-grained policies, library used by OpenAI/LangChain/many production projects | Slightly more verbose for simple cases | — |
| OpenAI SDK built-in retry | Already in our dependency tree, zero new code | Limited config, only handles OpenAI errors, no logging hooks, can't extend for cross-provider failover later | Locks us in to OpenAI's retry policy; doesn't extend when we add Claude in future sprints |
| Custom `try/except` loop | No dependency, full control | Easy to get wrong (forget jitter, miss specific exception classes, no observability) | Reinventing this badly is a common junior engineer pattern; tenacity exists precisely so we don't |
| `backoff` library | Similar feature set | Smaller community, fewer recent releases | Tenacity is more actively maintained and has better async story |

## How we use it

In `api/_lib/llm_service.py`:

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from openai import APIError, APITimeoutError, RateLimitError

@retry(
    # Retry only on transient errors. Bad requests (400) are our bugs, not retryable.
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError)),
    # Stop after 3 total attempts (initial + 2 retries)
    stop=stop_after_attempt(3),
    # Exponential backoff: 1s, 2s, 4s with jitter
    wait=wait_exponential(multiplier=1, min=1, max=10),
    # Log each retry attempt
    before_sleep=before_sleep_log(log, logging.WARNING),
    # Re-raise the final exception so caller can handle it
    reraise=True,
)
def _call_openai(system_prompt: str, user_prompt: str, request_id: str) -> str:
    # ... actual API call ...
```

## Gotchas and lessons learned

- **`reraise=True` is important.** Default behaviour wraps the final exception in `RetryError`, which is annoying to handle downstream. We want the original exception to bubble up.

- **Don't retry on `openai.BadRequestError` (HTTP 400).** That means your prompt is malformed or violates content policy. Retrying won't help. Tenacity's `retry_if_exception_type` only retries specified types — good default.

- **`wait_exponential` with `multiplier=1, min=1, max=10`** gives the sequence 1s, 2s, 4s (capped at 10s). Tune these based on observed failure patterns once we have production data.

- **Async version exists.** `@retry` works on async functions too. If we move to async in future, no migration needed.

## When to revisit this choice

- If we ever need retry policies that vary per-tenant or per-environment, we'd want a more configurable solution.
- If we move entirely to OpenAI Agents SDK or LangChain's built-in retry, may consolidate.
- If retry logic becomes spread across many functions, we'd extract a single retry policy module rather than decorating each function.

For now, tenacity is the right choice. Don't revisit until a concrete need surfaces.

## Resources

- Official docs: https://tenacity.readthedocs.io/
- Why retry is hard to get right: https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- The "thundering herd" problem (why we need jitter): https://en.wikipedia.org/wiki/Thundering_herd_problem