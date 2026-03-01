from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from dataclasses import dataclass
from re import Pattern

from .request import Request
from .response import Response

# Old style: handler(req) -> Response
HandlerFn = Callable[[Request], Response]
# New style: handler(req, params) -> Response
HandlerParamsFn = Callable[[Request, dict[str, str]], Response]
HandlerAny = HandlerFn | HandlerParamsFn


@dataclass(frozen=True)
class _Route:
    method: str
    kind: str  # "exact" | "regex"
    pattern: str
    regex: Pattern[str] | None
    handler: HandlerAny


class Router:
    def __init__(self) -> None:
        self._routes: list[_Route] = []

    # --- Registration helpers ---
    def get(self, path: str, handler: HandlerFn) -> None:
        self._routes.append(_Route("GET", "exact", path, None, handler))

    def post(self, path: str, handler: HandlerFn) -> None:
        self._routes.append(_Route("POST", "exact", path, None, handler))

    def route_regex(self, method: str, pattern: str, handler: HandlerAny) -> None:
        self._routes.append(_Route(method.upper(), "regex", pattern, re.compile(pattern), handler))

    # --- Internal call helper (keeps compatibility with old handlers) ---
    def _call_handler(self, handler: HandlerAny, req: Request, params: dict[str, str]) -> Response:
        """
        Call handler(req, params) if it supports 2 args, else call handler(req).
        This lets you migrate route-by-route.
        """
        try:
            # Fast path: attempt new style first
            return handler(req, params)  # type: ignore[misc]
        except TypeError:
            # Old style: handler(req)
            return handler(req)  # type: ignore[misc]

    # --- Dispatch ---
    def dispatch(self, req: Request) -> Response:
        for r in self._routes:
            if r.method != req.method:
                continue

            if r.kind == "exact":
                if req.path == r.pattern:
                    return self._call_handler(r.handler, req, {})

            elif r.kind == "regex":
                assert r.regex is not None
                m = r.regex.match(req.path)
                if m:
                    params = m.groupdict()  # <-- named groups become params
                    return self._call_handler(r.handler, req, params)

        return Response.not_found(f"No route for {req.method} {req.path}")