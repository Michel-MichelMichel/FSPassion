"""Lecture de la ligne modsDirectoryOverride et sauvegarde d'origine (3.5)."""

from __future__ import annotations

import pytest

from fspassion import gamesettings

# Formes relevées par le test T5 sur le PC de l'utilisateur.
T5_LINES = [
    ('<modsDirectoryOverride active="false" directory="C:/Temp" />', False, "C:/Temp"),
    ('<modsDirectoryOverride active="false" directory="C:/Temp"/>', False, "C:/Temp"),
    ("<modsDirectoryOverride active='false' directory='C:/Temp' />", False, "C:/Temp"),
    ('<modsDirectoryOverride active="true" directory="D:/FS25_Tests/Parties/Test A"/>', True, "D:/FS25_Tests/Parties/Test A"),
    ('<modsDirectoryOverride directory="D:/Mods &amp; Co" active="true"/>', True, "D:/Mods & Co"),
]


@pytest.mark.parametrize("line, active, directory", T5_LINES)
def test_parse_override(line, active, directory):
    text = f'<?xml version="1.0"?>\n<gameSettings revision="15">\n    {line}\n</gameSettings>'
    ov = gamesettings.parse_override(text)
    assert ov.found and ov.active is active and ov.directory == directory


def test_missing_line():
    assert not gamesettings.parse_override("<gameSettings></gameSettings>").found


def test_original_backup_created_once(tmp_path):
    gs = tmp_path / "gameSettings.xml"
    gs.write_text('<gameSettings><modsDirectoryOverride active="true" directory="D:/A"/></gameSettings>', encoding="utf-8")
    assert gamesettings.ensure_original_backup(gs) is True
    bak = gamesettings.original_backup_path(gs)
    original = bak.read_bytes()
    # Le fichier du jeu change : la sauvegarde d'origine n'est jamais écrasée.
    gs.write_text('<gameSettings><modsDirectoryOverride active="true" directory="D:/B"/></gameSettings>', encoding="utf-8")
    assert gamesettings.ensure_original_backup(gs) is False
    assert bak.read_bytes() == original
    assert bak.name == "gameSettings.xml.original.bak"


def test_read_override_file(tmp_path):
    gs = tmp_path / "gameSettings.xml"
    gs.write_bytes(b"\xef\xbb\xbf<gameSettings><modsDirectoryOverride active='true' directory='E:/M\xc3\xb6ds'/></gameSettings>")
    ov = gamesettings.read_override(gs)
    assert ov.directory == "E:/Möds"
    assert gamesettings.read_override(tmp_path / "absent.xml") is None
