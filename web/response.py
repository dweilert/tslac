from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Response:
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    # ----------------------------
    # Core builders
    # ----------------------------
    @staticmethod
    def html(content: str | bytes, status: int = 200) -> Response:
        b = content.encode("utf-8") if isinstance(content, str) else (content or b"")
        return Response(
            status=status,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "Content-Length": str(len(b)),
            },
            body=b,
        )

    @staticmethod
    def text(
        content: str | bytes,
        status: int = 200,
        content_type: str = "text/plain; charset=utf-8",
    ) -> Response:
        b = content.encode("utf-8") if isinstance(content, str) else (content or b"")
        return Response(
            status=status,
            headers={
                "Content-Type": content_type,
                "Content-Length": str(len(b)),
            },
            body=b,
        )

    @staticmethod
    def json(data: Any, status: int = 200) -> Response:
        b = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        return Response(
            status=status,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(b)),
            },
            body=b,
        )

    @staticmethod
    def bytes(
        data: bytes,
        *,
        status: int = 200,
        content_type: str = "application/octet-stream",
        headers: dict[str, str] | None = None,
    ) -> Response:
        """
        Raw bytes response for downloads (zip/png/pdf/etc).

        Example:
          return Response.bytes(zip_bytes, content_type="application/zip")
        """
        b = data or b""
        h = {
            "Content-Type": content_type,
            "Content-Length": str(len(b)),
        }
        if headers:
            h.update(headers)
        return Response(status=status, headers=h, body=b)

    @staticmethod
    def download(
        data: bytes,
        *,
        filename: str,
        content_type: str = "application/octet-stream",
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """
        Convenience wrapper for downloadable attachments.
        Adds RFC 5987 filename* for better cross-browser behavior.
        """
        from urllib.parse import quote

        fname = filename or "download"
        fname_ascii = fname.replace('"', "")  # avoid breaking the header
        fname_star = quote(fname, safe="")  # UTF-8 percent-encoded

        h = {
            "Content-Disposition": (
                f"attachment; filename=\"{fname_ascii}\"; filename*=UTF-8''{fname_star}"
            ),
            "Cache-Control": "no-store",
        }
        if headers:
            h.update(headers)
        return Response.bytes(data, status=status, content_type=content_type, headers=h)

    # ----------------------------
    # Redirects and errors
    # ----------------------------
    @staticmethod
    def redirect(location: str, status: int = 302) -> Response:
        # Keep body empty; browsers follow Location.
        return Response(
            status=status,
            headers={
                "Location": location,
                "Content-Length": "0",
            },
            body=b"",
        )

    @staticmethod
    def not_found(msg: str = "Not Found") -> Response:
        return Response.text(msg, status=404)

    @staticmethod
    def bad_request(msg: str = "Bad Request") -> Response:
        return Response.text(msg, status=400)

    @staticmethod
    def internal_error(msg: str = "Internal Server Error") -> Response:
        """
        500 response. Keep it generic by default; don't leak exception details.
        If you pass a message, we HTML-escape it so it is safe to embed in HTML.
        """
        safe = html.escape(msg or "Internal Server Error")
        body = f"<h1>500 Internal Server Error</h1><p>{safe}</p>"
        return Response.html(body, status=500)

    @staticmethod
    def method_not_allowed(allowed: list[str], msg: str = "Method Not Allowed") -> Response:
        # RFC: include Allow header
        r = Response.text(msg, status=405)
        r.headers["Allow"] = ", ".join(sorted(set(allowed)))
        return r
