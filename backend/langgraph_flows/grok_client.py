"""
Grok (xAI) is OpenAI-SDK-compatible, so we use the `openai` client pointed at
xAI's base URL. Each of the 3 LangGraph flows gets its OWN API key, per spec,
so usage/billing/rate-limits can be tracked independently per feature.
"""
import os
from openai import OpenAI

GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_grok_client(key_env_var: str) -> OpenAI:
    api_key = os.getenv(key_env_var)
    if not api_key:
        raise RuntimeError(f"{key_env_var} is not set in the environment (.env).")
    return OpenAI(api_key=api_key, base_url=GROQ_BASE_URL, max_retries=0, timeout=3.0)


def grok_chat(client: OpenAI, system_prompt: str, user_prompt: str) -> str:
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content
