from __future__ import annotations

from pathlib import Path

import pytest

from services import preview_service as svc


def test_load_preview_image_blocks_traversal(tmp_path: Path):
    # app_dir structure
    app_dir = tmp_path
    (app_dir / "output" / "preview").mkdir(parents=True)

    # attempt to escape preview dir
    with pytest.raises(ValueError):
        svc.load_preview_image(app_dir, "/preview/images/../secrets.txt")


def test_load_preview_image_returns_none_if_missing(tmp_path: Path):
    app_dir = tmp_path
    (app_dir / "output" / "preview" / "images").mkdir(parents=True)

    fb = svc.load_preview_image(app_dir, "/preview/images/missing.jpg")
    assert fb is None


def test_load_preview_image_reads_file_and_sets_content_type(tmp_path: Path):
    app_dir = tmp_path
    img_dir = app_dir / "output" / "preview" / "images"
    img_dir.mkdir(parents=True)

    p = img_dir / "x.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n...")

    fb = svc.load_preview_image(app_dir, "/preview/images/x.png")
    assert fb is not None
    assert fb.content_type == "image/png"
    assert fb.data.startswith(b"\x89PNG")
