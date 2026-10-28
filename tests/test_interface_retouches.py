"""0.7.9 : retouches après les thèmes définitifs.

- liste des langues sobre ; molette des Paramètres rangée par rangée dans les
  thèmes ; atelier de thèmes moins haut, avec ascenseur ;
- variante 300 px des icônes seulement pour FS25 et FS28 ;
- redimensionnement : plus de fiches de mods qui s'ouvrent au hasard, en-tête
  stable (hystérésis, logo de la version qui glisse sans sauter).
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image

from fspassion import icons

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _png(size: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (size, size), (120, 160, 90)).save(buf, "PNG")
    return buf.getvalue()


def test_language_list_is_plain():
    css = _read("ui", "css", "dialogs.css")
    block = css[css.index("0.7.9 : liste des langues sobre"):]
    rule = re.search(r"\.lang-list-vertical \.lang-item \{([^}]*)\}", block).group(1)
    assert "border-radius: 0" in rule and "background: transparent" in rule and "box-shadow: none" in rule
    assert "padding: 3px" in rule


def test_settings_wheel_stops_at_each_row_of_theme_swatches():
    js = _read("ui", "js", "settings.js")
    targets = js[js.index("const SNAP_TARGETS"):js.index("].join(', ');")]
    assert "'.swatch'" in targets and ".swatch-groups > .set-group-title" in targets


def test_atelier_scrolls_and_keeps_its_buttons_visible():
    css = _read("ui", "css", "dialogs.css")
    assert re.search(r"\.atelier \{[^}]*max-height: min\(640px", css)
    assert re.search(r"\.atelier-body \{[^}]*overflow-y: auto", css)
    assert ".atelier > .at-actions" in css
    js = _read("ui", "js", "atelier.js")
    assert "keepScroll" in js


def test_medium_icons_only_for_fs25_and_fs28(tmp_path):
    assert icons.MEDIUM_VERSIONS == {"FS25", "FS28"}
    assert icons.has_medium("FS25") and icons.has_medium("FS28")
    for vid in ("FS2011", "FS2013", "FS15", "FS17", "FS19", "FS22"):
        assert not icons.has_medium(vid)
    # FS22 : icône d'origine de 256 px, pas de variante moyenne.
    icons.convert_icon(_png(256), tmp_path, "a", medium=False)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a-small.webp", "a.webp"]
    # FS25 : icône de 1024 px, trois variantes (512, 300, 96).
    icons.convert_icon(_png(1024), tmp_path, "b", medium=True)
    assert (tmp_path / "b-medium.webp").is_file()
    with Image.open(tmp_path / "b.webp") as im:
        assert im.size == (512, 512)
    with Image.open(tmp_path / "b-medium.webp") as im:
        assert im.size == (300, 300)
    assert icons.icon_names("a", False) == ("a.webp", "a-small.webp")
    api = _read("ui", "js", "api.js")
    assert "new Set(['FS25', 'FS28'])" in api


def test_no_hover_cards_while_resizing():
    js = _read("ui", "js", "hovercard.js")
    assert "is-resizing" in js and "window.addEventListener('resize', onResize)" in js
    assert "html.is-resizing .tile" in _read("ui", "css", "lists.css")
    assert "is-resizing" in _read("ui", "js", "sidelists.js")


def test_header_is_stable_while_resizing():
    js = _read("ui", "js", "header.js")
    assert "const RELAX = 48;" in js
    assert "wasCompact && slack < RELAX" in js  # 0.8.0 : marge lue dans les espaces
    assert "function centerVersion()" in js and "vz.style.translate" in js
