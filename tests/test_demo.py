"""Pack de démonstration (14.2) : installation vérifiée, mode démonstration,
vrais chemins intacts, tout effacé en sortant."""

from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path

import pytest

from fspassion import config, demo, gamesettings
from fspassion.core import AppError, Core
from fspassion.events import EventBus

ROOT = Path(__file__).resolve().parents[1]
_PACK_CACHE: dict[str, Path] = {}


def build_pack(tmp_root: Path) -> Path:
    """Fabrique le pack une fois par session de tests (quelques secondes)."""
    if "pack" not in _PACK_CACHE:
        spec = importlib.util.spec_from_file_location("make_demo_pack", ROOT / "tools" / "make_demo_pack.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        out = tmp_root / "pack"
        _PACK_CACHE["pack"] = mod.build(out)
    return _PACK_CACHE["pack"]


@pytest.fixture(scope="session")
def pack(tmp_path_factory):
    return build_pack(tmp_path_factory.mktemp("demo"))


@pytest.fixture
def env(tmp_path, monkeypatch, pack):
    data = tmp_path / "FSPassion-data"
    (data / "demo").mkdir(parents=True)
    shutil.copy(pack, data / "demo" / pack.name)
    shutil.copy(pack.with_name(pack.name + ".sha256"), data / "demo" / (pack.name + ".sha256"))
    monkeypatch.setattr(config, "dev_data_dir", lambda: data)
    core = Core(dev=True, bus=EventBus())
    real = tmp_path / "Real" / "Mods"
    real.mkdir(parents=True)
    core.settings.update_version("FS25", {"mods_dir": str(real), "user_dir": str(tmp_path / "Real" / "Docs")})
    core.settings.set("first_detection_done", True)
    return {"core": core, "data": data, "real": real}


def test_demo_round_trip(env):
    core = env["core"]
    assert core.demo_state()["available"] is True
    core.demo_start()
    root = demo.demo_dir()
    assert core.settings.demo_active()
    vp = core.paths("FS25")
    assert vp.mods_dir is not None and str(vp.mods_dir).startswith(str(root))
    # Le jeu de démonstration charge son dossier de mods (Partie Pleine).
    ov = gamesettings.read_override(vp.gamesettings)
    assert ov.active and os.path.normpath(ov.directory) == os.path.normpath(str(vp.mods_dir))
    with pytest.raises(AppError):
        core.detect(None)
    lib = core.libs.get("FS25")
    lib._scan()
    mods = lib.snapshot()["mods"]
    assert len(mods) > 40 and any(m["is_map"] for m in mods)
    assert any(m["kind"] == "dir" for m in mods)
    # Créer et appliquer une partie fonctionne pour de vrai, dans le dossier de démonstration.
    the_map = next(m for m in mods if m["is_map"])
    pid = core.party_create("FS25", "Essai", the_map["id"])["party"]["id"]
    res = core.party_apply("FS25", pid)
    assert res["count"] >= 2
    assert str(res["directory"]).startswith(str(root))
    assert core.parties_state("FS25")["applied"] == pid
    # Les vrais chemins n'ont pas bougé.
    real_cfg = core.settings.snapshot()["versions"]["FS25"]
    assert real_cfg["mods_dir"] == str(env["real"])
    # Quitter : tout est effacé, les vrais chemins reviennent.
    core.demo_stop()
    assert not root.exists()
    assert not core.settings.demo_active()
    assert core.paths("FS25").mods_dir == env["real"]


def test_bad_pack_is_refused(env):
    pack = env["data"] / "demo" / demo.PACK
    pack.write_bytes(pack.read_bytes() + b"x")
    with pytest.raises(AppError) as err:
        env["core"].demo_start()
    assert err.value.key == "demo.bad_pack"
    assert not demo.demo_dir().exists()
    assert not env["core"].settings.demo_active()


def test_unsafe_archive_is_refused(env, tmp_path):
    import hashlib
    import zipfile
    pack = env["data"] / "demo" / demo.PACK
    with zipfile.ZipFile(pack, "w") as zf:
        zf.writestr("../evil.txt", "x")
        zf.writestr("demo.json", "{}")
    digest = hashlib.sha256(pack.read_bytes()).hexdigest()
    pack.with_name(pack.name + ".sha256").write_text(digest)
    with pytest.raises(AppError) as err:
        env["core"].demo_start()
    assert err.value.key == "demo.bad_pack"
    assert not (config.local_dir() / "evil.txt").exists()


def test_no_pack_means_unavailable(env):
    shutil.rmtree(env["data"] / "demo")
    assert env["core"].demo_state()["available"] is False
    with pytest.raises(AppError) as err:
        env["core"].demo_start()
    assert err.value.key == "demo.unavailable"
