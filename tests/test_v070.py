"""Version 0.7.0 : export et import, « Ne plus utiliser », catalogue des DLC
distant, diagnostic ; retouches des dons, invitation au don supprimée.

Vérifié ici :
- l'export contient les réglages (sans ceux de cette installation) et les
  parties de chaque version ; il est refusé en mode démonstration ;
- l'import garde les chemins par défaut, remplace les parties, sauvegarde
  l'état d'avant, n'applique rien, et ne laisse jamais le jeu pointer vers un
  dossier de partie supprimé ;
- « Ne plus utiliser » rétablit l'override d'origine, vide les dossiers de
  parties lien par lien (les mods restent intacts), ne supprime que ce qui
  est demandé, garde « Old versions », et refuse pendant le jeu ;
- le catalogue distant : adresse limitée à raw.githubusercontent.com, au plus
  une fois par jour, contrôle du contenu, icônes des seuls DLC détectés,
  images et empreintes vérifiées ; le plus récent des catalogues l'emporte.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

import pytest

from fspassion import apply, backup, config, dialogs, dlc, dlcremote, fsutil, gamesettings, stopuse
from fspassion.core import SETTABLE, AppError, Core
from fspassion.events import EventBus
from fspassion.parties import FULL

import fakemods

ROOT = Path(__file__).resolve().parents[1]

GS_TEXT = (
    '<?xml version="1.0" encoding="utf-8" standalone="no" ?>\n<gameSettings revision="15">\n'
    '    <modsDirectoryOverride active="true" directory="{mods}"/>\n</gameSettings>\n'
)


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def override_dir(gs: Path) -> str:
    ov = gamesettings.read_override(gs)
    assert ov is not None and ov.found
    return os.path.normpath(ov.directory or "")


@pytest.fixture
def env(tmp_path):
    mods = tmp_path / "FS25_Mods" / "Mods"
    info = fakemods.make_collection(mods, count=10)
    user = tmp_path / "Documents" / "FarmingSimulator2025"
    user.mkdir(parents=True)
    gs = user / "gameSettings.xml"
    gs.write_text(GS_TEXT.format(mods=mods.as_posix()), encoding="utf-8")
    core = Core(dev=True, bus=EventBus())
    core.settings.set("first_detection_done", True)
    core.settings.set("internet_access", False)
    core.settings.update_version("FS25", {"mods_dir": str(mods), "user_dir": str(user)})
    core._ensure_backups()
    core._reconciled.add("FS25")
    lib = core.libs.get("FS25")
    lib._scan()
    fsp = mods.parent / "FSPassion" / "FS25"
    yield {"core": core, "mods": mods, "gs": gs, "ids": info["ids"], "lib": lib, "user": user,
           "fsp": fsp, "parties": fsp / "Parties", "tmp": tmp_path}


def make_party(env, name="Hof Bergmann", n=3, start=0):
    core = env["core"]
    ids = env["ids"]
    pid = core.party_create("FS25", name)["party"]["id"]
    core.party_mods("FS25", "add", "party", ids[start:start + n], pid=pid)
    return pid


# --------------------------------------------------------------------------
# Dons : retouches et suppression de l'invitation
# --------------------------------------------------------------------------

def test_donation_prompt_is_gone():
    # ui\js\donate.js n'est plus chargé par l'interface (le fichier peut être supprimé).
    for name in ("main.js", "settings.js", "toast.js"):
        assert "donate.js" not in _read("ui", "js", name) and "Donation" not in _read("ui", "js", name)
    assert "toast-donate" not in _read("ui", "css", "dialogs.css")
    assert "donate_prompt" not in SETTABLE
    assert "launch_count" not in config.default_settings()
    for code in ("fr", "en"):
        assert "prompt" not in json.loads(_read("lang", f"{code}.json"))["settings"]["donate"]


def test_obsolete_settings_are_removed_on_load(isolated_home):
    path = config.settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": 1, "launch_count": 12, "donate_prompt": "done", "theme": "nord"}), "utf-8")
    s = config.Settings()
    snap = s.snapshot()
    assert "launch_count" not in snap and "donate_prompt" not in snap
    assert snap["theme"] == "nord"


def test_donate_texts():
    fr = json.loads(_read("lang", "fr.json"))["settings"]["donate"]
    assert fr["title"] == "Soutenir le projet"
    assert fr["text"].startswith("FS Passion est et restera un projet de confiance, open source et gratuit.")
    en = json.loads(_read("lang", "en.json"))["settings"]["donate"]
    assert en["title"] == "Support the project"


def test_buy_me_a_coffee_logo_stays_sharp():
    # Plus aucune image matricielle dans les deux SVG : tout est vectoriel.
    for name in ("Buymeacoffee-icon.svg", "Buymeacoffee-text.svg"):
        svg = _read("assets", "brand", name)
        assert "<image" not in svg and "base64" not in svg
        assert 'fill="#ffffff"' in svg
    # L'animation d'arrivée ne laisse plus le logo sur un calque figé.
    css = _read("ui", "css", "dialogs.css")
    block = re.search(r"\.brand-logos\.play \.brand-logo \{([^}]*)\}", css).group(1)
    assert "backwards" in block and "both" not in block


# --------------------------------------------------------------------------
# Exporter
# --------------------------------------------------------------------------

def test_export_contains_settings_and_parties(env, monkeypatch, tmp_path):
    core = env["core"]
    make_party(env)
    core.settings.set("window", {"x": 1, "y": 2, "width": 3, "height": 4, "maximized": False})
    target = tmp_path / "out" / "mon-export"
    target.parent.mkdir()
    monkeypatch.setattr(dialogs, "save_as", lambda *a, **k: str(target))

    res = core.export_config(from_window=False)

    written = Path(res["path"])
    assert written.name == "mon-export.json"
    data = json.loads(written.read_text("utf-8"))
    assert data["format"] == backup.FORMAT and data["schema"] == backup.SCHEMA
    assert "window" not in data["settings"] and "demo" not in data["settings"]
    assert data["settings"]["versions"]["FS25"]["mods_dir"] == str(env["mods"])
    assert [p["name"] for p in data["parties"]["FS25"]["parties"]] == ["Hof Bergmann"]
    assert res["parties"] == 1


def test_export_cancelled_and_refused_in_demo(env, monkeypatch):
    core = env["core"]
    monkeypatch.setattr(dialogs, "save_as", lambda *a, **k: None)
    assert core.export_config(False) == {"cancelled": True}
    state = core.settings.get("demo")
    state["active"] = True
    core.settings.set("demo", state)
    with pytest.raises(AppError) as exc:
        core.export_config(False)
    assert exc.value.key == "backup.demo_active"


# --------------------------------------------------------------------------
# Importer
# --------------------------------------------------------------------------

def _export_file(core: Core, path: Path) -> Path:
    backup.write_export(path, core.export_data())
    return path


def test_read_export_rejects_other_files(tmp_path):
    bad = tmp_path / "x.json"
    bad.write_text('{"hello": 1}', "utf-8")
    with pytest.raises(backup.BackupError) as e1:
        backup.read_export(bad)
    assert e1.value.key == "backup.not_export"
    bad.write_text("pas du json", "utf-8")
    with pytest.raises(backup.BackupError) as e2:
        backup.read_export(bad)
    assert e2.value.key == "backup.unreadable"
    bad.write_text(json.dumps({"format": backup.FORMAT, "schema": 99, "app_version": "9.0.0"}), "utf-8")
    with pytest.raises(backup.BackupError) as e3:
        backup.read_export(bad)
    assert e3.value.key == "backup.too_new"


def test_import_keeps_paths_and_replaces_parties(env, tmp_path):
    core = env["core"]
    make_party(env, "Partie A")
    exported = _export_file(core, tmp_path / "export.json")
    # Sur « l'autre PC » : d'autres chemins, une autre partie.
    data = json.loads(exported.read_text("utf-8"))
    data["settings"]["versions"]["FS25"]["mods_dir"] = "Z:\\Ailleurs\\Mods"
    data["settings"]["theme"] = "nord"
    exported.write_text(json.dumps(data), "utf-8")
    core.party_create("FS25", "Partie locale")

    prev = core.import_open(False, path=str(exported))
    assert prev["versions"][0]["parties"] == 1 and prev["paths_differ"] is True
    res = core.import_apply(prev["token"], True)

    assert core.settings.version("FS25")["mods_dir"] == str(env["mods"])  # chemin gardé
    assert core.settings.get("theme") == "nord"                           # réglage neutre repris
    names = [p["name"] for p in core._store("FS25").data["parties"]]
    assert names == ["Partie A"]
    assert core._store("FS25").data["applied_signature"] == {}
    assert Path(res["backup"]).is_file()
    saved = json.loads(Path(res["backup"]).read_text("utf-8"))
    assert {p["name"] for p in saved["parties"]["FS25"]["parties"]} == {"Partie A", "Partie locale"}
    # Le jeton ne sert qu'une fois.
    with pytest.raises(AppError):
        core.import_apply(prev["token"], True)


def test_import_never_leaves_the_game_on_a_deleted_folder(env, tmp_path):
    core = env["core"]
    make_party(env, "Exportée")
    exported = _export_file(core, tmp_path / "export.json")
    pid = make_party(env, "Appliquée", start=3)   # absente du fichier
    core.party_apply("FS25", pid)
    folder = core._store("FS25").party(pid)["folder"]
    assert override_dir(env["gs"]) == os.path.normpath(env["parties"] / folder)
    before = {p.name: sha(p) for p in env["mods"].iterdir() if p.is_file()}

    prev = core.import_open(False, path=str(exported))
    res = core.import_apply(prev["token"], True)

    row = res["versions"][0]
    assert row["fallback"] is True and row["removed_folders"] == 1
    assert override_dir(env["gs"]) == os.path.normpath(env["mods"])     # Partie Pleine
    assert not (env["parties"] / folder).exists()
    assert {p.name: sha(p) for p in env["mods"].iterdir() if p.is_file()} == before
    assert core._store("FS25").data["applied"] == FULL


def test_import_without_keeping_paths(env, tmp_path):
    core = env["core"]
    exported = _export_file(core, tmp_path / "export.json")
    data = json.loads(exported.read_text("utf-8"))
    other = tmp_path / "Autre" / "Mods"
    other.mkdir(parents=True)
    data["settings"]["versions"]["FS25"]["mods_dir"] = str(other)
    data["settings"]["downloads_dir"] = str(tmp_path / "DL")
    exported.write_text(json.dumps(data), "utf-8")

    prev = core.import_open(False, path=str(exported))
    core.import_apply(prev["token"], False)

    assert core.settings.version("FS25")["mods_dir"] == str(other)
    assert core.settings.get("downloads_dir") == str(tmp_path / "DL")


def test_import_refused_while_the_game_runs(env, tmp_path):
    core = env["core"]
    make_party(env)
    exported = _export_file(core, tmp_path / "export.json")
    prev = core.import_open(False, path=str(exported))
    core.monitor.running.add("FS25")
    try:
        with pytest.raises(AppError) as exc:
            core.import_apply(prev["token"], True)
        assert exc.value.key == "backup.running"
    finally:
        core.monitor.running.discard("FS25")


def test_safety_backups_are_limited(isolated_home):
    for _ in range(backup.KEEP_BACKUPS + 3):
        backup.write_safety_backup({"format": backup.FORMAT})
    assert len(list(backup.backups_dir().glob("avant-import-*.json"))) == backup.KEEP_BACKUPS


# --------------------------------------------------------------------------
# Ne plus utiliser FS Passion
# --------------------------------------------------------------------------

def test_stop_using_restores_the_game_and_keeps_the_mods(env):
    core = env["core"]
    pid = make_party(env)
    core.party_apply("FS25", pid)
    assert override_dir(env["gs"]) != os.path.normpath(env["mods"])
    old = env["fsp"] / apply.OLD_VERSIONS / "2026-10-22"
    old.mkdir(parents=True)
    (old / "FS25_Ancien.zip").write_bytes(b"PK")
    before = {p.name: sha(p) for p in env["mods"].iterdir() if p.is_file()}

    prev = core.stop_preview()
    row = prev["versions"][0]
    assert row["override"] == "restore" and row["folders"] >= 1
    assert row["kept"][0]["name"] == apply.OLD_VERSIONS

    res = core.stop_using([], True)

    assert res["versions"][0]["override"] == "restore"
    assert override_dir(env["gs"]) == os.path.normpath(env["mods"])
    assert not env["parties"].exists()
    assert {p.name: sha(p) for p in env["mods"].iterdir() if p.is_file()} == before
    assert (env["fsp"] / "parties.json").is_file()      # rien d'autre sans le demander
    assert (old / "FS25_Ancien.zip").is_file()
    assert core.stopped
    # Plus aucun scan : le cache ne peut plus être réécrit.
    lib = core.libs.get("FS25")
    assert lib.disabled


def test_stop_using_deletes_what_is_asked(env):
    core = env["core"]
    make_party(env)
    assert config.settings_path().is_file()
    res = core.stop_using(["parties", "caches", "settings", "logs"], True)

    assert not (env["fsp"] / "parties.json").exists()
    assert not (env["fsp"] / "cache").exists()
    # L'interface qui se rafraîchit ne recrée rien.
    assert core.parties_state("FS25")["supported"] is False
    core.state()
    assert not (env["fsp"] / "parties.json").exists()
    assert not env["fsp"].exists() and not env["fsp"].parent.exists()   # FSPassion\ vide : retiré
    assert not config.settings_path().exists()
    core.settings.set("theme", "nord")                                    # plus jamais réécrit
    assert not config.settings_path().exists()
    assert config.logs_dir() in core.exit_cleanup
    assert "settings" in res["removed"]
    assert env["mods"].is_dir() and any(env["mods"].iterdir())


def test_stop_using_refused_while_the_game_runs(env):
    core = env["core"]
    core.monitor.running.add("FS25")
    try:
        with pytest.raises(AppError) as exc:
            core.stop_using([], True)
        assert exc.value.key == "stop.running"
    finally:
        core.monitor.running.discard("FS25")
    with pytest.raises(AppError):
        core.stop_using([], False)   # confirmation explicite obligatoire


def test_override_plan_without_backup_or_pointing_inside_fspassion(env):
    core = env["core"]
    vp = core.paths("FS25")
    bak = gamesettings.original_backup_path(env["gs"])
    # Sauvegarde d'origine prise alors que le jeu chargeait une partie (R23).
    inside = env["parties"] / "test-1234"
    bak.write_text(GS_TEXT.format(mods=inside.as_posix()), "utf-8")
    plan = stopuse.override_plan(vp)
    assert plan["action"] == "restore" and plan.get("fixed") and plan["directory"] == str(env["mods"])
    # Pas de sauvegarde : l'override est désactivé.
    bak.unlink()
    plan = stopuse.override_plan(vp)
    assert plan["action"] == "deactivate" and plan["active"] is False
    stopuse.restore_override(vp)
    ov = gamesettings.read_override(env["gs"])
    assert ov is not None and ov.active is False


def test_remove_tree_never_follows_links(tmp_path):
    fakemods.need_symlinks()
    outside = tmp_path / "precieux"
    outside.mkdir()
    (outside / "mod.zip").write_bytes(b"PK")
    victim = tmp_path / "cache"
    victim.mkdir()
    (victim / "a.webp").write_bytes(b"x")
    os.symlink(outside, victim / "lien", target_is_directory=True)
    stopuse.remove_tree(victim)
    assert not victim.exists()
    assert (outside / "mod.zip").is_file()


# --------------------------------------------------------------------------
# Catalogue des DLC distant
# --------------------------------------------------------------------------

def test_remote_base_url_is_restricted():
    ok = {"remote_data": {"base_url": "https://raw.githubusercontent.com/u/FSPassion-data/main"}}
    assert dlcremote.base_url(ok) == "https://raw.githubusercontent.com/u/FSPassion-data/main/"
    for bad in ("http://raw.githubusercontent.com/u/r/main/", "https://example.com/u/r/main/",
                "https://raw.githubusercontent.com.evil.net/x/", "https://user:pw@raw.githubusercontent.com/x/", None):
        assert dlcremote.base_url({"remote_data": {"base_url": bad}}) is None
    info = config.load_app_info()
    assert dlcremote.base_url(info) is not None


def test_validate_catalog_filters_bad_entries():
    raw = {"schema": 1, "updated": "2026-11-01", "versions": {
        "FS25": {"icons_folder": "icons_dlc_fs25", "dlc": [
            {"file": "goodPack", "name": "Good Pack", "sha256": "A" * 64},
            {"file": "../evil", "name": "Evil"},
            {"file": "noName"},
            {"file": None, "keywords": ["beans"], "name": "Beans"},
            {"file": "x", "name": "X", "icon": "..\\..\\boot.ini"},
        ]},
        "FS99x": {"icons_folder": "icons_dlc_fs25", "dlc": []},
        "FS22": {"icons_folder": "../../etc", "dlc": []},
    }}
    cat = dlcremote.validate_catalog(raw)
    assert list(cat["versions"]) == ["FS25"]
    files = [e.get("file") for e in cat["versions"]["FS25"]["dlc"]]
    assert files == ["goodPack", None]
    assert cat["versions"]["FS25"]["dlc"][0]["sha256"] == "a" * 64
    with pytest.raises(dlcremote.RemoteError):
        dlcremote.validate_catalog({"schema": 2, "versions": {}})


def _catalog(updated="2099-01-01", sha=None):
    entry = {"file": "goodPack", "name": "Good Pack (distant)", "status": "released"}
    if sha:
        entry["sha256"] = sha
    return {"schema": 1, "updated": updated, "versions": {"FS25": {"icons_folder": "icons_dlc_fs25", "dlc": [
        entry, {"file": "otherPack", "name": "Other Pack", "status": "released"}]}}}


def test_update_catalog_once_a_day(monkeypatch):
    calls = []

    def fake_fetch(url, max_bytes):
        calls.append(url)
        return json.dumps(_catalog()).encode()

    monkeypatch.setattr(dlcremote, "fetch", fake_fetch)
    info = config.load_app_info()
    assert dlcremote.update_catalog(info)["status"] == "updated"
    assert dlcremote.update_catalog(info)["status"] == "recent"     # même jour
    assert len(calls) == 1 and calls[0].endswith("dlc/dlc_catalog.json")
    assert dlcremote.update_catalog(info, force=True)["status"] == "unchanged"
    cat = dlc.load_catalog()
    assert cat["_remote"] is True and cat["updated"] == "2099-01-01"
    meta = dlcremote.read_meta()
    assert meta["last_error"] is None and meta["fetched"]
    assert not dlcremote.due(meta) and dlcremote.due(meta, time.time() + dlcremote.REFRESH_S + 1)


def test_update_catalog_error_keeps_the_embedded_one(monkeypatch):
    def fail(url, max_bytes):
        raise dlcremote.RemoteError("not_found")

    monkeypatch.setattr(dlcremote, "fetch", fail)
    res = dlcremote.update_catalog(config.load_app_info())
    assert res == {"status": "error", "error": "not_found"}
    cat = dlc.load_catalog()
    assert cat.get("_remote") is False and cat["versions"]["FS25"]["dlc"]


def test_older_remote_catalog_does_not_win():
    target = config.dlc_cache_dir() / "dlc_catalog.json"
    fsutil.atomic_write_json(target, _catalog(updated="2000-01-01"))
    assert dlc.load_catalog().get("_remote") is False


def test_icons_for_detected_then_absent_dlc_and_checked(monkeypatch):
    png = fakemods.make_icon(3, 64, "png")
    fsutil.atomic_write_json(config.dlc_cache_dir() / "dlc_catalog.json", _catalog(sha=hashlib.sha256(png).hexdigest()))
    monkeypatch.setattr(dlc, "icon_dirs", lambda folder: [config.dlc_cache_dir() / folder])
    wanted = dlcremote.wanted_icons(dlc.load_catalog(), {"FS25": ["goodPack", "inconnu"]})
    # Le DLC détecté d'abord ; 0.8.2 : puis ceux du catalogue que l'on ne possède pas.
    assert [w["names"] for w in wanted] == [["goodPack.png", "goodPack.jpg"], ["otherPack.png", "otherPack.jpg"]]
    wanted = wanted[:1]

    served = {"goodPack.png": png}
    asked = []

    def fake_fetch(url, max_bytes):
        asked.append(url)
        name = url.rsplit("/", 1)[1]
        if name not in served:
            raise dlcremote.RemoteError("not_found")
        return served[name]

    monkeypatch.setattr(dlcremote, "fetch", fake_fetch)
    res = dlcremote.download_icons(config.load_app_info(), wanted)
    assert res["downloaded"] == 1
    assert (config.dlc_cache_dir() / "icons_dlc_fs25" / "goodPack.png").read_bytes() == png
    assert all("/dlc/icons_dlc_fs25/" in u for u in asked)
    # Déjà là, et conforme à son empreinte : rien à télécharger (reste otherPack).
    assert [w["names"][0] for w in dlcremote.wanted_icons(dlc.load_catalog(), {"FS25": ["goodPack"]})] == ["otherPack.png"]

    # Empreinte différente ou fichier qui n'est pas une image : refusé.
    (config.dlc_cache_dir() / "icons_dlc_fs25" / "goodPack.png").unlink()
    served["goodPack.png"] = fakemods.make_icon(4, 64, "png")
    assert dlcremote.download_icons(config.load_app_info(), wanted)["failed"] == 1
    item = {"version": "FS25", "folder": "icons_dlc_fs25", "names": ["otherPack.png"], "sha256": None}
    served["otherPack.png"] = b"<html>pas une image</html>"
    assert dlcremote.download_icons(config.load_app_info(), [item])["failed"] == 1
    assert not (config.dlc_cache_dir() / "icons_dlc_fs25" / "otherPack.png").exists()


def test_remote_data_respects_the_internet_setting(env, monkeypatch):
    core = env["core"]
    monkeypatch.setattr(dlcremote, "fetch", lambda *a: pytest.fail("aucun accès sans autorisation"))
    assert core.update_remote_data(force=True) == {"status": "disabled"}
    state = core.state()["dlc_catalog"]
    assert state["enabled"] is False and state["source_ok"] is True


# --------------------------------------------------------------------------
# Diagnostic, interface, routes
# --------------------------------------------------------------------------

def test_diagnostic_is_complete(env):
    text = env["core"].diagnostic()
    for needle in ("FS Passion", "Developer mode:", "Symlinks allowed:", "Internet access: no",
                   "DLC catalog:", "- FS25", "mods_dir:", "Recent errors"):
        assert needle in text


def test_interface_wiring():
    settings = _read("ui", "js", "settings.js")
    assert "soon(" not in settings
    assert "exportConfig" in settings and "importConfig" in settings and "openStopUsing" in settings
    assert "/api/dlc/refresh" in settings
    assert "/api/backup/export" in _read("ui", "js", "backup.js")
    assert "/api/backup/import" in _read("ui", "js", "backup.js")
    stop = _read("ui", "js", "stopuse.js")
    assert "/api/stop/preview" in stop and "/api/stop/quit" in stop
    assert "uninstall_mode" in _read("ui", "js", "main.js")
    assert "app-logo" in _read("ui", "js", "welcome.js")
    server = _read("src", "fspassion", "server.py")
    for route in ("/api/backup/export", "/api/backup/import-open", "/api/backup/import",
                  "/api/stop/preview", '"/api/stop"', "/api/stop/quit", "/api/dlc/refresh"):
        assert route in server


def test_notice_mentions_export_and_no_version_banner():
    for code in ("fr", "en"):
        blocks = json.loads(_read("lang", f"{code}.json"))["notice"]["blocks"]
        text = json.dumps(blocks, ensure_ascii=False)
        assert "0.6" not in text and "0.7" not in text
    fr = json.dumps(json.loads(_read("lang", "fr.json"))["notice"], ensure_ascii=False)
    assert "Exporter" in fr and "Ne plus utiliser FS Passion" in fr


# --------------------------------------------------------------------------
# Mesures de performance (diagnostic)
# --------------------------------------------------------------------------

def test_performance_measurements_reach_the_diagnostic(env):
    core = env["core"]
    core.record_ui_perf({"ready_ms": 812.4, "width": 1920, "height": 1080, "dpr": 1.25})
    core.record_ui_perf({"scroll": {"list": "l1", "frames": 120, "ms": 2000, "long": 2, "worst_ms": 41}})
    core.record_ui_perf({"scroll": {"list": "l1", "frames": 60, "ms": 1000, "long": 0, "worst_ms": 20}})
    core.record_ui_perf({"scroll": {"list": "x", "frames": 1, "ms": 1}})          # ignoré
    with pytest.raises(AppError):
        core.record_ui_perf("pas un objet")
    assert env["lib"].perf["scan_s"] is not None
    text = core.diagnostic()
    assert "Performance:" in text
    assert "UI ready: 812 ms" in text
    assert "Scrolling list 1: 2 times, 180 frames, 60.0 fps on average, 2 frames > 33 ms, worst 41 ms" in text
    assert re.search(r"Library FS25: \d+ mods, last scan [\d.]+ s", text)
    assert "Memory:" in text
    assert "/api/perf" in _read("src", "fspassion", "server.py")
    assert "initPerf()" in _read("ui", "js", "main.js")
