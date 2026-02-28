from __future__ import annotations

from pathlib import Path

import export_preview
from web.request import Request
from web.response import Response
from web.router import Router

APP_DIR = Path(__file__).resolve().parent.parent


def register(router: Router) -> None:
    router.get("/preview", get_preview)
    router.get("/preview/file", get_preview_file)
    router.route_regex("GET", r"^/preview/images/.*", get_preview_image)


def get_preview(_: Request) -> Response:
    # IMPORTANT: return HTML directly; do not redirect.
    html_bytes = export_preview.build_preview_html()
    return Response.html(html_bytes)


def get_preview_file(_: Request) -> Response:
    p = APP_DIR / "output" / "preview" / "index.html"
    if not p.exists():
        return Response.not_found(
            "Preview file not found. Run the export that generates output/preview/index.html."
        )
    return Response.html(p.read_bytes())


def get_preview_image(req: Request) -> Response:
    # req.path is like: /preview/images/xxx.jpg
    rel = req.path[len("/preview/") :]  # images/xxx.jpg
    base = (APP_DIR / "output" / "preview").resolve()
    img_path = (APP_DIR / "output" / "preview" / rel).resolve()

    # prevent path traversal
    if not str(img_path).startswith(str(base)):
        return Response.bad_request("Invalid image path")

    if not img_path.exists():
        return Response.not_found("Image not found")

    data = img_path.read_bytes()
    suf = img_path.suffix.lower()
    ct = "image/jpeg"
    if suf == ".png":
        ct = "image/png"
    elif suf == ".webp":
        ct = "image/webp"
    elif suf == ".gif":
        ct = "image/gif"

    return Response(
        status=200, headers={"Content-Type": ct, "Content-Length": str(len(data))}, body=data
    )
