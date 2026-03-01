# web/errors.py

from __future__ import annotations


class BadRequestError(Exception):
    """Raise this when the client sent invalid input (missing field, bad number, etc)."""