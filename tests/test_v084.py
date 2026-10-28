"""0.8.4 : icône, numéro de version unique, bienvenue, thème par défaut,
champs des thèmes clairs, ordre des DLC de FS2011, détection FS15 / FS2013."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fspassion import __version__, config, detect, dlc, versions

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_version_has_a_single_source():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    assert 'dynamic = ["version"]' in _read("pyproject.toml")
    assert 'attr = "fspassion.__version__"' in _read("pyproject.toml")
    assert not re.search(r'^version\s*=\s*"', _read("pyproject.toml"), re.M)
    for code in ("fr", "en"):
        assert "app_version" not in json.loads(_read("lang", f"{code}.json"))["_meta"]
    assert __version__ not in _read("README.md")
    assert "src/fspassion/__init__.py" in _read("packaging", "github", "build.yml")
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_tool", ROOT / "tools" / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.version() == __version__
    assert mod.ICON_SOURCE == ROOT / "assets" / "brand" / "tray.png"


def test_old_logo_files_are_no_longer_used():
    for rel in ("tools/build.py", "packaging/fspassion.spec", "packaging/installer.iss", "tests/test_v067.py"):
        assert "FS_passion_logo" not in _read(*rel.split("/"))


def test_gruvbox_light_is_the_default_theme(tmp_path):
    assert config.DEFAULT_THEME == "gruvbox-light"
    assert config.Settings(tmp_path / "s.json").get("theme") == "gruvbox-light"
    assert "let chosenId = 'gruvbox-light'" in _read("ui", "js", "theme.js")


def test_light_inputs_follow_the_theme():
    base = _read("ui", "css", "base.css")
    assert "--fill-input-focus: #FFFFFF" not in base
    assert ':root[data-mode="light"][data-surfaces]' in _read("ui", "css", "themes.css")


def test_welcome_and_notice_move_the_window_and_close_with_ok_only():
    js = _read("ui", "js", "welcome.js")
    assert "dismissible: false, dragWindow: true" in js
    assert "backdropClose: false" in js
    assert "makeDragZone(backdrop)" in _read("ui", "js", "dialog.js")


def test_settings_cleanup():
    js = _read("ui", "js", "settings.js")
    assert "resetThemes" not in js and "settings.theme.reset" not in js
    assert "stop-row" in js and ".set-row.stop-row" in _read("ui", "css", "dialogs.css")


def test_fs2011_dlc_keep_catalog_order(tmp_path, monkeypatch):
    cat = json.loads(_read("assets", "fallback", "dlc_catalog.json"))
    assert cat["versions"]["FS2011"]["fixed_order"] is True
    monkeypatch.setattr(dlc, "load_catalog", lambda: cat)
    pdlc = tmp_path / "pdlc"
    pdlc.mkdir()
    (pdlc / "dlcPack3.dlc").write_bytes(b"x")
    (pdlc / "ProFarm1.dlc").write_bytes(b"x")
    out = dlc.scan_dlc(versions.get("FS2011"), [pdlc])
    names = [d["names"]["_"] for d in out]
    assert names[:4] == ["Farming Classics (Add-on 2)", "Equipment Pack (DLC 1)",
                         "Renewable Energy Pack (DLC 2)", "Trailers and Glasshouse Pack (DLC 3)"]
    assert names[4] == "ProFarm1" and len(out) == 5
    assert "byRank" in _read("ui", "js", "library.js")


def test_fs2013_prefers_the_64_bit_exe(tmp_path):
    game = tmp_path / "Farming Simulator 2013"
    (game / "x64").mkdir(parents=True)
    for n in ("FarmingSimulator2013.exe", "FarmingSimulator2013_64bit.exe", "x64/FarmingSimulator2013Game.exe"):
        (game / n).write_bytes(b"")
    found = detect.fallback_installs([tmp_path])
    assert [(i.version, i.exe.name) for i in found] == [("FS2013", "FarmingSimulator2013_64bit.exe")]


def test_fs15_gold_edition_and_plain_folder(tmp_path):
    for folder in ("Farming Simulator 15 Gold Edition", "Farming Simulator 15"):
        d = tmp_path / folder
        d.mkdir()
        (d / "FarmingSimulator2015.exe").write_bytes(b"")
    found = detect.fallback_installs([tmp_path])
    assert sorted(i.game_dir.name for i in found if i.version == "FS15") == [
        "Farming Simulator 15", "Farming Simulator 15 Gold Edition"]


def test_not_configured_message_is_a_card():
    js = _read("ui", "js", "library.js")
    assert "grid-empty-card" in js and "cats = [];" in js
    assert ".grid-empty-card" in _read("ui", "css", "lists.css")
