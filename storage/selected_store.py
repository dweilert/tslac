from __future__ import annotations

from datetime import datetime
from typing import Any

import yaml

from config import DEFAULT_INTRO, DEFAULT_SUBJECT, SELECTED_FILE


def load_selected() -> dict[str, Any]:
    if not SELECTED_FILE.exists():
        return {}
    return yaml.safe_load(SELECTED_FILE.read_text("utf-8")) or {}


def save_selected(subject: str, intro: str, urls: list[str]) -> None:
    doc = {
        "month": datetime.now().strftime("%Y-%m"),
        "subject": (subject or "").strip() or DEFAULT_SUBJECT,
        "intro": (intro or "").strip() or DEFAULT_INTRO,
        "items": [{"url": u} for u in urls],
    }
    SELECTED_FILE.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), "utf-8")
