"""Version 0.4 : réconciliation, téléchargements et intégration, suppression
définitive, renommage d'un mod.

Invariants vérifiés ici :
- I1/I9 : un mod n'existe qu'à un seul endroit, son contenu n'est jamais
  modifié (renommer ne change que le nom) ;
- I4 : rien n'est supprimé sans « Supprimer définitivement » (anciennes versions
  mises de côté, copies d'un mod supprimé à la main laissées en place) ;
- I5 : rien ne bouge pendant que le jeu tourne ;
- I8 : un renommage interrompu est terminé au démarrage suivant ;
- I10 : supprimer un mod non compressé ne suit jamais un lien qu'il contient.
"""

from __future__ import annotations

import errno
import hashlib
import os
import time
from pathlib import Path

import pytest

from fspassion import apply, downloads, fsutil, gamesettings, links, modops
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


def age(p: Path, seconds: int = 60) -> None:
    """Fichier « stable » : modifié il y a plus de 10 secondes."""
    t = time.time() - seconds
    os.utime(p, (t, t))


@pytest.fixture
def env(tmp_path):
    mods = tmp_path / "FS25_Mods" / "Mods"
    info = fakemods.make_collection(mods, count=12)
    user = tmp_path / "Documents" / "My Games" / "FarmingSimulator2025"
    user.mkdir(parents=True)
    gs = user / "gameSettings.xml"
    gs.write_text(GS_TEXT.format(mods=mods.as_posix()), encoding="utf-8")
    dl = tmp_path / "Downloads"
    dl.mkdir()
    core = Core(dev=True, bus=EventBus())
    core.settings.set("first_detection_done", True)
    core.settings.set("downloads_dir", str(dl))
    core.settings.update_version("FS25", {"mods_dir": str(mods), "user_dir": str(user)})
    core._reconciled.add("FS25")  # pas de réconciliation automatique en arrière-plan
    lib = core.libs.get("FS25")
    lib._scan()
    fsp = mods.parent / "FSPassion" / "FS25"
    yield {"core": core, "mods": mods, "gs": gs, "info": info, "lib": lib, "user": user, "dl": dl,
           "fsp": fsp, "parties": fsp / "Parties"}


def party(env, name, ids, common=()):
    core = env["core"]
    pid = core.party_create("FS25", name)["party"]["id"]
    core.party_mods("FS25", "add", "party", list(ids), pid=pid)
    if common:
        core.party_mods("FS25", "add", "common", list(common))
    return pid


def folder_of(env, pid):
    return env["parties"] / env["core"]._store("FS25").party(pid)["folder"]


def two_applied_parties(env):
    """Deux parties appliquées tour à tour, qui partagent un mod. La partie B
    reste appliquée."""
    core, ids = env["core"], env["info"]["ids"]
    a = party(env, "Partie A", ids[:3])
    b = party(env, "Partie B", ids[:2] + ids[5:6])
    core.party_apply("FS25", a)
    core.party_apply("FS25", b)
    return a, b


# --------------------------------------------------------------------------
# Réconciliation (4.9)
# --------------------------------------------------------------------------

def test_update_in_one_party_relinks_every_party(env):
    """T3bis complet : le ModHub dépose une mise à jour dans la partie appliquée.
    La réconciliation la rapatrie, et les liens de l'autre partie suivent."""
    core, mods = env["core"], env["mods"]
    a, b = two_applied_parties(env)
    name = f"{env['info']['ids'][0]}.zip"                  # dans les deux parties
    shared = folder_of(env, b) / name
    old = (mods / name).read_bytes()
    os.unlink(shared)
    fakemods.make_zip_mod(folder_of(env, b), name[:-4], title="MAJ", seed=99, version="9.9.0.0")
    new = sha(shared)
    rep = core.reconcile("FS25")
    assert rep["updated"] == [name]
    assert sha(mods / name) == new
    for pid in (a, b):
        assert links.file_id(folder_of(env, pid) / name) == links.file_id(mods / name)
    olds = list((env["fsp"] / apply.OLD_VERSIONS).rglob(name))
    assert len(olds) == 1 and olds[0].read_bytes() == old
    assert core.reconcile("FS25")["updated"] == []  # rien de plus à faire


def test_archive_rewritten_in_mods_relinks_all_parties(env):
    """Cas T3 : l'archive est réécrite dans Mods (nouveau fichier). Toutes les
    parties sont refaites vers le nouveau fichier, l'ancien est gardé une fois."""
    core, mods = env["core"], env["mods"]
    a, b = two_applied_parties(env)
    name = sorted(p.name for p in folder_of(env, a).iterdir() if (folder_of(env, b) / p.name).exists())[0]
    old = (mods / name).read_bytes()
    os.unlink(mods / name)
    (mods / name).write_bytes(old + b"\0")
    rep = core.reconcile("FS25")
    assert rep["relinked"] == 2
    for pid in (a, b):
        assert links.file_id(folder_of(env, pid) / name) == links.file_id(mods / name)
    olds = list((env["fsp"] / apply.OLD_VERSIONS).rglob(name))
    assert len(olds) == 1 and olds[0].read_bytes() == old


def test_unknown_mod_joins_its_party_without_apply(env):
    core, mods = env["core"], env["mods"]
    a, b = two_applied_parties(env)
    fakemods.make_zip_mod(folder_of(env, a), "FS25_ServerMod", seed=4)
    rep = core.reconcile("FS25")
    assert rep["added"] == {a: ["FS25_ServerMod"]}
    assert (mods / "FS25_ServerMod.zip").is_file()
    assert links.file_id(folder_of(env, a) / "FS25_ServerMod.zip") is not None
    assert "FS25_ServerMod" in core._store("FS25").party(a)["mods"]


def test_pending_downloads_are_recovered(env):
    """Étape 6 : mises à jour bloquées dans pending_downloads (jeu fermé)."""
    core, mods, ids = env["core"], env["mods"], env["info"]["ids"]
    a, b = two_applied_parties(env)
    pending = env["user"] / "pending_downloads"
    pending.mkdir()
    queue = pending / "pendingDownloadQueue.dat"
    queue.write_bytes(b"\x01\x02queue")
    name = f"{ids[0]}.zip"
    upd = fakemods.make_zip_mod(pending, ids[0], seed=55, version="7.0.0.0")
    new_mod = fakemods.make_zip_mod(pending, "FS25_FromServer", seed=56)
    fresh = fakemods.make_zip_mod(pending, "FS25_StillDownloading", seed=57)
    upd_hash = sha(upd)
    age(upd)
    age(new_mod)
    rep = core.reconcile("FS25")
    assert name in rep["updated"] and set(rep["pending"]) == {name, "FS25_FromServer.zip"}
    assert sha(mods / name) == upd_hash
    assert rep["added"] == {b: ["FS25_FromServer"]}         # partie appliquée
    assert queue.read_bytes() == b"\x01\x02queue"            # jamais touché
    assert fresh.is_file() and not (mods / fresh.name).exists()  # en cours d'écriture
    for pid in (a, b):
        assert links.file_id(folder_of(env, pid) / name) == links.file_id(mods / name)


def test_older_pending_version_never_replaces(env):
    core, mods, ids = env["core"], env["mods"], env["info"]["ids"]
    two_applied_parties(env)
    pending = env["user"] / "pending_downloads"
    old = fakemods.make_zip_mod(pending, ids[1], seed=3, version="0.0.0.1")
    age(old)
    before = sha(mods / f"{ids[1]}.zip")
    rep = core.reconcile("FS25")
    assert rep["set_aside"] == [old.name]
    assert sha(mods / f"{ids[1]}.zip") == before
    assert list((env["fsp"] / apply.RECOVERED).rglob(old.name))


def test_reconcile_refused_while_game_runs(env):
    core = env["core"]
    two_applied_parties(env)
    core.monitor.running = {"FS25"}
    with pytest.raises(AppError) as err:
        core.reconcile("FS25")
    assert err.value.key == "apply.running"


def test_reconcile_runs_once_when_library_is_first_ready(env):
    core = env["core"]
    core._reconciled.discard("FS25")
    calls = []
    core.reconcile = lambda vid, reason="manual", publish=True: calls.append((vid, reason)) or {}  # type: ignore[method-assign]
    core._library_ready("FS25")
    core._library_ready("FS25")
    for _ in range(50):
        if calls:
            break
        time.sleep(0.02)
    assert calls == [("FS25", "startup")]


# --------------------------------------------------------------------------
# Mods absents des dossiers de mods (A7, A8) : fenêtre du démarrage
# --------------------------------------------------------------------------

def test_hand_deleted_mod_is_a8_and_can_be_restored(env):
    core, mods, ids = env["core"], env["mods"], env["info"]["ids"]
    a, b = two_applied_parties(env)
    name = f"{ids[0]}.zip"
    content = (mods / name).read_bytes()
    os.unlink(mods / name)                                  # supprimé à la main
    env["lib"]._scan()
    rep = core.reconcile("FS25")                            # la copie reste en place
    assert set(rep["copies"][name]) == {folder_of(env, a).name, folder_of(env, b).name}
    anoms = {(x["type"], x["name"]) for x in core.library("FS25")["anomalies"]}
    assert ("A8", ids[0]) in anoms and ("A7", ids[0]) not in anoms
    res = core.missing_resolve("FS25", "restore", [ids[0]])
    assert res["done"] == [ids[0]]
    assert (mods / name).read_bytes() == content
    assert links.file_id(mods / name) == links.file_id(folder_of(env, a) / name)  # rien de copié


def test_hand_deleted_mod_can_be_deleted_for_good(env):
    core, mods, ids = env["core"], env["mods"], env["info"]["ids"]
    a, b = two_applied_parties(env)
    name = f"{ids[1]}.zip"
    os.unlink(mods / name)
    env["lib"]._scan()
    res = core.missing_resolve("FS25", "delete", [ids[1]])
    assert res["done"] == [ids[1]]
    for pid in (a, b):
        assert not os.path.lexists(folder_of(env, pid) / name)
        assert ids[1] not in core._store("FS25").party(pid)["mods"]


def test_missing_mod_removed_from_every_list(env):
    core, ids = env["core"], env["info"]["ids"]
    a = party(env, "Partie A", ids[:2])
    st = core._store("FS25")
    st.change_mods("add", "party", ["FS25_Disparu"], pid=a)     # mod disparu depuis
    st.change_mods("add", "common", ["FS25_Disparu"])
    anoms = {(x["type"], x["name"]) for x in core.library("FS25")["anomalies"]}
    assert ("A7", "FS25_Disparu") in anoms
    res = core.missing_resolve("FS25", "remove", ["fs25_disparu"])
    assert res["lists"] == 2
    st = core._store("FS25")
    assert "FS25_Disparu" not in st.party(a)["mods"] and "FS25_Disparu" not in st.data["common_mods"]


# --------------------------------------------------------------------------
# Supprimer définitivement (4.7)
# --------------------------------------------------------------------------

def test_delete_removes_lists_links_then_file(env):
    core, mods, ids = env["core"], env["mods"], env["info"]["ids"]
    a, b = two_applied_parties(env)
    core.party_mods("FS25", "add", "common", [ids[0]])
    others = {p.name: sha(p) for p in mods.iterdir() if p.is_file() and p.name != f"{ids[0]}.zip"}
    prev = core.mods_delete_preview("FS25", [ids[0]])
    assert prev["mods"][0]["parties"] == ["Partie A", "Partie B"] and prev["mods"][0]["common"]
    with pytest.raises(AppError):
        core.mods_delete("FS25", [ids[0]], confirm=False)   # double validation obligatoire
    res = core.mods_delete("FS25", [ids[0]], confirm=True)
    # Sous Windows le mod part dans la Corbeille (« recycled ») ; ailleurs, supprimé.
    assert res["deleted"] + res["recycled"] == [ids[0]] and not res["failed"]
    assert not (mods / f"{ids[0]}.zip").exists()
    for pid in (a, b):
        assert not os.path.lexists(folder_of(env, pid) / f"{ids[0]}.zip")
    st = core._store("FS25")
    assert all(ids[0] not in p["mods"] for p in st.data["parties"]) and ids[0] not in st.data["common_mods"]
    assert {p.name: sha(p) for p in mods.iterdir() if p.is_file()} == others
    assert ids[0].lower() not in env["lib"].index()


def test_delete_refused_while_game_runs(env):
    core, mods, ids = env["core"], env["mods"], env["info"]["ids"]
    core.monitor.running = {"FS25"}
    with pytest.raises(AppError) as err:
        core.mods_delete("FS25", [ids[0]], confirm=True)
    assert err.value.key == "delete.running"
    assert (mods / f"{ids[0]}.zip").exists()


def test_delete_unpacked_mod_never_follows_inner_links(env, tmp_path):
    """I10 : un lien placé dans un mod non compressé est retiré comme un lien."""
    fakemods.need_symlinks()
    core, mods = env["core"], env["mods"]
    outside = tmp_path / "Ailleurs"
    outside.mkdir()
    (outside / "precieux.txt").write_text("à garder")
    os.symlink(outside, mods / "FS25_DevMod" / "lien", target_is_directory=True)
    pid = party(env, "Dev", ["FS25_DevMod"])
    core.party_apply("FS25", pid)
    res = core.mods_delete("FS25", ["FS25_DevMod"], confirm=True)
    assert res["deleted"] + res["recycled"] == ["FS25_DevMod"]
    assert not (mods / "FS25_DevMod").exists()
    assert (outside / "precieux.txt").read_text() == "à garder"
    assert not os.path.lexists(folder_of(env, pid) / "FS25_DevMod")


def test_discard_uses_recycle_bin_when_available(tmp_path, monkeypatch):
    f = tmp_path / "FS25_X.zip"
    f.write_bytes(b"PK")
    monkeypatch.setattr(modops.winapi, "recycle_bin_available", lambda p: True)
    monkeypatch.setattr(modops.winapi, "send_to_recycle_bin", lambda p: (os.unlink(p), True)[1])
    assert modops.discard(f) == "recycled"
    f.write_bytes(b"PK")
    monkeypatch.setattr(modops.winapi, "send_to_recycle_bin", lambda p: False)
    with pytest.raises(OSError):
        modops.discard(f)       # refusé ou annulé : le fichier reste
    assert f.exists()


# --------------------------------------------------------------------------
# Renommer un mod (4.21)
# --------------------------------------------------------------------------

def test_rename_follows_everywhere_and_keeps_content(env):
    core, mods, gs, ids = env["core"], env["mods"], env["gs"], env["info"]["ids"]
    m = env["info"]["maps"][0]
    a = party(env, "Carte", [m, ids[0]], common=[ids[0]])
    b = party(env, "Autre", [ids[0], ids[1]])
    core.party_apply("FS25", a)
    core.party_apply("FS25", b)
    before = sha(mods / f"{m}.zip")
    fid = links.file_id(mods / f"{m}.zip")
    prev = core.mod_rename_preview("FS25", m)
    assert prev["prefix"] == "FS25_" and prev["rest"] == m[5:] and prev["parties"] == ["Carte"]
    new = f"{m}_perso"
    res = core.mod_rename("FS25", m, new)
    assert res["new"] == new and res["links"] == 1 and res["where"]["parties"] == ["Carte"]
    assert not (mods / f"{m}.zip").exists()
    assert sha(mods / f"{new}.zip") == before and links.file_id(mods / f"{new}.zip") == fid  # même fichier
    st = core._store("FS25")
    # 0.4 (correction) : le renommage ne touche pas aux listes, qui gardent l'ancien nom.
    assert m in st.party(a)["mods"] and new not in st.party(a)["mods"]
    assert links.file_id(folder_of(env, a) / f"{new}.zip") == fid
    assert not os.path.lexists(folder_of(env, a) / f"{m}.zip")
    inv = links.Inventory(env["fsp"] / apply.INVENTORY).folder(folder_of(env, a).name)
    assert f"{new}.zip" in inv and f"{m}.zip" not in inv
    assert gamesettings.read_override(gs).directory.endswith(folder_of(env, b).name)  # override intact
    assert new.lower() in env["lib"].index()
    assert not (env["fsp"] / apply.JOURNAL).exists()
    # Confirmation de l'utilisateur : les listes suivent le nouveau nom.
    assert core.mod_lists_rename("FS25", m, new)["lists"] >= 1
    st = core._store("FS25")
    assert new in st.party(a)["mods"] and st.party(a)["map"] == new


def test_rename_unpacked_mod_rebuilds_junction(env):
    core, mods = env["core"], env["mods"]
    pid = party(env, "Dev", ["FS25_DevMod"])
    core.party_apply("FS25", pid)
    core.mod_rename("FS25", "FS25_DevMod", "FS25_DevModV2")
    link = folder_of(env, pid) / "FS25_DevModV2"
    assert links.is_link(link) and Path(links.link_target(link)) == mods / "FS25_DevModV2"
    assert (mods / "FS25_DevModV2" / "modDesc.xml").is_file()


@pytest.mark.parametrize("bad,key", [
    ("FS25_Avec espace", "rename.invalid"), ("FS25_Rénové", "rename.invalid"), ("", "rename.empty"),
])
def test_rename_rejects_bad_names(env, bad, key):
    core, ids = env["core"], env["info"]["ids"]
    with pytest.raises(AppError) as err:
        core.mod_rename("FS25", ids[0], bad)
    assert err.value.key == key


def test_rename_rejects_taken_name_case_insensitive(env):
    core, ids = env["core"], env["info"]["ids"]
    with pytest.raises(AppError) as err:
        core.mod_rename("FS25", ids[0], ids[1].upper())
    assert err.value.key == "rename.taken"
    with pytest.raises(AppError) as err:
        core.mod_rename("FS25", ids[0], "FS25_ModPack")       # une anomalie occupe aussi le nom
    assert err.value.key == "rename.taken"


def test_rename_back_and_case_only(env):
    core, mods, ids = env["core"], env["mods"], env["info"]["ids"]
    pid = party(env, "P", [ids[2]])
    core.mod_rename("FS25", ids[2], "FS25_Temp")
    core.mod_rename("FS25", "FS25_Temp", ids[2])                 # retour à l'ancien nom
    assert (mods / f"{ids[2]}.zip").is_file()
    core.mod_rename("FS25", ids[2], ids[2].upper())              # seule la casse change
    core.mod_lists_rename("FS25", ids[2], ids[2].upper())        # confirmé : les listes suivent
    assert core._store("FS25").party(pid)["mods"] == [ids[2].upper()]


def test_rename_refused_while_game_runs(env):
    core, ids = env["core"], env["info"]["ids"]
    core.monitor.running = {"FS25"}
    with pytest.raises(AppError) as err:
        core.mod_rename("FS25", ids[0], "FS25_Nouveau")
    assert err.value.key == "rename.running"


def test_interrupted_rename_is_finished(env):
    """I8 : coupure juste après le renommage du fichier : le renommage est terminé
    au démarrage suivant (liens compris). Les listes ne changent qu'avec l'accord
    de l'utilisateur, qui n'a pas pu être demandé : elles gardent l'ancien nom."""
    core, mods, ids = env["core"], env["mods"], env["info"]["ids"]
    pid = party(env, "P", [ids[3]])
    core.party_apply("FS25", pid)
    folders = core._folders("FS25")
    folders._journal(op="mod_rename", old_id=ids[3], new_id="FS25_Coupure", old_file=f"{ids[3]}.zip",
                     new_file="FS25_Coupure.zip", storage=0, step="storage")
    os.rename(mods / f"{ids[3]}.zip", mods / "FS25_Coupure.zip")
    assert folders.recover() == "finished"
    assert ids[3] in core._store("FS25").party(pid)["mods"]
    assert links.file_id(folder_of(env, pid) / "FS25_Coupure.zip") == links.file_id(mods / "FS25_Coupure.zip")


# --------------------------------------------------------------------------
# Téléchargements et intégration (4.8)
# --------------------------------------------------------------------------

def make_download(dl: Path, mod_id: str, file: str | None = None, **kw) -> Path:
    p = fakemods.make_zip_mod(dl, mod_id, seed=hash(mod_id) % 1000, **kw)
    if file and file != p.name:
        p = p.rename(dl / file)
    age(p)
    return p


def test_scan_finds_stable_mods_only(env):
    core, dl, ids = env["core"], env["dl"], env["info"]["ids"]
    make_download(dl, "FS25_Nouveau")
    make_download(dl, "FS25_Doublon", file="FS25_Doublon (1).zip")
    make_download(dl, ids[0], version="9.0.0.0")                  # mise à jour
    make_download(dl, "FS22_AutreJeu", desc_version=72)
    fakemods.write_zip(dl / "pas_un_mod.zip", {"readme.txt": "x"})
    age(dl / "pas_un_mod.zip")
    fakemods.make_zip_mod(dl, "FS25_EnCours", seed=1)               # trop récent
    make_download(dl, "FS25_Firefox")
    (dl / "FS25_Firefox.zip.part").write_bytes(b"...")               # téléchargement en cours
    res = core.downloads_scan()
    items = {i["file"]: i for i in res["items"]}
    assert set(items) == {"FS25_Nouveau.zip", "FS25_Doublon (1).zip", f"{ids[0]}.zip", "FS22_AutreJeu.zip"}
    assert items["FS25_Doublon (1).zip"]["id"] == "FS25_Doublon" and items["FS25_Doublon (1).zip"]["suffix_removed"]
    assert items["FS22_AutreJeu.zip"]["detected"] == "FS22"
    assert items["FS25_Nouveau.zip"]["states"]["FS25"]["state"] == "new"
    upd = items[f"{ids[0]}.zip"]["states"]["FS25"]
    assert upd["state"] == "update" and upd["to"] == "9.0.0.0" and upd["checked"]
    assert items["FS25_Nouveau.zip"]["icon"].startswith("data:image/webp;base64,")
    core.downloads_ignore(["FS25_Nouveau.zip"])
    assert "FS25_Nouveau.zip" not in {i["file"] for i in core.downloads_scan()["items"]}


def test_integrate_new_update_and_suffix(env):
    core, dl, mods, ids = env["core"], env["dl"], env["mods"], env["info"]["ids"]
    pid = party(env, "P", [ids[0]])
    core.party_apply("FS25", pid)
    new = make_download(dl, "FS25_Nouveau")
    dup = make_download(dl, "FS25_Copie", file="FS25_Copie (2).zip")
    upd = make_download(dl, ids[0], version="9.0.0.0")
    upd_hash, new_hash = sha(upd), sha(new)
    old_hash = sha(mods / f"{ids[0]}.zip")
    res = core.downloads_integrate([
        {"file": new.name, "version": "FS25", "destination": "common"},
        {"file": dup.name, "version": "FS25", "destination": "party", "party": pid},
        {"file": upd.name, "version": "FS25", "destination": "none"},
    ])
    assert res["count"] == 3 and not res["failed"]
    assert sha(mods / "FS25_Nouveau.zip") == new_hash and not new.exists()
    assert (mods / "FS25_Copie.zip").is_file() and not dup.exists()          # suffixe retiré
    assert sha(mods / f"{ids[0]}.zip") == upd_hash
    olds = list((env["fsp"] / apply.OLD_VERSIONS).rglob(f"{ids[0]}.zip"))
    assert len(olds) == 1 and sha(olds[0]) == old_hash
    st = core._store("FS25")
    assert "FS25_Nouveau" in st.data["common_mods"] and "FS25_Copie" in st.party(pid)["mods"]
    # La partie appliquée suit la mise à jour (réconciliation après intégration).
    assert links.file_id(folder_of(env, pid) / f"{ids[0]}.zip") == links.file_id(mods / f"{ids[0]}.zip")
    assert "fs25_nouveau" in env["lib"].index()


def test_older_or_present_never_replaces_without_confirmation(env):
    core, dl, mods, ids = env["core"], env["dl"], env["mods"], env["info"]["ids"]
    older = make_download(dl, ids[1], version="0.0.0.1")
    before = sha(mods / f"{ids[1]}.zip")
    res = core.downloads_integrate([{"file": older.name, "version": "FS25", "destination": "none"}])
    assert res["skipped"][0]["reason"] == "older" and older.exists()
    assert sha(mods / f"{ids[1]}.zip") == before
    res = core.downloads_integrate([{"file": older.name, "version": "FS25", "destination": "none",
                                     "replace_older": True}])
    assert res["count"] == 1 and not older.exists()
    copy = dl / f"{ids[2]}.zip"
    copy.write_bytes((mods / f"{ids[2]}.zip").read_bytes())
    age(copy)
    item = next(i for i in core.downloads_scan()["items"] if i["file"] == copy.name)
    assert item["states"]["FS25"]["state"] == "present" and not item["states"]["FS25"]["checked"]


def test_integration_postponed_while_game_runs(env):
    core, dl, mods = env["core"], env["dl"], env["mods"]
    new = make_download(dl, "FS25_Plustard")
    core.monitor.running = {"FS25"}
    res = core.downloads_integrate([{"file": new.name, "version": "FS25", "destination": "common"}])
    assert res["postponed"] == [{"file": new.name, "version": "FS25"}] and new.exists()
    core.monitor.running = set()
    core._on_game_exit("FS25")
    assert (mods / "FS25_Plustard.zip").is_file() and not new.exists()
    assert "FS25_Plustard" in core._store("FS25").data["common_mods"]
    assert core.settings.get("downloads_postponed") == []


def test_move_between_disks_is_verified(tmp_path, monkeypatch):
    src = fakemods.make_zip_mod(tmp_path / "a", "FS25_Gros", seed=8)
    data = src.read_bytes()
    dst = tmp_path / "b" / "FS25_Gros.zip"
    real_rename = os.rename

    def cross(a, b):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(os, "rename", cross)
    assert fsutil.move_file(src, dst, downloads.archive_ok) == "copied"
    assert dst.read_bytes() == data and not src.exists()
    # Copie abîmée : rien n'est remplacé, l'original reste.
    monkeypatch.setattr(os, "rename", real_rename)
    src2 = fakemods.make_zip_mod(tmp_path / "a", "FS25_Abime", seed=9)
    monkeypatch.setattr(os, "rename", cross)
    with pytest.raises(fsutil.MoveError):
        fsutil.move_file(src2, tmp_path / "b" / "FS25_Abime.zip", lambda p: False)
    assert src2.exists() and not (tmp_path / "b" / "FS25_Abime.zip").exists()
    assert not list((tmp_path / "b").glob(".fsp-*"))


# --------------------------------------------------------------------------
# Arguments de lancement dans l'état d'une version (0.4)
# --------------------------------------------------------------------------

def test_version_state_tells_where_arguments_go(env):
    core = env["core"]
    core.settings.update_version("FS25", {"launch_args": {"skip_start_videos": True, "cheats": False}})
    (env["user"] / "game.xml").write_text("<game><development><controls>false</controls></development></game>")
    li = core.version_state("FS25")["launch"]
    assert li["args_text"] == "-skipStartVideos" and li["args_mode"] == "command" and li["controls"] is False
    state = core.enable_console("FS25")
    assert state["game_xml"] == "changed" and state["launch"]["controls"] is True


def test_full_party_still_applies_after_reconcile(env):
    core = env["core"]
    two_applied_parties(env)
    res = core.party_apply("FS25", FULL)
    assert res["party"] == FULL


# --------------------------------------------------------------------------
# Mod décompressé puis recompressé
# --------------------------------------------------------------------------

def test_rezipped_mod_replaces_old_junction(env):
    """Le mod non compressé « FS25_DevMod » est recompressé en FS25_DevMod.zip :
    la partie ne doit plus charger l'ancienne forme (le jeu ne pouvait alors pas
    le mettre à jour). La jonction est remplacée par un lien vers l'archive."""
    core, mods = env["core"], env["mods"]
    pid = party(env, "Dev", ["FS25_DevMod"])
    core.party_apply("FS25", pid)
    folder = folder_of(env, pid)
    assert links.is_link(folder / "FS25_DevMod")
    modops.remove_tree(mods / "FS25_DevMod")
    fakemods.make_zip_mod(mods, "FS25_DevMod", seed=12)
    env["lib"]._scan()
    rep = core.reconcile("FS25")
    assert rep["reshaped"] == ["FS25_DevMod"]
    assert not os.path.lexists(folder / "FS25_DevMod")
    assert links.file_id(folder / "FS25_DevMod.zip") == links.file_id(mods / "FS25_DevMod.zip")
    assert not core.party_apply("FS25", pid)["missing"]


def test_unzipped_mod_replaces_old_hardlink(env):
    """Sens inverse : l'archive est décompressée dans un dossier du même nom, puis
    supprimée. La partie reçoit une jonction ; l'ancienne archive est gardée."""
    core, mods, ids = env["core"], env["mods"], env["info"]["ids"]
    pid = party(env, "Zip", [ids[6]])
    core.party_apply("FS25", pid)
    folder = folder_of(env, pid)
    zipped = mods / f"{ids[6]}.zip"
    content = zipped.read_bytes()
    fakemods.make_dir_mod(mods, ids[6], seed=13)
    os.unlink(zipped)
    env["lib"]._scan()
    rep = core.reconcile("FS25")
    assert rep["reshaped"] == [f"{ids[6]}.zip"]
    assert links.is_link(folder / ids[6]) and not os.path.lexists(folder / f"{ids[6]}.zip")
    olds = list((env["fsp"] / apply.OLD_VERSIONS).rglob(f"{ids[6]}.zip"))
    assert len(olds) == 1 and olds[0].read_bytes() == content
    assert not any(a["type"] == "A8" for a in core.library("FS25")["anomalies"])


def test_rename_suggestion_for_refused_name(env):
    core = env["core"]
    prev = core.mod_rename_preview("FS25", "FS25_Tracteur Rénové (1)")
    assert prev["prefix"] == "FS25_" and prev["suggestion"] == "Tracteur_Renove"
    res = core.mod_rename("FS25", "FS25_Tracteur Rénové (1)", "FS25_Tracteur_Renove")
    assert (env["mods"] / "FS25_Tracteur_Renove.zip").is_file()
    assert res["new"] == "FS25_Tracteur_Renove"
    assert not any(a["type"] == "A5" for a in core.library("FS25")["anomalies"])


def test_zip_and_folder_side_by_side_is_a9(env):
    """Cause probable du problème du ModHub (liste du 18 octobre) : l'archive
    recompressée et le dossier décompressé côte à côte dans Mods."""
    core, mods = env["core"], env["mods"]
    fakemods.make_zip_mod(mods, "FS25_DevMod", seed=14)       # à côté du dossier FS25_DevMod
    env["lib"]._scan()
    lib = core.library("FS25")
    a9 = [a for a in lib["anomalies"] if a["type"] == "A9"]
    assert len(a9) == 1 and a9[0]["name"] == "FS25_DevMod" and a9[0]["detail"]["zip_and_dir"]
    assert [m["kind"] for m in lib["mods"] if m["id"] == "FS25_DevMod"] == ["zip"]   # une seule tuile, l'archive
