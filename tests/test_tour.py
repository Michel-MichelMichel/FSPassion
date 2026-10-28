"""0.9.0 : tour guidé (ampoule de l'en-tête) et versions absentes non sélectionnables."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fspassion import config
from fspassion.core import SETTABLE

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "ui" / "js"
CSS = ROOT / "ui" / "css"


def _lang(code: str) -> dict:
    return json.loads((ROOT / "lang" / f"{code}.json").read_text(encoding="utf-8"))


def _tour_ids() -> list[str]:
    src = (JS / "tour.js").read_text(encoding="utf-8")
    block = src[src.index("const STEPS = ["):]
    return re.findall(r"^    id: '([a-z0-9]+)',", block, re.M)


def test_tour_files_are_loaded():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    assert 'href="css/tour.css"' in html
    header = (JS / "header.js").read_text(encoding="utf-8")
    assert "tourButton()" in header
    main = (JS / "main.js").read_text(encoding="utf-8")
    assert "initTour(app)" in main and "maybeShowTourHint()" in main


def test_tour_steps_have_texts_in_every_language():
    ids = _tour_ids()
    # 0.9.1 : étapes « downloads » et « close » ajoutées.
    assert ids == ["versions", "parties", "tools", "common", "apply", "buttons", "list1", "downloads", "list2",
                   "list3", "select", "move", "keys", "close", "end"]
    for code in ("fr", "en"):
        tour = _lang(code)["tour"]
        for sid in ids:
            assert tour[sid]["caption"], (code, sid)
            assert tour[sid]["body"], (code, sid)
        assert tour["hint"]["caption"] and tour["hint"]["start"] and tour["hint"]["later"]
        rows = tour["keys"]["rows"]
        assert len(rows) >= 10 and all(r["k"] and r["d"] for r in rows)
        assert len(tour["demo"]["parties"]) == 3 and len(tour["demo"]["mods"]) == 6


def test_tour_hint_setting():
    assert SETTABLE["tour_hint_shown"] is bool
    assert config.default_settings()["tour_hint_shown"] is False


def test_handwritten_font_present():
    css = (CSS / "tour.css").read_text(encoding="utf-8")
    files = re.findall(r'url\("/assets/(fonts/Caveat-[a-z-]+\.woff2)"\)', css)
    assert len(files) == 4
    for f in files:
        assert (ROOT / "assets" / f).is_file(), f
    assert (ROOT / "assets" / "fonts" / "OFL-Caveat.txt").is_file()


def test_absent_versions_are_not_selectable():
    src = (JS / "header.js").read_text(encoding="utf-8")
    assert "const absent = !coming && !ver.installed && !ver.ready;" in src
    assert "const disabled = coming || (absent && !current);" in src
    css = (CSS / "layout.css").read_text(encoding="utf-8")
    # Pas d'agrandissement au survol d'une version inactive.
    assert '.version-item[aria-disabled="true"]:hover .game-logo { scale: 1; }' in css
    for code in ("fr", "en"):
        assert _lang(code)["versions"]["absent_help"]


def test_compact_header_has_room_for_the_bulb():
    css = (CSS / "layout.css").read_text(encoding="utf-8")
    assert "grid-template-columns: repeat(7, auto);" in css
