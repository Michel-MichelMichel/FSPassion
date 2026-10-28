"""Version 0.7.3 : mods requis et facultatifs des anciennes versions
(<SearchMods> : <mod zipName=…> et <optionalMod zipName=…>), liens de
téléchargement, fiche épinglée (bouton « i »)."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.test_mods_operations import env  # noqa: F401  (fixture)

from fspassion import library, moddesc, winapi
from fspassion.core import AppError
from fspassion.parties import resolve_dependencies

from fakemods import write_zip

ROOT = Path(__file__).resolve().parents[1]

SEARCH = """<?xml version="1.0" encoding="utf-8" standalone="no" ?>
<modDesc descVersion="28">
  <author>Testeur</author>
  <version>1.0</version>
  <title><en>Tunxdorf</en></title>
  <maps><map id="t"><title><en>Tunxdorf</en></title></map></maps>
  <dependencies><dependency>FS25_Already</dependency></dependencies>
	<SearchMods>
		<mod zipName="{req}" downloadLink = "http://vertexdezign.net/downloads/animationmaptrigger"/>
		<mod zipName="ZZZ_multiFruit.zip" downloadLink = "http://www.modhoster.de/mods/multifruit--4"/>
		<mod zipName="FS25_Already" downloadLink = "https://example.com/already"/>
		<optionalMod zipName="{opt}" downloadLink = "https://example.com/optional"/>
		<optionalMod zipName="Kotte_Universal" downloadLink = "http://www.marhu.net/phpBB3/viewtopic.php?f=137&t=1752"/>
		<optionalMod zipName="Bad" downloadLink = "javascript:alert(1)"/>
	</SearchMods>
</modDesc>
"""


def _desc(req: str = "AnimationMapTrigger", opt: str = "SoilManagement") -> str:
    return SEARCH.format(req=req, opt=opt)


def test_searchmods_required_and_optional():
    info = moddesc.extract_info(_desc().encode("utf-8"))
    assert info is not None and info.xml_ok  # le « & » non échappé est toléré
    # Les mods requis rejoignent les dépendances, sans doublon ni « .zip ».
    assert info.dependencies == ["FS25_Already", "AnimationMapTrigger", "ZZZ_multiFruit"]
    assert [m["name"] for m in info.search_mods] == ["AnimationMapTrigger", "ZZZ_multiFruit", "FS25_Already"]
    assert info.search_mods[1]["url"] == "http://www.modhoster.de/mods/multifruit--4"
    assert [m["name"] for m in info.optional_mods] == ["SoilManagement", "Kotte_Universal", "Bad"]
    assert info.optional_mods[1]["url"] == "http://www.marhu.net/phpBB3/viewtopic.php?f=137&t=1752"
    assert info.optional_mods[2]["url"] is None  # adresse refusée


def test_searchmods_in_unreadable_xml():
    broken = _desc().replace("</modDesc>", "<oops></modDesc>")
    info = moddesc.extract_info(broken.encode("utf-8"))
    assert info is not None and not info.xml_ok
    assert "AnimationMapTrigger" in info.dependencies and "ZZZ_multiFruit" in info.dependencies
    assert [m["name"] for m in info.optional_mods][:2] == ["SoilManagement", "Kotte_Universal"]


@pytest.mark.parametrize("url,ok", [
    ("http://www.fs-uk.com/mods/view/36108", True),
    ("https://www.dropbox.com/s/x/y.zip?dl=0", True),
    ("javascript:alert(1)", False),
    ("file:///C:/Windows/System32/cmd.exe", False),
    ("ftp://example.com/mod.zip", False),
    ("https://user:pass@example.com/", False),
    ("https://example.com/a b", False),
    ("https://", False),
    ("http://example.com/" + "a" * 2000, False),
])
def test_safe_url(url, ok):
    assert (moddesc.safe_url(url) == url) is ok


def test_resolve_optional_and_links():
    mods = {
        "fs25_map": {"id": "FS25_Map", "dependencies": ["FS25_Lib", "AnimationMapTrigger"],
                     "search_mods": [{"name": "FS25_Lib", "url": "https://example.com/lib"},
                                     {"name": "AnimationMapTrigger", "url": "http://vertexdezign.net/x"}],
                     "optional_mods": [{"name": "FS25_Opt", "url": "https://example.com/opt"},
                                       {"name": "SoilManagement", "url": "http://www.fs-uk.com/soil"},
                                       {"name": "FS25_Lib", "url": None}]},
        "fs25_lib": {"id": "FS25_Lib", "dependencies": [],
                     "optional_mods": [{"name": "FS25_Opt2", "url": None}]},
        "fs25_opt": {"id": "FS25_Opt", "dependencies": []},
        "fs25_opt2": {"id": "FS25_Opt2", "dependencies": []},
    }
    res = resolve_dependencies(["FS25_Map"], mods)
    assert res["present"] == ["FS25_Lib"] and res["missing"] == ["AnimationMapTrigger"]
    # Un mod déjà requis n'est pas facultatif ; les facultatifs des dépendances comptent.
    assert [(o["name"], o["present"]) for o in res["optional"]] == [
        ("FS25_Opt", True), ("FS25_Opt2", True), ("SoilManagement", False)]
    assert res["optional"][1]["required_by"] == "FS25_Map"
    # Liens : seulement pour les mods absents, avec le mod qui les donne.
    assert res["links"] == {
        "animationmaptrigger": {"url": "http://vertexdezign.net/x", "mod": "FS25_Map"},
        "soilmanagement": {"url": "http://www.fs-uk.com/soil", "mod": "FS25_Map"},
    }


def _add_map(env, req: str, opt: str) -> None:  # noqa: F811
    write_zip(env["mods"] / "FS25_Tunxdorf.zip", {"modDesc.xml": _desc(req=req, opt=opt)})
    env["lib"]._scan()


def test_library_entry_and_party_with_optional(env):  # noqa: F811
    ids = env["info"]["ids"]
    _add_map(env, req=ids[0], opt=ids[1])
    core = env["core"]
    entry = core._lib_index("FS25")["fs25_tunxdorf"]
    assert entry["search_mods"][0]["name"] == ids[0]
    assert ids[0] in entry["dependencies"]
    assert entry["optional_mods"][0] == {"name": ids[1], "url": "https://example.com/optional"}
    # « ＋ Partie » : les facultatifs cochés entrent dans la partie, pas les autres.
    res = core.party_create("FS25", "Tunx", from_map="FS25_Tunxdorf", optional=[ids[1], ids[5]])
    mods = core._store("FS25").party(res["party"]["id"])["mods"]
    assert set(mods) == {"FS25_Tunxdorf", ids[0], ids[1]}
    res2 = core.party_create("FS25", "Tunx 2", from_map="FS25_Tunxdorf")
    assert ids[1] not in core._store("FS25").party(res2["party"]["id"])["mods"]
    with pytest.raises(AppError):
        core.party_create("FS25", "Tunx 3", from_map="FS25_Tunxdorf", optional="nope")


def test_open_mod_link_only_opens_urls_of_the_mod(env, monkeypatch):  # noqa: F811
    ids = env["info"]["ids"]
    _add_map(env, req=ids[0], opt=ids[1])
    opened = []
    monkeypatch.setattr(winapi, "open_url", lambda url: opened.append(url) or True)
    core = env["core"]
    assert core.open_mod_link("FS25", "FS25_Tunxdorf", "http://www.modhoster.de/mods/multifruit--4")
    assert opened == ["http://www.modhoster.de/mods/multifruit--4"]
    for bad in ("https://evil.example/", "javascript:alert(1)", " http://www.modhoster.de/mods/multifruit--4"):
        with pytest.raises(AppError):
            core.open_mod_link("FS25", "FS25_Tunxdorf", bad)
    with pytest.raises(AppError):  # adresse d'un autre mod
        core.open_mod_link("FS25", ids[2], "http://www.modhoster.de/mods/multifruit--4")
    assert len(opened) == 1


def test_old_cache_is_reread_once(env):  # noqa: F811
    lib = env["lib"]
    assert library.CACHE_SCHEMA == 4 and 3 in library.CACHE_SCHEMAS_REREAD
    import json

    path = lib.cache_dir / "mods.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["schema"] = 3
    path.write_text(json.dumps(data), encoding="utf-8")
    lib._load_cache()
    assert lib._cache and all(v.get("stamp") == "" for v in lib._cache.values())


def test_ui_pinned_card_and_info_button():
    hc = (ROOT / "ui" / "js" / "hovercard.js").read_text(encoding="utf-8")
    lib = (ROOT / "ui" / "js" / "library.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "css" / "lists.css").read_text(encoding="utf-8")
    assert "export function togglePin(" in hc and "'/api/mod-link'" in hc
    assert "class: 'tile-info'" in lib and "togglePin(el, el._item)" in lib
    assert ".tile-info" in css and ".hovercard.is-pinned" in css
    assert "pointer-events: auto;" in css.split(".hovercard.is-pinned {", 1)[1].split("}", 1)[0]
