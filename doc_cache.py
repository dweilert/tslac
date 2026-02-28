from __future__ import annotations

import hashlib
import json
import os
from typing import Any

CACHE_DIR = "state/doc_cache"


def _ensure_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _safe_key(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_cached_summary(cache_key: str) -> str | None:
    _ensure_dir()
    path = os.path.join(CACHE_DIR, _safe_key(cache_key) + ".json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    return obj.get("summary")


def save_cached_summary(cache_key: str, payload: dict[str, Any]) -> None:
    _ensure_dir()
    path = os.path.join(CACHE_DIR, _safe_key(cache_key) + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
