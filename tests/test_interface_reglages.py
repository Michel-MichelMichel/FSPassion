"""Version 0.6.6 : retouches de l'interface et réinitialisation des thèmes.

Les contrôles d'interface lisent les fichiers : c'est ce que livre l'application.
"""

from __future__ import annotations

import re
from pathlib import Path

from fspassion import config, fsutil
from fspassion.core import SETTABLE, THEME_KEYS, Core
from fspassion.events import EventBus

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _start(core: Core) -> None:
    core.settings.set("first_detection_done", True)
    core.startup()
    core.shutdown()


# -- lanceur, en-tête, pied de page, paramètres --------------------------------

def test_lancer_dev_opens_the_app_only():
    assert "-m fspassion --dev --no-browser" in _read("lancer_dev.bat")


def test_version_menu_is_centered_under_its_icon():
    css = _read("ui", "css", "layout.css")
    assert ".version-pick > .menu.version-menu" in css
    assert "translate: -50% 0" in css
    # L'ancien sélecteur ne trouvait plus le menu : il ne doit pas revenir.
    assert ".topbar > .version-pick > .menu" not in css


def test_light_version_readable():
    # Le trajet du logo GitHub est revu en 0.6.7 (test_lancement_serveur).
    css = _read("ui", "css", "layout.css")
    assert ':root[data-mode="light"] .footer-version' in css


def test_settings_pages_have_no_empty_band_at_the_bottom():
    css = _read("ui", "css", "dialogs.css")
    block = re.search(r"\.settings-pane \{([^}]*)\}", css)
    assert block and "padding: 26px 0 0;" in block.group(1)


def test_theme_swatches_have_a_fixed_distance():
    css = _read("ui", "css", "dialogs.css")
    assert "grid-template-columns: repeat(auto-fill, 128px)" in css
    assert re.search(r"\.swatch \{[^}]*width: 128px", css)


def test_side_note_has_its_own_line_under_the_title():
    js = _read("ui", "js", "sidelists.js")
    assert "this.head, this.noteEl, this.emptyEl" in js
    assert "this.countEl, this.noteEl" not in js
    assert ".side-note:empty { display: none; }" in _read("ui", "css", "lists.css")


def test_donation_logos_keep_their_colours():
    js = _read("ui", "js", "settings.js")
    assert "#635bff" in js
    brand = ROOT / "assets" / "brand"
    for name in ("Buymeacoffee-icon.svg", "Buymeacoffee-text.svg", "Stripe.svg"):
        assert (brand / name).is_file(), name
        assert name in js
    # Buy Me a Coffee en images, pas en masque : la couleur du fichier est gardée.
    assert "brand-logo-img" in js
    assert ".brand-img" in _read("ui", "css", "dialogs.css")


# -- réinitialisation des thèmes ----------------------------------------------

def test_theme_reset_restores_defaults_in_development(monkeypatch, tmp_path):
    ui = tmp_path / "ui"
    ui.mkdir()
    fsutil.atomic_write_json(ui / "themes.json", {"themes": [{"id": "modifie"}]})
    monkeypatch.setattr(config, "ui_dir", lambda: ui)
    core = Core(dev=True, bus=EventBus())
    core.settings.update({"theme": "nord", "theme_loop": True, "light_effects": False, "reduce_motion": True})

    out = core.reset_themes()

    assert out["settings"] == {"theme": "gruvbox-light", "theme_loop": False, "light_effects": True, "reduce_motion": None}
    assert out["themes_restored"] is True
    ids = [t.get("id") for t in fsutil.read_json(ui / "themes.json", {})["themes"]]
    assert "lime" in ids and "modifie" not in ids


def test_theme_reset_outside_development_keeps_the_definitions(monkeypatch, tmp_path):
    ui = tmp_path / "ui"
    ui.mkdir()
    fsutil.atomic_write_json(ui / "themes.json", {"themes": [{"id": "modifie"}]})
    monkeypatch.setattr(config, "ui_dir", lambda: ui)
    core = Core(dev=False, bus=EventBus())

    out = core.reset_themes()

    assert out["themes_restored"] is False
    assert fsutil.read_json(ui / "themes.json", {})["themes"] == [{"id": "modifie"}]


def test_theme_reset_is_wired_to_the_interface():
    assert set(THEME_KEYS) <= set(SETTABLE)
    # La route n'a plus d'appelant dans l'interface : elle est retirée du serveur.
    assert "/api/themes/reset" not in _read("src", "fspassion", "server.py")
    assert "/api/themes/reset" not in _read("ui", "js", "settings.js")


# 0.7.0 : invitation au don supprimée.
