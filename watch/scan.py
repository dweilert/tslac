# watch/scan.py 
from __future__ import annotations

import json
import time
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from threading import Event
from typing import Any

from setup.config import OUT_DIR, WATCH_RESULTS_FILE
from storage.watch_store import load_watch

from .fetch import fetch
from .parse import LinkTextParser, pick_links
from .score import score_page_against_topics, should_exclude


def parse_site_line(line: str) -> tuple[str, str, int | None]:
    """
    Returns (mode, url, max_links_override)
    mode: 'home' or 'crawl' (default crawl)
    """
    s = (line or "").strip()
    if not s:
        return "crawl", "", None

    parts = s.split()
    if not parts:
        return "crawl", "", None

    mode = "crawl"
    idx = 0
    if parts[0].lower() in ("home", "crawl"):
        mode = parts[0].lower()
        idx = 1

    url = parts[idx] if idx < len(parts) else ""
    max_links_override = None

    for tok in parts[idx + 1 :]:
        if tok.startswith("max_links="):
            with suppress(Exception):
                max_links_override = int(tok.split("=", 1)[1])

    return mode, url, max_links_override


def run_watch_scan(
    cancel_event: Event | None = None,
    progress_cb: Callable[..., None] | None = None,
) -> dict[str, Any]:
    """
    Scan sites for topic matches.
    Supports site modes:
      - "home <url>"  : score only homepage content
      - "crawl <url>" : homepage + follow up to N links
    """
    cfg = load_watch()
    sites = cfg.sites or []
    topics = cfg.topics or []
    settings = cfg.settings or {}

    max_links_default = int(settings.get("max_links_per_site", 25) or 25)
    timeout_s = int(settings.get("fetch_timeout_seconds", 15) or 15)
    same_domain_only = bool(settings.get("same_domain_only", True))

    exclude_patterns = settings.get("exclude_patterns") or []
    if not isinstance(exclude_patterns, list):
        exclude_patterns = []
    exclude_patterns = [str(x) for x in exclude_patterns if x is not None]

    max_total_pages = int(settings.get("max_total_pages", 60) or 60)
    max_seconds = int(settings.get("max_seconds", 45) or 45)
    max_results = int(settings.get("max_results", 200) or 200)

    if progress_cb:
        progress_cb(
            message="Loaded config",
            sites_total=len(sites),
            sites_done=0,
            pages_done=0,
            pages_cap=max_total_pages,
            current_site="",
            current_url="",
            results_found=0,
        )

    t0 = time.monotonic()
    pages_done = 0
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for si, site_line in enumerate(sites):
        if cancel_event and cancel_event.is_set():
            break
        if time.monotonic() - t0 > max_seconds:
            errors.append(
                {
                    "site": str(site_line),
                    "url": "",
                    "error": f"Stopped: exceeded max_seconds={max_seconds}",
                }
            )
            break

        mode, site, max_links_override = parse_site_line(site_line)
        site = (site or "").strip()
        if not site:
            continue

        per_site_max_links = (
            max_links_override if max_links_override is not None else max_links_default
        )

        if progress_cb:
            progress_cb(
                message=f"Fetching ({mode}) ...", current_site=site, current_url=site, sites_done=si
            )

        try:
            home_html, _ct = fetch(site, timeout_s=timeout_s)
            p_home = LinkTextParser()
            p_home.feed(home_html)

            home_title = p_home.title() or ""
            home_meta = p_home.meta_desc or ""
            home_body = p_home.text() or ""

            if mode == "home":
                scored = score_page_against_topics(site, home_title, home_meta, home_body, topics)
                if scored:
                    results.append({"site": site, **scored})
                if progress_cb:
                    progress_cb(
                        message="Home scan done",
                        current_site=site,
                        current_url="",
                        sites_done=si + 1,
                        results_found=len(results),
                    )
                continue

            links = pick_links(site, p_home.links, same_domain_only=same_domain_only)
            links = [u for u in links if not should_exclude(u, exclude_patterns)]
            links = links[:per_site_max_links]

            for url in links:
                if cancel_event and cancel_event.is_set():
                    break
                if pages_done >= max_total_pages:
                    errors.append(
                        {
                            "site": site,
                            "url": url,
                            "error": f"Stopped: exceeded max_total_pages={max_total_pages}",
                        }
                    )
                    break
                if time.monotonic() - t0 > max_seconds:
                    errors.append(
                        {
                            "site": site,
                            "url": url,
                            "error": f"Stopped: exceeded max_seconds={max_seconds}",
                        }
                    )
                    break

                pages_done += 1
                if progress_cb:
                    progress_cb(
                        message="Fetching page...",
                        current_site=site,
                        current_url=url,
                        sites_done=si,
                        pages_done=pages_done,
                        pages_cap=max_total_pages,
                        results_found=len(results),
                    )

                try:
                    page_html, _ = fetch(url, timeout_s=timeout_s)
                    p2 = LinkTextParser()
                    p2.feed(page_html)

                    title = p2.title() or ""
                    meta = p2.meta_desc or ""
                    body = p2.text() or ""

                    scored = score_page_against_topics(url, title, meta, body, topics)
                    if scored:
                        results.append({"site": site, **scored})
                except Exception as e:
                    errors.append({"site": site, "url": url, "error": str(e)})

        except Exception as e:
            errors.append({"site": site, "url": site, "error": str(e)})

        if progress_cb:
            progress_cb(message="Site done", current_site=site, current_url="", sites_done=si + 1)

    # Sort: topic priority first, then score
    results.sort(key=lambda r: (r.get("best_topic_index", 10**9), -(r.get("score", 0) or 0)))
    results = results[:max_results]

    payload = {
        "ran_at": datetime.now().isoformat(timespec="seconds"),
        "topics": topics,
        "sites": sites,
        "settings": settings,
        "results": results,
        "errors": errors,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WATCH_RESULTS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    return payload


def load_latest_results() -> dict[str, Any]:
    if not WATCH_RESULTS_FILE.exists():
        return {"_error": "No results file yet", "results": [], "errors": []}
    try:
        return json.loads(WATCH_RESULTS_FILE.read_text("utf-8"))
    except Exception as e:
        return {"_error": f"Failed to parse results JSON: {e}", "results": [], "errors": []}
