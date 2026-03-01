# openai_client.py
from __future__ import annotations

import os
from collections.abc import Callable

import httpx
from openai import OpenAI

MODEL = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4.1-mini")

# Public contract used by pipeline/services
SummarizerFn = Callable[[str], str]

_client: OpenAI | None = None


# ------------------------------------------------------------
# Client creation
# ------------------------------------------------------------
def _get_client() -> OpenAI:
    global _client

    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set or missing in .env file")

        _client = OpenAI(
            api_key=api_key,
            timeout=httpx.Timeout(
                60.0,
                connect=10.0,
                read=60.0,
                write=30.0,
            ),
            max_retries=0,
        )

    return _client


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _truncate_text(text: str, max_chars: int = 15000) -> str:
    """
    Truncate on paragraph boundaries instead of raw characters.
    Prevents mid-sentence cuts that confuse summaries.
    """
    if len(text) <= max_chars:
        return text

    parts = text.split("\n\n")

    out: list[str] = []
    total = 0

    for p in parts:
        if total + len(p) > max_chars:
            break
        out.append(p)
        total += len(p)

    return "\n\n".join(out)


# ------------------------------------------------------------
# Default OpenAI summarizer
# ------------------------------------------------------------
def summarize_document(text: str) -> str:
    text = _truncate_text(text)

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


# ------------------------------------------------------------
# Test helper summarizer
# ------------------------------------------------------------
def dummy_summarizer(text: str) -> str:
    """
    Useful for tests or offline runs.
    """
    return text[:200] + "..."
