"""0.8.2 : retours sur le premier exécutable (icônes des DLC, thèmes livrés,
droits au démarrage)."""

from __future__ import annotations

import json
from pathlib import Path

from fspassion import config, dlc, dlcremote, fsutil

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_avif_icons_are_accepted():
    """20 icônes du dépôt de données sont des AVIF nommés « .jpg »."""
    avif = b"\x00\x00\x00\x1cftypavif\x00\x00\x00\x00avifmif1"
    assert dlcremote._image_ok(avif)
    assert dlcremote._image_ok(b"\x00\x00\x00\x20ftypavis" + b"\x00" * 8)
    assert not dlcremote._image_ok(b"\x00\x00\x00\x1cftypmp42" + b"\x00" * 8)   # une vidéo n'est pas une icône
    assert not dlcremote._image_ok(b"<html>")


def test_icons_of_dlc_you_do_not_own_are_wanted(monkeypatch):
    cat = {"schema": 1, "updated": "2099-01-01", "versions": {
        "FS17": {"icons_folder": "icons_dlc_fs17", "dlc": [
            {"keywords": ["modern"], "name": "Modern Pack", "icon": "modern.png"},      # non possédé, nom de fichier inconnu
            {"file": "bigBudPack", "name": "Big Bud Pack"},
            {"keywords": ["x"], "name": "Sans icône"},
        ]}}}
    fsutil.atomic_write_json(config.dlc_cache_dir() / "dlc_catalog.json", cat)
    monkeypatch.setattr(dlc, "icon_dirs", lambda folder: [config.dlc_cache_dir() / folder])
    wanted = dlcremote.wanted_icons(dlc.load_catalog(), {})
    assert [w["names"] for w in wanted] == [["modern.png"], ["bigBudPack.png", "bigBudPack.jpg"]]


def test_fs25_precision_checksum_matches_its_own_icon():
    """Le catalogue donnait à Precision Farming (FS25) l'empreinte de l'icône de FS19."""
    cat = json.loads(_read("assets", "fallback", "dlc_catalog.json"))
    e25 = next(e for e in cat["versions"]["FS25"]["dlc"] if e.get("icon") == "precision.jpg")
    e19 = next(e for e in cat["versions"]["FS19"]["dlc"] if e.get("icon") == "precision.jpg")
    assert e25["sha256"] != e19["sha256"]


def test_shipped_themes_are_the_designed_ones():
    """Les essais d'atelier (néon sur Cuivre, Nord Snow…) ne sont pas livrés."""
    for path in (("ui", "themes.json"), ("src", "fspassion", "data", "themes_default.json")):
        by_id = {t["id"]: t for t in json.loads(_read(*path))["themes"]}
        assert {k for k, t in by_id.items() if t.get("neon")} == {"synthwave-84", "synthwave-84-light"}
        assert by_id["cuivre"]["grain"] == 14 and by_id["cuivre"]["effect_intensity"] == 70


def test_rights_are_logged_at_startup():
    src = _read("src", "fspassion", "app.py")
    assert "administrateur : %s" in src and "winapi.is_admin()" in src
    assert "runasoriginaluser" in _read("packaging", "installer.iss")


def test_build_stops_clearly_when_the_built_app_is_open():
    """0.8.3 : FS Passion lancé depuis build\\dist verrouille ses fichiers
    (ClrLoader.dll) ; la fabrication le dit au lieu d'une erreur de PyInstaller."""
    build = _read("tools", "build.py")
    assert "def running_from_build()" in build and "busy = running_from_build()" in build
    assert "except PermissionError as exc:" in build
