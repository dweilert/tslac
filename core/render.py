from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

_BASE_DIR = Path(__file__).resolve().parent.parent
_TEMPLATES_DIR = _BASE_DIR / "templates_j2"


_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    # trim blocks helps keep HTML clean-ish
    trim_blocks=True,
    lstrip_blocks=True,
)

_env.filters["urlencode"] = lambda s: urllib.parse.quote(str(s), safe="")


def render(template_name: str, **context: object) -> bytes:
    tmpl = _env.get_template(template_name)
    return tmpl.render(**context)


def tojson_filter(x) -> Markup:
    return Markup(json.dumps(x, ensure_ascii=False))


_env.filters["tojson"] = tojson_filter
