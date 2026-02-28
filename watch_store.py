from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from config import WATCH_FILE


@dataclass
class WatchConfig:
    sites: list[str]
    topics: list[str]
    settings: dict[str, Any]


DEFAULT_WATCH: WatchConfig = WatchConfig(
    sites=[
        "https://www.tsl.texas.gov/info",
    ],
    topics=[
        "grants",
        "archival",
        "digitization",
    ],
    settings={
        "max_links_per_site": 25,
        "fetch_timeout_seconds": 15,
        "same_domain_only": True,
        # NEW: exclude noisy nav/search/pagination URLs by default
        "exclude_patterns": [
            "search",
            "advanced",
            "browse",
            "facet",
            "filter",
            "sort=",
            "page=",
            "?",
        ],
        # NEW: global caps so scans cannot run away
        "max_total_pages": 60,
        "max_seconds": 45,
    },
)


def _clean_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for x in lines or []:
        if not isinstance(x, str):
            continue
        x = x.strip()
        if not x:
            continue
        out.append(x)
    # preserve order while de-duping
    dedup: list[str] = []
    seen = set()
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        dedup.append(x)
    return dedup


def load_watch() -> WatchConfig:
    if not WATCH_FILE.exists():
        return DEFAULT_WATCH

    try:
        data = yaml.safe_load(WATCH_FILE.read_text("utf-8")) or {}
    except Exception:
        return DEFAULT_WATCH

    sites = _clean_lines(data.get("sites") if isinstance(data, dict) else [])
    topics = _clean_lines(data.get("topics") if isinstance(data, dict) else [])
    settings = data.get("settings") if isinstance(data, dict) else None
    if not isinstance(settings, dict):
        settings = {}

    # fill defaults (but do not overwrite user-provided values)
    for k, v in DEFAULT_WATCH.settings.items():
        settings.setdefault(k, v)

    return WatchConfig(
        sites=sites or DEFAULT_WATCH.sites,
        topics=topics or DEFAULT_WATCH.topics,
        settings=settings,
    )


def save_watch_from_lines(
    sites_text: str, topics_text: str, settings: dict[str, Any] | None = None
) -> None:
    sites = _clean_lines((sites_text or "").splitlines())
    topics = _clean_lines((topics_text or "").splitlines())
    cfg = {
        "sites": sites,
        "topics": topics,
        "settings": settings or DEFAULT_WATCH.settings,
    }
    WATCH_FILE.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), "utf-8")
