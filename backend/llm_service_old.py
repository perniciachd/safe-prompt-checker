"""
Model-agnostic LLM service.
Switch providers by changing LLM_PROVIDER in .env.
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

if LLM_PROVIDER == "openai":
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Sends a prompt to the configured LLM and returns the raw response text.
    Provider-agnostic. Switch backends by changing LLM_PROVIDER.
    """
    if LLM_PROVIDER == "openai":
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def analyse_prompt(user_prompt: str, detection_system_prompt: str) -> dict:
    """
    Runs detection on a user prompt. Returns parsed JSON dictionary.
    """
    raw_response = call_llm(detection_system_prompt, user_prompt)
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse LLM response",
            "raw_response": raw_response,
            "details": str(e)
        }