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
        # gpt-3.5-turbo doesn't reliably support JSON mode, so we instruct 
        # the model explicitly in the user message and clean the response 
        # afterwards.
        json_instruction = (
            "\n\nIMPORTANT: Respond ONLY with a valid JSON object. "
            "Do not include any text before or after the JSON. "
            "Do not wrap the JSON in markdown code fences. "
            "Do not include any explanation or commentary outside the JSON structure."
        )
        
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt + json_instruction}
            ],
            temperature=0.2,
            max_tokens=2048
        )
        return response.choices[0].message.content
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def analyse_prompt(user_prompt: str, detection_system_prompt: str) -> dict:
    """
    Runs detection on a user prompt. Returns parsed JSON dictionary.
    Handles common JSON parsing issues from less-disciplined models.
    """
    raw_response = call_llm(detection_system_prompt, user_prompt)
    
    try:
        # Clean common formatting issues that gpt-3.5-turbo sometimes produces
        cleaned = raw_response.strip()
        
        # Strip markdown code fences if the model added them despite instructions
        if cleaned.startswith("```"):
            # Remove opening fence (handles ```json and ```)
            cleaned = cleaned.split("```", 1)[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            # Remove closing fence
            if "```" in cleaned:
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()
        
        # Sometimes the model wraps the JSON in extra text — try to extract 
        # just the JSON object by finding the first { and last }
        if not cleaned.startswith("{"):
            first_brace = cleaned.find("{")
            last_brace = cleaned.rfind("}")
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                cleaned = cleaned[first_brace:last_brace + 1]
        
        return json.loads(cleaned)
    
    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse LLM response as JSON",
            "raw_response": raw_response,
            "details": str(e)
        }
    except Exception as e:
        return {
            "error": "Unexpected error processing LLM response",
            "details": str(e)
        }