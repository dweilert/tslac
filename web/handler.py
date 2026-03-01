from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from logutil import error
from web.errors import BadRequestError  # <-- add this (create web/errors.py)
from web.request import build_request
from web.response import Response
from web.router import Router


class RoutedHandler(BaseHTTPRequestHandler):
    router: Router  # set by factory

    def log_message(self, format: str, *args) -> None:
        # Optional: keep the console quieter. Comment this out if you want default logging.
        return

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def _handle(self, method: str) -> None:
        # --- read body safely ---
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except Exception:
            length = 0

        body = self.rfile.read(length) if length > 0 else b""
        req = build_request(method=method, raw_path=self.path, headers=self.headers, body=body)

        # --- dispatch with correct error mapping ---
        try:
            resp = self.router.dispatch(req)

        except BadRequestError as e:
            # Client error: missing/invalid input, bad params, etc.
            # Keep message short and user-facing.
            resp = Response.bad_request(str(e))

        except Exception:
            # Server error: bugs, runtime failures, unexpected issues.
            # Log traceback for debugging, but don't leak details to the client.
            error(f"Unhandled exception while handling {method} {self.path}", exc_info=True)
            resp = Response.internal_error()

        # --- write response ---
        self.send_response(resp.status)
        for k, v in (resp.headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if resp.body:
            self.wfile.write(resp.body)
