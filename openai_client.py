# openai_client.py
import os

import httpx
from openai import OpenAI

MODEL = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4.1-mini")
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set or missing in .env file")

        # Keep it sane for a local newsletter helper.
        # If OpenAI is slow/hung, fail-open and keep going.
        _client = OpenAI(
            api_key=api_key,
            timeout=httpx.Timeout(60.0, connect=10.0, read=60.0, write=30.0),
            max_retries=0,  # important: don't sit there retrying for a long time
        )
    return _client


def summarize_document(text: str) -> str:
    MAX_CHARS = 15000
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    prompt = (
        "Summarize the following document in 2–4 clear sentences. "
        "Focus specifically on what the document is suggesting or recommending. "
        "Be concise.\n\n"
        f"{text}"
    )

    client = _get_client()
    resp = client.responses.create(
        model=MODEL,
        input=prompt,
        max_output_tokens=250,
    )
    return resp.output_text.strip()
