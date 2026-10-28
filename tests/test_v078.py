"""0.7.8 : thèmes définitifs.

- thèmes bicolores (Lime, Blanc, Jade, Cuivre ; le rouge est retiré) : la
  couleur sombre partout, la couleur dominante dans les textes et les icônes,
  des contours fins et des lueurs animées à la place des nuances de fond ;
- thèmes inspirés de thèmes populaires, chacun en sombre et en clair, avec
  les couleurs officielles de leurs fonds (surfaces) ;
- effet néon (Synthwave '84), réglable dans l'atelier.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fspassion import config
from fspassion.config import Settings

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def _themes() -> dict[str, dict]:
    data = json.loads(_read("ui", "themes.json"))
    return {th["id"]: th for th in data["themes"]}


HEX = re.compile(r"^#[0-9A-F]{6}$")


def test_default_themes_are_complete():
    """Thèmes livrés (réinitialisation, 0.6.6). 0.8.0 : plus d'égalité exigée
    avec ui/themes.json, que l'atelier de thèmes peut modifier sur une installation
    de développement (la fabrication échouait après un réglage d'atelier) ; on
    vérifie qu'ils sont complets."""
    default = json.loads(_read("src", "fspassion", "data", "themes_default.json"))["themes"]
    ids = [th["id"] for th in default]
    assert len(ids) == 20 and len(set(ids)) == 20 and "red" not in ids
    for th in default:
        assert th.get("style") in ("duo", "palette") and HEX.match(th["dark"]) and HEX.match(th["light"])


def test_two_color_themes():
    by_id = _themes()
    duo = [th for th in by_id.values() if th.get("style") == "duo"]
    assert [th["id"] for th in duo] == ["lime", "blue", "jade", "cuivre"]
    assert "red" not in by_id
    # Blanc sur fond bleu #272B3E (à la place du rouge).
    assert by_id["blue"]["dark"] == "#272B3E" and by_id["blue"]["light"] == "#FFFFFF"
    for th in duo:
        assert "surfaces" not in th and "accents" not in th and "gradient" not in th
        assert HEX.match(th["dark"]) and HEX.match(th["light"])


def test_popular_themes_have_a_dark_and_a_light_twin():
    by_id = _themes()
    palette = [th for th in by_id.values() if th.get("style") == "palette"]
    assert len(palette) == 16
    for th in palette:
        twin = by_id[th["pair"]]
        assert twin["pair"] == th["id"]
        assert twin.get("mode", "dark") != th.get("mode", "dark")
        assert 2 <= len(th["surfaces"]) <= 4 and th["dark"] == th["surfaces"][0]
        assert len(th["accents"]) == 4 and len(th["gradient"]) == 2
        assert 1 <= len(th["texts"]) <= 4 and th["texts"][0] == th["text"]
        for c in [th["dark"], th["light"], th["text"], *th["surfaces"], *th["texts"], *th["accents"], *th["gradient"]]:
            assert HEX.match(c), (th["id"], c)
    families = {th["id"].split("-")[0] for th in palette}
    assert families == {"catppuccin", "nord", "solarized", "monokai", "gruvbox", "dracula", "tokyo", "synthwave"}


def test_official_surfaces_from_your_references():
    """Fonds officiels, de l'extérieur vers l'intérieur (Catppuccin Mocha)."""
    by_id = _themes()
    assert by_id["catppuccin-mocha"]["surfaces"][:3] == ["#11111B", "#181825", "#1E1E2E"]  # Crust, Mantle, Base
    assert by_id["catppuccin-latte"]["surfaces"][:3] == ["#9CA0B0", "#ACB0BE", "#BCC0CC"]  # Overlay 0, Surface 2, Surface 1
    assert by_id["nord"]["surfaces"] == ["#2E3440", "#3B4252", "#434C5E", "#4C566A"]
    assert by_id["nord-snow"]["surfaces"] == ["#D8DEE9", "#E5E9F0", "#ECEFF4"]


def test_official_palettes_of_the_new_themes():
    by_id = _themes()
    assert by_id["solarized-dark"]["surfaces"][:2] == ["#002B36", "#073642"]  # base03, base02
    assert by_id["solarized-light"]["surfaces"][:2] == ["#EEE8D5", "#FDF6E3"]  # base2, base3
    assert by_id["monokai-pro"]["surfaces"][:3] == ["#19181A", "#221F22", "#2D2A2E"]
    assert by_id["monokai-pro"]["accents"] == ["#FC9867", "#A9DC76", "#78DCE8", "#AB9DF2"]
    assert by_id["monokai-pro-light"]["surfaces"] == ["#D3CDCC", "#EDE7E5", "#FAF4F2"]
    assert by_id["gruvbox-dark"]["surfaces"] == ["#1D2021", "#282828", "#32302F", "#3C3836"]
    assert by_id["gruvbox-light"]["accents"] == ["#AF3A03", "#79740E", "#076678", "#8F3F71"]
    assert by_id["dracula-van-helsing"]["dark"] == "#0B0D0F"  # hsl(210, 15 %, 5 %)
    assert by_id["dracula-alucard"]["surfaces"] == ["#CFCFDE", "#DCDEEF", "#F5F5F5"]
    assert by_id["tokyo-night"]["surfaces"][:2] == ["#16161E", "#1A1B26"]
    assert by_id["tokyo-night-light"]["text"] == "#343B58"
    assert by_id["synthwave-84"]["gradient"] == ["#FC28A8", "#03EDF9"]


def test_neon_effect():
    by_id = _themes()
    assert by_id["synthwave-84"]["neon"] > 0 and by_id["synthwave-84-light"]["neon"] > 0
    css = _read("ui", "css", "themes.css")
    assert ":root[data-neon]" in css and "text-shadow" in css and "drop-shadow" in css
    js = _read("ui", "js", "theme.js")
    assert "root.dataset.neon" in js and "--neon" in js
    atelier = _read("ui", "js", "atelier.js")
    assert "rangeRow(t('atelier.neon'), 'neon')" in atelier


def test_two_color_style_uses_outlines_and_running_glow():
    css = _read("ui", "css", "themes.css")
    # Plus aucun fond plus clair : voiles transparents, surfaces = fond.
    assert re.search(r':root\[data-style="duo"\] \{[^}]*--fill-2: transparent;', css)
    assert re.search(r':root\[data-style="duo"\] \{[^}]*--surface-1: var\(--bg\);', css)
    # Textes dans la couleur dominante.
    assert re.search(r':root\[data-style="duo"\] \{[^}]*--text-1: var\(--fg\);', css)
    # Lueur le long des contours, arrêtée par les réglages.
    assert ".glow-ring" in css and "@keyframes glow-run" in css
    assert "html.fx-still .glow-ring" in css and "html.is-idle" in css
    glow = _read("ui", "js", "glow.js")
    assert "MutationObserver" in glow and "ResizeObserver" in glow
    assert "initGlow" in _read("ui", "js", "main.js")
    assert "set-frame-glow" in _read("ui", "js", "settings.js")
    assert 'href="css/themes.css"' in _read("ui", "index.html")


def test_palette_style_uses_official_surfaces():
    css = _read("ui", "css", "themes.css")
    assert ":root[data-surfaces]" in css
    for var in ("--surf-window", "--surf-list", "--surf-section", "--surf-sub"):
        assert var in css
    js = _read("ui", "js", "theme.js")
    assert "export function themeSurfaces" in js and "root.dataset.surfaces" in js


def test_readable_color_direction_follows_luminance():
    """Un fond clair grisé (Latte, luminance 0,35) assombrit les textes."""
    js = _read("ui", "js", "theme.js")
    assert "const toward = luminance(base) < luminance(back) ? 0 : 255;" in js


def test_red_theme_choice_moves_to_blue(tmp_path):
    assert config.RENAMED_THEMES == {"red": "blue"}
    (tmp_path / "settings.json").write_text(json.dumps({"theme": "red"}), encoding="utf-8")
    s = Settings(tmp_path / "settings.json")
    assert s.get("theme") == "blue"


def test_swatch_groups_and_texts():
    settings = _read("ui", "js", "settings.js")
    assert "group_duo" in settings and "paintSwatch" in settings
    for code in ("fr", "en"):
        strings = json.loads(_read("lang", f"{code}.json"))
        assert strings["themes"]["blue"]
        assert "red" not in strings["themes"]
        for key in ("style", "neon", "surface_1", "surface_4", "text_n"):
            assert strings["atelier"][key]
        assert strings["settings"]["theme"]["group_duo"]
