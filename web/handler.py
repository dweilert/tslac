from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from logutil import error
from web.errors import BadRequestError
from web.request import build_request
from web.response import Response
from web.router import Router

MAX_BODY = 2 * 1024 * 1024  # 2MB safety cap (adjust or remove if you prefer)


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

        if length < 0:
            length = 0
        if length > MAX_BODY:
            # Treat as client error (payload too large)
            resp = Response.bad_request(f"Request body too large (max {MAX_BODY} bytes)")
            self._write_response(resp)
            return

        body = self.rfile.read(length) if length > 0 else b""
        req = build_request(method=method, raw_path=self.path, headers=self.headers, body=body)

        # --- dispatch with correct error mapping ---
        try:
            resp = self.router.dispatch(req)

        except BadRequestError as e:
            # Client error: missing/invalid input, bad params, etc.
            resp = Response.bad_request(str(e))

        except Exception:
            # Server error: bugs, runtime failures, unexpected issues.
            error(f"Unhandled exception while handling {method} {self.path}", exc_info=True)
            resp = Response.internal_error()

        self._write_response(resp)

    def _write_response(self, resp: Response) -> None:
        # --- write response ---
        self.send_response(resp.status)
        for k, v in (resp.headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if resp.body:
            self.wfile.write(resp.body)
