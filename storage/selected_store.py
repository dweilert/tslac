# storage/selected_store.py
from __future__ import annotations

import os
import time
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from setup.config import DEFAULT_INTRO, DEFAULT_SUBJECT

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SELECTED_FILE = PROJECT_ROOT / "selected.yaml"


# ----------------------------
# Helpers
# ----------------------------
def _as_dict(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _norm_urls(urls: list[str]) -> list[str]:
    """Strip, drop blanks, preserve order, de-dupe."""
    out: list[str] = []
    seen: set[str] = set()
    for u in urls or []:
        s = (u or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _content_id_for_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith(("web:", "gdrive:", "local:")):
        return u
    return f"web:{u}"


def _atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """
    Atomic file write:
      - write to a sibling temp file
      - flush + fsync
      - Path.replace() into place
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{int(time.time() * 1000)}")

    with tmp.open("w", encoding=encoding, newline="\n") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")
        f.flush()

        with suppress(Exception):
            os.fsync(f.fileno())

    tmp.replace(path)


# ----------------------------
# Public API
# ----------------------------
def load_selected() -> dict[str, Any]:
    """
    Load selected.yaml.

    Always returns a dict.
    If the file is missing or invalid YAML, returns {}.

    Back-compat:
      - items may be [{"url": "..."}] (old)
      - or [{"id": "...", "url": "..."}] (new)
    """
    if not SELECTED_FILE.exists():
        return {}

    try:
        data = yaml.safe_load(SELECTED_FILE.read_text("utf-8"))
    except Exception:
        return {}

    doc = _as_dict(data)

    # Backfill ids for old items (in-memory only; we don’t rewrite automatically)
    items = doc.get("items")
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                if not it.get("id") and isinstance(it.get("url"), str) and it["url"].strip():
                    it["id"] = _content_id_for_url(it["url"])

    return doc


def save_selected(subject: str, intro: str, urls: list[str]) -> None:
    """
    Persist the selected issue metadata and selected items.

    Schema (new):
      {
        "month": "YYYY-MM",
        "subject": "...",
        "intro": "...",
        "items": [{"id": "web:<url>", "url": "<url>"}, ...],
        "updated_at": "YYYY-MM-DDTHH:MM:SS"
      }

    Back-compat:
      - Function signature still accepts urls list (web items only for now)
    """
    urls2 = _norm_urls(urls)

    now = datetime.now()
    doc: dict[str, Any] = {
        "month": now.strftime("%Y-%m"),
        "subject": (subject or "").strip() or DEFAULT_SUBJECT,
        "intro": (intro or "").strip() or DEFAULT_INTRO,
        "items": [{"id": _content_id_for_url(u), "url": u} for u in urls2],
        "updated_at": now.isoformat(timespec="seconds"),
    }

    text = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    _atomic_write_text(SELECTED_FILE, text, encoding="utf-8")


def save_selected_item(url: str) -> bool:
    """
    Add one item to selected.yaml. Returns True if the file changed.
    Preserves existing subject/intro/month metadata.
    """
    u = (url or "").strip()
    if not u:
        return False

    doc = load_selected()
    subject = (doc.get("subject") or "").strip() if isinstance(doc, dict) else ""
    intro = (doc.get("intro") or "").strip() if isinstance(doc, dict) else ""

    items = []
    existing_urls: set[str] = set()
    if isinstance(doc, dict):
        for it in doc.get("items") or []:
            if not isinstance(it, dict):
                continue
            existing_url = (it.get("url") or "").strip()
            if not existing_url or existing_url in existing_urls:
                continue
            existing_urls.add(existing_url)
            items.append(
                {
                    "id": (it.get("id") or _content_id_for_url(existing_url)).strip(),
                    "url": existing_url,
                }
            )

    if u in existing_urls:
        return False

    items.append({"id": _content_id_for_url(u), "url": u})
    save_selected(subject, intro, [it["url"] for it in items])
    return True


def remove_selected_item(url: str) -> bool:
    """
    Remove one item from selected.yaml. Returns True if the file changed.
    Preserves existing subject/intro/month metadata.
    """
    u = (url or "").strip()
    if not u:
        return False

    doc = load_selected()
    subject = (doc.get("subject") or "").strip() if isinstance(doc, dict) else ""
    intro = (doc.get("intro") or "").strip() if isinstance(doc, dict) else ""

    kept_urls: list[str] = []
    removed = False

    if isinstance(doc, dict):
        for it in doc.get("items") or []:
            if not isinstance(it, dict):
                continue
            existing_url = (it.get("url") or "").strip()
            if not existing_url:
                continue
            if existing_url == u:
                removed = True
                continue
            if existing_url not in kept_urls:
                kept_urls.append(existing_url)

    if not removed:
        return False

    save_selected(subject, intro, kept_urls)
    return True
