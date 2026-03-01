from __future__ import annotations

from services.api_service import clean_article_payload
from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.get("/api/clean", get_api_clean)


def get_api_clean(req: Request) -> Response:
    payload = clean_article_payload(url=req.query_first.get("url") or "")
    return Response.json(payload, status=200)
