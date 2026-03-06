# config_ui.py
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote

from setup.secrets_env import *
from render import render
from web.request import Request
from web.response import Response
from web.router import Router

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Missing dependency: pyyaml. Install via conda: conda install -c conda-forge pyyaml"
    ) from e


APP_DIR = Path(__file__).resolve().parent
CONFIG_YAML = APP_DIR / "config.yaml"


# ----- Defaults (mirror your existing config.py) -----
DEFAULTS: dict[str, Any] = {
    "tsl": {"base_url": "https://www.tsl.texas.gov", "news_path": "/info"},
    "server": {"host": "127.0.0.1", "port": 5055},
    "http": {"user_agent": "newsletter-bot/1.0 (local script)"},
    "defaults": {
        "subject": "Monthly Update — New from the Texas State Library",
        "intro": (
            "Hello everyone—here are highlights and resources recently published by the Texas State Library "
            "and Archives Commission."
        ),
    },
    "filtering": {
        "exact_exclude_paths": [
            "/contact",
            "/visit",
            "/about",
            "/tslac-statutesandrules",
            "/libsearch",
            "/arc",
            "/tbp",
            "/slrm",
        ],
        "exclude_texts": [
            "see more news and events",
            "view our calendar",
            "subscribe to events",
        ],
        "last_3_months_days": 92,
    },
    "watch": {"sites": [], "keywords": []},
}


def register(router: Router) -> None:
    router.get("/config", get_config)
    router.post("/config", post_config)


def _parse_post_form(req: Request) -> dict[str, list[str]]:
    raw = req.body.decode("utf-8", errors="replace")
    return parse_qs(raw, keep_blank_values=True)


def _deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    # src wins
    out = dict(dst)
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def _load_config_yaml() -> dict[str, Any]:
    if not CONFIG_YAML.exists():
        return dict(DEFAULTS)

    data = yaml.safe_load(CONFIG_YAML.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return dict(DEFAULTS)

    merged = _deep_merge(DEFAULTS, data)
    return merged


def _dump_config_yaml(data: dict[str, Any]) -> None:
    CONFIG_YAML.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def _lines_to_list(text: str) -> list[str]:
    out: list[str] = []
    for line in (text or "").splitlines():
        s = line.strip()
        if s:
            out.append(s)
    return out


def _to_int(s: str, default: int) -> int:
    try:
        return int((s or "").strip())
    except Exception:
        return default


def _derive_paths() -> dict[str, str]:
    out_dir = APP_DIR / "output"
    state_dir = APP_DIR / "state"
    return {
        "app_dir": str(APP_DIR),
        "out_dir": str(out_dir),
        "state_dir": str(state_dir),
        "seen_file": str(state_dir / "seen_urls.json"),
        "candidates_file": str(out_dir / "candidates_latest.json"),
        "selected_file": str(APP_DIR / "selected.yaml"),
        "curation_file": str(APP_DIR / "curation.yaml"),
        "watch_file": str(APP_DIR / "watch.yaml"),
        "watch_results_file": str(out_dir / "watch_results_latest.json"),
    }


def get_config(req: Request, _params: dict[str, str] | None = None) -> Response:
    secrets_env.load_env()

    cfg = _load_config_yaml()

    status = ""
    q = req.query or {}
    # In this app, query values may be str or list[str]; handle both.
    v = q.get("status")
    if isinstance(v, list):
        status = v[0] if v else ""
    elif isinstance(v, str):
        status = v
    else:
        status = ""

    openai_key = secrets_env.read_secret("OPENAI_API_KEY")
    tinymce_key = secrets_env.read_secret("TINYMCE_API_KEY")

    paths = _derive_paths()

    html = render(
        "config.html",
        title="TSL App Configuration",
        page_css="/static/css/config.css",
        status=status,
        # Secrets (masked)
        openai_key_masked=secrets_env.mask_secret(openai_key) or "(not set)",
        tinymce_key_masked=secrets_env.mask_secret(tinymce_key) or "(not set)",
        # YAML fields
        base_url=cfg["tsl"]["base_url"],
        news_path=cfg["tsl"]["news_path"],
        host=cfg["server"]["host"],
        port=str(cfg["server"]["port"]),
        user_agent=cfg["http"]["user_agent"],
        default_subject=cfg["defaults"]["subject"],
        default_intro=cfg["defaults"]["intro"],
        exact_exclude_paths_text="\n".join(cfg["filtering"]["exact_exclude_paths"]),
        exclude_texts_text="\n".join(cfg["filtering"]["exclude_texts"]),
        last_3_months_days=str(cfg["filtering"]["last_3_months_days"]),
        watch_sites_text="\n".join(cfg["watch"]["sites"]),
        watch_keywords_text="\n".join(cfg["watch"]["keywords"]),
        # Read-only derived paths
        paths=paths,
    )
    return Response.html(html)


def post_config(req: Request, _params: dict[str, str] | None = None) -> Response:
    form = _parse_post_form(req)
    cfg = _load_config_yaml()

    # ---- Update YAML (non-secrets) ----
    cfg["tsl"]["base_url"] = (form.get("base_url") or [cfg["tsl"]["base_url"]])[0].strip() or cfg[
        "tsl"
    ]["base_url"]
    cfg["tsl"]["news_path"] = (form.get("news_path") or [cfg["tsl"]["news_path"]])[
        0
    ].strip() or cfg["tsl"]["news_path"]

    cfg["server"]["host"] = (form.get("host") or [cfg["server"]["host"]])[0].strip() or cfg[
        "server"
    ]["host"]
    cfg["server"]["port"] = _to_int(
        (form.get("port") or [str(cfg["server"]["port"])])[0], int(cfg["server"]["port"])
    )

    cfg["http"]["user_agent"] = (form.get("user_agent") or [cfg["http"]["user_agent"]])[
        0
    ].strip() or cfg["http"]["user_agent"]

    cfg["defaults"]["subject"] = (form.get("default_subject") or [cfg["defaults"]["subject"]])[0]
    cfg["defaults"]["intro"] = (form.get("default_intro") or [cfg["defaults"]["intro"]])[0]

    cfg["filtering"]["exact_exclude_paths"] = _lines_to_list(
        (form.get("exact_exclude_paths") or [""])[0]
    )
    cfg["filtering"]["exclude_texts"] = _lines_to_list((form.get("exclude_texts") or [""])[0])
    cfg["filtering"]["last_3_months_days"] = _to_int(
        (form.get("last_3_months_days") or ["92"])[0], 92
    )

    cfg["watch"]["sites"] = _lines_to_list((form.get("watch_sites") or [""])[0])
    cfg["watch"]["keywords"] = _lines_to_list((form.get("watch_keywords") or [""])[0])

    _dump_config_yaml(cfg)

    # ---- Update .env secrets only if provided (blank means "keep") ----
    updates: dict[str, str] = {}

    new_openai = (form.get("openai_api_key") or [""])[0].strip()
    if new_openai:
        updates["OPENAI_API_KEY"] = new_openai

    new_tinymce = (form.get("tinymce_api_key") or [""])[0].strip()
    if new_tinymce:
        updates["TINYMCE_API_KEY"] = new_tinymce

    if updates:
        secrets_env.update_env(updates)

    status = quote("Saved.")
    return Response.redirect(f"/config?status={status}")
