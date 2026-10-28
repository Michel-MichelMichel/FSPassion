"""Sécurité du serveur local (chapitre 6) et quelques routes de l'API."""

from __future__ import annotations

import http.client
import json

import pytest

from fspassion.core import Core
from fspassion.events import EventBus
from fspassion.server import Server


@pytest.fixture
def server():
    core = Core(dev=True, bus=EventBus())
    core.settings.set("first_detection_done", True)
    srv = Server(core, 0)
    srv.start()
    yield srv
    srv.stop()


def req(srv, method, path, body=None, headers=None, host=None):
    conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=5)
    h = {"Host": host or f"127.0.0.1:{srv.port}"}
    h.update(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    conn.request(method, path, body=data, headers=h)
    r = conn.getresponse()
    raw = r.read()
    conn.close()
    return r.status, r.headers, raw


def tok(srv):
    return {"X-FSP-Token": srv.token}


def test_listens_on_localhost_only(server):
    assert server.httpd.server_address[0] == "127.0.0.1"


def test_api_requires_token(server):
    assert req(server, "GET", "/api/state")[0] == 403
    assert req(server, "GET", "/api/state", headers={"X-FSP-Token": "faux"})[0] == 403
    status, _, raw = req(server, "GET", "/api/state", headers=tok(server))
    assert status == 200
    state = json.loads(raw)
    assert state["active_version"] == "FS25"
    assert {v["id"] for v in state["versions"]} >= {"FS2011", "FS25", "FS28"}


def test_rejects_foreign_origin_and_host(server):
    h = tok(server) | {"Origin": "http://evil.example"}
    assert req(server, "GET", "/api/state", headers=h)[0] == 403
    h = tok(server) | {"Sec-Fetch-Site": "cross-site"}
    assert req(server, "GET", "/api/state", headers=h)[0] == 403
    # Protection contre le « DNS rebinding » : nom d'hôte inattendu
    assert req(server, "GET", "/", host="evil.example:80")[0] == 403
    h = tok(server) | {"Origin": f"http://127.0.0.1:{server.port}"}
    assert req(server, "GET", "/api/state", headers=h)[0] == 200


def test_post_needs_json(server):
    status, _, _ = req(server, "POST", "/api/settings", headers=tok(server) | {"Content-Type": "text/plain"}, body={"theme": "red"})
    assert status == 415


def test_settings_validation(server):
    status, _, raw = req(server, "POST", "/api/settings", headers=tok(server), body={"theme": "red"})
    assert status == 200 and json.loads(raw)["theme"] == "red"
    assert req(server, "POST", "/api/settings", headers=tok(server), body={"theme": 5})[0] == 400
    assert req(server, "POST", "/api/settings", headers=tok(server), body={"inconnu": True})[0] == 400
    assert req(server, "POST", "/api/settings", headers=tok(server), body={"language": "xx"})[0] == 400


def test_static_files(server):
    status, headers, raw = req(server, "GET", "/")
    assert status == 200 and b"FS Passion" in raw
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert req(server, "GET", "/js/main.js")[0] == 200
    assert req(server, "GET", "/assets/icons/x.svg")[0] == 200
    # Pas de sortie du dossier de l'interface
    assert req(server, "GET", "/../src/fspassion/server.py")[0] == 404
    assert req(server, "GET", "/assets/../../src/fspassion/server.py")[0] == 404


def test_icons_need_token(server):
    assert req(server, "GET", "/icons/FS25/x.webp")[0] == 403
    cookie = {"Cookie": f"fsp_session={server.token}"}
    assert req(server, "GET", "/icons/FS25/..%2F..%2Fx.webp", headers=cookie)[0] == 404


def test_token_never_in_address(server):
    # L'adresse d'ouverture porte un billet, jamais le jeton de session.
    url = server.url("browser")
    assert server.token not in url
    assert "token=" not in url
    # Le jeton dans l'adresse n'ouvre plus l'API.
    assert req(server, "GET", f"/api/state?t={server.token}")[0] == 403
    assert req(server, "GET", f"/api/state?token={server.token}")[0] == 403


def test_ticket_is_exchanged_once_for_cookie(server):
    ticket = server.url("browser").split("ticket=")[1].split("&")[0]
    status, headers, _ = req(server, "GET", f"/?ticket={ticket}&shell=browser")
    assert status == 302
    assert headers["Location"] == "/?shell=browser"
    cookie = headers["Set-Cookie"]
    assert cookie.startswith(f"fsp_session={server.token};")
    for attr in ("Path=/", "HttpOnly", "SameSite=Strict"):
        assert attr in cookie
    assert "Domain=" not in cookie and "Max-Age" not in cookie
    # Le billet ne sert qu'une fois.
    assert req(server, "GET", f"/?ticket={ticket}")[0] == 403


def test_cookie_authorizes_api(server):
    status, _, _ = req(server, "GET", "/api/state", headers={"Cookie": f"fsp_session={server.token}"})
    assert status == 200
    assert req(server, "GET", "/api/state", headers={"Cookie": "fsp_session=faux"})[0] == 403


def test_expired_ticket_refused(server):
    server._tickets["vieux"] = 0.0
    assert server.take_ticket("vieux") is False
    assert req(server, "GET", "/?ticket=vieux")[0] == 403


def test_bad_content_length_and_chunked_refused(server):
    h = tok(server) | {"Content-Type": "application/json"}
    assert req(server, "POST", "/api/settings", headers=h | {"Content-Length": "abc"}, body=None)[0] == 400
    status, _, _ = req(server, "POST", "/api/settings", headers=h | {"Transfer-Encoding": "chunked"}, body=None)
    assert status == 411


def test_i18n_route(server):
    status, _, raw = req(server, "GET", "/api/i18n?lang=fr", headers=tok(server))
    data = json.loads(raw)
    assert status == 200 and data["code"] == "fr"
    assert data["strings"]["list1"]["title"] == "Tous les mods"


def test_themes_save_dev_only(server, tmp_path, monkeypatch):
    server.core.dev = False
    assert req(server, "POST", "/api/themes/save", headers=tok(server), body={"themes": []})[0] == 403
