from __future__ import annotations

from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.get("/healthz", get_health)


def get_health(_: Request) -> Response:
    return Response.json({"ok": True})