from __future__ import annotations

from pathlib import Path

from logutil import error
from services import preview_service
from web.request import Request
from web.response import Response
from web.router import Router

APP_DIR = Path(__file__).resolve().parent.parent


def register(router: Router) -> None:
    router.get("/preview", get_preview)
    router.get("/preview/file", get_preview_file)
    router.route_regex("GET", r"^/preview/images/.*", get_preview_image)


def get_preview(_: Request) -> Response:
    html_bytes = preview_service.build_preview_html()
    return Response.html(html_bytes)


def get_preview_file(_: Request) -> Response:
    data = preview_service.load_preview_index(APP_DIR)
    if data is None:
        return Response.not_found(
            "Preview file not found. Run the export that generates output/preview/index.html."
        )
    return Response.html(data)


def get_preview_image(req: Request) -> Response:
    try:
        fb = preview_service.load_preview_image(APP_DIR, req.path)
    except ValueError:
        return Response.bad_request("Invalid image path")
    except Exception:
        error("Preview image load failed", exc_info=True)
        return Response.internal_error()

    if fb is None:
        return Response.not_found("Image not found")

    return Response(
        status=200,
        headers={"Content-Type": fb.content_type, "Content-Length": str(len(fb.data))},
        body=fb.data,
    )
