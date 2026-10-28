"""Mises à jour de FS Passion.

Les versions sont publiées dans les « Releases » du dépôt GitHub de
FS Passion (adresse : app_info.json → github_url). Une publication contient
l'installeur, la version portable et SHA256SUMS.txt (tools\\build.py).

Règles :
- seulement si l'utilisateur l'autorise (réglage « update_check », activé
  par défaut, indépendant du catalogue des DLC) ;
- une recherche au lancement, puis une par jour tant que FS Passion reste
  ouvert (zone de notification) ;
- seule la dernière publication définitive compte : GitHub n'y range ni les
  brouillons ni les préversions ;
- une simple lecture de pages publiques : ni identifiant, ni cookie, ni
  donnée personnelle ;
- adresses en https uniquement, sur GitHub seulement, redirections
  comprises (les fichiers d'une publication sont servis par
  objects.githubusercontent.com ou release-assets.githubusercontent.com) ;
- le fichier téléchargé doit correspondre à son empreinte dans
  SHA256SUMS.txt, publié avec lui : sans empreinte, rien n'est installé ;
- installation : l'installeur se lance après la fermeture de FS Passion
  (il refuse de travailler tant que FS Passion est ouvert), en mode
  silencieux avec sa barre de progression, puis relance FS Passion ;
- version portable : le .zip vérifié est rangé dans le dossier des
  téléchargements, et l'Explorateur l'affiche ; le remplacement du dossier
  reste fait à la main (le dossier « data » à côté de l'exécutable garde
  les réglages).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fspassion import __version__, config, winapi

log = logging.getLogger(__name__)

API_HOST = "api.github.com"
# Hôtes permis pour les fichiers d'une publication (adresse d'origine et
# redirections).
DOWNLOAD_HOSTS = (
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
)
TIMEOUT = 20
INTERVAL_S = 24 * 3600
STARTUP_DELAY_S = 8
# Recherche automatique (lancement, puis une fois par jour). Coupée par les
# tests, qui ne doivent jamais aller sur Internet.
AUTO_CHECK = True
MAX_API = 1024 * 1024
MAX_SUMS = 64 * 1024
MAX_INSTALLER = 300 * 1024 * 1024
MAX_PORTABLE = 400 * 1024 * 1024
NOTES_MAX = 4000

_VERSION_RE = re.compile(r"^v?(\d{1,4})\.(\d{1,4})\.(\d{1,4})$")
_SUM_RE = re.compile(r"^([0-9a-fA-F]{64})\s+\*?(\S+)\s*$")
_REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")


class UpdateError(Exception):
    """Erreur prévue, avec une clé courte traduite par l'interface
    (settings.updates.error_<clé>)."""

    def __init__(self, key: str, detail: str = "") -> None:
        super().__init__(key)
        self.key = key
        self.detail = detail


# --------------------------------------------------------------------------
# Numéros de version
# --------------------------------------------------------------------------

def parse_version(text: Any) -> tuple[int, int, int] | None:
    """« v1.2.3 » ou « 1.2.3 » → (1, 2, 3) ; None pour tout autre texte
    (préversion « 1.0.0-beta », numéro abîmé…)."""
    if not isinstance(text, str):
        return None
    m = _VERSION_RE.match(text.strip())
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def is_newer(candidate: Any, current: str = __version__) -> bool:
    c, cur = parse_version(candidate), parse_version(current)
    return c is not None and cur is not None and c > cur


# --------------------------------------------------------------------------
# Adresses
# --------------------------------------------------------------------------

def repo_slug(app_info: dict[str, Any]) -> tuple[str, str] | None:
    """(propriétaire, dépôt) d'après github_url, seulement pour une adresse
    https://github.com/<propriétaire>/<dépôt>."""
    url = app_info.get("github_url")
    if not isinstance(url, str):
        return None
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or (parts.hostname or "").lower() != "github.com":
        return None
    if parts.username or parts.password or parts.port or parts.query or parts.fragment:
        return None
    bits = [b for b in parts.path.split("/") if b]
    if len(bits) != 2 or not _REPO_RE.match(bits[0]) or not _NAME_RE.match(bits[1]) or ".." in bits[1]:
        return None
    return bits[0], bits[1]


def api_url(app_info: dict[str, Any]) -> str | None:
    slug = repo_slug(app_info)
    if slug is None:
        return None
    return f"https://{API_HOST}/repos/{slug[0]}/{slug[1]}/releases/latest"


def releases_url(app_info: dict[str, Any]) -> str | None:
    slug = repo_slug(app_info)
    if slug is None:
        return None
    return f"https://github.com/{slug[0]}/{slug[1]}/releases/latest"


def _host_ok(url: str, hosts: tuple[str, ...]) -> bool:
    parts = urllib.parse.urlsplit(url)
    return (
        parts.scheme == "https"
        and (parts.hostname or "").lower() in hosts
        and not parts.username
        and not parts.password
        and parts.port in (None, 443)
    )


class _GuardedRedirect(urllib.request.HTTPRedirectHandler):
    """Redirections suivies seulement vers les hôtes permis, en https."""

    def __init__(self, hosts: tuple[str, ...]) -> None:
        super().__init__()
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if not _host_ok(newurl, self.hosts):
            raise urllib.error.HTTPError(req.full_url, code, "redirection refusée", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url: str, hosts: tuple[str, ...], accept: str):  # type: ignore[no-untyped-def]
    if not _host_ok(url, hosts):
        raise UpdateError("unreachable", "adresse refusée")
    opener = urllib.request.build_opener(_GuardedRedirect(hosts))
    req = urllib.request.Request(url, headers={"User-Agent": f"FSPassion/{__version__}", "Accept": accept})
    try:
        return opener.open(req, timeout=TIMEOUT)  # noqa: S310 - https et hôte vérifiés
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError("not_found", "404") from exc
        if exc.code in (403, 429):
            raise UpdateError("rate_limited", f"HTTP {exc.code}") from exc
        raise UpdateError("unreachable", f"HTTP {exc.code}") from exc
    except (OSError, ValueError) as exc:
        raise UpdateError("unreachable", str(exc)) from exc


def fetch(url: str, hosts: tuple[str, ...], max_bytes: int, accept: str = "*/*") -> bytes:
    with _open(url, hosts, accept) as r:
        try:
            data = r.read(max_bytes + 1)
        except OSError as exc:
            raise UpdateError("unreachable", str(exc)) from exc
    if len(data) > max_bytes:
        raise UpdateError("invalid", "trop volumineux")
    return data


def download(
    url: str, dest: Path, max_bytes: int, expected_sha: str,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Télécharge `url` dans `dest` en vérifiant la taille et l'empreinte.
    Le fichier n'apparaît sous son nom qu'une fois vérifié."""
    tmp = dest.with_name(dest.name + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    done = 0
    try:
        with _open(url, DOWNLOAD_HOSTS, "application/octet-stream") as r, tmp.open("wb") as fh:
            total = int(r.headers.get("Content-Length") or 0)
            if total > max_bytes:
                raise UpdateError("invalid", "trop volumineux")
            while True:
                try:
                    chunk = r.read(256 * 1024)
                except OSError as exc:
                    raise UpdateError("unreachable", str(exc)) from exc
                if not chunk:
                    break
                done += len(chunk)
                if done > max_bytes:
                    raise UpdateError("invalid", "trop volumineux")
                h.update(chunk)
                fh.write(chunk)
                if progress:
                    progress(done, total)
        if h.hexdigest().lower() != expected_sha.lower():
            raise UpdateError("checksum", "empreinte différente")
        tmp.replace(dest)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    return dest


# --------------------------------------------------------------------------
# Publication
# --------------------------------------------------------------------------

def installer_name(version: str) -> str:
    return f"FSPassion-{version}-setup.exe"


def portable_name(version: str) -> str:
    return f"FSPassion-{version}-portable.zip"


def parse_release(raw: Any) -> dict[str, Any]:
    """Contrôle la réponse de GitHub (dernière publication). Lève
    UpdateError(« invalid ») si elle est inutilisable."""
    if not isinstance(raw, dict) or raw.get("draft") or raw.get("prerelease"):
        raise UpdateError("invalid", "publication inattendue")
    ver = parse_version(raw.get("tag_name"))
    if ver is None:
        raise UpdateError("invalid", "numéro illisible")
    version = f"{ver[0]}.{ver[1]}.{ver[2]}"
    assets: dict[str, dict[str, Any]] = {}
    for a in raw.get("assets") or []:
        if not isinstance(a, dict):
            continue
        name, url, size = a.get("name"), a.get("browser_download_url"), a.get("size")
        if isinstance(name, str) and isinstance(url, str) and _host_ok(url, DOWNLOAD_HOSTS):
            assets[name] = {"url": url, "size": size if isinstance(size, int) else 0}
    page = raw.get("html_url")
    if not isinstance(page, str) or not _host_ok(page, ("github.com",)):
        page = None
    body, when = raw.get("body"), raw.get("published_at")
    notes = body if isinstance(body, str) else ""
    published = when if isinstance(when, str) else ""
    return {
        "version": version,
        "page": page,
        "published": published[:10],
        "notes": notes[:NOTES_MAX],
        "installer": assets.get(installer_name(version)),
        "portable": assets.get(portable_name(version)),
        "sums": assets.get("SHA256SUMS.txt"),
    }


def parse_sums(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = _SUM_RE.match(line.strip())
        if m:
            out[m[2]] = m[1].lower()
    return out


def latest_release(app_info: dict[str, Any]) -> dict[str, Any]:
    url = api_url(app_info)
    if url is None:
        raise UpdateError("no_source")
    data = fetch(url, (API_HOST,), MAX_API, "application/vnd.github+json")
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("invalid", "réponse illisible") from exc
    return parse_release(raw)


# --------------------------------------------------------------------------
# Mode de l'application
# --------------------------------------------------------------------------

def install_kind() -> str:
    """« installed » (installeur), « portable » (zip) ou « source » (lancé
    depuis le code : la mise à jour passe par GitHub)."""
    if not config.is_frozen():
        return "source"
    return "portable" if config.is_portable() else "installed"


def updates_dir() -> Path:
    return config.local_dir() / "updates"


def clean_old_downloads() -> None:
    """Installeurs déjà utilisés (ou abandonnés) : supprimés au démarrage."""
    folder = updates_dir()
    if not folder.is_dir():
        return
    for f in folder.iterdir():
        try:
            if f.is_file():
                f.unlink()
        except OSError:
            pass


def launch_installer_after_exit(installer: Path, pid: int) -> None:
    """Lance l'installeur dès que le processus `pid` (FS Passion) est fermé.

    Un petit PowerShell caché attend la fin de FS Passion, puis démarre
    l'installeur en silencieux (barre de progression visible), sans
    redémarrage du PC, et lui demande de relancer FS Passion à la fin
    (/RELAUNCH=1, voir packaging\\installer.iss)."""
    if sys.platform != "win32":
        raise UpdateError("unsupported")
    path = str(installer).replace("'", "''")
    args = "'/SILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOCANCEL','/RELAUNCH=1'"
    script = (
        f"Wait-Process -Id {int(pid)} -Timeout 90 -ErrorAction SilentlyContinue; "
        f"Start-Process -FilePath '{path}' -ArgumentList {args}"
    )
    flags = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED, NEW_PROCESS_GROUP, NO_WINDOW
    subprocess.Popen(  # noqa: S603 - commande fixe, chemin de notre dossier
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-WindowStyle", "Hidden", "-Command", script],
        creationflags=flags, close_fds=True,
    )


# --------------------------------------------------------------------------
# Gestionnaire
# --------------------------------------------------------------------------

class Updater:
    """État des mises à jour, partagé entre le cœur et l'interface."""

    def __init__(
        self, app_info: dict[str, Any], enabled: Callable[[], bool],
        publish: Callable[..., None], downloads_dir: Callable[[], Path | None],
    ) -> None:
        self.app_info = app_info
        self.enabled = enabled
        self.publish = publish
        self.downloads_dir = downloads_dir
        self._lock = threading.Lock()
        self.checking = False
        self.last_check = 0.0
        self.error: str | None = None
        self.release: dict[str, Any] | None = None
        self.download_state = "idle"  # idle | downloading | ready | error
        self.download_error: str | None = None
        self.progress = 0.0
        self.file: Path | None = None
        self._timer: threading.Timer | None = None
        self.stopped = False

    # -- état ------------------------------------------------------------

    def available(self) -> bool:
        return bool(self.release and is_newer(self.release["version"]))

    def state(self) -> dict[str, Any]:
        rel = self.release if self.available() else None
        kind = install_kind()
        can = False
        if rel is not None and rel.get("sums"):
            can = bool(rel.get("installer")) if kind == "installed" else bool(rel.get("portable")) if kind == "portable" else False
        return {
            "enabled": bool(self.enabled()),
            "source_ok": api_url(self.app_info) is not None,
            "current": __version__,
            "kind": kind,
            "checking": self.checking,
            "last_check": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.last_check)) if self.last_check else None,
            "error": self.error,
            "available": rel is not None,
            "latest": None if rel is None else {
                "version": rel["version"],
                "published": rel["published"],
                "has_page": bool(rel.get("page")),
            },
            "up_to_date": self.release is not None and rel is None and self.error is None,
            "can_install": can,
            "download": {
                "state": self.download_state,
                "progress": round(self.progress, 3),
                "error": self.download_error,
            },
        }

    def _changed(self) -> None:
        self.publish("update", state=self.state())

    # -- recherche -------------------------------------------------------

    def check(self) -> dict[str, Any]:
        if not self.enabled():
            return self.state()
        if not self._lock.acquire(blocking=False):
            return self.state()
        try:
            self.checking = True
            self._changed()
            try:
                rel = latest_release(self.app_info)
                prev = self.release["version"] if self.release else None
                self.release = rel
                self.error = None
                if prev != rel["version"]:
                    self.download_state, self.download_error, self.progress, self.file = "idle", None, 0.0, None
                if is_newer(rel["version"]):
                    log.info("Mise à jour disponible : %s (version actuelle %s)", rel["version"], __version__)
                else:
                    log.info("FS Passion est à jour (%s ; publiée : %s)", __version__, rel["version"])
            except UpdateError as exc:
                self.error = exc.key
                log.info("Recherche des mises à jour : %s %s", exc.key, exc.detail)
            except Exception:  # noqa: BLE001 - jamais bloquant
                self.error = "unreachable"
                log.exception("Recherche des mises à jour en échec")
            self.last_check = time.time()
        finally:
            self.checking = False
            self._lock.release()
        self._changed()
        return self.state()

    def check_later(self, delay: float) -> None:
        """Recherche en arrière-plan après `delay` secondes, puis une fois
        par jour."""
        if self.stopped:
            return
        if self._timer is not None:
            self._timer.cancel()

        def run() -> None:
            try:
                if self.enabled() and not self.stopped:
                    self.check()
            finally:
                self.check_later(INTERVAL_S)

        self._timer = threading.Timer(delay, run)
        self._timer.daemon = True
        self._timer.start()

    def stop(self) -> None:
        self.stopped = True
        if self._timer is not None:
            self._timer.cancel()

    # -- téléchargement --------------------------------------------------

    def _target(self, rel: dict[str, Any], kind: str) -> tuple[dict[str, Any], Path, int]:
        if kind == "installed":
            asset = rel.get("installer")
            return asset or {}, updates_dir() / installer_name(rel["version"]), MAX_INSTALLER
        asset = rel.get("portable")
        folder = self.downloads_dir() or updates_dir()
        return asset or {}, folder / portable_name(rel["version"]), MAX_PORTABLE

    def download(self) -> Path:
        """Télécharge et vérifie le fichier de la nouvelle version (installeur
        ou version portable). Renvoie son chemin."""
        if not self.enabled():
            raise UpdateError("disabled")
        rel = self.release if self.available() else None
        kind = install_kind()
        if rel is None:
            raise UpdateError("none")
        if kind == "source":
            raise UpdateError("unsupported")
        asset, dest, limit = self._target(rel, kind)
        if not asset.get("url"):
            raise UpdateError("missing_file")
        if not rel.get("sums"):
            raise UpdateError("no_checksum")
        if self.download_state == "downloading":
            raise UpdateError("busy")
        self.download_state, self.download_error, self.progress = "downloading", None, 0.0
        self._changed()
        last = [0.0]

        def progress(done: int, total: int) -> None:
            total = total or int(asset.get("size") or 0)
            if total:
                self.progress = min(1.0, done / total)
                now = time.monotonic()
                if now - last[0] > 0.25:
                    last[0] = now
                    self._changed()

        try:
            sums = parse_sums(fetch(rel["sums"]["url"], DOWNLOAD_HOSTS, MAX_SUMS).decode("utf-8", "replace"))
            sha = sums.get(dest.name)
            if not sha:
                raise UpdateError("no_checksum")
            path = download(asset["url"], dest, limit, sha, progress)
            if kind == "installed" and not _is_exe(path):
                path.unlink(missing_ok=True)
                raise UpdateError("invalid", "pas un programme")
        except UpdateError as exc:
            self.download_state, self.download_error = "error", exc.key
            log.warning("Téléchargement de la mise à jour en échec : %s %s", exc.key, exc.detail)
            self._changed()
            raise
        except Exception as exc:
            self.download_state, self.download_error = "error", "unreachable"
            log.exception("Téléchargement de la mise à jour en échec")
            self._changed()
            raise UpdateError("unreachable") from exc
        self.file, self.download_state, self.progress = path, "ready", 1.0
        log.info("Mise à jour téléchargée et vérifiée : %s", path.name)
        self._changed()
        return path

    def release_page(self) -> str | None:
        rel = self.release
        page = rel.get("page") if rel else None
        return page or releases_url(self.app_info)


def _is_exe(path: Path) -> bool:
    with path.open("rb") as fh:
        return fh.read(2) == b"MZ"


def default_downloads_dir(settings_value: Any) -> Path | None:
    """Dossier des téléchargements de FS Passion (réglage), sinon celui de
    Windows."""
    if isinstance(settings_value, str) and settings_value.strip():
        p = Path(settings_value.strip())
        if p.is_dir():
            return p
    d = winapi.downloads_dir()
    return Path(d) if d else None
