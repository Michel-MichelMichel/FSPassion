"""Sens des flèches : ce qui sort de FS Passion monte (Exporter : file-up),
ce qui y entre descend (Importer, téléchargements, mises à jour)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "ui" / "js"


def _src(name: str) -> str:
    return (JS / name).read_text(encoding="utf-8")


def _icons_before(text: str, key: str) -> set[str]:
    """Icônes des boutons dont le texte est la clé `key`."""
    return set(re.findall(r"icon\('([a-z0-9-]+)'[^)]*\)[^\n]*" + re.escape(key), text))


def test_export_goes_up_import_goes_down():
    settings, backup, stopuse = _src("settings.js"), _src("backup.js"), _src("stopuse.js")
    assert _icons_before(settings, "settings.backup.export") == {"file-up"}
    assert _icons_before(stopuse, "settings.backup.export") == {"file-up"}
    assert _icons_before(settings, "settings.backup.import") == {"file-down"}
    assert _icons_before(backup, "backup.import.ok") == {"file-down"}


def test_section_icons():
    settings = _src("settings.js")
    assert "group('save-check', 'settings.backup.title'" in settings
    assert "group('cloud-download', 'settings.updates.title'" in settings
    # Mise à jour : rien ne « monte » vers GitHub, tout descend vers le PC.
    upd = _src("updates.js")
    assert "arrow-up" not in upd and "file-up" not in upd
    for name in ("save-check", "cloud-download", "file-up", "file-down"):
        assert (ROOT / "assets" / "icons" / f"{name}.svg").is_file(), name
