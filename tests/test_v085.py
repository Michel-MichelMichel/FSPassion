"""0.8.5 : cache de l'interface, catalogue et fabrication."""

from __future__ import annotations

import json
from pathlib import Path

from fspassion import dlcremote

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_interface_files_are_never_cached():
    assert 'cache="no-cache"' in _read("src", "fspassion", "server.py")
    assert "max-age=600" not in _read("src", "fspassion", "server.py")


def test_downloaded_catalog_keeps_fixed_order():
    raw = json.loads(_read("assets", "fallback", "dlc_catalog.json"))
    clean = dlcremote.validate_catalog(raw)
    assert clean["versions"]["FS2011"].get("fixed_order") is True
    assert "fixed_order" not in clean["versions"]["FS25"]


def test_build_drops_unused_files():
    spec = _read("packaging", "fspassion.spec")
    for part in ('"PIL/_avif."', '"clr_loader/ffi/dlls/x86/"'):
        assert part in spec
    # 0.8.7 : pywebview ajoute au PATH les trois dossiers win-arm64, win-x64 et
    # win-x86 et plante si l'un manque : aucun ne doit être retiré.
    drop = spec[spec.index("DROP = ("):spec.index("def keep")]
    assert "runtimes" not in drop.replace("webview/lib/runtimes/win-arm64 et win-x86", "")
    assert "a.binaries = [b for b in a.binaries if keep(b)]" in spec


def test_dlc_icons_are_never_avif():
    """Les icônes AVIF (nommées .jpg) du dépôt de données sont devenues de vrais
    JPEG : le catalogue embarqué porte leurs nouvelles empreintes."""
    cat = json.loads(_read("assets", "fallback", "dlc_catalog.json"))
    assert cat["updated"] >= "2026-10-27"
    nexat = next(e for e in cat["versions"]["FS25"]["dlc"] if e.get("file") == "nexatPack")
    assert nexat["sha256"] != "0" * 64
