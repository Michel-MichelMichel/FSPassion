"""Serveur local : API JSON, flux d'événements et fichiers de l'interface.

Sécurité : le serveur n'écoute que sur 127.0.0.1, chaque requête de l'API porte
un jeton secret propre à la session, et l'origine des requêtes est contrôlée.
Sans cela, une page web ouverte dans le navigateur pourrait commander
l'application.

Le jeton n'apparaît jamais dans une adresse. L'adresse d'ouverture porte un
billet à usage unique, échangé contre un cookie HttpOnly (SameSite=Strict) qui
porte le jeton ; l'interface n'a plus besoin de le lire.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import queue
import secrets
import threading
import time
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from fspassion import config, fsutil, versions
from fspassion.core import AppError, Core
from fspassion.parties import PartyError
from fspassion.window_ops import native

log = logging.getLogger(__name__)

MAX_BODY = 1024 * 1024
SESSION_COOKIE = "fsp_session"
TICKET_TTL = 120  # secondes : durée de validité d'une adresse d'ouverture
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".webm": "video/webm",
}
CSP = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; connect-src 'self'; font-src 'self'; media-src 'self'; "
    "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)

Handler = Callable[[Core, dict[str, Any], dict[str, list[str]], "RequestContext"], Any]


class RequestContext:
    def __init__(self, from_window: bool) -> None:
        self.from_window = from_window


class Server:
    def __init__(self, core: Core, port: int = 0) -> None:
        self.core = core
        self.token = secrets.token_urlsafe(32)
        self._tickets: dict[str, float] = {}
        self._tickets_lock = threading.Lock()
        self.routes: dict[tuple[str, str], Handler] = {}
        self._register_routes()
        self.httpd = _HTTPServer(("127.0.0.1", port), _RequestHandler)
        self.httpd.app = self  # type: ignore[attr-defined]
        self.port = self.httpd.server_address[1]
        self._thread: threading.Thread | None = None
        self.quit_callback: Callable[[], None] | None = None
        self.focus_callback: Callable[[], None] | None = None
        # Croix de la fenêtre (0.2.1) : cacher dans la zone de notification, ou
        # quitter. Sans réglage : quitter.
        self.close_callback: Callable[[], None] | None = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def url(self, shell: str = "browser") -> str:
        """Adresse d'ouverture : un billet à usage unique, jamais le jeton de session."""
        ticket = secrets.token_urlsafe(24)
        now = time.monotonic()
        with self._tickets_lock:
            self._tickets = {t: exp for t, exp in self._tickets.items() if exp > now}
            self._tickets[ticket] = now + TICKET_TTL
        return f"{self.base_url}/?ticket={ticket}&shell={shell}"

    def take_ticket(self, ticket: str) -> bool:
        """Consomme un billet : valable une seule fois, dans la durée prévue."""
        with self._tickets_lock:
            expires = self._tickets.pop(ticket, None)
        return expires is not None and expires > time.monotonic()

    def allowed_origins(self) -> set[str]:
        return {f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}"}

    def allowed_hosts(self) -> set[str]:
        return {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}

    def start(self) -> None:
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="http", daemon=True)
        self._thread.start()
        log.info("Serveur local : %s", self.base_url)

    def stop(self) -> None:
        # 0.6.7 : shutdown() arrête la boucle mais garde le port ouvert jusqu'à la
        # fin du processus. La relance en administrateur démarrait alors avant que
        # le port soit libre (« Port 8765 indisponible ») : on le ferme vraiment.
        self.httpd.shutdown()
        self.httpd.server_close()

    # ------------------------------------------------------------------
    # Routes de l'API
    # ------------------------------------------------------------------

    def route(self, method: str, path: str) -> Callable[[Handler], Handler]:
        def deco(fn: Handler) -> Handler:
            self.routes[(method, path)] = fn
            return fn
        return deco

    def _register_routes(self) -> None:
        r = self.route

        @r("GET", "/api/state")
        def _state(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.state()

        @r("GET", "/api/i18n")
        def _i18n(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            code = (q.get("lang") or [core.settings.get("language") or "en"])[0]
            if not core.langs.has(code):
                code = "en"
            return {"code": code, "strings": core.langs.strings(code)}

        @r("POST", "/api/settings")
        def _settings(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.set_settings(body)

        @r("POST", "/api/version/active")
        def _active(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            core.set_active_version(str(body.get("version", "")))
            return {"ok": True}

        @r("POST", "/api/version/path")
        def _path(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.set_path(str(body.get("version", "")), str(body.get("field", "")), str(body.get("value", "")))

        @r("POST", "/api/older/resolve")
        def _older(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.older_resolve(str(body.get("version") or core.active_version()), body.get("path"),
                                      str(body.get("action", "")))

        @r("POST", "/api/version/storages")
        def _storages(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.set_storages(str(body.get("version", "")), body.get("dirs"))

        @r("POST", "/api/rights")
        def _rights(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            out = core.rights_action(str(body.get("action", "")))
            if out.get("restart"):
                # Relance en administrateur : FS Passion se ferme d'abord (app.py).
                threading.Timer(0.4, self._quit).start()
            return out

        @r("POST", "/api/version/launch-method")
        def _method(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.set_launch_method(str(body.get("version", "")), str(body.get("method", "")))

        @r("POST", "/api/version/launch-args")
        def _launch_args(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.set_launch_args(
                str(body.get("version", "")),
                bool(body.get("skip_start_videos")),
                bool(body.get("cheats")),
            )

        @r("POST", "/api/version/console")
        def _console(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.enable_console(str(body.get("version", "")))

        @r("POST", "/api/detect")
        def _detect(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            vid = body.get("version")
            return core.detect(str(vid) if vid else None)

        @r("POST", "/api/browse")
        def _browse(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            path = core.browse(
                str(body.get("kind", "")), body.get("version"), body.get("field"),
                body.get("initial"), ctx.from_window,
            )
            return {"path": path}

        @r("GET", "/api/library")
        def _library(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            vid = (q.get("version") or [core.active_version()])[0]
            return core.library(vid)

        @r("POST", "/api/library/rescan")
        def _rescan(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            core.rescan(str(body.get("version") or core.active_version()), bool(body.get("quick")))
            return {"ok": True}

        @r("POST", "/api/anomalies")
        def _anoms(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.anomalies_action(
                str(body.get("version") or core.active_version()),
                str(body.get("action", "")), body.get("value"),
            )

        # -- Parties et classement (4.1, 4.5, 4.6) --------------------------------

        def vid_of(core: Core, body: dict[str, Any]) -> str:
            return str(body.get("version") or core.active_version())

        def text(body: dict[str, Any], key: str) -> str:
            value = body.get(key)
            if not isinstance(value, str):
                raise AppError("error.bad_request")
            return value

        @r("GET", "/api/parties")
        def _parties(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.parties_state((q.get("version") or [core.active_version()])[0])

        @r("POST", "/api/parties/create")
        def _p_create(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            from_map = body.get("map")
            return core.party_create(vid_of(core, body), text(body, "name"), str(from_map) if from_map else None,
                                     optional=body.get("optional"))

        @r("POST", "/api/parties/duplicate")
        def _p_dup(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.party_duplicate(vid_of(core, body), text(body, "id"), text(body, "name"))

        @r("POST", "/api/parties/rename")
        def _p_rename(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.party_rename(vid_of(core, body), text(body, "id"), text(body, "name"))

        @r("POST", "/api/parties/delete")
        def _p_delete(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.party_delete(vid_of(core, body), text(body, "id"))

        @r("POST", "/api/parties/select")
        def _p_select(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.party_select(vid_of(core, body), text(body, "id"))

        @r("POST", "/api/parties/common")
        def _p_common(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            enabled = body.get("enabled")
            if not isinstance(enabled, bool):
                raise AppError("error.bad_request")
            return core.party_common(vid_of(core, body), text(body, "id"), enabled)

        @r("POST", "/api/parties/mods")
        def _p_mods(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            party = body.get("party")
            source = body.get("source")
            return core.party_mods(
                vid_of(core, body), text(body, "action"), text(body, "target"), body.get("ids"),
                pid=str(party) if party else None, source=str(source) if source else None,
            )

        @r("POST", "/api/parties/replace")
        def _p_replace(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.party_replace(vid_of(core, body), text(body, "old"), text(body, "new"))

        @r("POST", "/api/parties/apply")
        def _p_apply(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            party = body.get("id")
            return core.party_apply(vid_of(core, body), str(party) if party else None)

        @r("POST", "/api/override/resolve")
        def _ov_resolve(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            directory = body.get("directory")
            party = body.get("id")
            return core.override_resolve(vid_of(core, body), text(body, "action"),
                                         str(directory) if directory else None, str(party) if party else None)

        @r("POST", "/api/demo")
        def _demo(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            action = text(body, "action")
            if action == "start":
                return core.demo_start()
            if action == "stop":
                return core.demo_stop()
            if action == "offered":
                core.demo_offered()
                return core.demo_state()
            raise AppError("error.bad_request")

        # -- 0.4 : réconciliation, téléchargements, supprimer, renommer -----------

        @r("POST", "/api/reconcile")
        def _reconcile(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.reconcile(vid_of(core, body), "manual")

        @r("POST", "/api/missing/resolve")
        def _missing(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.missing_resolve(vid_of(core, body), text(body, "action"), body.get("ids"))

        @r("POST", "/api/downloads/scan")
        def _dl_scan(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.downloads_scan()

        @r("POST", "/api/downloads/integrate")
        def _dl_integrate(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.downloads_integrate(body.get("items"))

        @r("POST", "/api/downloads/ignore")
        def _dl_ignore(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.downloads_ignore(body.get("files"))

        @r("POST", "/api/mods/delete-preview")
        def _del_preview(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.mods_delete_preview(vid_of(core, body), body.get("ids"))

        @r("POST", "/api/mods/delete")
        def _del(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.mods_delete(vid_of(core, body), body.get("ids"), body.get("confirm"))

        @r("POST", "/api/mods/rename-preview")
        def _ren_preview(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.mod_rename_preview(vid_of(core, body), body.get("id"))

        @r("POST", "/api/mods/rename")
        def _ren(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.mod_rename(vid_of(core, body), body.get("id"), body.get("new"))

        @r("POST", "/api/mods/rename-lists")
        def _ren_lists(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            # 0.4 (correction) : deuxième temps du renommage, sur confirmation.
            return core.mod_lists_rename(vid_of(core, body), body.get("old"), body.get("new"))

        @r("POST", "/api/deps")
        def _deps(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.resolve_deps(vid_of(core, body), body.get("ids"))

        @r("POST", "/api/game/launch")
        def _launch(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.launch(str(body.get("version") or core.active_version()), bool(body.get("apply")))

        @r("POST", "/api/open")
        def _open(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return {"ok": core.open_folder(str(body.get("what", "")))}

        @r("POST", "/api/link")
        def _link(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return {"ok": core.open_link(str(body.get("key", "")))}

        @r("POST", "/api/mod-link")
        def _mod_link(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            # 0.7.3 : lien de téléchargement d'un mod requis ou facultatif (<SearchMods>).
            return {"ok": core.open_mod_link(vid_of(core, body), body.get("mod"), body.get("url"))}

        @r("POST", "/api/reveal")
        def _reveal(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return {"ok": core.reveal_item(
                str(body.get("version") or core.active_version()), body.get("storage"), body.get("name"),
            )}

        @r("GET", "/api/diagnostic")
        def _diag(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return {"text": core.diagnostic()}

        @r("POST", "/api/window")
        def _window(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            action = str(body.get("action", ""))
            if action == "minimize":
                native.minimize()
            elif action == "toggle-maximize":
                return {"maximized": native.toggle_maximize()}
            elif action == "close":
                if self.close_callback:
                    self.close_callback()
                else:
                    self._quit()
            elif action == "drag":
                return {"ok": native.begin_drag(str(body.get("edge", "")))}
            elif action == "rect":
                return {"rect": native.rect(), "maximized": native.is_maximized()}
            elif action == "set-rect":
                try:
                    x, y, width, height = (int(body[k]) for k in ("x", "y", "width", "height"))
                except (KeyError, TypeError, ValueError) as exc:
                    raise AppError("error.bad_request") from exc
                native.set_rect(x, y, width, height)
            else:
                raise AppError("error.bad_request")
            return {"ok": True}

        @r("POST", "/api/app/quit")
        def _quit(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            threading.Timer(0.2, self._quit).start()
            return {"ok": True}

        @r("POST", "/api/app/focus")
        def _focus(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            if self.focus_callback:
                self.focus_callback()
            return {"ok": True}

        @r("POST", "/api/themes/save")
        def _themes(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            # Atelier de thèmes : outil de développement uniquement (5.5).
            if not core.dev or config.is_frozen():
                raise AppError("error.forbidden", status=403)
            themes = body.get("themes")
            if not isinstance(themes, list):
                raise AppError("error.bad_request")
            data = fsutil.read_json(config.ui_dir() / "themes.json", {}) or {}
            data["themes"] = themes
            fsutil.atomic_write_json(config.ui_dir() / "themes.json", data)
            return {"ok": True}

        # -- 0.7.0 : sauvegarde de la configuration (4.17) --------------------

        @r("POST", "/api/backup/export")
        def _export(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.export_config(ctx.from_window)

        @r("POST", "/api/backup/import-open")
        def _import_open(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.import_open(ctx.from_window)

        @r("POST", "/api/backup/import")
        def _import(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.import_apply(body.get("token"), body.get("keep_paths"))

        # -- 0.7.0 : ne plus utiliser FS Passion (4.18) ------------------------

        @r("GET", "/api/stop/preview")
        def _stop_preview(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.stop_preview()

        @r("POST", "/api/stop")
        def _stop(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.stop_using(body.get("options"), body.get("confirm"))

        @r("POST", "/api/stop/quit")
        def _stop_quit(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            core.stop_quit(body.get("uninstaller"))
            threading.Timer(0.2, self._quit).start()
            return {"ok": True}

        # -- 0.7.0 : mesures de performance (diagnostic) -----------------------

        @r("POST", "/api/perf")
        def _perf(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            return core.record_ui_perf(body)

        # -- 0.7.0 : catalogue des DLC distant (4.11) --------------------------

        @r("POST", "/api/dlc/refresh")
        def _dlc_refresh(core: Core, body: dict[str, Any], q: dict[str, list[str]], ctx: RequestContext) -> Any:
            res = core.update_remote_data(force=True)
            res["state"] = core.dlc_catalog_state()
            return res

    def _quit(self) -> None:
        if self.quit_callback:
            self.quit_callback()


class _HTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


class _RequestHandler(BaseHTTPRequestHandler):
    server_version = "FSPassion"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    # Délai par socket : une connexion locale muette ne bloque pas son fil indéfiniment.
    timeout = 30

    @property
    def app(self) -> Server:
        return self.server.app  # type: ignore[attr-defined,no-any-return]

    def log_message(self, fmt: str, *args: Any) -> None:  # silence de la console
        log.debug("HTTP " + fmt, *args)

    # -- contrôles de sécurité ----------------------------------------------

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").lower()
        return host in self.app.allowed_hosts()

    def _origin_ok(self) -> bool:
        # Un navigateur indique l'origine d'une requête venue d'une autre page.
        site = (self.headers.get("Sec-Fetch-Site") or "").lower()
        if site in ("cross-site", "same-site"):
            return False
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return origin in self.app.allowed_origins()

    def _cookie(self, name: str) -> str:
        for part in (self.headers.get("Cookie") or "").split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return ""

    def _token_ok(self) -> bool:
        # Le cookie de session sert à l'interface ; l'en-tête sert aux autres clients locaux.
        tok = self.headers.get("X-FSP-Token") or self._cookie(SESSION_COOKIE)
        return bool(tok) and secrets.compare_digest(tok.encode("utf-8"), self.app.token.encode("ascii"))

    # -- réponses -------------------------------------------------------------

    def _send(self, status: int, body: bytes, ctype: str, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, obj: Any) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(status, data, "application/json; charset=utf-8", {"Cache-Control": "no-store"})

    def _error(self, status: int, key: str, **params: Any) -> None:
        self._json(status, {"error": key, "params": params})

    # -- méthodes HTTP --------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        try:
            if not self._host_ok():
                self._error(403, "error.forbidden")
                return
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            query = parse_qs(parsed.query)

            if path.startswith("/api/"):
                self._api(method, path, query)
                return
            if method != "GET":
                self._error(405, "error.bad_request")
                return
            if path == "/" and "ticket" in query:
                self._open_ticket(query)
                return
            if path.startswith("/icons/"):
                self._icon(path)
                return
            if path.startswith("/dlc-icons/"):
                self._dlc_icon(path)
                return
            self._static(path)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception:  # noqa: BLE001
            log.exception("Erreur du serveur local")
            try:
                self._error(500, "error.unexpected")
            except Exception:  # noqa: BLE001
                pass

    def _open_ticket(self, query: dict[str, list[str]]) -> None:
        """Échange le billet d'ouverture contre le cookie de session, puis retire le billet de l'adresse."""
        if not self.app.take_ticket((query.get("ticket") or [""])[0]):
            self._error(403, "error.forbidden")
            return
        rest = urlencode([(k, v) for k, values in query.items() if k != "ticket" for v in values])
        cookie = f"{SESSION_COOKIE}={self.app.token}; Path=/; HttpOnly; SameSite=Strict"
        self._send(
            HTTPStatus.FOUND,
            b"",
            "text/plain; charset=utf-8",
            {
                "Location": "/?" + rest if rest else "/",
                "Set-Cookie": cookie,
                "Cache-Control": "no-store",
            },
        )

    def _api(self, method: str, path: str, query: dict[str, list[str]]) -> None:
        if not self._origin_ok() or not self._token_ok():
            self.close_connection = True
            self._error(403, "error.forbidden")
            return
        if path == "/api/events" and method == "GET":
            self._events()
            return
        handler = self.app.routes.get((method, path))
        if handler is None:
            # Corps éventuel non lu : la connexion ne doit pas resservir (0.8.8).
            self.close_connection = True
            self._error(404, "error.not_found")
            return
        body: dict[str, Any] = {}
        if method == "POST":
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype != "application/json":
                self.close_connection = True
                # Oblige un navigateur tiers à une requête de contrôle (CORS), refusée.
                self._error(415, "error.bad_request")
                return
            if self.headers.get("Transfer-Encoding"):
                # Corps en morceaux : non lu, donc la connexion ne doit pas resservir.
                self.close_connection = True
                self._error(411, "error.bad_request")
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if length < 0:
                self.close_connection = True
                self._error(400, "error.bad_request")
                return
            if length > MAX_BODY:
                self.close_connection = True
                self._error(413, "error.bad_request")
                return
            raw = self.rfile.read(length) if length else b"{}"
            try:
                parsed = json.loads(raw.decode("utf-8") or "{}")
            except (ValueError, UnicodeDecodeError):
                self._error(400, "error.bad_request")
                return
            if not isinstance(parsed, dict):
                self._error(400, "error.bad_request")
                return
            body = parsed
        ctx = RequestContext(from_window=(self.headers.get("X-FSP-Shell") == "window"))
        try:
            result = handler(self.app.core, body, query, ctx)
        except (AppError, PartyError) as exc:
            self._error(exc.status, exc.key, **exc.params)
            return
        except KeyError:
            self._error(400, "error.bad_request")
            return
        self._json(200, result if result is not None else {"ok": True})

    def _events(self) -> None:
        """Flux d'événements (Server-Sent Events)."""
        bus = self.app.core.bus
        q = bus.subscribe()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.wfile.write(b"retry: 1500\n\n")
            self.wfile.flush()
            while True:
                try:
                    ev = q.get(timeout=15)
                    data = json.dumps(ev, ensure_ascii=False)
                    self.wfile.write(f"data: {data}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            bus.unsubscribe(q)
            self.close_connection = True

    def _icon(self, path: str) -> None:
        if not self._token_ok():
            self._error(403, "error.forbidden")
            return
        parts = path.split("/")  # ['', 'icons', 'FS25', 'nom.webp']
        if len(parts) != 4 or versions.get(parts[2]) is None:
            self._error(404, "error.not_found")
            return
        f = self.app.core.libs.get(parts[2]).icon_file(parts[3])
        if f is None:
            self._error(404, "error.not_found")
            return
        self._file(f, cache="private, max-age=31536000, immutable")

    def _dlc_icon(self, path: str) -> None:
        if not self._token_ok():
            self._error(403, "error.forbidden")
            return
        parts = path.split("/")
        if len(parts) != 4 or versions.get(parts[2]) is None:
            self._error(404, "error.not_found")
            return
        f = self.app.core.libs.get(parts[2]).dlc_icon_file(parts[3])
        if f is None:
            self._error(404, "error.not_found")
            return
        self._file(f, cache="private, max-age=3600")

    def _static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        if path.startswith("/assets/"):
            base = config.assets_dir()
            rel = path[len("/assets/"):]
        else:
            base = config.ui_dir()
            rel = path.lstrip("/")
        target = (base / rel)
        if not fsutil.is_within(target, base) or not target.is_file():
            self._error(404, "error.not_found")
            return
        extra = {}
        if target.suffix == ".html":
            extra["Content-Security-Policy"] = CSP
        # « no-cache » aussi dans l'exécutable : après une mise à jour, WebView2
        # gardait les anciens fichiers de l'interface.
        self._file(target, cache="no-cache", extra=extra)

    def _file(self, f: Path, cache: str, extra: dict[str, str] | None = None) -> None:
        try:
            data = f.read_bytes()
        except OSError:
            self._error(404, "error.not_found")
            return
        ctype = TYPES.get(f.suffix.lower()) or mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        headers = {"Cache-Control": cache}
        headers.update(extra or {})
        self._send(HTTPStatus.OK, data, ctype, headers)
