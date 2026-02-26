from __future__ import annotations

from web.request import Request
from web.response import Response
from web.router import Router


def register(router: Router) -> None:
    router.get("/", get_root)


def get_root(_: Request) -> Response:
    return Response.redirect("/preview")