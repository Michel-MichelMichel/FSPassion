"""Lancement du jeu et surveillance de son processus.

L'exécutable seul refuse de démarrer quand Steam est fermé. FS Passion lance
donc le jeu par sa plateforme :

| Steam                         | steam://rungameid/<appid> (lu dans le manifeste) |
| Epic Games                    | com.epicgames.launcher://apps/<AppName>?action=launch&silent=true |
| Microsoft Store / Xbox        | identifiant du package (shell:AppsFolder\\…)     |
| dépendant de Steam, hors Steam| démarrer Steam s'il est fermé, puis l'exécutable |
| GIANTS ou inconnu             | exécutable                                      |

Si FS Passion tourne en administrateur, le jeu et sa plateforme sont lancés
par l'Explorateur Windows, donc avec des droits normaux.

« Lancer le jeu » sans application de partie : le jeu démarre avec son réglage
actuel.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fspassion import detect, versions, winapi
from fspassion.events import EventBus

log = logging.getLogger(__name__)

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

POLL_SECONDS = 2.0

# Passer la vidéo d'intro : « -restart » dans ces versions, « -skipStartVideos » ailleurs.
RESTART_ARG_VERSIONS = frozenset({"FS2011", "FS2013", "FS15", "FS17", "FS19"})
STEAM_RUNGAMEID_RE = re.compile(r"^steam://rungameid/(\d+)$")

# Où passent les arguments de lancement, selon la façon dont le jeu est lancé :
# - « command » : FS Passion lance l'exécutable et ajoute les arguments ;
# - « steam » / « epic » : la plateforme refuse les arguments venus d'un autre
#   programme (Steam demande de confirmer à chaque lancement). L'utilisateur les
#   colle une fois dans les options de lancement de la plateforme ;
# - « unsupported » : Microsoft Store / Xbox, aucun champ prévu par Windows.
ARGS_MODES = ("command", "steam", "epic", "unsupported")


def launch_args(vid: str, opts: dict[str, Any] | None) -> list[str]:
    """Arguments de lancement cochés pour une version."""
    opts = opts or {}
    out: list[str] = []
    if opts.get("skip_start_videos"):
        out.append("-restart" if vid in RESTART_ARG_VERSIONS else "-skipStartVideos")
    if opts.get("cheats"):
        out.append("-cheats")
    return out


def args_text(args: list[str]) -> str:
    """Arguments tels qu'on les colle dans une plateforme : « -restart -cheats »."""
    return " ".join(args)


def route(method: str, info: dict[str, Any]) -> str:
    """Comment le jeu sera lancé : « exe » (exécutable) ou la plateforme."""
    plat = info.get("platform", "exe")
    uri = info.get("uri")
    if method == "exe" or plat in ("exe", "steam_dependent") or (plat == "xbox" and not uri):
        return "exe"
    if plat in ("steam", "epic", "xbox") and uri:
        return plat
    return "exe"


def args_mode(method: str, info: dict[str, Any]) -> str:
    """Où passent les arguments de lancement (ARGS_MODES)."""
    r = route(method, info)
    if r == "exe":
        return "command"
    if r == "xbox":
        return "unsupported"
    return r


def steam_uri_with_args(uri: str, args: list[str]) -> str | None:
    """steam://rungameid/<appid> → steam://run/<appid>//<args>/.

    N'est plus utilisé pour lancer le jeu : Steam demande alors à chaque
    lancement de confirmer les arguments. Gardé pour les tests et le diagnostic.
    """
    m = STEAM_RUNGAMEID_RE.match(uri)
    if m is None or not args:
        return None
    return f"steam://run/{m.group(1)}//{quote(' '.join(args))}/"


def _process_names() -> set[str]:
    if psutil is None:
        return set()
    names: set[str] = set()
    for p in psutil.process_iter(["name"]):
        try:
            n = p.info.get("name")
            if n:
                names.add(n.lower())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return names


def running_versions(names: set[str] | None = None) -> set[str]:
    """Versions du jeu dont un exécutable tourne."""
    names = _process_names() if names is None else names
    out = set()
    for v in versions.all_versions():
        if v.exe_names & names:
            out.add(v.id)
    return out


class GameMonitor:
    """Surveille les processus du jeu. Prévient l'interface aux changements."""

    def __init__(self, bus: EventBus, on_exit: Callable[[str], None]) -> None:
        self.bus = bus
        self.on_exit = on_exit
        self.running: set[str] = set()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="game-monitor", daemon=True)

    def start(self) -> None:
        try:
            self.running = running_versions()
        except Exception as exc:  # noqa: BLE001
            log.warning("Surveillance du jeu impossible : %s", exc)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def is_running(self, vid: str) -> bool:
        return vid in self.running

    def _loop(self) -> None:
        while not self._stop.wait(POLL_SECONDS):
            try:
                now = running_versions()
            except Exception as exc:  # noqa: BLE001
                log.debug("Surveillance : %s", exc)
                continue
            if now != self.running:
                started = now - self.running
                stopped = self.running - now
                self.running = now
                for vid in started:
                    log.info("%s est en cours d'exécution", vid)
                for vid in stopped:
                    log.info("%s s'est fermé", vid)
                self.bus.publish("game", running=sorted(now))
                for vid in stopped:
                    try:
                        self.on_exit(vid)
                    except Exception:  # noqa: BLE001
                        log.exception("Traitement après fermeture du jeu en échec")


def _steam_running() -> bool:
    return "steam.exe" in _process_names()


def _start(target: str, cwd: str | None = None, args: list[str] | None = None) -> bool:
    """Lance une cible : par l'Explorateur si FS Passion est administrateur.

    Les arguments ne peuvent pas passer par l'Explorateur : en mode administrateur
    ils sont donc ignorés (signalé dans le résultat).
    """
    if winapi.is_admin():
        if args:
            log.warning("Arguments de lancement ignorés : FS Passion est administrateur")
        return winapi.start_via_explorer(target)
    return winapi.startfile(target, cwd, args)


def launch(vid: str, cfg: dict[str, Any], info: dict[str, Any] | None = None) -> dict[str, Any]:
    """Lance le jeu. Renvoie {ok, key, params, platform, args_mode}.

    Arguments de lancement : ajoutés à la commande seulement quand FS
    Passion lance l'exécutable. Par Steam ou Epic, le jeu est lancé sans
    arguments : ils sont à indiquer une fois dans la plateforme (Paramètres →
    Jeu et chemins → Arguments de lancement donne le texte à copier).
    """
    v = versions.require(vid)
    exe = cfg.get("game_exe")
    if not exe or not Path(exe).is_file():
        return {"ok": False, "key": "launch.no_exe", "params": {"game": v.name}}
    method = cfg.get("launch_method") or "auto"
    args = launch_args(vid, cfg.get("launch_args"))
    if info is None:
        info = {"platform": "exe", "uri": None}
        if method != "exe":
            try:
                info = detect.platform_of(exe)
            except Exception as exc:  # noqa: BLE001
                log.warning("Plateforme inconnue : %s", exc)
    plat = info.get("platform", "exe")
    uri = info.get("uri")
    how = route(method, info)
    mode = args_mode(method, info)
    log.info("Lancement de %s : méthode=%s plateforme=%s arguments=%s (%s)", vid, method, plat, args_text(args) or "-", mode)

    def result(ok: bool, platform: str) -> dict[str, Any]:
        return {"ok": ok, "key": "launch.started" if ok else "launch.failed",
                "params": {"game": v.name}, "platform": platform, "args_mode": mode}

    if how in ("steam", "epic", "xbox") and uri:
        # La plateforme démarre le jeu avec ses propres options de lancement.
        ok = _start(uri)
        if not ok and method == "auto":
            ok = _start(exe, str(Path(exe).parent), args)
        return result(ok, plat)

    if plat == "steam_dependent" and method != "exe":
        def worker() -> None:
            try:
                if not _steam_running():
                    steam = detect.steam_exe()
                    if steam is not None:
                        _start(str(steam), str(steam.parent))
                        for _ in range(60):
                            time.sleep(1)
                            if _steam_running():
                                break
                        time.sleep(5)  # laisser Steam se connecter
                _start(exe, str(Path(exe).parent), args)
            except Exception:  # noqa: BLE001
                # Le lancement a déjà été annoncé : l'erreur ne doit pas disparaître en silence.
                log.exception("Lancement du jeu via Steam interrompu")

        threading.Thread(target=worker, name="launch", daemon=True).start()
        return result(True, plat)

    ok = _start(exe, str(Path(exe).parent), args)
    return result(ok, "exe" if method == "exe" else plat)
