"""Version 0.6.7 : relance en administrateur (port libéré), logo FS Passion,
trajet du logo GitHub, lanceur d'archive."""

from __future__ import annotations

import re
import socket
import threading
import time
from pathlib import Path

from fspassion import app
from fspassion.core import Core
from fspassion.events import EventBus
from fspassion.server import Server

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


# -- relance en administrateur : le port doit être libre ------------------------

def test_server_stop_releases_the_port():
    """Après stop(), le port restait tenu jusqu'à la fin du processus, et
    l'instance relancée en administrateur s'arrêtait sur « Port 8765 indisponible »."""
    core = Core(dev=True, bus=EventBus())
    first = Server(core, 0)
    first.start()
    port = first.port
    first.stop()
    second = Server(core, port)  # lèverait OSError si le port était encore tenu
    second.start()
    second.stop()


def test_open_server_waits_for_the_previous_instance():
    core = Core(dev=True, bus=EventBus())
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    holder.bind(("127.0.0.1", 0))
    holder.listen()
    port = holder.getsockname()[1]
    threading.Timer(0.8, holder.close).start()

    started = time.monotonic()
    server = app.open_server(core, port, wait_s=8)
    try:
        assert server.port == port
        assert time.monotonic() - started >= 0.5
    finally:
        server.httpd.server_close()


def test_open_server_gives_up_after_the_delay():
    core = Core(dev=True, bus=EventBus())
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    holder.bind(("127.0.0.1", 0))
    holder.listen()
    port = holder.getsockname()[1]
    try:
        try:
            app.open_server(core, port, wait_s=0.6)
        except OSError:
            pass
        else:
            raise AssertionError("le port occupé aurait dû être refusé")
    finally:
        holder.close()


def test_symlink_log_says_admin_and_developer_mode():
    src = _read("src", "fspassion", "storage.py")
    assert "administrateur : %s, Mode développeur : %s" in src


# -- logo FS Passion ------------------------------------------------------------

def test_app_logo_in_header_and_about():
    # 0.9.1 : le logo recadré assets/brand/fs-passion-logo.svg a disparu ; seul
    # le logo « deux tracteurs » (assets/FS_Passion_logo/logo.svg) est utilisé.
    logo = ROOT / "assets" / "FS_Passion_logo" / "logo.svg"
    assert logo.is_file()
    for parts in (("header.js",), ("settings.js",), ("welcome.js",)):
        js = _read("ui", "js", *parts)
        assert "class: 'app-logo app-logo-art'" in js, parts
    settings = _read("ui", "js", "settings.js")
    assert re.search(r"about-logo'.*app-logo", settings)
    css = _read("ui", "css", "layout.css")
    assert 'url("/assets/FS_Passion_logo/logo.svg")' in css
    assert "fs-passion-logo.svg\")" not in css
    assert ":root[data-grad] .app-logo" in css


# -- pied de page : trajet du logo GitHub ----------------------------------------

def test_github_logo_travels_from_the_centre_to_the_left():
    css = _read("ui", "css", "layout.css")
    block = re.search(r"\.gh-btn \{([^}]*)\}", css).group(1)
    assert "width: 116px" in block and "--gh-shift: 43px" in block
    assert (116 - 30) / 2 == 43
    assert "transform: translateX(var(--gh-shift))" in css
    assert re.search(r"\.gh-btn:hover \.gh-logo[^{]*\{ transform: translateX\(0\); \}", css)


# -- archive ----------------------------------------------------------------------

def test_archive_launcher():
    # Fichier suivi par git à la racine du dépôt.
    assert (ROOT / "archiver_version.bat").is_file()
    bat = (ROOT / "archiver_version.bat").read_bytes()
    assert b"\r\n" in bat
    text = bat.decode("utf-8")
    assert r"tools\archive_version.py" in text and "pause" in text
