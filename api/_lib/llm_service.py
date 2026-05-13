"""
Model-agnostic LLM service.
Switch providers by changing LLM_PROVIDER env var.
"""

import os
import json
from openai import OpenAI

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

_client = None


def _get_client():
    global _client
    if _client is None and LLM_PROVIDER == "openai":
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
    if LLM_PROVIDER == "openai":
        json_instruction = (
            "\n\nIMPORTANT: Respond ONLY with a valid JSON object. "
            "Do not include any text before or after the JSON. "
            "Do not wrap the JSON in markdown code fences. "
            "Do not include any explanation or commentary outside the JSON structure."
        )

        response = _get_client().chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt + json_instruction},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def _extract_json(raw_response: str) -> dict:
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
    raw_response = call_llm(detection_system_prompt, user_prompt)

    try:
        return _extract_json(raw_response)
    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse LLM response as JSON",
            "raw_response": raw_response,
            "details": str(e),
        }
    except Exception as e:
        return {
            "error": "Unexpected error processing LLM response",
            "details": str(e),
        }


def rewrite_prompt(
    original_prompt: str,
    detection_result: dict,
    rewriter_system_prompt: str,
) -> dict:
    user_payload = json.dumps(
        {
            "original_prompt": original_prompt,
            "detection_result": detection_result,
        },
        ensure_ascii=False,
    )

    raw_response = call_llm(
        rewriter_system_prompt,
        user_payload,
        max_tokens=3072,
    )

    try:
        return _extract_json(raw_response)
    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse rewriter response as JSON",
            "raw_response": raw_response,
            "details": str(e),
        }
    except Exception as e:
        return {
            "error": "Unexpected error processing rewriter response",
            "details": str(e),
        }
