"""Corrections du lot serveur et réseau : jeton hors des adresses, archives, journaux."""

from __future__ import annotations

import http.client
import json

import pytest

from fspassion import logs
from fspassion.core import AppError, Core
from fspassion.events import EventBus
from fspassion.server import Server


@pytest.fixture
def core():
    c = Core(dev=True, bus=EventBus())
    c.settings.set("first_detection_done", True)
    return c


def test_anonymize_hides_any_user_profile(monkeypatch):
    monkeypatch.setenv("USERPROFILE", "C:\\Users\\Utilisateur")
    assert logs.anonymize("Fichier D:\\Users\\Bob\\x") == "Fichier %USERPROFILE%\\x"
    assert logs.anonymize("c:/users/Carol/AppData/Local") == "%USERPROFILE%/AppData/Local"
    assert logs.anonymize("C:\\Users\\Utilisateur\\y") == "%USERPROFILE%\\y"
    # Sans nom après « Users » : rien à remplacer.
    assert logs.anonymize("dossier C:\\Users") == "dossier C:\\Users"


def test_downloads_integrate_refuses_non_zip_and_traversal(core):
    for name in ("../evil.zip", "..", ".", "photo.exe", "sous/x.zip", "a:b.zip"):
        with pytest.raises(AppError):
            core.downloads_integrate([{"file": name, "version": "FS25", "destination": "none"}])


def test_integrate_file_refuses_invalid_archive_on_same_disk(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from fspassion import downloads

    src = tmp_path / "faux.zip"
    src.write_bytes(b"pas une archive")
    mods = tmp_path / "mods"
    mods.mkdir()
    vp = SimpleNamespace(mods_dir=mods, storages=[mods], fsp_dir=None, version=SimpleNamespace(id="FS25"))
    monkeypatch.setattr(downloads, "assess", lambda item, vp: {"state": "new", "storage": 0})
    # Même disque : l'archive est contrôlée avant le déplacement.
    with pytest.raises(OSError):
        downloads.integrate_file(src, vp, "faux")
    assert src.exists() and not (mods / "faux.zip").exists()


@pytest.fixture
def server(core):
    srv = Server(core, 0)
    srv.start()
    yield srv
    srv.stop()


def _post(srv, path, body, headers):
    conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=5)
    data = json.dumps(body).encode()
    h = {"Host": f"127.0.0.1:{srv.port}", "Content-Type": "application/json"} | headers
    conn.request("POST", path, body=data, headers=h)
    r = conn.getresponse()
    status = r.status
    r.read()
    conn.close()
    return status


def test_set_rect_rejects_non_numeric_values(server):
    headers = {"X-FSP-Token": server.token}
    status = _post(server, "/api/window", {"action": "set-rect", "x": "abc", "y": 0, "width": 1, "height": 1},
                   headers)
    assert status == 400
    status = _post(server, "/api/window", {"action": "set-rect", "y": 0}, headers)
    assert status == 400
