"""
Model-agnostic LLM service.

Production hardened (Sprint 1):
- Retry on transient errors with exponential backoff (tenacity)
- Structured logging on every call (structlog)
- Preserves existing interface — analyse_prompt and rewrite_prompt return
  the same shape they always did

Switch providers by changing LLM_PROVIDER env var.
Currently only "openai" is supported. Claude support is a future sprint.
"""

import json
import logging
import os
import time

import structlog
from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
    APITimeoutError,
    BadRequestError,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")

# Tenacity's before_sleep_log expects a stdlib logging.Logger (tenacity is
# a generic library that doesn't know about structlog). Because we've
# configured stdlib logging to flow through structlog's processor chain
# (see logging_config.py), this stdlib logger's output ends up as JSON
# with the same request_id context as our own structlog calls.
#
# In other words: this looks like we're using two logging systems, but
# they converge into one output stream.
_tenacity_log = logging.getLogger("safe_tool.tenacity")

_client = None


def _get_client() -> OpenAI:
    """Lazily initialize the OpenAI client. Cached for the process lifetime."""
    global _client
    if _client is None and LLM_PROVIDER == "openai":
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# Retry policy for transient errors.
#
# RETRY ON:
#   - RateLimitError (429): wait and try again
#   - APITimeoutError: network/server slowness, often transient
#   - APIConnectionError: transient network issue
#   - APIError: catch-all for OpenAI server errors (5xx)
#
# DO NOT RETRY ON:
#   - BadRequestError (400): our prompt is malformed; retrying won't fix
#   - AuthenticationError (401): our API key is wrong; retrying won't fix
#   - PermissionDeniedError (403): we don't have access; retrying won't fix
#
# Tenacity's retry_if_exception_type only retries the listed types,
# so all other exceptions (including BadRequestError) propagate immediately.
_RETRYABLE_EXCEPTIONS = (
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIError,  # parent class of many transient errors; placed last
)


@retry(
    retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    # When tenacity is about to sleep before retrying, log a WARNING.
    # The log line will be JSON with request_id because stdlib logging
    # flows through structlog's processor chain (see logging_config.py).
    before_sleep=before_sleep_log(_tenacity_log, logging.WARNING),
    reraise=True,  # Re-raise the original exception, don't wrap in RetryError
)
def _call_openai_with_retry(system_prompt: str, user_prompt: str, max_tokens: int):
    """
    Make a single OpenAI Chat Completion call, with retry on transient failures.

    Separated from call_llm() so retry wraps only the network call,
    not prompt construction or response parsing.
    """
    return _get_client().chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )


def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2048,
) -> str:
    """
    Send a prompt to the configured LLM provider and return the raw response text.

    Adds a JSON-only instruction to the user prompt to coerce structured output.

    Logs:
        - llm.call.started: provider, model, prompt sizes
        - llm.call.completed: latency_ms, tokens_used, finish_reason
        - llm.call.failed: error type and message (does NOT log prompt content)
    """
    log = structlog.get_logger()

    if LLM_PROVIDER != "openai":
        log.error("llm.provider.unsupported", provider=LLM_PROVIDER)
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

    # Append the JSON-only instruction. Existing behavior; preserved.
    json_instruction = (
        "\n\nIMPORTANT: Respond ONLY with a valid JSON object. "
        "Do not include any text before or after the JSON. "
        "Do not wrap the JSON in markdown code fences. "
        "Do not include any explanation or commentary outside the JSON structure."
    )
    full_user_prompt = user_prompt + json_instruction

    log.info(
        "llm.call.started",
        provider=LLM_PROVIDER,
        model=DEFAULT_MODEL,
        system_prompt_chars=len(system_prompt),
        user_prompt_chars=len(full_user_prompt),
        max_tokens=max_tokens,
    )

    start_time = time.perf_counter()
    try:
        response = _call_openai_with_retry(system_prompt, full_user_prompt, max_tokens)
    except BadRequestError as e:
        # 400: our prompt is bad. Not retried; logged and re-raised.
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log.error(
            "llm.call.failed",
            error_type="BadRequestError",
            error_message=str(e),
            latency_ms=latency_ms,
            retryable=False,
        )
        raise
    except _RETRYABLE_EXCEPTIONS as e:
        # Transient error that exhausted retries.
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log.error(
            "llm.call.failed",
            error_type=type(e).__name__,
            error_message=str(e),
            latency_ms=latency_ms,
            retryable=True,
            retries_exhausted=True,
        )
        raise
    except Exception as e:
        # Unexpected error type. Log and re-raise so caller sees it.
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log.error(
            "llm.call.failed",
            error_type=type(e).__name__,
            error_message=str(e),
            latency_ms=latency_ms,
            unexpected=True,
        )
        raise

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    usage = response.usage

    log.info(
        "llm.call.completed",
        latency_ms=latency_ms,
        prompt_tokens=usage.prompt_tokens if usage else None,
        completion_tokens=usage.completion_tokens if usage else None,
        total_tokens=usage.total_tokens if usage else None,
        finish_reason=response.choices[0].finish_reason,
    )

    return response.choices[0].message.content


def _extract_json(raw_response: str) -> dict:
    """
    Extract a JSON object from an LLM response.

    Handles common deviations from the JSON-only instruction:
    - Markdown code fences (```json ... ```)
    - Leading/trailing whitespace or commentary
    - JSON embedded within other text
    """
    cleaned = raw_response.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 1)[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        if "```" in cleaned:
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    if not cleaned.startswith("{"):
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace:last_brace + 1]

    return json.loads(cleaned)


def analyse_prompt(user_prompt: str, detection_system_prompt: str) -> dict:
    """
    Analyse a user prompt using the SAFE detection system prompt.

    Returns the structured detection result as a dict.
    On failure, returns an error dict (preserves existing API contract).
    """
    log = structlog.get_logger()

    try:
        raw_response = call_llm(detection_system_prompt, user_prompt)
    except Exception as e:
        # call_llm has already logged the failure with details.
        return {
            "error": "LLM call failed",
            "details": str(e),
            "error_type": type(e).__name__,
        }

    try:
        result = _extract_json(raw_response)
        log.info("analyse.parse.completed", items_count=len(result.get("items", [])))
        return result
    except json.JSONDecodeError as e:
        log.warning(
            "analyse.parse.failed",
            error_message=str(e),
            raw_response_preview=raw_response[:200],
        )
        return {
            "error": "Failed to parse LLM response as JSON",
            "raw_response": raw_response,
            "details": str(e),
        }
    except Exception as e:
        log.error("analyse.unexpected_error", error_type=type(e).__name__, error_message=str(e))
        return {
            "error": "Unexpected error processing LLM response",
            "details": str(e),
        }


def rewrite_prompt(
    original_prompt: str,
    detection_result: dict,
    rewriter_system_prompt: str,
) -> dict:
    """
    Rewrite a user prompt using the SAFE rewriter system prompt.

    Returns the structured rewriter result as a dict.
    Same error handling pattern as analyse_prompt.
    """
    log = structlog.get_logger()

    user_payload = json.dumps(
        {
            "original_prompt": original_prompt,
            "detection_result": detection_result,
        },
        ensure_ascii=False,
    )

    try:
        raw_response = call_llm(
            rewriter_system_prompt,
            user_payload,
            max_tokens=3072,
        )
    except Exception as e:
        return {
            "error": "LLM call failed",
            "details": str(e),
            "error_type": type(e).__name__,
        }

    try:
        result = _extract_json(raw_response)
        log.info("rewrite.parse.completed")
        return result
    except json.JSONDecodeError as e:
        log.warning(
            "rewrite.parse.failed",
            error_message=str(e),
            raw_response_preview=raw_response[:200],
        )
        return {
            "error": "Failed to parse rewriter response as JSON",
            "raw_response": raw_response,
            "details": str(e),
        }
    except Exception as e:
        log.error("rewrite.unexpected_error", error_type=type(e).__name__, error_message=str(e))
        return {
            "error": "Unexpected error processing rewriter response",
            "details": str(e),
        }