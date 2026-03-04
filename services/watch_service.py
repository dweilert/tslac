from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import watcher
import config_runtime


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
    latest = watcher.load_latest_results()

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
    # Watch config is now managed in /config (config.yaml).
    # Keep a clear error so callers/UI can show the right status message.
    raise RuntimeError("Watch settings are now managed in /config (config.yaml).")