from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from setup.config import STATE_DIR
from util.logutil import info, warn

DOC_CANDIDATES_FILE = Path(STATE_DIR) / "doc_candidates.json"


def save_doc_candidates(doc_candidates: list[dict[str, Any]]) -> None:
    """
    Deprecated: doc candidates should be merged into the unified candidates list
    and persisted via the normal candidates store.
    Kept temporarily for compatibility, but should not be used by new code.
    """
    warn(
        "Docs: save_doc_candidates() is deprecated; docs should be merged into unified candidates."
    )
    DOC_CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    DOC_CANDIDATES_FILE.write_text(
        json.dumps(doc_candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    info(f"Docs: wrote {len(doc_candidates)} doc candidate(s) to {DOC_CANDIDATES_FILE}")


def load_doc_candidates() -> list[dict[str, Any]]:
    """
    Loads doc candidates from the legacy file if it exists.

    Milestone 2 goal: eventually docs should be sourced from the same unified persisted
    candidates list, or a canonical doc index, not this file.
    """
    if not DOC_CANDIDATES_FILE.exists():
        return []
    try:
        data = json.loads(DOC_CANDIDATES_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:
        warn(f"Docs: failed to read {DOC_CANDIDATES_FILE}: {e}")
        return []


def clear_doc_candidates() -> None:
    try:
        if DOC_CANDIDATES_FILE.exists():
            DOC_CANDIDATES_FILE.unlink()
            info(f"Docs: cleared {DOC_CANDIDATES_FILE}")
    except Exception as e:
        warn(f"Docs: failed to clear doc candidates: {e}")
