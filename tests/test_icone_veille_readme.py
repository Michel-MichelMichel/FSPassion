"""0.9.1 : visite guidée complétée, icône de l'application, dormance pendant le
jeu, textes « développement » retirés, icône des maps, README en anglais."""

from __future__ import annotations

import importlib.util
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "ui" / "js"
CSS = ROOT / "ui" / "css"


def _read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def _lang(code: str) -> dict:
    return json.loads(_read("lang", f"{code}.json"))


def _tour_ids() -> list[str]:
    src = _read("ui", "js", "tour.js")
    block = src[src.index("const STEPS = ["):]
    return re.findall(r"^    id: '([a-z0-9]+)',", block, re.M)


# -- visite guidée ----------------------------------------------------------------

def test_tour_has_downloads_and_close_steps():
    ids = _tour_ids()
    assert ids.index("downloads") == ids.index("list1") + 1
    assert ids.index("close") == ids.index("end") - 1
    for code in ("fr", "en"):
        tour = _lang(code)["tour"]
        for key in ("caption", "body", "found"):
            assert tour["downloads"][key], (code, key)
        for key in ("caption", "body", "tip_close", "tip_more", "tip_icon"):
            assert tour["close"][key], (code, key)
    assert "find-new-btn" in _read("ui", "js", "library.js")
    # Aperçu de la barre des tâches : flèche des icônes cachées, horloge, icône FS.
    js = _read("ui", "js", "tour.js")
    assert "/assets/brand/tray.png" in js and "tour-tb-more" in js and "tour-tb-clock" in js


def test_drag_and_drop_ghosts_twice_slower():
    js = _read("ui", "js", "tour.js")
    assert "const dur = 2200;" in js


def test_tour_bubbles_text_centred():
    css = _read("ui", "css", "tour.css")
    kbd = re.search(r"\.tour-kbd \{([^}]*)\}", css).group(1)
    assert "padding: 3px 7px 0;" in kbd and "vertical-align: 1px;" in kbd
    label = re.search(r"\.tour-flow-label \{([^}]*)\}", css).group(1)
    assert "padding: 7px 12px 4px;" in label


# -- icône de l'application ---------------------------------------------------------

def _load_build():
    spec = importlib.util.spec_from_file_location("fsp_build", ROOT / "tools" / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_icon_written_from_tray_png(tmp_path):
    from PIL import Image

    build = _load_build()
    assert build.ICON_SOURCE == ROOT / "assets" / "brand" / "tray.png"
    out = tmp_path / "fspassion.ico"
    with Image.open(build.ICON_SOURCE) as im:
        build.write_ico(im.convert("RGBA"), out)
    data = out.read_bytes()
    _, kind, count = struct.unpack("<HHH", data[:6])
    assert kind == 1 and count == len(build.ICON_SIZES)
    for i in range(count):
        w, _h, _c, _r, _p, bpp, size, offset = struct.unpack("<BBBBHHII", data[6 + 16 * i:22 + 16 * i])
        chunk = data[offset:offset + size]
        if w == 0:  # 256 px : PNG
            assert chunk.startswith(b"\x89PNG")
        else:  # petites tailles : BMP 32 bits
            assert struct.unpack("<I", chunk[:4])[0] == 40 and bpp == 32
    with Image.open(out) as ico:
        assert (16, 16) in ico.ico.sizes() and (256, 256) in ico.ico.sizes()
        small = ico.ico.getimage((32, 32)).convert("RGBA")
        assert small.getpixel((16, 16))[1] > 200  # vert lime au centre
    src = _read("tools", "build.py")
    assert "refresh_icon_cache()" in src and "ie4uinit.exe" in src


def test_maps_use_map_icon():
    for name in ("modops.js", "sidelists.js", "hovercard.js", "actions.js", "downloads.js", "header.js", "library.js"):
        assert "'farm'" not in _read("ui", "js", name), name


# -- dormance pendant le jeu --------------------------------------------------------

def test_sleep_when_hidden_and_wake():
    ops = _read("src", "fspassion", "window_ops.py")
    assert "TrySuspendAsync" in ops and "MemoryUsageTargetLevel" in ops and "core.Resume()" in ops
    assert "fsp-wake" in ops
    assert "form.Activated += on_show" in ops
    assert "native.sleep_later(3.0)" in _read("src", "fspassion", "core.py")
    assert "native.sleep_later()" in _read("src", "fspassion", "app.py")
    assert "'fsp-wake'" in _read("ui", "js", "main.js")


def test_sleep_is_harmless_outside_windows():
    from fspassion.window_ops import NativeWindow

    w = NativeWindow()
    w.sleep_later()  # aucune fenêtre : rien ne se passe
    assert w.asleep is False


# -- textes -------------------------------------------------------------------------

def test_no_development_version_in_texts():
    for code in ("fr", "en"):
        text = _read("lang", f"{code}.json")
        assert "lancer_dev" not in text
        assert "Version de développement" not in text and "Development version" not in text


def test_rename_warning_speaks_of_game_savegames():
    fr = _lang("fr")["rename"]
    assert fr["warning_save"].startswith("Dans le jeu,")
    assert _lang("en")["rename"]["warning_save"].startswith("In the game,")


# -- README -------------------------------------------------------------------------

def test_readme_english_with_translations():
    md = _read("README.md")
    assert md.startswith("# FS Passion")
    assert "**English** ·" in md and "Français" in md
    links = re.findall(r"\((readme/README\.[^)]+\.md)\)", md)
    assert len(links) == 25
    for link in links:
        assert (ROOT / link).is_file(), link
