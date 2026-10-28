"""Version 0.7.4 : retouches (infobulle des adresses, liste des langues sur la
ligne du titre, technique de la fenêtre dans « Application »)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_tooltip_wraps_long_urls():
    css = _read("ui", "css", "dialogs.css")
    rule = css.split(".tooltip {", 1)[1].split("}", 1)[0]
    assert "overflow-wrap: anywhere;" in rule


def test_language_list_on_title_line_and_over_the_rest():
    js = _read("ui", "js", "settings.js")
    css = _read("ui", "css", "dialogs.css")
    assert "group('languages', 'settings.language.title', buildLanguage(), '', languageSelect(changeLanguage))" in js
    assert "languageSelect(changeLanguage),\n" not in js.split("function buildLanguage()", 1)[1].split("}", 1)[0]
    rule = css.split(".lang-select-box > .lang-list.lang-list-vertical {", 1)[1].split("}", 1)[0]
    assert "position: absolute;" in rule and "max-height: 360px;" in rule
    # Échap ferme la liste seule (avant la fenêtre des Paramètres) ; la molette la fait défiler.
    assert "window.addEventListener('keydown', onKey, true)" in js
    assert "[data-own-scroll]" in _read("ui", "js", "snapscroll.js")


def test_window_mode_moved_to_application_page():
    js = _read("ui", "js", "settings.js")
    app_page = js.split("function buildApp()", 1)[1].split("\n}\n", 1)[0]
    about = js.split("function buildAbout()", 1)[1].split("\n}\n", 1)[0]
    assert "windowModeGroup()" in app_page
    assert "window_mode" not in about
    assert re.search(r"group\('app-window', 'settings\.about\.window_mode',[\s\S]*?'', seg\)", js)
