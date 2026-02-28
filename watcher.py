from __future__ import annotations

import json
import re
import threading
import time
from collections.abc import Callable, Iterable
from contextlib import suppress
from datetime import datetime
from html.parser import HTMLParser
from threading import Event, Lock
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from config import HEADERS, OUT_DIR, WATCH_RESULTS_FILE
from watch_store import load_watch

# ============================================================
# Runtime status + async scan control
# ============================================================

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


# ============================================================
# HTML parsing + fetch helpers
# ============================================================


class _LinkTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self._in_title = False
        self.title_parts: list[str] = []
        self.meta_desc: str = ""
        self.text_parts: list[str] = []
        self._skip_depth = 0  # skip script/style/noscript

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        a = dict((k.lower(), (v or "")) for k, v in attrs)

        if tag in ("script", "style", "noscript"):
            self._skip_depth += 1

        if tag == "a":
            href = a.get("href", "").strip()
            if href:
                self.links.append(href)

        if tag == "title":
            self._in_title = True

        if tag == "meta":
            name = (a.get("name") or "").lower().strip()
            prop = (a.get("property") or "").lower().strip()
            if name == "description" or prop == "og:description":
                content = (a.get("content") or "").strip()
                if content and not self.meta_desc:
                    self.meta_desc = content

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ("script", "style", "noscript") and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if not data:
            return
        if self._in_title:
            self.title_parts.append(data)
        else:
            self.text_parts.append(data)

    def title(self) -> str:
        return " ".join(x.strip() for x in self.title_parts if x and x.strip()).strip()

    def text(self) -> str:
        s = " ".join(x.strip() for x in self.text_parts if x and x.strip())
        s = re.sub(r"\s+", " ", s).strip()
        return s


def _fetch(url: str, timeout_s: int) -> tuple[str, str]:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout_s) as r:
        ct = (r.headers.get("Content-Type") or "").lower()
        raw = r.read()

    enc = "utf-8"
    m = re.search(r"charset=([a-z0-9_\-]+)", ct)
    if m:
        enc = m.group(1)

    try:
        return raw.decode(enc, errors="replace"), ct
    except Exception:
        return raw.decode("utf-8", errors="replace"), ct


def _norm_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return u
    p = urlparse(u)
    return p._replace(fragment="").geturl()


def _same_domain(a: str, b: str) -> bool:
    try:
        return (urlparse(a).netloc or "").lower() == (urlparse(b).netloc or "").lower()
    except Exception:
        return False


def _pick_links(base_url: str, hrefs: Iterable[str], same_domain_only: bool) -> list[str]:
    out: list[str] = []
    seen = set()
    for h in hrefs:
        h = (h or "").strip()
        if not h:
            continue
        if (
            h.startswith("#")
            or h.lower().startswith("javascript:")
            or h.lower().startswith("mailto:")
        ):
            continue

        absu = urljoin(base_url, h)
        absu = _norm_url(absu)

        if not absu.lower().startswith(("http://", "https://")):
            continue

        if same_domain_only and not _same_domain(base_url, absu):
            continue

        if absu in seen:
            continue
        seen.add(absu)
        out.append(absu)
    return out


# ============================================================
# Site line parsing: "home <url>" or "crawl <url> max_links=10"
# ============================================================


def _parse_site_line(line: str) -> tuple[str, str, int | None]:
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

    # for tok in parts[idx + 1 :]:
    #     if tok.startswith("max_links="):
    #         try:
    #             max_links_override = int(tok.split("=", 1)[1])
    #         except Exception:
    #             pass

    for tok in parts[idx + 1 :]:
        if tok.startswith("max_links="):
            with suppress(Exception):
                max_links_override = int(tok.split("=", 1)[1])

    return mode, url, max_links_override


# ============================================================
# Topic scoring + exclude filtering
# ============================================================


def _score(topic: str, title: str, meta: str, body: str, weight: int) -> tuple[int, int]:
    """
    Returns (score, body_hits)
    """
    t = (topic or "").lower().strip()
    if not t:
        return 0, 0

    title_l = (title or "").lower()
    meta_l = (meta or "").lower()
    body_l = (body or "").lower()

    score = 0
    if t in title_l:
        score += weight * 3
    if t in meta_l:
        score += weight * 2

    hits = body_l.count(t)
    score += weight * min(5, hits)
    return score, hits


def _score_page_against_topics(
    url: str, title: str, meta: str, body: str, topics: list[str]
) -> dict[str, Any] | None:
    snippet = (body or "")[:240].strip()

    best_topic_index: int | None = None
    matched_topics: list[str] = []
    total_score = 0

    for i, topic in enumerate(topics):
        weight = (len(topics) - i) * 10
        s, _hits = _score(topic, title, meta, body, weight=weight)
        if s > 0:
            matched_topics.append(topic)
            total_score += s
            if best_topic_index is None:
                best_topic_index = i

    if best_topic_index is None:
        return None

    return {
        "url": url,
        "title": title,
        "snippet": snippet,
        "matched_topics": matched_topics,
        "best_topic_index": best_topic_index,
        "score": total_score,
    }


def _should_exclude(url: str, patterns: list[str]) -> bool:
    u = (url or "").lower()
    for p in patterns or []:
        if p is None:
            continue
        p = str(p).lower()
        if not p:
            continue
        if p == "?":
            if "?" in u:
                return True
        else:
            if p in u:
                return True
    return False


# ============================================================
# Public API: scan + load latest results
# ============================================================


def run_watch_scan(
    cancel_event: Event | None = None,
    progress_cb: Callable[..., None] | None = None,
) -> dict[str, Any]:
    """
    Scan sites for topic matches. Supports site modes:
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

        mode, site, max_links_override = _parse_site_line(site_line)
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
            # Fetch homepage once for both modes
            home_html, _ct = _fetch(site, timeout_s=timeout_s)
            p_home = _LinkTextParser()
            p_home.feed(home_html)

            home_title = p_home.title() or ""
            home_meta = p_home.meta_desc or ""
            home_body = p_home.text() or ""

            if mode == "home":
                scored = _score_page_against_topics(site, home_title, home_meta, home_body, topics)
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

            # crawl mode
            links = _pick_links(site, p_home.links, same_domain_only=same_domain_only)
            links = [u for u in links if not _should_exclude(u, exclude_patterns)]
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
                    page_html, _ = _fetch(url, timeout_s=timeout_s)
                    p2 = _LinkTextParser()
                    p2.feed(page_html)

                    title = p2.title() or ""
                    meta = p2.meta_desc or ""
                    body = p2.text() or ""

                    scored = _score_page_against_topics(url, title, meta, body, topics)
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

    # Cap output size
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


# def load_latest_results() -> dict[str, Any]:
#     if not WATCH_RESULTS_FILE.exists():
#         return {}
#     try:
#         return json.loads(WATCH_RESULTS_FILE.read_text("utf-8"))
#     except Exception:
#         return {}


def load_latest_results() -> dict[str, Any]:
    if not WATCH_RESULTS_FILE.exists():
        return {"_error": "No results file yet", "results": [], "errors": []}
    try:
        return json.loads(WATCH_RESULTS_FILE.read_text("utf-8"))
    except Exception as e:
        return {"_error": f"Failed to parse results JSON: {e}", "results": [], "errors": []}
