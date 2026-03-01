from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import watch_store
import watcher


@dataclass(frozen=True)
class WatchPageModel:
    sites_text: str
    topics_text: str
    latest: Any
    settings: Any


def get_status() -> dict[str, Any]:
    return watcher.get_watch_status()


def start_scan() -> bool:
    # returns True if started, False if already running
    return watcher.start_watch_scan_async()


def cancel_scan() -> None:
    watcher.cancel_watch_scan()


def load_page_model() -> WatchPageModel:
    cfg = watch_store.load_watch()
    latest = watcher.load_latest_results()
    sites_text = "\n".join(getattr(cfg, "sites", None) or [])
    topics_text = "\n".join(getattr(cfg, "topics", None) or [])
    return WatchPageModel(
        sites_text=sites_text,
        topics_text=topics_text,
        latest=latest,
        settings=getattr(cfg, "settings", None),
    )


def save_watch_config(*, sites_text: str, topics_text: str) -> None:
    # preserve settings unless you also post settings fields
    cfg = watch_store.load_watch()
    watch_store.save_watch_from_lines(
        sites_text, topics_text, settings=getattr(cfg, "settings", None)
    )
