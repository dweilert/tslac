from __future__ import annotations

from pathlib import Path
from typing import Any
from markupsafe import Markup
from jinja2 import Environment, FileSystemLoader, select_autoescape

import urllib.parse
import json


_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates_j2"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    # trim blocks helps keep HTML clean-ish
    trim_blocks=True,
    lstrip_blocks=True,
)

_env.filters["urlencode"] = lambda s: urllib.parse.quote(str(s), safe="")

def render(template_name: str, **ctx: Any) -> str:
    tmpl = _env.get_template(template_name)
    return tmpl.render(**ctx)

def tojson_filter(x) -> Markup:
    return Markup(json.dumps(x, ensure_ascii=False))

_env.filters["tojson"] = tojson_filter