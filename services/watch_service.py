from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import config_runtime
import watch_store  # NEW: compat alias for tests that patch svc.watch_store
import watch.runtime as watcher  # NEW: compat alias for tests that patch svc.watcher
from watch.scan import load_latest_results

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
    latest = load_latest_results()

    sites = config_runtime.get_watch_sites()
    topics = config_runtime.get_watch_keywords()

    sites_text = "\n".join(sites)
    topics_text = "\n".join(topics)

    # settings were previously stored in watch.yaml; we’re not using them now.
    # Keep field for template compatibility.
    return WatchPageModel(
        sites_text=sites_text,
        topics_text=topics_text,
        latest=latest,
        settings=None,
    )


def save_watch_config(*, sites_text: str, topics_text: str) -> None:
    """
    Back-compat: older code/tests expect watch settings to persist via watch_store.save_watch_from_lines.
    """
    cfg = watch_store.load_watch()
    settings = getattr(cfg, "settings", None)
    watch_store.save_watch_from_lines(sites_text, topics_text, settings)    