# watch/score.py
from __future__ import annotations

from typing import Any


def score_term(topic: str, title: str, meta: str, body: str, weight: int) -> tuple[int, int]:
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


def score_page_against_topics(
    url: str, title: str, meta: str, body: str, topics: list[str]
) -> dict[str, Any] | None:
    snippet = (body or "")[:240].strip()

    best_topic_index: int | None = None
    matched_topics: list[str] = []
    total_score = 0

    for i, topic in enumerate(topics):
        weight = (len(topics) - i) * 10
        s, _hits = score_term(topic, title, meta, body, weight=weight)
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


def should_exclude(url: str, patterns: list[str]) -> bool:
    u = (url or "").lower()
    for p in patterns or []:
        if p is None:
            continue
        p = str(p).lower().strip()
        if not p:
            continue
        if p == "?":
            if "?" in u:
                return True
        else:
            if p in u:
                return True
    return False
