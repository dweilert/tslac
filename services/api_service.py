from __future__ import annotations

from typing import Any

import cleaner
from web.errors import BadRequestError


def clean_article_payload(*, url: str) -> dict[str, Any]:
    url = (url or "").strip()
    if not url:
        raise BadRequestError("Missing required query parameter: url")

    # Optional but recommended input sanity: avoid weird schemes
    if not (url.startswith("http://") or url.startswith("https://")):
        raise BadRequestError("url must start with http:// or https://")

    res = cleaner.clean_article(url)

    return {
        "url": res.url,
        "title": res.title,
        "published_date": res.published_date,
        "date_confidence": res.date_confidence,
        "clean_html": res.clean_html,
        "text_plain": res.text_plain,
        "images": res.images,
        "extraction_quality": res.extraction_quality,
    }
