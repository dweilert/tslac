# config_runtime.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Missing dependency: pyyaml. Install via conda: conda install -c conda-forge pyyaml"
    ) from e

APP_DIR = Path(__file__).resolve().parent
CONFIG_YAML = Path(os.getenv("TSLAC_CONFIG_YAML", str(APP_DIR / "config.yaml")))


def _load() -> dict[str, Any]:
    if not CONFIG_YAML.exists():
        return {}
    data = yaml.safe_load(CONFIG_YAML.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _as_list_str(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    if isinstance(x, str):
        return [line.strip() for line in x.splitlines() if line.strip()]
    s = str(x).strip()
    return [s] if s else []


def get_watch_sites() -> list[str]:
    data = _load()
    watch = data.get("watch") or {}
    return _as_list_str(watch.get("sites"))


def get_watch_keywords() -> list[str]:
    data = _load()
    watch = data.get("watch") or {}
    return _as_list_str(watch.get("keywords"))
