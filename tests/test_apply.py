"""« Appliquer » (0.3) : dossiers de parties, liens, override, journal.

Les invariants vérifiés ici :
- I1/I9 : les mods du dossier de mods ne sont ni déplacés, ni copiés, ni
  modifiés par « Appliquer » (même contenu, même date, même identifiant) ;
- I2 : un dossier de partie ne contient que des liens ;
- I4 : aucun fichier physique n'est supprimé (rapatrié ou mis de côté) ;
- I5 : rien ne bouge pendant que le jeu tourne ;
- I8 : une opération interrompue est terminée ou annulée ;
- I10 : vider un dossier de partie ne traverse jamais une jonction.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from fspassion import apply, gamesettings, links
from fspassion.core import AppError, Core
from fspassion.events import EventBus
from fspassion.parties import EMPTY, FULL

import fakemods

GS_TEXT = (
    '<?xml version="1.0" encoding="utf-8" standalone="no" ?>\n<gameSettings revision="15">\n'
    '    <modsDirectoryOverride active="true" directory="{mods}"/>\n'
    '    <motorStopTimerDuration>30000</motorStopTimerDuration>\n'
    '    <volume master="0.8" music="0.2"/>\n</gameSettings>\n'
)


def snapshot(folder: Path) -> dict[str, str]:
    """Empreinte de chaque fichier du dossier de mods (contenu, date, identifiant)."""
    out = {}
    for p in sorted(folder.rglob("*")):
        if p.is_file() and not p.is_symlink():
            st = p.stat()
            out[str(p.relative_to(folder))] = f"{st.st_mtime_ns}-{st.st_ino}-{hashlib.sha256(p.read_bytes()).hexdigest()}"
    return out


@pytest.fixture
def env(tmp_path):
    mods = tmp_path / "FS25_Mods" / "Mods"
    info = fakemods.make_collection(mods, count=12)
    user = tmp_path / "Documents" / "My Games" / "FarmingSimulator2025"
    user.mkdir(parents=True)
    gs = user / "gameSettings.xml"
    gs.write_text(GS_TEXT.format(mods=mods.as_posix()), encoding="utf-8")
    core = Core(dev=True, bus=EventBus())
    core.settings.set("first_detection_done", True)
    core.settings.update_version("FS25", {"mods_dir": str(mods), "user_dir": str(user)})
    core._ensure_backups()
    lib = core.libs.get("FS25")
    lib._scan()
    yield {"core": core, "mods": mods, "gs": gs, "info": info, "lib": lib,
           "parties": mods.parent / "FSPassion" / "FS25" / "Parties"}


def make_party(env, name="Hof Bergmann", n=4, common=0):
    core = env["core"]
    ids = env["info"]["ids"]
    res = core.party_create("FS25", name)
    pid = res["party"]["id"]
    core.party_mods("FS25", "add", "party", ids[:n], pid=pid)
    if common:
        core.party_mods("FS25", "add", "common", ids[n:n + common])
    return pid


def override_dir(gs: Path) -> str:
    ov = gamesettings.read_override(gs)
    assert ov is not None and ov.found
    return os.path.normpath(ov.directory or "")


# --------------------------------------------------------------------------
# Écriture de gameSettings.xml
# --------------------------------------------------------------------------

def test_write_override_is_surgical(tmp_path):
    gs = tmp_path / "gameSettings.xml"
    original = ("\ufeff<gameSettings>\r\n  <modsDirectoryOverride active='false' directory='C:/Temp' />\r\n"
                "  <player name=\"Élise\"/>\r\n</gameSettings>\r\n")
    gs.write_bytes(original.encode("utf-8"))
    gamesettings.ensure_original_backup(gs)
    gamesettings.write_override(gs, str(tmp_path / "Parties" / "a&b"), True)
    data = gs.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")                     # marque BOM gardée
    text = data.decode("utf-8-sig")
    assert "active='true'" in text and "a&amp;b'" in text       # apostrophes gardées
    assert '<player name="Élise"/>\r\n' in text                 # reste intact, CRLF gardés
    assert text.replace(text[text.index("<mods"):text.index("/>", text.index("<mods")) + 2], "") == \
        original.lstrip("\ufeff").replace("<modsDirectoryOverride active='false' directory='C:/Temp' />", "")
    # Sauvegarde avant modification, et sauvegarde d'origine jamais écrasée.
    assert gamesettings.backup_path(gs).read_bytes() == original.encode("utf-8")
    assert gamesettings.original_backup_path(gs).read_bytes() == original.encode("utf-8")
    gamesettings.write_override(gs, str(tmp_path / "Mods"), True)
    assert gamesettings.original_backup_path(gs).read_bytes() == original.encode("utf-8")


def test_write_override_restores_on_failed_check(tmp_path, monkeypatch):
    gs = tmp_path / "gameSettings.xml"
    gs.write_text('<gameSettings>\n<modsDirectoryOverride active="false" directory="C:/Temp"/>\n</gameSettings>\n')
    before = gs.read_bytes()
    monkeypatch.setattr(gamesettings, "read_override", lambda p: gamesettings.Override(found=False))
    with pytest.raises(gamesettings.WriteError) as err:
        gamesettings.write_override(gs, str(tmp_path / "X"), True)
    assert err.value.key == "override.check_failed"
    assert gs.read_bytes() == before


def test_write_override_adds_missing_line(tmp_path):
    gs = tmp_path / "gameSettings.xml"
    gs.write_text('<gameSettings revision="15">\n    <a/>\n</gameSettings>\n')
    gamesettings.write_override(gs, str(tmp_path / "M"), True)
    ov = gamesettings.read_override(gs)
    assert ov.found and ov.active and "<a/>" in gs.read_text()


# --------------------------------------------------------------------------
# Appliquer
# --------------------------------------------------------------------------

def test_apply_party_builds_links_only(env):
    core, mods, gs = env["core"], env["mods"], env["gs"]
    pid = make_party(env, n=4, common=3)
    before = snapshot(mods)
    res = core.party_apply("FS25")
    folder = env["parties"] / core._store("FS25").party(pid)["folder"]
    assert res["count"] == 7 and res["missing"] == []
    # I2 : uniquement des hardlinks vers les vrais mods (même identifiant).
    names = sorted(p.name for p in folder.iterdir())
    assert len(names) == 7
    for p in folder.iterdir():
        assert links.kind_of(p) == "file"
        assert links.file_id(p) == links.file_id(mods / p.name)
    # I1, I9 : le dossier de mods est intact.
    assert snapshot(mods) == before
    assert override_dir(gs) == os.path.normpath(str(folder))
    st = core.parties_state("FS25")
    assert st["applied"] == pid and st["needs_apply"] is False
    assert st["applied_history"][0] == pid
    assert not (mods.parent / "FSPassion" / "FS25" / apply.JOURNAL).exists()
    inv = links.Inventory(mods.parent / "FSPassion" / "FS25" / apply.INVENTORY).folder(folder.name)
    assert set(inv) == set(names)
    # Changer la partie : « Appliquer » est de nouveau mis en évidence.
    core.party_mods("FS25", "add", "party", env["info"]["ids"][8:9], pid=pid)
    st = core.parties_state("FS25")
    assert st["applied_stale"] is True and st["needs_apply"] is True
    core.party_apply("FS25")
    assert len(list(folder.iterdir())) == 8
    assert core.parties_state("FS25")["needs_apply"] is False
    assert snapshot(mods) == before


def test_apply_full_and_empty(env):
    core, mods, gs = env["core"], env["mods"], env["gs"]
    make_party(env)
    core.party_apply("FS25")
    core.party_apply("FS25", EMPTY)
    assert override_dir(gs) == os.path.normpath(str(env["parties"] / "_vide"))
    assert list((env["parties"] / "_vide").iterdir()) == []
    assert core.parties_state("FS25")["applied"] == EMPTY
    core.party_apply("FS25", FULL)
    assert override_dir(gs) == os.path.normpath(str(mods))
    assert core.parties_state("FS25")["applied"] == FULL


def test_unpacked_mod_uses_junction_and_survives_delete(env):
    """I10 : vider un dossier de partie ne traverse jamais une jonction."""
    core, mods = env["core"], env["mods"]
    pid = make_party(env, n=2)
    core.party_mods("FS25", "add", "party", ["FS25_DevMod"], pid=pid)
    core.party_apply("FS25")
    folder = env["parties"] / core._store("FS25").party(pid)["folder"]
    link = folder / "FS25_DevMod"
    assert links.is_link(link)
    content = sorted(p.name for p in (mods / "FS25_DevMod").iterdir())
    assert content
    core.party_delete("FS25", pid)
    assert not folder.exists()
    assert sorted(p.name for p in (mods / "FS25_DevMod").iterdir()) == content
    # La partie appliquée a été supprimée : retour à la Partie Pleine.
    assert override_dir(env["gs"]) == os.path.normpath(str(mods))


def test_delete_applied_party_reapplies_previous(env):
    core = env["core"]
    a = make_party(env, "Etruria", n=3)
    core.party_apply("FS25", a)
    b = make_party(env, "Hof Bergmann", n=2)
    core.party_apply("FS25", b)
    res = core.party_delete("FS25", b)
    assert res["was_applied"] and res["fallback"] == a
    folder_a = env["parties"] / core._store("FS25").party(a)["folder"]
    assert override_dir(env["gs"]) == os.path.normpath(str(folder_a))
    assert core.parties_state("FS25")["applied"] == a


def test_rename_moves_folder_and_override(env):
    core = env["core"]
    pid = make_party(env, "Hof Bergmann")
    core.party_apply("FS25")
    old = env["parties"] / core._store("FS25").party(pid)["folder"]
    core.party_rename("FS25", pid, "Ferme du Lac")
    new = env["parties"] / core._store("FS25").party(pid)["folder"]
    assert new.name.startswith("ferme-du-lac-") and new.is_dir() and not old.exists()
    assert override_dir(env["gs"]) == os.path.normpath(str(new))
    assert core.parties_state("FS25")["applied"] == pid


def test_running_game_blocks_everything(env):
    """I5 : rien ne bouge pendant que le jeu tourne."""
    core = env["core"]
    pid = make_party(env)
    core.party_apply("FS25")
    gs_before = env["gs"].read_bytes()
    core.monitor.running = {"FS25"}
    with pytest.raises(AppError) as err:
        core.party_apply("FS25", FULL)
    assert err.value.key == "apply.running"
    with pytest.raises(AppError):
        core.party_rename("FS25", pid, "Autre nom")
    with pytest.raises(AppError):
        core.party_delete("FS25", pid)
    assert env["gs"].read_bytes() == gs_before


# --------------------------------------------------------------------------
# Fichiers déposés par le jeu dans le dossier de la partie (I2, I4)
# --------------------------------------------------------------------------

def test_game_update_is_repatriated(env):
    """Cas T3bis : le ModHub dépose une nouvelle version dans le dossier de la
    partie. Elle remplace le mod du dossier de mods ; l'ancienne est gardée."""
    core, mods = env["core"], env["mods"]
    pid = make_party(env, n=3)
    core.party_apply("FS25")
    folder = env["parties"] / core._store("FS25").party(pid)["folder"]
    target = sorted(folder.iterdir())[0]
    name = target.name
    old_bytes = (mods / name).read_bytes()
    os.unlink(target)  # le jeu remplace le fichier par un nouveau
    fakemods.make_zip_mod(folder, name[:-4], title="Mise à jour", seed=77, version="9.0.0.0")
    new_bytes = target.read_bytes()
    res = core.party_apply("FS25")
    assert res["tidy"]["updated"] == [name]
    assert (mods / name).read_bytes() == new_bytes
    olds = list((mods.parent / "FSPassion" / "FS25" / apply.OLD_VERSIONS).rglob(name))
    assert len(olds) == 1 and olds[0].read_bytes() == old_bytes
    assert links.file_id(folder / name) == links.file_id(mods / name)


def test_older_version_is_set_aside(env):
    core, mods = env["core"], env["mods"]
    pid = make_party(env, n=2)
    core.party_apply("FS25")
    folder = env["parties"] / core._store("FS25").party(pid)["folder"]
    name = sorted(folder.iterdir())[0].name
    before = (mods / name).read_bytes()
    os.unlink(folder / name)
    fakemods.make_zip_mod(folder, name[:-4], seed=5, version="0.0.0.1")
    res = core.party_apply("FS25")
    assert res["tidy"]["set_aside"] == [name]
    assert (mods / name).read_bytes() == before
    assert list((mods.parent / "FSPassion" / "FS25" / apply.RECOVERED).rglob(name))


def test_unknown_mod_joins_the_party(env):
    """Mod téléchargé par le jeu (multijoueur) : rapatrié et ajouté à la partie."""
    core, mods = env["core"], env["mods"]
    pid = make_party(env, n=2)
    core.party_apply("FS25")
    folder = env["parties"] / core._store("FS25").party(pid)["folder"]
    fakemods.make_zip_mod(folder, "FS25_ServerMod", seed=9)
    res = core.party_apply("FS25")
    assert res["tidy"]["added"] == ["FS25_ServerMod"]
    assert (mods / "FS25_ServerMod.zip").is_file()
    assert "FS25_ServerMod" in core._store("FS25").party(pid)["mods"]


def test_orphan_link_is_rebuilt_and_kept(env):
    """Cas T3 : l'archive du dossier de mods a été réécrite (nouveau fichier).
    Le lien devenu orphelin est refait ; l'ancienne version n'est pas perdue."""
    core, mods = env["core"], env["mods"]
    pid = make_party(env, n=2)
    core.party_apply("FS25")
    folder = env["parties"] / core._store("FS25").party(pid)["folder"]
    name = sorted(folder.iterdir())[0].name
    old_bytes = (mods / name).read_bytes()
    data = old_bytes + b"\0"
    os.unlink(mods / name)
    (mods / name).write_bytes(data)  # nouveau fichier, nouvel identifiant
    env["lib"]._scan()
    core.party_apply("FS25")
    assert links.file_id(folder / name) == links.file_id(mods / name)
    olds = list((mods.parent / "FSPassion" / "FS25" / apply.OLD_VERSIONS).rglob(name))
    assert len(olds) == 1 and olds[0].read_bytes() == old_bytes


# --------------------------------------------------------------------------
# Échecs et reprise (I8)
# --------------------------------------------------------------------------

def test_link_failure_changes_nothing(env, monkeypatch):
    core, mods, gs = env["core"], env["mods"], env["gs"]
    pid = make_party(env, n=3)
    core.party_apply("FS25")
    folder = env["parties"] / core._store("FS25").party(pid)["folder"]
    before_links = sorted(p.name for p in folder.iterdir())
    gs_before = gs.read_bytes()
    core.party_mods("FS25", "add", "party", env["info"]["ids"][5:7], pid=pid)

    def broken(src, dst):
        raise OSError(18, "Invalid cross-device link")

    monkeypatch.setattr(os, "link", broken)
    with pytest.raises(AppError) as err:
        core.party_apply("FS25")
    assert err.value.key == "apply.not_same_disk"
    assert sorted(p.name for p in folder.iterdir()) == before_links
    assert gs.read_bytes() == gs_before
    assert not any(p.name.startswith(".tmp-") for p in env["parties"].iterdir())
    assert not (mods.parent / "FSPassion" / "FS25" / apply.JOURNAL).exists()


def test_interrupted_build_is_cancelled(env):
    core, mods = env["core"], env["mods"]
    pid = make_party(env, n=3)
    before = snapshot(mods)
    fsp = mods.parent / "FSPassion" / "FS25"
    tmp = env["parties"] / f".tmp-{pid}"
    tmp.mkdir(parents=True)
    for name in sorted(os.listdir(mods))[:2]:
        if (mods / name).is_file():
            os.link(mods / name, tmp / name)
    from fspassion import fsutil
    fsutil.atomic_write_json(fsp / apply.JOURNAL, {"op": "apply", "party": pid, "folder": "x", "step": "build"})
    core._parties.clear()
    st = core.parties_state("FS25")
    assert st["notice"]["key"] == "apply.recovered_cancelled"
    assert not tmp.exists() and not (fsp / apply.JOURNAL).exists()
    assert snapshot(mods) == before


def test_interrupted_swap_is_finished(env):
    core, gs = env["core"], env["gs"]
    pid = make_party(env, n=3)
    folders = core._folders("FS25")
    folder_name = core._store("FS25").party(pid)["folder"]
    tmp = env["parties"] / f".tmp-{pid}"
    entries, _, _ = folders._build(tmp, folders.active_ids(pid))
    from fspassion import fsutil
    fsutil.atomic_write_json(folders.journal_path, {"op": "apply", "party": pid, "folder": folder_name, "step": "swap"})
    core._parties.clear()
    st = core.parties_state("FS25")
    assert st["notice"]["key"] == "apply.recovered_finished"
    final = env["parties"] / folder_name
    assert final.is_dir() and len(list(final.iterdir())) == 3 and not tmp.exists()
    assert override_dir(gs) == os.path.normpath(str(final))
    assert st["applied"] == pid


def test_override_check_proposes_choices(env, tmp_path):
    core, gs = env["core"], env["gs"]
    make_party(env)
    other = tmp_path / "AutreDossier"
    other.mkdir()
    gamesettings.write_override(gs, str(other), True)
    st = core.parties_state("FS25")
    assert st["override_check"]["directory"] == os.path.normpath(str(other))
    core.override_resolve("FS25", "ignore", st["override_check"]["directory"], None)
    assert core.parties_state("FS25")["override_check"] is None
    core.override_resolve("FS25", "reapply", None, FULL)
    assert override_dir(gs) == os.path.normpath(str(env["mods"]))
