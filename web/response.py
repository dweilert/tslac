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

    @staticmethod
    def html(content: str | bytes, status: int = 200) -> "Response":
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
    ) -> "Response":
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
    def json(data: Any, status: int = 200) -> "Response":
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
    def redirect(location: str, status: int = 302) -> "Response":
        # Keep body empty; browsers follow Location.
        return Response(status=status, headers={"Location": location}, body=b"")

    @staticmethod
    def not_found(msg: str = "Not Found") -> "Response":
        return Response.text(msg, status=404)

    @staticmethod
    def bad_request(msg: str = "Bad Request") -> "Response":
        return Response.text(msg, status=400)

    @staticmethod
    def internal_error(msg: str = "Internal Server Error") -> "Response":
        """
        500 response. Keep it generic by default; don't leak exception details.
        If you pass a message, we HTML-escape it so it is safe to embed in HTML.
        """
        safe = html.escape(msg or "Internal Server Error")
        return Response.html(
            f"<h1>500 Internal Server Error</h1><p>{safe}</p>",
            status=500,
        )