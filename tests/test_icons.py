"""Conversion des icônes DDS et PNG en WebP (3.4, 4.12)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from fspassion import icons


def make(fmt: str, size: int, mode: str = "RGB") -> bytes:
    im = Image.new(mode, (size, size), (180, 90, 20) if mode == "RGB" else (180, 90, 20, 128))
    buf = io.BytesIO()
    if fmt == "DDS":
        im.save(buf, "DDS", pixel_format="DXT5" if mode == "RGBA" else "DXT1")
    else:
        im.save(buf, fmt)
    return buf.getvalue()


@pytest.mark.parametrize("fmt, size", [("DDS", 512), ("DDS", 256), ("PNG", 512), ("PNG", 256)])
def test_convert_keeps_resolution(tmp_path, fmt, size):
    w, h = icons.convert_icon(make(fmt, size), tmp_path, "FS25_X-1-2")
    assert (w, h) == (size, size)
    with Image.open(tmp_path / "FS25_X-1-2.webp") as big:
        assert big.size == (size, size)
        assert big.format == "WEBP"
    with Image.open(tmp_path / "FS25_X-1-2-small.webp") as small:
        assert small.size == (96, 96)


def test_alpha_kept_when_needed(tmp_path):
    icons.convert_icon(make("DDS", 256, "RGBA"), tmp_path, "a")
    with Image.open(tmp_path / "a.webp") as im:
        assert im.mode == "RGBA"
    icons.convert_icon(make("PNG", 256), tmp_path, "b")
    with Image.open(tmp_path / "b.webp") as im:
        assert im.mode == "RGB"


def test_invalid_icon_raises(tmp_path):
    with pytest.raises(Exception):  # noqa: B017 - toute erreur de Pillow convient
        icons.convert_icon(b"not an image", tmp_path, "c")
    assert not (tmp_path / "c.webp").exists()


def test_names():
    assert icons.icon_basename("FS25_Hof", 1234, 1700000000.7) == "FS25_Hof-1234-1700000000-r512"
    assert icons.small_name("x") == "x-small.webp"
