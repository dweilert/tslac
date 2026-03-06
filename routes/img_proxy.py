from __future__ import annotations

import requests

from web.request import Request
from web.response import Response
from web.router import Router

# UA style (keep it simple + browser-like)
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}


def register(router: Router) -> None:
    router.get("/img", get_img)


def get_img(req: Request) -> Response:
    try:
        q = req.query_first
        u = (q.get("u") or "").strip()
        base = (q.get("base") or "").strip()

        if not u:
            return Response.bad_request("Missing query param: u")

        # safety: only proxy http(s)
        if not (u.startswith("http://") or u.startswith("https://")):
            return Response.bad_request("Invalid image URL")

        headers = dict(UA)
        if base and (base.startswith("http://") or base.startswith("https://")):
            headers["Referer"] = base

        # Stream so we don't load huge images into memory unnecessarily
        r = requests.get(u, headers=headers, timeout=20, stream=True)
        r.raise_for_status()

        content_type = r.headers.get("Content-Type") or "application/octet-stream"
        data = r.content

        return Response(
            status=200,
            headers={"Content-Type": content_type, "Content-Length": str(len(data))},
            body=data,
        )

    except Exception as e:
        # Keep it simple; the UI already shows a friendly error.
        return Response.text(f"Image proxy failed: {e}", status=400)
