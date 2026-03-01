# watch/parse.py
from __future__ import annotations

import re
from collections.abc import Iterable
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse


class LinkTextParser(HTMLParser):
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
        return re.sub(r"\s+", " ", s).strip()


def norm_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return u
    p = urlparse(u)
    return p._replace(fragment="").geturl()


def same_domain(a: str, b: str) -> bool:
    try:
        return (urlparse(a).netloc or "").lower() == (urlparse(b).netloc or "").lower()
    except Exception:
        return False


def pick_links(base_url: str, hrefs: Iterable[str], same_domain_only: bool) -> list[str]:
    out: list[str] = []
    seen = set()

    for h in hrefs:
        h = (h or "").strip()
        if not h:
            continue
        hl = h.lower()
        if h.startswith("#") or hl.startswith("javascript:") or hl.startswith("mailto:"):
            continue

        absu = norm_url(urljoin(base_url, h))
        if not absu.lower().startswith(("http://", "https://")):
            continue
        if same_domain_only and not same_domain(base_url, absu):
            continue
        if absu in seen:
            continue

        seen.add(absu)
        out.append(absu)

    return out
