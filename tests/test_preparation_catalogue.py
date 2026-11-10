"""Préparation du catalogue des DLC (tools/prepare_data_repo.py) et catalogue
embarqué à la fabrication (tools/build.py)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _tool(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


prep = _tool("prepare_data_repo")


def _catalog() -> dict:
    return {"schema": 1, "updated": "2026-10-29", "versions": {"FS25": {"icons_folder": "icons_dlc_fs25", "dlc": [
        {"file": "vredoPack", "name": "Vredo Pack", "status": "released"},
        {"file": None, "keywords": ["beans", "alpacas"], "name": "Beans & Alpacas Expansion", "icon": "b.jpg"},
        {"file": None, "keywords": ["fendt"], "name": "Fendt Pack"},
        {"file": None, "keywords": ["holland"], "name": "New Holland Free", "type": "dlc"},
        {"file": None, "keywords": ["cool"], "name": "Cool Pack", "status": "announced", "release_date": "2026-12-01"},
    ]}}}


def test_keyword_entry_gets_the_exact_file_name():
    raw = _catalog()
    local = {"FS25": [("beansAndAlpacasPack", ".dlc"), ("vredoPack", ".dlc"), ("newHollandFree", ".zip"),
                      ("fendtPackA", ".dlc"), ("fendtPackB", ".dlc"), ("mysteryPack", ".dlc")]}
    lines, linked = prep.link_local_files(raw, local)
    entries = raw["versions"]["FS25"]["dlc"]
    assert linked == 2
    assert entries[1]["file"] == "beansAndAlpacasPack" and "keywords" not in entries[1] and entries[1]["icon"] == "b.jpg"
    assert entries[3]["file"] == "newHollandFree" and entries[3]["type"] == "zip"
    # Deux fichiers pour les mêmes mots-clés : rien n'est décidé à la place de l'auteur.
    assert entries[2]["file"] is None and entries[2]["keywords"] == ["fendt"]
    assert any("à trancher" in x and "fendtPackA" in x for x in lines)
    assert any("inconnu" in x and "mysteryPack" in x for x in lines)
    assert not any("vredoPack" in x for x in lines)


def test_announced_dlc_is_released_after_its_date():
    raw = _catalog()
    assert prep.release_announced(raw, "2026-11-30") == []
    assert prep.release_announced(raw, "2026-12-01") == ["FS25 Cool Pack"]
    assert raw["versions"]["FS25"]["dlc"][4]["status"] == "released"


def test_preparation_batch_pulls_first_and_scans_pdlc():
    bat = (ROOT / "preparer_catalogue_dlc.bat").read_text(encoding="utf-8")
    assert bat.index("pull --ff-only") < bat.index("prepare_data_repo.py")
    assert "--write --pdlc" in bat and "--snapshot" not in bat


@pytest.fixture()
def build(monkeypatch, tmp_path):
    mod = _tool("build")
    target = tmp_path / "dlc_catalog.json"
    target.write_text(json.dumps(_catalog()), encoding="utf-8")
    monkeypatch.setattr(mod, "FALLBACK_CATALOG", target)
    return mod, target


def test_build_embeds_the_published_catalog(build, monkeypatch):
    mod, target = build
    from fspassion import dlcremote

    published = _catalog()
    published["updated"] = "2026-11-10"
    monkeypatch.setattr(dlcremote, "fetch", lambda url, limit: json.dumps(published).encode("utf-8"))
    mod.embed_dlc_catalog(strict=True)
    assert json.loads(target.read_text(encoding="utf-8"))["updated"] == "2026-11-10"


def test_build_offline_keeps_the_catalog_or_stops_on_github(build, monkeypatch):
    mod, target = build
    from fspassion import dlcremote

    def down(url, limit):
        raise dlcremote.RemoteError("unreachable", detail="hors ligne")

    monkeypatch.setattr(dlcremote, "fetch", down)
    before = target.read_text(encoding="utf-8")
    mod.embed_dlc_catalog(strict=False)
    assert target.read_text(encoding="utf-8") == before
    with pytest.raises(SystemExit):
        mod.embed_dlc_catalog(strict=True)


def test_build_refuses_an_empty_published_catalog(build, monkeypatch):
    mod, _ = build
    from fspassion import dlcremote

    empty = {"schema": 1, "updated": "2026-11-10", "versions": {}}
    monkeypatch.setattr(dlcremote, "fetch", lambda url, limit: json.dumps(empty).encode("utf-8"))
    with pytest.raises(SystemExit):
        mod.embed_dlc_catalog(strict=True)
