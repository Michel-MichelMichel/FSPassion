"""Version 0.7.2 : redimensionnement de la fenêtre.

- la liste 1 garde 2 colonnes de tuiles de 300 px sans réduire l'échelle ;
- l'en-tête passe sur 2 lignes quand la fenêtre est étroite ;
- les marges de la fenêtre Paramètres diminuent avant qu'elle ne rétrécisse ;
- l'échelle ne se réduit qu'en dessous de 1140 px (ou de la largeur minimale
  de l'en-tête sur 2 lignes).

Les contrôles d'interface lisent les fichiers : c'est ce que livre l'application.
"""

from __future__ import annotations

import re
from pathlib import Path

from fspassion import app

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _num(pattern: str, text: str) -> int:
    m = re.search(pattern, text)
    assert m, pattern
    return int(m.group(1))


def test_scale_threshold_keeps_two_columns_of_300px_tiles():
    scale = _read("ui", "js", "scale.js")
    lib = _read("ui", "js", "library.js")
    layout = _read("ui", "css", "layout.css")
    min_w = _num(r"export const DESIGN_MIN_W = (\d+);", scale)
    tile = _num(r"const TILE_W = (\d+);", lib)
    gap = _num(r"const MIN_GAP_X = (\d+);", lib)
    pad = _num(r"const PAD_X = (\d+);", lib)
    side = _num(r"grid-template-columns: minmax\(0, 1fr\) (\d+)px;", layout)
    assert tile == 300
    assert "cols = Math.max(2," in lib
    # Fenêtre : marges 36 + 24, espace 16, colonne de droite, ascenseur 12 ;
    # grille : 8 px réservés et 2 marges de PAD_X.
    needed = 36 + 24 + 16 + side + 12 + 8 + 2 * pad + 2 * tile + gap
    assert needed <= min_w < 1600
    assert "setContentMinWidth" in scale and "Math.max(DESIGN_MIN_W, contentMinW)" in scale


def test_header_goes_on_two_lines_when_narrow():
    js = _read("ui", "js", "header.js")
    css = _read("ui", "css", "layout.css")
    assert "export function fitHeader()" in js
    # 0.7.9 : avec hystérésis (test_interface_retouches).
    assert "classList.toggle('is-compact', compact)" in js
    assert "setContentMinWidth(naturalWidth(cs))" in js
    assert "window.addEventListener('resize', fitHeader)" in js
    # « Partie en cours » sur la même ligne que le menu ; le reste en dessous.
    assert ".topbar.is-compact .party-label" in css
    assert ".topbar.is-compact .party-block" in css and "grid-column: 1 / -1;" in css
    compact_h = _num(r"\.topbar\.is-compact \{ height: (\d+)px; \}", css)
    normal_h = _num(r"\.topbar \{[^}]*height: (\d+)px;", css)
    assert normal_h < compact_h <= normal_h + 40


def test_settings_margins_shrink_before_the_window():
    css = _read("ui", "css", "dialogs.css")
    assert re.search(r"\.dlg-settings \{[^}]*width: 1240px;", css)
    assert "padding-inline: clamp(12px, calc((100% - 1240px) / 2), 40px)" in css
    assert ".dlg-backdrop:has(> .dlg-settings)" in css


def test_list1_head_and_action_bar_fit_a_narrow_list():
    css = _read("ui", "css", "lists.css")
    assert re.search(r"\.lib-head \{[^}]*flex-wrap: wrap;", css)
    assert ".ab-sort.is-grid" in css
    assert "function fitBar()" in _read("ui", "js", "actionbar.js")


def test_window_can_be_narrower_than_before():
    assert app.MIN_WINDOW == (960, 720)
    assert "const minW = 960 *" in _read("ui", "js", "frame.js")
