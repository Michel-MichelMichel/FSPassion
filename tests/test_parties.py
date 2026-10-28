"""Parties (4.1), parties.json (3.3), classement (4.6) et dépendances (4.5)."""

from __future__ import annotations

import json

import pytest

from fspassion import parties
from fspassion.parties import EMPTY, FULL, PartiesStore, PartyError, resolve_dependencies


@pytest.fixture
def store(tmp_path):
    st = PartiesStore("FS25", tmp_path / "FSPassion" / "FS25" / "parties.json", "D:/FS25_Mods/Mods")
    st.load()
    return st


def reload(st: PartiesStore) -> PartiesStore:
    fresh = PartiesStore(st.vid, st.path, "D:/FS25_Mods/Mods")
    fresh.load()
    return fresh


# --------------------------------------------------------------------------
# Noms et dossiers
# --------------------------------------------------------------------------

def test_folder_names():
    assert parties.slugify("Hof Bergmann") == "hof-bergmann"
    assert parties.slugify("Élevage d'Été  à Großdorf") == "elevage-d-ete-a-grossdorf"
    assert parties.slugify("***") == "partie"
    assert parties.folder_name("Hof Bergmann", "2c91") == "hof-bergmann-2c91"
    assert len(parties.slugify("x" * 200)) <= 40
    assert parties.clean_name("  Hof\t  Bergmann \n") == "Hof Bergmann"


def test_create_rules(store):
    assert not store.path.exists()  # rien n'est écrit tant qu'on ne crée rien
    p = store.create("Etruria")
    assert p["name"] == "Etruria" and p["mods"] == [] and p["common_enabled"] is True
    assert p["folder"] == f"etruria-{p['id']}"
    assert store.data["selected"] == p["id"]  # la nouvelle partie devient la partie sélectionnée
    assert store.path.is_file()
    with pytest.raises(PartyError) as e:
        store.create("  ")
    assert e.value.key == "parties.name_empty"
    with pytest.raises(PartyError) as e:
        store.create("x" * 61)
    assert e.value.key == "parties.name_too_long"
    with pytest.raises(PartyError) as e:
        store.create("ETRURIA")  # unique dans la version, sans tenir compte de la casse
    assert e.value.key == "parties.name_taken"
    assert store.create("x" * 60)["name"] == "x" * 60
    assert store.create("Élevage d'été")["name"] == "Élevage d'été"  # accents et espaces acceptés


def test_specials_are_locked(store):
    for pid in (FULL, EMPTY):
        for call in (lambda p=pid: store.rename(p, "X"), lambda p=pid: store.delete(p),
                     lambda p=pid: store.duplicate(p, "X"), lambda p=pid: store.set_common_enabled(p, False),
                     lambda p=pid: store.change_mods("add", "party", ["FS25_A"], pid=p)):
            with pytest.raises(PartyError) as e:
                call()
            assert e.value.key == "parties.special_locked"
    store.select(EMPTY)
    assert store.data["selected"] == EMPTY
    with pytest.raises(PartyError):
        store.select("abcd")


def test_persistence(store):
    a = store.create("Etruria", ["FS25_Etruria", "FS25_Swan"], "FS25_Etruria")
    store.set_common_enabled(a["id"], False)
    b = reload(store)
    pa = b.party(a["id"])
    assert pa["mods"] == ["FS25_Etruria", "FS25_Swan"]
    assert pa["map"] == "FS25_Etruria" and pa["common_enabled"] is False
    assert b.data["selected"] == a["id"] and b.data["schema"] == 1 and b.data["game_version"] == "FS25"
    assert b.data["mods_dir"] == "D:/FS25_Mods/Mods"


def test_duplicate_and_rename(store):
    a = store.create("Etruria", ["FS25_Etruria", "FS25_Swan"], "FS25_Etruria")
    store.set_common_enabled(a["id"], False)
    c = store.duplicate(a["id"], "Etruria (copie)")
    assert c["id"] != a["id"] and c["mods"] == a["mods"] and c["common_enabled"] is False
    assert c["map"] == "FS25_Etruria" and store.data["selected"] == c["id"]
    r = store.rename(c["id"], "Hof Bergmann")
    assert r["name"] == "Hof Bergmann" and r["folder"] == f"hof-bergmann-{c['id']}"
    with pytest.raises(PartyError) as e:
        store.rename(c["id"], "etruria")
    assert e.value.key == "parties.name_taken"
    assert store.rename(a["id"], "Etruria")["name"] == "Etruria"  # même nom : accepté


def test_delete_and_history(store):
    a = store.create("A")
    b = store.create("B")
    c = store.create("C")
    for pid in (FULL, a["id"], b["id"], c["id"]):
        store.record_applied(pid)
    assert store.data["applied"] == c["id"]
    assert store.data["applied_history"] == [c["id"], b["id"], a["id"], FULL]
    # Supprimer la partie appliquée : la précédente de l'historique la remplace (B2, Q9).
    store.select(c["id"])
    res = store.delete(c["id"])
    assert res["was_applied"] and res["fallback"] == b["id"]
    assert store.data["applied"] == b["id"] and store.data["selected"] == b["id"]
    assert c["id"] not in store.data["applied_history"]
    # Partie non appliquée : rien ne change côté jeu.
    res = store.delete(a["id"])
    assert not res["was_applied"] and store.data["applied"] == b["id"]
    # Historique vide : la Partie Pleine.
    store.data["applied_history"] = [b["id"]]
    res = store.delete(b["id"])
    assert res["fallback"] == FULL and store.data["applied"] == FULL and store.data["selected"] == FULL


def test_history_is_capped(store):
    ids = [store.create(f"P{i}")["id"] for i in range(14)]
    for pid in ids:
        store.record_applied(pid)
    assert len(store.data["applied_history"]) == parties.HISTORY_MAX
    assert store.data["applied_history"][0] == ids[-1]
    assert not store.record_applied(ids[-1])  # déjà appliquée : rien à écrire


# --------------------------------------------------------------------------
# Sauvegardes et fichier abîmé
# --------------------------------------------------------------------------

def test_backup_rotation(store):
    a = store.create("A")
    for i in range(7):
        store.change_mods("add", "common", [f"FS25_M{i}"])
    for n in range(1, 6):
        assert store.backup_path(n).is_file()
    assert not store.backup_path(6).exists()
    bak1 = json.loads(store.backup_path(1).read_text(encoding="utf-8"))
    assert bak1["common_mods"] == [f"FS25_M{i}" for i in range(6)]  # version précédente
    # Changer seulement de partie sélectionnée ne fait pas tourner les sauvegardes.
    before = store.backup_path(1).read_bytes()
    store.select(FULL)
    store.select(a["id"])
    assert store.backup_path(1).read_bytes() == before
    assert reload(store).data["selected"] == a["id"]
    # Aucun fichier temporaire laissé.
    assert not [f for f in store.path.parent.iterdir() if f.name.endswith(".tmp")]


def test_corrupted_file_uses_latest_valid_backup(store):
    store.create("A")
    store.create("B")
    store.create("C")  # bak1 : A et B ; bak2 : A
    store.path.write_text("{ abîmé", encoding="utf-8")
    store.backup_path(1).write_text("[]", encoding="utf-8")  # sauvegarde la plus récente abîmée aussi
    st = reload(store)
    assert st.recovered == "bak2"
    assert [p["name"] for p in st.data["parties"]] == ["A"]
    assert json.loads(st.path.read_text(encoding="utf-8"))["parties"][0]["name"] == "A"
    assert list(st.path.parent.glob("parties.json.illisible-*"))  # mis de côté, jamais supprimé


def test_nothing_readable_starts_fresh(store):
    store.create("A")
    store.path.write_text("pas du json", encoding="utf-8")
    st = reload(store)
    assert st.lost and st.data["parties"] == []
    assert list(st.path.parent.glob("parties.json.illisible-*"))


def test_validate_cleans_and_refuses_newer_schema():
    raw = {
        "schema": 1,
        "parties": [
            {"id": "7f3a", "name": "Etruria", "mods": ["FS25_A", "fs25_a", 3, "FS25_B"]},
            {"id": "7f3a", "name": "Doublon"},
            {"id": "zz", "name": "Mauvais identifiant"},
            {"id": "1234", "name": ""},
            "pas une partie",
        ],
        "common_mods": ["FS25_C", None],
        "selected": "inconnue",
        "applied": "7f3a",
        "applied_history": ["7f3a", "7f3a", "_pleine", "disparue"],
    }
    data = parties.validate(raw, "FS25")
    assert [p["id"] for p in data["parties"]] == ["7f3a"]
    assert data["parties"][0]["mods"] == ["FS25_A", "FS25_B"]
    assert data["parties"][0]["folder"] == "etruria-7f3a"
    assert data["common_mods"] == ["FS25_C"]
    assert data["selected"] == FULL and data["applied"] == "7f3a"
    assert data["applied_history"] == ["7f3a", "_pleine"]
    with pytest.raises(ValueError):
        parties.validate({"schema": 99, "parties": []}, "FS25")
    with pytest.raises(ValueError):
        parties.validate({"parties": []}, "FS25")


# --------------------------------------------------------------------------
# Classement
# --------------------------------------------------------------------------

def test_change_mods(store):
    maps = {"fs25_etruria", "fs25_other_map"}
    is_map = lambda m: m.lower() in maps  # noqa: E731
    p = store.create("Etruria")
    r = store.change_mods("add", "party", ["FS25_Etruria", "FS25_Swan", "fs25_swan"], pid=p["id"], is_map=is_map)
    assert r == {"added": 2, "removed": 0}
    assert store.party(p["id"])["map"] == "FS25_Etruria"  # la map de la partie suit son contenu
    store.change_mods("add", "common", ["FS25_AutoDrive", "FS25_Swan"])
    # Un mod peut être dans la partie et dans les mods communs (Q2).
    assert "FS25_Swan" in store.data["common_mods"] and "FS25_Swan" in store.party(p["id"])["mods"]
    # Déplacer de la partie vers les communs
    r = store.change_mods("move", "common", ["FS25_Etruria"], pid=p["id"], source="party", is_map=is_map)
    assert r == {"added": 1, "removed": 1}
    assert store.party(p["id"])["mods"] == ["FS25_Swan"] and store.party(p["id"])["map"] is None
    # Déplacer des communs vers la partie ; un mod absent de la liste d'origine est ignoré
    r = store.change_mods("move", "party", ["FS25_AutoDrive", "FS25_Inconnu"], pid=p["id"], source="common")
    assert r == {"added": 1, "removed": 1}
    assert store.data["common_mods"] == ["FS25_Swan", "FS25_Etruria"]
    r = store.change_mods("remove", "common", ["fs25_swan", "FS25_Absent"])
    assert r == {"added": 0, "removed": 1}
    with pytest.raises(PartyError):
        store.change_mods("move", "common", ["x"], pid=p["id"], source="common")
    with pytest.raises(PartyError):
        store.change_mods("explode", "common", ["x"])


def test_replace_mod(store):
    p = store.create("Etruria", ["FS25_Old", "FS25_B"], "FS25_Old")
    store.change_mods("add", "common", ["FS25_Old", "FS25_New"])
    n = store.replace_mod("fs25_old", "FS25_New", is_map=lambda m: m == "FS25_New")
    assert n == 2
    assert store.party(p["id"])["mods"] == ["FS25_New", "FS25_B"] and store.party(p["id"])["map"] == "FS25_New"
    assert store.data["common_mods"] == ["FS25_New"]  # jamais en double
    assert store.replace_mod("FS25_Inexistant", "FS25_B") == 0


def test_referenced(store):
    store.create("A", ["FS25_X", "FS25_Y"])
    store.create("B", ["fs25_x"])
    store.change_mods("add", "common", ["FS25_Y"])
    ref = store.referenced()
    assert ref["fs25_x"]["parties"] == ["A", "B"] and not ref["fs25_x"]["common"]
    assert ref["fs25_y"]["common"] and ref["fs25_y"]["parties"] == ["A"]


# --------------------------------------------------------------------------
# Dossier d'une partie : jamais hors de « Parties » (L2-01)
# --------------------------------------------------------------------------

def test_party_folder_comes_from_name_and_id_not_from_the_file():
    raw = {
        "schema": 1,
        "parties": [
            {"id": "7f3a", "name": "Etruria", "folder": "..\\..\\Documents"},
            {"id": "1b2c", "name": "Bergmann", "folder": "C:\\Users\\Public\\Desktop"},
            {"id": "9d9d", "name": "Abs", "folder": "/etc"},
        ],
    }
    data = parties.validate(raw, "FS25")
    assert {p["id"]: p["folder"] for p in data["parties"]} == {
        "7f3a": "etruria-7f3a", "1b2c": "bergmann-1b2c", "9d9d": "abs-9d9d",
    }


def test_party_dir_refuses_names_leaving_the_folder(tmp_path):
    from fspassion import apply

    base = tmp_path / "Parties"
    assert apply.party_dir(base, "etruria-7f3a") == base / "etruria-7f3a"
    for bad in ("..\\..\\Documents", "../x", "C:\\Users\\Public\\Desktop", "/etc", "..", ".", "", "a:b"):
        with pytest.raises(apply.ApplyError):
            apply.party_dir(base, bad)


def test_unreadable_file_not_overwritten_when_set_aside_fails(store, monkeypatch):
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{ pas du json", encoding="utf-8")

    def refuse(self, target):
        raise OSError("verrouillé")

    monkeypatch.setattr(type(store.path), "replace", refuse)
    st = reload(store)
    assert st.lost and st.blocked
    with pytest.raises(PartyError) as e:
        st.create("Nouvelle")
    assert e.value.key == "parties.write_failed"
    assert store.path.read_text(encoding="utf-8") == "{ pas du json"  # rien n'est écrasé


# --------------------------------------------------------------------------
# Dépendances
# --------------------------------------------------------------------------

def test_resolve_dependencies():
    mods = {
        "fs25_map": {"id": "FS25_Map", "dependencies": ["FS25_Swan", "fs25_sigma", "FS25_Absent", "pdlc_vredoPack", "pdlc_newPack"]},
        "fs25_swan": {"id": "FS25_Swan", "dependencies": ["FS25_Base"]},
        "fs25_sigma": {"id": "FS25_Sigma", "dependencies": ["FS25_Map", "FS25_Base"]},  # boucle
        "fs25_base": {"id": "FS25_Base", "dependencies": ["FS25_Deep"]},
        "fs25_deep": {"id": "FS25_Deep", "dependencies": []},
    }
    res = resolve_dependencies(["FS25_Map"], mods, {"vredopack"})
    assert res["present"] == ["FS25_Base", "FS25_Deep", "FS25_Sigma", "FS25_Swan"]
    assert res["missing"] == ["FS25_Absent"]
    assert res["dlc"] == [{"id": "newPack", "owned": False}, {"id": "vredoPack", "owned": True}]
    # Plusieurs racines : une racine n'est jamais sa propre dépendance
    assert res["required_by"]["fs25_deep"] == "FS25_Map"  # dépendance d'une dépendance : la racine
    # Plusieurs racines : une racine n'est jamais sa propre dépendance
    res = resolve_dependencies(["FS25_Swan", "FS25_Base"], mods)
    assert res["present"] == ["FS25_Deep"]
    assert res["required_by"] == {"fs25_deep": "FS25_Base"}
    res = resolve_dependencies(["FS25_Map", "fs25_swan"], mods)
    assert res["required_by"]["fs25_base"] == "FS25_Swan"  # racine en minuscules : identifiant réel
    # 0.7.3 : mods facultatifs et liens (<SearchMods>) en plus.
    assert resolve_dependencies(["FS25_Inconnu"], mods) == {"present": [], "missing": [], "dlc": [], "required_by": {},
                                                           "optional": [], "links": {}}
