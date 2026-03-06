# watch/runtime.py
from __future__ import annotations

import threading
from datetime import datetime
from threading import Event, Lock
from typing import Any

from storage.watch_store import load_watch

from .scan import run_watch_scan

_STATUS_LOCK = Lock()
_STATUS: dict[str, Any] = {
    "state": "idle",  # idle|running|done|error
    "message": "",
    "started_at": "",
    "ended_at": "",
    "current_site": "",
    "current_url": "",
    "sites_total": 0,
    "sites_done": 0,
    "pages_done": 0,
    "pages_cap": 0,
    "results_found": 0,
}

_SCAN_THREAD: threading.Thread | None = None
_CANCEL = Event()


def get_watch_status() -> dict[str, Any]:
    with _STATUS_LOCK:
        return dict(_STATUS)


def _set_status(**kwargs: Any) -> None:
    with _STATUS_LOCK:
        _STATUS.update(kwargs)


def _progress_update(**kwargs: Any) -> None:
    _set_status(**kwargs)


def start_watch_scan_async() -> bool:
    """
    Start a scan in a background thread.
    Returns True if started, False if already running.
    """
    global _SCAN_THREAD
    if _SCAN_THREAD and _SCAN_THREAD.is_alive():
        return False
    _CANCEL.clear()
    _SCAN_THREAD = threading.Thread(target=_scan_thread_main, daemon=True)
    _SCAN_THREAD.start()
    return True


def cancel_watch_scan() -> None:
    _CANCEL.set()


def _scan_thread_main() -> None:
    cfg = load_watch()
    _set_status(
        state="running",
        message="Starting scan...",
        started_at=datetime.now().isoformat(timespec="seconds"),
        ended_at="",
        current_site="",
        current_url="",
        sites_total=len(cfg.sites or []),
        sites_done=0,
        pages_done=0,
        pages_cap=int((cfg.settings or {}).get("max_total_pages", 60) or 60),
        results_found=0,
    )
    try:
        payload = run_watch_scan(cancel_event=_CANCEL, progress_cb=_progress_update)
        _set_status(
            state="done",
            message="Scan cancelled" if _CANCEL.is_set() else "Scan complete",
            ended_at=datetime.now().isoformat(timespec="seconds"),
            results_found=len(payload.get("results", []) or []),
            current_url="",
        )
    except Exception as e:
        _set_status(
            state="error",
            message=f"Scan failed: {e}",
            ended_at=datetime.now().isoformat(timespec="seconds"),
            current_url="",
        )
