"""API des parties et du classement (0.2), sur une vraie collection de faux mods.

Règle de la version 0.2 : elle ne modifie aucun fichier du jeu
ni aucun mod. Seul parties.json (et ses sauvegardes) est écrit, dans
FSPassion\\<version>\\.
"""

from __future__ import annotations

import hashlib
import http.client
import json
from pathlib import Path

import pytest

from fspassion import gamesettings
from fspassion.core import Core
from fspassion.events import EventBus
from fspassion.parties import FULL
from fspassion.server import Server

import fakemods


def snapshot(folder: Path) -> dict[str, str]:
    """Empreinte de chaque fichier d'un dossier (contenu et date)."""
    return {
        str(p.relative_to(folder)): f"{p.stat().st_mtime_ns}-{hashlib.sha256(p.read_bytes()).hexdigest()}"
        for p in sorted(folder.rglob("*")) if p.is_file()
    }


@pytest.fixture
def env(tmp_path):
    mods = tmp_path / "FS25_Mods" / "Mods"
    info = fakemods.make_collection(mods, count=20)
    user = tmp_path / "Documents" / "My Games" / "FarmingSimulator2025"
    user.mkdir(parents=True)
    gs = user / "gameSettings.xml"
    gs.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<gameSettings revision="15">\n'
        f'    <modsDirectoryOverride active="true" directory="{mods.as_posix()}"/>\n</gameSettings>\n',
        encoding="utf-8",
    )
    core = Core(dev=True, bus=EventBus())
    core.settings.set("first_detection_done", True)
    core.settings.update_version("FS25", {"mods_dir": str(mods), "user_dir": str(user)})
    core.settings.update_version("FS2011", {"user_dir": str(tmp_path / "FS2011")})
    core._ensure_backups()
    lib = core.libs.get("FS25")
    lib._scan()
    srv = Server(core, 0)
    srv.start()
    before = {"mods": snapshot(mods), "gs": gs.read_bytes()}
    yield {"srv": srv, "core": core, "mods": mods, "gs": gs, "info": info, "before": before, "tmp": tmp_path}
    srv.stop()


def call(srv, method, path, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=10)
    headers = {"Host": f"127.0.0.1:{srv.port}", "X-FSP-Token": srv.token}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=headers)
    r = conn.getresponse()
    raw = r.read()
    conn.close()
    return r.status, json.loads(raw)


def test_full_workflow(env):
    srv, info = env["srv"], env["info"]
    st, state = call(srv, "GET", "/api/parties?version=FS25")
    assert st == 200 and state["supported"]
    # Premier lancement : la partie sélectionnée reflète l'état réel du jeu.
    assert state["selected"] == FULL and state["applied"] == FULL and state["applied_kind"] == "full"
    assert state["applied_history"] == [FULL]

    # « ＋ Partie » sur une map : la map et ses dépendances présentes (4.5).
    the_map = info["maps"][0]
    st, deps = call(srv, "POST", "/api/deps", {"version": "FS25", "ids": [the_map]})
    assert st == 200 and len(deps["present"]) == 3
    assert deps["missing"] == ["FS25_Absent0"] and deps["dlc"] == [{"id": "vredoPack", "owned": False}]
    st, res = call(srv, "POST", "/api/parties/create", {"version": "FS25", "name": "Carte A", "map": the_map})
    assert st == 200 and res["count"] == 4 and res["missing"] == ["FS25_Absent0"]
    party = res["party"]
    assert party["map"] == the_map and party["mods"][0] == the_map and party["common_enabled"]
    assert res["state"]["selected"] == party["id"]

    # Nom déjà pris
    st, err = call(srv, "POST", "/api/parties/create", {"version": "FS25", "name": "carte a"})
    assert st == 400 and err["error"] == "parties.name_taken"

    # Classement : mods communs, déplacement, retrait
    some = info["ids"][:5]
    st, res = call(srv, "POST", "/api/parties/mods",
                   {"version": "FS25", "action": "add", "target": "common", "ids": some + ["FS25_PasLa"]})
    assert st == 200 and res["added"] == 5  # un mod absent ne s'ajoute pas
    st, res = call(srv, "POST", "/api/parties/mods", {"version": "FS25", "action": "move", "target": "party",
                                                       "source": "common", "party": party["id"], "ids": some[:2]})
    assert res["added"] + res["removed"] >= 2
    assert set(some[2:]) == set(res["state"]["common_mods"])
    st, res = call(srv, "POST", "/api/parties/mods",
                   {"version": "FS25", "action": "add", "target": "party", "party": FULL, "ids": some})
    assert st == 400 and res["error"] == "parties.special_locked"

    # Switch « Mods communs », duplication, renommage, sélection
    st, state = call(srv, "POST", "/api/parties/common", {"version": "FS25", "id": party["id"], "enabled": False})
    assert not next(p for p in state["parties"] if p["id"] == party["id"])["common_enabled"]
    st, res = call(srv, "POST", "/api/parties/duplicate", {"version": "FS25", "id": party["id"], "name": "Carte A (copie)"})
    copy_id = res["party"]["id"]
    assert res["party"]["mods"] == next(p for p in res["state"]["parties"] if p["id"] == party["id"])["mods"]
    st, res = call(srv, "POST", "/api/parties/rename", {"version": "FS25", "id": copy_id, "name": "Hof Bergmann"})
    assert res["party"]["folder"] == f"hof-bergmann-{copy_id}"
    st, state = call(srv, "POST", "/api/parties/select", {"version": "FS25", "id": party["id"]})
    assert state["selected"] == party["id"]
    st, res = call(srv, "POST", "/api/parties/delete", {"version": "FS25", "id": copy_id})
    assert st == 200 and not res["was_applied"] and len(res["state"]["parties"]) == 1

    # La bibliothèque active le classement (Non classés, repères).
    st, lib = call(srv, "GET", "/api/library?version=FS25")
    assert lib["classification"] is True

    # Rien n'a été touché dans le dossier de mods ni dans gameSettings.xml ;
    # aucun dossier de partie n'est créé en 0.2.
    assert snapshot(env["mods"]) == env["before"]["mods"]
    assert env["gs"].read_bytes() == env["before"]["gs"]
    fsp = env["mods"].parent / "FSPassion" / "FS25"
    assert (fsp / "parties.json").is_file()
    assert not (fsp / "Parties").exists()
    assert gamesettings.original_backup_path(env["gs"]).is_file()


def test_missing_mod_and_replace(env):
    srv, core, info = env["srv"], env["core"], env["info"]
    call(srv, "GET", "/api/parties?version=FS25")
    store = core._store("FS25")
    p = store.create("Etruria", ["FS25_Disparu", info["ids"][0]])
    store.change_mods("add", "common", ["fs25_disparu"])
    st, lib = call(srv, "GET", "/api/library?version=FS25")
    a7 = [a for a in lib["anomalies"] if a["type"] == "A7"]
    assert len(a7) == 1 and a7[0]["name"] == "FS25_Disparu"
    assert a7[0]["detail"] == {"parties": ["Etruria"], "common": True} and a7[0]["new"]
    # « Remplacer par… » : le mod reprend sa place dans toutes les listes (R14).
    st, res = call(srv, "POST", "/api/parties/replace", {"version": "FS25", "old": "FS25_Disparu", "new": info["ids"][1].lower()})
    assert st == 200 and res["lists"] == 2 and res["new"] == info["ids"][1]
    assert info["ids"][1] in next(x for x in res["state"]["parties"] if x["id"] == p["id"])["mods"]
    st, lib = call(srv, "GET", "/api/library?version=FS25")
    assert not [a for a in lib["anomalies"] if a["type"] == "A7"]
    st, err = call(srv, "POST", "/api/parties/replace", {"version": "FS25", "old": "x", "new": "FS25_PasLa"})
    assert st == 404 and err["error"] == "parties.mod_not_found"


def test_unavailable_versions(env):
    srv = env["srv"]
    st, state = call(srv, "GET", "/api/parties?version=FS2011")
    assert st == 200 and not state["supported"] and state["reason"]["key"] == "lists.no_parties"
    st, state = call(srv, "GET", "/api/parties?version=FS22")
    assert not state["supported"] and state["reason"]["key"] == "parties.not_configured"
    st, err = call(srv, "POST", "/api/parties/create", {"version": "FS22", "name": "X"})
    assert st == 400 and err["error"] == "parties.not_configured"
    st, err = call(srv, "POST", "/api/parties/mods", {"version": "FS25", "action": "add", "target": "common", "ids": "pas une liste"})
    assert st == 400


def test_running_game_blocks_applied_party(env):
    srv, core = env["srv"], env["core"]
    call(srv, "GET", "/api/parties?version=FS25")
    core.monitor.running = {"FS25"}
    # La Partie Pleine est appliquée : les autres parties restent modifiables.
    st, res = call(srv, "POST", "/api/parties/create", {"version": "FS25", "name": "Libre"})
    assert st == 200
    st, res = call(srv, "POST", "/api/parties/rename", {"version": "FS25", "id": res["party"]["id"], "name": "Libre 2"})
    assert st == 200
    core.monitor.running = set()


def test_corrupted_parties_file_is_reported_once(env):
    srv, core = env["srv"], env["core"]
    call(srv, "POST", "/api/parties/create", {"version": "FS25", "name": "A"})
    call(srv, "POST", "/api/parties/create", {"version": "FS25", "name": "B"})
    store = core._store("FS25")
    store.path.write_text("{", encoding="utf-8")
    core._parties.clear()
    st, state = call(srv, "GET", "/api/parties?version=FS25")
    assert state["notice"]["key"] == "parties.recovered" and state["notice"]["params"]["backup"] == "bak1"
    assert [p["name"] for p in state["parties"]] == ["A"]
    st, state = call(srv, "GET", "/api/parties?version=FS25")
    assert state["notice"] is None
