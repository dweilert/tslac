from __future__ import annotations

import hashlib
import time
from typing import Any

from .cache import load_cached_summary, save_cached_summary
from .extract import extract_text
from .sources import DocumentSource
from logutil import debug, info, warn
from openai_client import summarize_document


def _hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build_doc_candidates(source: DocumentSource) -> list[dict[str, Any]]:
    """
    Returns list of dicts ready to be merged into your Candidate list rendering.
    Each dict includes: id/url, title, source, summary
    """
    out: list[dict[str, Any]] = []

    for doc in source.list_docs():
        data, filename = source.fetch_bytes(doc)

        # Cache key: stable + changes when content changes.
        # - Drive: doc_id + modified_ts is typically enough
        # - Local: doc_id + file mtime may be enough, but hashing bytes is safer
        if doc.source == "gdrive" and doc.modified_ts:
            cache_key = f"{doc.doc_id}|{doc.modified_ts}"
        else:
            cache_key = f"{doc.doc_id}|{_hash_bytes(data)}"

        debug(f"Docs: processing {doc.doc_id} name='{doc.display_name}' source={doc.source}")
        summary = load_cached_summary(cache_key)
        if summary is not None:
            debug(f"Docs: cache hit for {doc.display_name}")
        else:
            debug(f"Docs: cache miss; extracting text for {doc.display_name}")
            text = extract_text(filename, doc.mime_type, data)
            debug(f"Docs: extracted {len(text)} chars from {doc.display_name}")
            if not text.strip():
                warn(f"Docs: no extractable text for {doc.display_name} (scanned PDF?)")

            debug(f"OpenAI: summarizing {doc.display_name}")
            try:
                summary = summarize_document(text)
            except Exception as e:
                warn(f"OpenAI: summarization failed for {doc.display_name}: {e}")
                summary = "Summary unavailable (OpenAI not configured)."

            debug(f"OpenAI: summary length={len(summary)} for {doc.display_name}")
            debug(f"OpenAI: summary for {doc.display_name}: {summary}")
            save_cached_summary(
                cache_key,
                {
                    "doc_id": doc.doc_id,
                    "display_name": doc.display_name,
                    "source": doc.source,
                    "modified_ts": doc.modified_ts,
                    "summary": summary,
                },
            )

        out.append(
            {
                "id": doc.doc_id,  # use as unique id
                "title": doc.display_name,
                "source": doc.source,
                "summary": summary,
            }
        )

    debug(f"Docs: built {len(out)} doc candidates")
    return out


def summarize_with_openai(text: str, title: str) -> str:
    debug(f"OpenAI: summarizing {title}")
    t0 = time.time()

    try:
        summary = summarize_document(text, title=title)

        info(f"Docs: summary complete for {title} " f"(chars={len(summary)})")

        dt = time.time() - t0
        info(f"OpenAI: summary returned for {title} " f"in {dt:.1f}s ({len(summary)} chars)")

        return summary

    except Exception as e:
        dt = time.time() - t0
        warn(f"OpenAI: summary FAILED for {title} after {dt:.1f}s: {e}")

        # fail-open so UI still shows candidate
        return "Summary unavailable (OpenAI call failed)."
