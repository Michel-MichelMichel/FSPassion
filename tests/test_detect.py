"""Détection des installations et règles de préremplissage (4.13, 4.14)."""

from __future__ import annotations

import os
from pathlib import Path

from fspassion import config, detect

LIBRARYFOLDERS_NEW = r'''
"libraryfolders"
{
	"0"
	{
		"path"		"C:\\Program Files (x86)\\Steam"
		"apps" { "228980" "1" }
	}
	"1"
	{
		"path"		"%s"
	}
}
'''

APPMANIFEST = '''
"AppState"
{
	"appid"		"2300320"
	"name"		"Farming Simulator 25"
	"installdir"		"Farming Simulator 25"
}
'''


def test_parse_vdf():
    data = detect.parse_vdf(LIBRARYFOLDERS_NEW % "D:\\\\SteamLibrary")
    assert data["libraryfolders"]["1"]["path"] == "D:\\SteamLibrary"
    old = detect.parse_vdf('"LibraryFolders" { "TimeNextStatsReport" "1" "1" "E:\\\\Games" }')
    assert old["libraryfolders"]["1"] == "E:\\Games"
    app = detect.parse_vdf(APPMANIFEST)["appstate"]
    assert app["appid"] == "2300320" and app["installdir"] == "Farming Simulator 25"


def test_steam_installs(tmp_path):
    lib = tmp_path / "SteamLibrary"
    game = lib / "steamapps" / "common" / "Farming Simulator 25"
    game.mkdir(parents=True)
    (game / "FarmingSimulator2025.exe").write_bytes(b"MZ")
    (lib / "steamapps" / "appmanifest_2300320.acf").write_text(APPMANIFEST, encoding="utf-8")
    found = detect.steam_installs([lib])
    assert len(found) == 1
    assert found[0].version == "FS25" and found[0].info["appid"] == "2300320"
    assert found[0].exe.name == "FarmingSimulator2025.exe"


def test_versions_in_dir_case_insensitive(tmp_path):
    (tmp_path / "farmingsimulator2019.EXE").write_bytes(b"MZ")
    assert [v.id for v in detect.versions_in_dir(tmp_path)] == ["FS19"]


def test_game_root_and_version_of_exe():
    assert detect.game_root_of_exe(r"D:\FS22\x64\FarmingSimulator2022Game.exe".replace("\\", "/")).name == "FS22"
    assert detect.version_of_exe("FarmingSimulator2013Game.exe").id == "FS2013"
    assert detect.version_of_exe("notepad.exe") is None


def test_epic_installs(tmp_path):
    game = tmp_path / "FS22"
    game.mkdir()
    (game / "FarmingSimulator2022.exe").write_bytes(b"MZ")
    man = [{"DisplayName": "Farming Simulator 22", "InstallLocation": str(game), "AppName": "Cobra"}]
    found = detect.epic_installs(man)
    assert found and found[0].version == "FS22" and found[0].info["app_name"] == "Cobra"


def test_fallback_installs(tmp_path):
    d = tmp_path / "Games" / "Farming Simulator 2013"
    d.mkdir(parents=True)
    (d / "FarmingSimulator2013Game.exe").write_bytes(b"MZ")
    found = detect.fallback_installs([tmp_path])
    assert [(f.version, f.source) for f in found] == [("FS2013", "fallback")]


def test_publisher_id():
    # Valeur connue : la calculatrice de Windows (Microsoft.WindowsCalculator_8wekyb3d8bbwe)
    pub = "CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US"
    assert detect.publisher_id(pub) == "8wekyb3d8bbwe"


def test_suggest_mods_dir(tmp_path):
    from fspassion import versions

    v = versions.require("FS25")
    user = tmp_path / "FarmingSimulator2025"
    user.mkdir()
    assert detect.suggest_mods_dir(v, user) == user / "mods"
    (user / "gameSettings.xml").write_text('<gameSettings><modsDirectoryOverride active="true" directory="D:/FS25_Mods/Mods"/></gameSettings>')
    assert str(detect.suggest_mods_dir(v, user)).replace("\\", "/").endswith("D:/FS25_Mods/Mods")
    # Override vers un dossier de partie : remonter au dossier de mods mémorisé
    parties = tmp_path / "X" / "FSPassion" / "FS25"
    (parties / "Parties" / "etruria-7f3a").mkdir(parents=True)
    (parties / "parties.json").write_text('{"mods_dir": "D:/FS25_Mods/Mods"}')
    (user / "gameSettings.xml").write_text(
        f'<gameSettings><modsDirectoryOverride active="true" directory="{(parties / "Parties" / "etruria-7f3a").as_posix()}"/></gameSettings>')
    # 0.8.0 : sous Windows le chemin revient avec des « \\ » : comparaison normalisée.
    assert os.path.normpath(str(detect.suggest_mods_dir(v, user))) == os.path.normpath("D:/FS25_Mods/Mods")
    # Override inactif : dossier par défaut
    (user / "gameSettings.xml").write_text('<gameSettings><modsDirectoryOverride active="false" directory="C:/Temp"/></gameSettings>')
    assert detect.suggest_mods_dir(v, user) == user / "mods"


def test_prefill_rules():
    det = {"game_exe": "D:/FS25/FarmingSimulator2025.exe", "user_dir": "G:/Documents/My Games/FarmingSimulator2025", "mods_dir": "D:/FS25_Mods/Mods"}
    # Champs vides : préremplis
    cfg = config.default_version_cfg()
    cfg, changed = detect.prefill(cfg, det, "FS25")
    assert set(changed) == {"game_exe", "user_dir", "mods_dir"}
    assert cfg["auto"]["mods_dir"] == "D:/FS25_Mods/Mods"
    # Champ personnalisé : jamais modifié
    cfg["mods_dir"] = "E:/MesMods"
    det2 = dict(det, mods_dir="D:/Autre")
    cfg, changed = detect.prefill(cfg, det2, "FS25")
    assert cfg["mods_dir"] == "E:/MesMods" and "mods_dir" not in changed
    # Champ resté à la valeur automatique précédente : mis à jour
    det3 = dict(det, game_exe="F:/FS25/FarmingSimulator2025.exe")
    cfg, changed = detect.prefill(cfg, det3, "FS25")
    assert cfg["game_exe"] == "F:/FS25/FarmingSimulator2025.exe"
    # Modèle automatique d'une AUTRE version : remplacé
    cfg2 = config.default_version_cfg()
    cfg2["user_dir"] = "G:/Documents/My Games/FarmingSimulator2022"
    cfg2, changed = detect.prefill(cfg2, det, "FS25")
    assert cfg2["user_dir"] == det["user_dir"]


def test_detect_version_not_launched(tmp_path):
    from fspassion import versions

    v = versions.require("FS22")
    game = tmp_path / "FS22"
    game.mkdir()
    exe = game / "FarmingSimulator2022.exe"
    exe.write_bytes(b"MZ")
    inst = detect.Install("FS22", game, exe, "steam")
    res = detect.detect_version(v, [inst], {}, tmp_path / "Docs")
    # Jeu installé mais jamais lancé : chemin standard de Mes documents proposé
    assert Path(res["user_dir"]) == tmp_path / "Docs" / "My Games" / "FarmingSimulator2022"
    assert res["game_exe"] == str(exe)
