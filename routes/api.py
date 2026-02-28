from __future__ import annotations

import cleaner
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.get("/api/clean", get_api_clean)


def get_api_clean(req: Request) -> Response:
    try:
        url = (req.query_first.get("url") or "").strip()
        if not url:
            raise ValueError("Missing required query parameter: url")

        res = cleaner.clean_article(url)

        payload = {
            "url": res.url,
            "title": res.title,
            "published_date": res.published_date,
            "date_confidence": res.date_confidence,
            "clean_html": res.clean_html,
            "text_plain": res.text_plain,
            "images": res.images,
            "extraction_quality": res.extraction_quality,
        }
        return Response.json(payload, status=200)

    except Exception as e:
        return Response.json({"error": str(e)}, status=400)
