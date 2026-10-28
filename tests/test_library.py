"""Scan d'un dossier de mods, cache, icônes, anomalies (3.4, 4.4, 4.10).

Le test le plus important : le scan ne modifie AUCUN fichier du dossier de
mods (versions 0.1 et 0.2 en lecture seule ; invariant I9).
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest

from fspassion import gamepaths, library, moddesc, versions
from fspassion.events import EventBus

import fakemods


def snapshot(folder: Path) -> dict[str, tuple[int, int, str]]:
    out = {}
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(folder))] = (p.stat().st_size, p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
        else:
            out[str(p.relative_to(folder)) + "/"] = (0, 0, "")
    return out


@pytest.fixture
def setup(tmp_path):
    mods = tmp_path / "FS25_Mods" / "Mods"
    info = fakemods.make_collection(mods, count=12)
    user = tmp_path / "Documents" / "My Games" / "FarmingSimulator2025"
    fakemods.make_dlc(user / "pdlc", ["vredoPack.dlc", "skyAgriculturePack.dlc", "FS25_freeStuff.zip"])
    cfg = {"user_dir": str(user), "mods_dir": str(mods), "game_exe": ""}
    vp = gamepaths.from_cfg(versions.require("FS25"), cfg)
    lib = library.Library("FS25", EventBus(), lambda: vp)
    return lib, mods, vp, info


def run_scan(lib):
    lib._scan()
    for _ in range(200):
        if lib.icons_pending == 0:
            break
        time.sleep(0.05)


def test_scan_contents(setup):
    lib, mods, vp, info = setup
    run_scan(lib)
    snap = lib.snapshot()
    ids = {m["id"] for m in snap["mods"]}
    assert set(info["ids"]) <= ids
    assert set(info["maps"]) <= ids
    assert "FS25_DevMod" in ids  # mod non compressé
    dev = next(m for m in snap["mods"] if m["id"] == "FS25_DevMod")
    assert dev["kind"] == "dir"
    types = sorted(a["type"] for a in snap["anomalies"])
    assert types == ["A1", "A1", "A2", "A2", "A3", "A4", "A5", "A6"]
    a5 = next(a for a in snap["anomalies"] if a["type"] == "A5")
    assert a5["detail"]["suggestion"] == "FS25_Tracteur_Renove"
    a6 = next(a for a in snap["anomalies"] if a["type"] == "A6")
    assert a6["detail"]["detected"] == "FS22"
    assert [o["name"] for o in snap["others"]] == ["notes.txt"]
    # DLC : catalogue (noms) et .zip (titre du modDesc)
    dlc = {d["id"]: d for d in snap["dlc"]}
    assert dlc["vredoPack"]["known"] is True
    assert dlc["FS25_freeStuff"]["type"] == "zip"
    # Les maps : dépendances lues
    m = next(x for x in snap["mods"] if x["id"] == info["maps"][0])
    assert m["is_map"] and len(m["dependencies"]) == 5


def test_icons_converted_without_reduction(setup):
    lib, mods, vp, info = setup
    run_scan(lib)
    icons_dir = vp.fsp_dir / "cache" / "icons"
    snap = lib.snapshot()
    ok = [m for m in snap["mods"] if m["icon_state"] == "ok"]
    assert len(ok) == len(snap["mods"])
    from PIL import Image

    any_mod = ok[0]
    with Image.open(icons_dir / f"{any_mod['icon']}.webp") as im:
        assert im.size == (256, 256)  # résolution d'origine conservée
    with Image.open(icons_dir / f"{any_mod['icon']}-small.webp") as im:
        assert max(im.size) == 96


def test_scan_is_read_only(setup):
    """I9 : la v0.1 ne modifie aucun fichier de mods."""
    lib, mods, vp, info = setup
    before = snapshot(mods)
    run_scan(lib)
    run_scan(lib)
    assert snapshot(mods) == before
    # Tout ce que FS Passion écrit est dans FSPassion\FS25\ à côté du dossier de mods.
    assert (mods.parent / "FSPassion" / "FS25" / "cache" / "mods.json").is_file()


def test_cache_reused_and_purged(setup, monkeypatch):
    lib, mods, vp, info = setup
    run_scan(lib)
    count = len(lib.entries)

    calls = []
    real = moddesc.read_zip
    # Seuls les mods comptent (les .zip de DLC, peu nombreux, sont relus).
    monkeypatch.setattr(moddesc, "read_zip", lambda p: (calls.append(p) if p.parent == mods else None) or real(p))
    lib2 = library.Library("FS25", EventBus(), lambda: vp)
    run_scan(lib2)
    assert calls == []  # rien n'est relu : tout vient du cache
    assert len(lib2.entries) == count

    # Un mod modifié est relu ; un mod disparu est purgé (cache et icônes).
    victim = mods / f"{info['ids'][0]}.zip"
    victim.unlink()
    changed = mods / f"{info['ids'][1]}.zip"
    fakemods.make_zip_mod(mods, info["ids"][1], seed=999, version="9.9.9.9")
    run_scan(lib2)
    assert [Path(p).name for p in calls] == [changed.name]
    ids = {e["id"] for e in lib2.entries.values()}
    assert info["ids"][0] not in ids
    assert next(e for e in lib2.entries.values() if e["id"] == info["ids"][1])["version"] == "9.9.9.9"
    icons_dir = vp.fsp_dir / "cache" / "icons"
    assert not any(p.name.startswith(info["ids"][0] + "-") for p in icons_dir.iterdir())


def test_quick_check_detects_changes(setup):
    lib, mods, vp, info = setup
    run_scan(lib)
    sig = lib._signature
    assert lib._compute_signature(vp) == sig
    fakemods.make_zip_mod(mods, "FS25_NewOne", seed=50)
    assert lib._compute_signature(vp) != sig


def test_missing_mods_dir(tmp_path):
    vp = gamepaths.from_cfg(versions.require("FS25"), {"mods_dir": str(tmp_path / "absent")})
    lib = library.Library("FS25", EventBus(), lambda: vp)
    lib._scan()
    assert lib.status == "error"
    assert lib.error["key"] == "library.error.no_mods_dir"


def test_fs2011_mods_dir_fixed(tmp_path):
    user = tmp_path / "My Games" / "FarmingSimulator2011"
    vp = gamepaths.from_cfg(versions.require("FS2011"), {"user_dir": str(user), "mods_dir": "D:/ailleurs"})
    assert vp.mods_dir == user / "mods"
    assert vp.gamesettings is None
    assert [p.name for p in vp.dlc_dirs] == ["pdlc2.1"]
