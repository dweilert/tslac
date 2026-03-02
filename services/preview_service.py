from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import preview_generator


@dataclass(frozen=True)
class FileBytes:
    data: bytes
    content_type: str


def build_preview_html() -> bytes:
    return preview_generator.build_preview_html()


def load_preview_index(app_dir: Path) -> bytes | None:
    p = app_dir / "output" / "preview" / "index.html"
    return p.read_bytes() if p.exists() else None


def load_preview_image(app_dir: Path, request_path: str) -> FileBytes | None:
    prefix = "/preview/"
    if not request_path.startswith(prefix):
        raise ValueError("Invalid preview path")

    rel = request_path[len(prefix) :]  # e.g. 'images/xxx.jpg'
    rel = rel.lstrip("/")  # defensive

    # Enforce we only serve from images/
    if not rel.startswith("images/"):
        raise ValueError("Invalid image path")

    # Reject any traversal segments explicitly
    rel_path = Path(rel)
    if any(part in ("..", "") for part in rel_path.parts):
        raise ValueError("Invalid image path")

    base = (app_dir / "output" / "preview").resolve()
    img_path = (base / rel_path).resolve()

    # Containment check (Py 3.12 has is_relative_to)
    if not img_path.is_relative_to(base):
        raise ValueError("Invalid image path")

    if not img_path.exists():
        return None

    data = img_path.read_bytes()
    ct = _content_type_for_suffix(img_path.suffix.lower())
    return FileBytes(data=data, content_type=ct)


def _content_type_for_suffix(suf: str) -> str:
    if suf == ".png":
        return "image/png"
    if suf == ".webp":
        return "image/webp"
    if suf == ".gif":
        return "image/gif"
    if suf == ".svg":
        return "image/svg+xml"
    # default
    return "image/jpeg"
    # svg
