"""Version 0.6 : stockage des mods sur plusieurs disques (4.20).

Sous Linux, tous les dossiers de test sont sur le même disque : « Disque2 »
dans un chemin simule un autre disque (lien symbolique au lieu d'un hardlink).

Vérifié ici :
- les mods d'un stockage supplémentaire sont listés, et liés par un lien
  symbolique (autre disque) ou un hardlink (même disque) ;
- sans droits pour les liens symboliques, ces mods sont « bloqués » : la partie
  s'applique quand même avec les autres, rien n'est touché ;
- la Partie Pleine devient un dossier de liens « _pleine », puis redevient le
  dossier de mods quand il n'y a plus qu'un stockage ;
- une mise à jour déposée par le jeu rejoint le stockage d'où venait le mod,
  l'ancienne version va dans « Anciennes versions » (sur le disque principal) ;
- renommer un mod d'un autre disque refait ses liens symboliques ;
- l'intégration d'un téléchargement peut viser un stockage supplémentaire ;
- les chemins n° 2 et n° 3 sont contrôlés (chevauchement, nombre).
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

import pytest

from fspassion import apply, gamepaths, links, storage, versions
from fspassion.core import AppError, Core
from fspassion.events import EventBus
from fspassion.parties import FULL

import fakemods

GS_TEXT = (
    '<?xml version="1.0" encoding="utf-8" standalone="no" ?>\n<gameSettings revision="15">\n'
    '    <modsDirectoryOverride active="true" directory="{mods}"/>\n</gameSettings>\n'
)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def env(tmp_path, monkeypatch):
    mods = tmp_path / "FS25_Mods" / "Mods"
    info = fakemods.make_collection(mods, count=6)
    extra = tmp_path / "Disque2" / "FS25_Mods2"
    extra.mkdir(parents=True)
    extra_ids = []
    for i in range(3):
        mod_id = f"FS25_Extra{i}"
        fakemods.make_zip_mod(extra, mod_id, title=f"Extra {i}", seed=500 + i, version="1.0.0.0")
        extra_ids.append(mod_id)
    user = tmp_path / "Documents" / "FarmingSimulator2025"
    user.mkdir(parents=True)
    gs = user / "gameSettings.xml"
    gs.write_text(GS_TEXT.format(mods=mods.as_posix()), encoding="utf-8")
    dl = tmp_path / "Downloads"
    dl.mkdir()
    # « Disque2 » dans le chemin = autre disque.
    monkeypatch.setattr(storage, "on_other_disk", lambda vp, p: "Disque2" in str(p))
    storage.set_symlinks_allowed(True)
    core = Core(dev=True, bus=EventBus())
    core.settings.set("first_detection_done", True)
    core.settings.set("downloads_dir", str(dl))
    core.settings.update_version("FS25", {"mods_dir": str(mods), "user_dir": str(user)})
    core.set_storages("FS25", [str(extra)])
    core._reconciled.add("FS25")
    lib = core.libs.get("FS25")
    lib._scan()
    fsp = mods.parent / "FSPassion" / "FS25"
    yield {"core": core, "mods": mods, "extra": extra, "ids": info["ids"], "extra_ids": extra_ids,
           "gs": gs, "lib": lib, "user": user, "dl": dl, "fsp": fsp, "parties": fsp / "Parties",
           "tmp": tmp_path}
    storage.set_symlinks_allowed(None)


def party(env, name, ids):
    core = env["core"]
    pid = core.party_create("FS25", name)["party"]["id"]
    core.party_mods("FS25", "add", "party", list(ids), pid=pid)
    return pid


def folder_of(env, pid):
    return env["parties"] / env["core"]._store("FS25").party(pid)["folder"]


def override(gs: Path) -> str:
    from fspassion import gamesettings

    ov = gamesettings.read_override(gs)
    assert ov is not None
    return os.path.normpath(ov.directory or "")


# --------------------------------------------------------------------------


def test_extra_storage_mods_are_listed(env):
    lib = env["core"].library("FS25")
    by_id = {e["id"]: e for e in lib["mods"]}
    for mod_id in env["extra_ids"]:
        assert by_id[mod_id]["storage"] == 1
    assert len(lib["storages"]) == 2


def test_party_links_extra_mods_with_symlinks(env):
    fakemods.need_symlinks()
    core, extra = env["core"], env["extra"]
    before = {p.name: sha(p) for p in extra.iterdir()}
    pid = party(env, "Multi", env["ids"][:2] + env["extra_ids"][:2])
    res = core.party_apply("FS25", pid)
    assert res["count"] == 4 and res["blocked"] == []
    folder = folder_of(env, pid)
    for mod_id in env["extra_ids"][:2]:
        item = folder / f"{mod_id}.zip"
        assert links.kind_of(item) == "symlink"
        assert os.path.samefile(links.link_target(item), extra / f"{mod_id}.zip")
    for mod_id in env["ids"][:2]:
        item = folder / f"{mod_id}.zip"
        assert links.kind_of(item) == "file"
        assert links.file_id(item) == links.file_id(env["mods"] / f"{mod_id}.zip")
    # Le stockage supplémentaire n'a reçu aucun fichier, et rien n'a changé.
    assert {p.name: sha(p) for p in extra.iterdir()} == before
    inv = apply.Inventory(env["fsp"] / apply.INVENTORY).folder(folder.name)
    assert inv[f"{env['extra_ids'][0]}.zip"]["kind"] == "symlink"


def test_same_disk_extra_storage_uses_hardlinks(env, monkeypatch):
    monkeypatch.setattr(storage, "on_other_disk", lambda vp, p: False)
    core = env["core"]
    pid = party(env, "Même disque", env["extra_ids"][:1])
    core.party_apply("FS25", pid)
    item = folder_of(env, pid) / f"{env['extra_ids'][0]}.zip"
    assert links.kind_of(item) == "file"
    assert links.file_id(item) == links.file_id(env["extra"] / item.name)


def test_without_symlink_rights_extra_mods_are_blocked(env):
    storage.set_symlinks_allowed(False)
    core = env["core"]
    pid = party(env, "Sans droits", env["ids"][:2] + env["extra_ids"][:1])
    res = core.party_apply("FS25", pid)
    assert res["blocked"] == [env["extra_ids"][0]]
    assert res["count"] == 2
    names = {p.name for p in folder_of(env, pid).iterdir()}
    assert f"{env['extra_ids'][0]}.zip" not in names
    assert override(env["gs"]) == os.path.normpath(str(folder_of(env, pid)))


def test_full_party_becomes_a_link_folder(env):
    fakemods.need_symlinks()
    core = env["core"]
    res = core.party_apply("FS25", FULL)
    full = env["parties"] / apply.FULL_FOLDER
    assert override(env["gs"]) == os.path.normpath(str(full))
    names = {p.name for p in full.iterdir()}
    for mod_id in env["ids"] + env["extra_ids"]:
        assert f"{mod_id}.zip" in names
    assert res["count"] == len(names)
    assert core.applied_state("FS25")["kind"] == "full"
    # Un mod nouveau dans un stockage : la Partie Pleine est à réappliquer.
    folders = core._folders("FS25")
    assert not folders.is_stale(FULL)
    fakemods.make_zip_mod(env["extra"], "FS25_Nouveau", seed=77)
    env["lib"]._scan()
    assert core._folders("FS25").is_stale(FULL)


def test_back_to_one_storage_full_party_is_the_mods_folder(env):
    core = env["core"]
    core.party_apply("FS25", FULL)
    full = env["parties"] / apply.FULL_FOLDER
    assert full.is_dir()
    extra_files = {p.name: sha(p) for p in env["extra"].iterdir()}
    core.set_storages("FS25", [])
    env["lib"]._scan()
    assert core._folders("FS25").is_stale(FULL)
    core.party_apply("FS25", FULL)
    assert override(env["gs"]) == os.path.normpath(str(env["mods"]))
    assert not os.path.lexists(full)
    assert {p.name: sha(p) for p in env["extra"].iterdir()} == extra_files


def test_game_update_returns_to_its_own_storage(env):
    """Le ModHub remplace, dans le dossier de partie, le lien d'un mod d'un autre
    disque par la nouvelle version : elle rejoint SON stockage."""
    fakemods.need_symlinks()
    core, extra = env["core"], env["extra"]
    mod_id = env["extra_ids"][0]
    name = f"{mod_id}.zip"
    a = party(env, "A", [mod_id, env["ids"][0]])
    b = party(env, "B", [mod_id])
    core.party_apply("FS25", a)
    core.party_apply("FS25", b)
    old = sha(extra / name)
    item = folder_of(env, b) / name
    links.remove_link(item)
    fakemods.make_zip_mod(folder_of(env, b), mod_id, title="MAJ", seed=901, version="2.0.0.0")
    new = sha(item)
    rep = core.reconcile("FS25")
    assert rep["updated"] == [name]
    assert sha(extra / name) == new                         # dans son stockage
    assert not os.path.lexists(env["mods"] / name)          # pas dans le principal
    olds = list((env["fsp"] / apply.OLD_VERSIONS).rglob(name))
    assert len(olds) == 1 and sha(olds[0]) == old           # mise de côté (disque principal)
    assert not any(p.name.startswith(".fsp-") for p in extra.iterdir())
    for pid in (a, b):
        link = folder_of(env, pid) / name
        assert links.kind_of(link) == "symlink"
        assert sha(link) == new


def test_rename_extra_mod_recreates_symlinks(env):
    fakemods.need_symlinks()
    core, extra = env["core"], env["extra"]
    mod_id = env["extra_ids"][1]
    pid = party(env, "Renommage", [mod_id])
    core.party_apply("FS25", pid)
    res = core.mod_rename("FS25", mod_id, "FS25_ExtraPerso")
    assert res["new"] == "FS25_ExtraPerso"
    assert (extra / "FS25_ExtraPerso.zip").is_file()
    link = folder_of(env, pid) / "FS25_ExtraPerso.zip"
    assert links.kind_of(link) == "symlink"
    assert os.path.samefile(links.link_target(link), extra / "FS25_ExtraPerso.zip")
    assert not os.path.lexists(folder_of(env, pid) / f"{mod_id}.zip")


def test_delete_extra_mod_removes_symlinks(env, monkeypatch):
    from fspassion import winapi

    monkeypatch.setattr(winapi, "recycle_bin_available", lambda p: False)
    core, extra = env["core"], env["extra"]
    mod_id = env["extra_ids"][2]
    pid = party(env, "Suppression", [mod_id, env["ids"][0]])
    core.party_apply("FS25", pid)
    res = core.mods_delete("FS25", [mod_id], True)
    assert res["deleted"] == [mod_id]
    assert not os.path.lexists(extra / f"{mod_id}.zip")
    assert not os.path.lexists(folder_of(env, pid) / f"{mod_id}.zip")
    assert (env["mods"] / f"{env['ids'][0]}.zip").is_file()


def test_download_integrated_into_extra_storage(env):
    core, dl, extra = env["core"], env["dl"], env["extra"]
    fakemods.make_zip_mod(dl, "FS25_Telecharge", seed=321)
    t = time.time() - 60
    os.utime(dl / "FS25_Telecharge.zip", (t, t))
    scan = core.downloads_scan()
    fs25 = next(v for v in scan["versions"] if v["id"] == "FS25")
    assert len(fs25["storages"]) == 2
    res = core.downloads_integrate([{"file": "FS25_Telecharge.zip", "version": "FS25",
                                     "destination": "none", "storage": 1}])
    assert res["count"] == 1
    assert (extra / "FS25_Telecharge.zip").is_file()
    assert not (env["mods"] / "FS25_Telecharge.zip").exists()
    with pytest.raises(AppError):
        core.downloads_integrate([{"file": "x.zip", "version": "FS25", "destination": "none", "storage": 7}])


def test_storages_are_checked(env):
    core, mods, tmp = env["core"], env["mods"], env["tmp"]
    third = tmp / "Disque3" / "FS25_Mods3"
    third.mkdir(parents=True)
    st = core.set_storages("FS25", [str(env["extra"]), str(third)])
    assert [x["level"] for x in st["storage"]["extra"]] == ["ok", "ok"]
    assert st["storage"]["needs_symlinks"] is True
    assert "rights" in st
    with pytest.raises(AppError):
        core.set_storages("FS25", [str(env["extra"]), str(third), str(tmp)])
    with pytest.raises(AppError):
        core.set_storages("FS25", "pas une liste")
    # Chevauchements : le principal, un dossier qui le contient, un doublon.
    st = core.set_storages("FS25", [str(mods.parent), str(env["extra"])])
    assert st["storage"]["extra"][0]["key"] == "path.storage_overlap"
    st = core.set_storages("FS25", [str(env["extra"]), str(env["extra"] / "sous-dossier")])
    assert st["storage"]["extra"][1]["key"] == "path.storage_duplicate"
    vp = core.paths("FS25")
    assert vp.storages == [mods, env["extra"]]          # chemins écartés
    st = core.set_storages("FS25", [str(tmp / "absent")])
    assert st["storage"]["extra"][0]["key"] == "path.not_found"
    assert core.settings.version("FS25")["extra_mods_dirs"] == [str(tmp / "absent")]


def test_storage_paths_without_overlap():
    v = versions.require("FS25")
    vp = gamepaths.VersionPaths(v, None, None, Path("/d/FS25/Mods"),
                                [Path("/d/FS25/FSPassion/x"), Path("/f/Mods2"), Path("/f/Mods2/a")])
    assert vp.storages == [Path("/d/FS25/Mods"), Path("/f/Mods2")]


def test_rights_actions(env):
    fakemods.need_symlinks()
    core = env["core"]
    r = core.rights_action("check")
    assert r["symlinks"] is True and r["needed"] is True
    with pytest.raises(AppError):
        core.rights_action("n_importe_quoi")
    state = core.state()
    assert "rights" in state
    fs25 = next(v for v in state["versions"] if v["id"] == "FS25")
    assert fs25["storage"]["max_extra"] == 2


def test_full_party_flagged_when_second_storage_added(env):
    """Le jeu charge encore le seul dossier principal : la Partie Pleine est
    signalée « à appliquer » tant que son dossier de liens n'existe pas."""
    st = env["core"].parties_state("FS25")
    assert st["applied"] == FULL and st["needs_apply"] is True
    env["core"].party_apply("FS25", FULL)
    assert env["core"].parties_state("FS25")["needs_apply"] is False


# --------------------------------------------------------------------------
# 0.6.1 : relance en administrateur en développement
# --------------------------------------------------------------------------

def test_admin_in_dev_mode_never_sets_the_interpreter_flag(env, monkeypatch):
    """En développement, la case « administrateur » serait posée sur Python et
    empêcherait lancer_dev.bat de démarrer (bogue de la 0.6.0)."""
    from fspassion import config, winapi

    calls = []
    monkeypatch.setattr(winapi, "set_run_as_admin_flag", lambda enabled: calls.append(enabled) or True)
    monkeypatch.setattr(config, "is_frozen", lambda: False)
    out = env["core"].rights_action("admin")
    assert out["restart"] is True and out["once"] is True
    assert calls == []
    assert env["core"].restart_elevated is True


def test_admin_in_built_app_sets_the_flag(env, monkeypatch):
    from fspassion import config, winapi

    calls = []
    monkeypatch.setattr(winapi, "set_run_as_admin_flag", lambda enabled: calls.append(enabled) or True)
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    out = env["core"].rights_action("admin")
    assert calls == [True] and out["once"] is False


def test_dev_relaunch_goes_through_lancer_dev(tmp_path, monkeypatch):
    """La relance en développement passe par lancer_dev.bat, qui prépare
    l'environnement (PYTHONPATH…) que Windows ne transmet pas à un programme
    relancé en administrateur."""
    from fspassion import winapi

    monkeypatch.setenv("COMSPEC", r"C:\Windows\system32\cmd.exe")
    bat = tmp_path / "Mon dossier" / "lancer_dev.bat"
    exe, params, cwd = winapi.elevated_command(bat)
    assert exe.lower().endswith("cmd.exe")
    assert params == f'/c ""{bat}""'
    assert cwd == str(bat.parent)


def test_stale_interpreter_flag_is_removed_at_startup(monkeypatch):
    from fspassion import config, winapi

    calls = []
    monkeypatch.setattr(config, "is_frozen", lambda: False)
    monkeypatch.setattr(winapi, "run_as_admin_flag", lambda: True)
    monkeypatch.setattr(winapi, "set_run_as_admin_flag", lambda enabled: calls.append(enabled) or True)
    core = Core(dev=True, bus=EventBus())
    core.startup()
    assert calls == [False]
    core.shutdown()


# --------------------------------------------------------------------------
# 0.6.2 : version plus ancienne déposée par le jeu
# --------------------------------------------------------------------------

def _older_case(env):
    """Cas : le mod de F: porte la version 1.5.0.0 (modifiée à la main) ; le
    ModHub dépose son original, 1.0.0.0, dans la Partie Pleine appliquée."""
    fakemods.need_symlinks()
    core, extra = env["core"], env["extra"]
    name = "FS25_Joskin.zip"
    fakemods.make_zip_mod(extra, "FS25_Joskin", title="Joskin", seed=640, version="1.5.0.0")
    env["lib"]._scan()
    core.party_apply("FS25", FULL)
    full = env["parties"] / apply.FULL_FOLDER
    assert links.kind_of(full / name) == "symlink"
    links.remove_link(full / name)
    fakemods.make_zip_mod(full, "FS25_Joskin", title="Joskin ModHub", seed=641, version="1.0.0.0")
    modhub = sha(full / name)
    mine = sha(extra / name)
    rep = core.reconcile("FS25")
    return name, modhub, mine, rep


def test_older_version_waits_for_your_decision(env):
    core, extra = env["core"], env["extra"]
    name, modhub, mine, rep = _older_case(env)
    assert rep["older"] == [name] and rep["updated"] == []
    assert sha(extra / name) == mine                     # la version 1.5.0.0 n'est pas touchée
    older = core.parties_state("FS25")["older"]
    assert len(older) == 1 and older[0]["new"] == "1.0.0.0" and older[0]["old"] == "1.5.0.0"
    assert Path(older[0]["path"]).parent.parent.name == apply.RECOVERED == "Recovered"
    assert sha(Path(older[0]["path"])) == modhub
    # La partie garde ce mod : le lien vers la version du mod est refait.
    link = env["parties"] / apply.FULL_FOLDER / name
    assert links.kind_of(link) == "symlink" and sha(link) == mine


def _wait_ready(lib, timeout=15.0):
    """0.8 : la réconciliation relance un scan en arrière-plan ; « Appliquer »
    est refusé tant qu'il tourne (apply.library_busy). Le test échouait une
    fois sur trois environ, selon la vitesse du scan : on l'attend."""
    import time

    deadline = time.monotonic() + timeout
    while lib.status != "ready" and time.monotonic() < deadline:
        time.sleep(0.05)
    assert lib.status == "ready"


def test_use_game_version_replaces_yours_in_its_own_storage(env):
    core, extra = env["core"], env["extra"]
    name, modhub, mine, _ = _older_case(env)
    path = core.parties_state("FS25")["older"][0]["path"]
    pid = party(env, "Avec Joskin", ["FS25_Joskin"])
    _wait_ready(env["lib"])
    core.party_apply("FS25", pid)
    res = core.older_resolve("FS25", path, "use")
    assert res["state"]["older"] == []
    assert sha(extra / name) == modhub                   # sur F:, dans son stockage
    olds = list((env["fsp"] / apply.OLD_VERSIONS).rglob(name))
    assert len(olds) == 1 and sha(olds[0]) == mine       # la 1.5.0.0 est gardée dans Old versions
    for folder in (env["parties"] / apply.FULL_FOLDER, folder_of(env, pid)):
        assert sha(folder / name) == modhub
    assert not any(p.name.startswith(".fsp-") for p in extra.iterdir())


def test_keep_your_version(env):
    core, extra = env["core"], env["extra"]
    name, modhub, mine, _ = _older_case(env)
    path = core.parties_state("FS25")["older"][0]["path"]
    core.older_resolve("FS25", path, "keep")
    assert core.parties_state("FS25")["older"] == []
    assert sha(extra / name) == mine
    assert Path(path).is_file()                          # rien n'est effacé
    with pytest.raises(AppError):
        core.older_resolve("FS25", path, "use")          # décision déjà prise
    with pytest.raises(AppError):
        core.older_resolve("FS25", str(extra / name), "nimporte")


def test_legacy_aside_folders_are_renamed(tmp_path):
    fsp = tmp_path / "FSPassion" / "FS25"
    (fsp / "Recuperes" / "2026-10-21").mkdir(parents=True)
    (fsp / "Recuperes" / "2026-10-21" / "a.zip").write_bytes(b"x")
    (fsp / "Anciennes versions").mkdir()
    apply.migrate_aside_folders(fsp)
    assert (fsp / "Recovered" / "2026-10-21" / "a.zip").is_file()
    assert (fsp / "Old versions").is_dir()
    assert not (fsp / "Recuperes").exists() and not (fsp / "Anciennes versions").exists()
