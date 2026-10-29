"""Démarrage de FS Passion : instance unique, serveur local, fenêtre.

Utilisation :
    python -m fspassion            application normale (fenêtre)
    python -m fspassion --dev      mode développement : port fixe 8765,
                                   ouverture du navigateur en plus de la fenêtre
Options :
    --no-window     sans fenêtre (navigateur seulement)
    --no-browser    sans ouvrir le navigateur (mode développement)
    --window-mode   technique de la fenêtre : native | script | thin
    --debug         outils de développement dans la fenêtre
    --uninstall     ouvre directement « Ne plus utiliser FS Passion » (lancé par
                    le désinstalleur Windows)
    --uninstall-quiet  désinstallation sans fenêtre (lancée par le désinstalleur
                    Windows, qui pose lui-même les questions) : réglage du jeu
                    rétabli, dossiers de parties retirés ; avec
                    --remove parties,caches,settings,logs,langs : suppressions
                    en plus. Code de sortie : 0 fait, 1 erreur, 3 jeu ouvert.
    --uninstall-check  code de sortie 3 si un jeu configuré est ouvert, sinon 0
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
import urllib.request
import webbrowser
from typing import Any

from fspassion import __version__, config, fsutil, logs, stopuse, winapi
from fspassion.core import Core
from fspassion.server import Server
from fspassion.tray import Tray
from fspassion.window_ops import native, rect_visible

log = logging.getLogger("fspassion")

MUTEX_NAME = "Local\\FSPassion.Instance"
# Taille minimale de la fenêtre (px logiques).
# L'interface ne réduit son échelle qu'en dessous de 1140 px de large (ui/js/scale.js).
MIN_WINDOW = (960, 720)
_mutex_handle: Any = None


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="fspassion", description="FS Passion")
    p.add_argument("--dev", action="store_true")
    p.add_argument("--no-window", action="store_true")
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--window-mode", choices=["native", "script", "thin"])
    p.add_argument("--port", type=int)
    p.add_argument("--debug", action="store_true")
    p.add_argument("--uninstall", action="store_true")
    p.add_argument("--uninstall-quiet", action="store_true")
    p.add_argument("--uninstall-check", action="store_true")
    p.add_argument("--remove", default="")
    return p.parse_args(argv)


# --------------------------------------------------------------------------
# Instance unique : relancer FS Passion ramène la fenêtre existante.
# --------------------------------------------------------------------------

def acquire_single_instance() -> bool:
    global _mutex_handle
    if sys.platform != "win32":
        return True
    import ctypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = ctypes.c_void_p
    handle = k32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        # Ne pas garder ce handle : il ferait exister le verrou même après la
        # fin de l'autre instance (nouvel essai dans handle_stuck_instance).
        if handle:
            k32.CloseHandle(ctypes.c_void_p(handle))
        return False
    _mutex_handle = handle
    return True


def notify_existing_instance() -> bool:
    if sys.platform == "win32":
        # Autorise l'instance déjà ouverte à passer au premier plan.
        try:
            import ctypes

            ctypes.windll.user32.AllowSetForegroundWindow(-1)
        except Exception:  # noqa: BLE001
            pass
    info = fsutil.read_json(config.instance_file(), None)
    if not isinstance(info, dict) or not info.get("port") or not info.get("token"):
        return False
    url = f"http://127.0.0.1:{info['port']}/api/app/focus"
    req = urllib.request.Request(
        url, data=b"{}", method="POST",
        headers={"Content-Type": "application/json", "X-FSP-Token": info["token"]},
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as r:  # noqa: S310 - adresse locale
            return r.status == 200
    except OSError:
        return False


def write_instance_file(server: Server) -> None:
    try:
        fsutil.atomic_write_json(
            config.instance_file(),
            {"port": server.port, "token": server.token, "pid": os.getpid()},
        )
    except OSError as exc:
        log.warning("Fichier d'instance non écrit : %s", exc)


def remove_instance_file() -> None:
    try:
        config.instance_file().unlink()
    except OSError:
        pass


# --------------------------------------------------------------------------
# Fermeture : le processus doit vraiment se terminer.
# --------------------------------------------------------------------------
# 0.9.9 : après la fermeture de la fenêtre, un processus FS Passion pouvait
# rester en arrière-plan, sans fenêtre ni icône : un fil d'exécution de la
# fenêtre (WebView2 / .NET) le gardait en vie, et il tenait le verrou
# d'instance unique. Les lancements suivants « ramenaient au premier plan »
# une instance qui n'existait plus : rien ne s'ouvrait.

EXIT_WATCHDOG_S = 20.0   # au-delà, la fermeture est forcée
STUCK_WAIT_S = 8.0       # une instance qui se ferme a ce délai pour finir


def end_process(code: int = 0) -> None:
    """Termine le processus sans attendre les fils d'exécution restants
    (application fabriquée seulement : les tests appellent main())."""
    if config.is_frozen():
        os._exit(code)


def start_exit_watchdog(delay: float = EXIT_WATCHDOG_S) -> None:
    """Si la fermeture se bloque (fenêtre, .NET…), le processus est arrêté."""
    def force() -> None:
        try:
            log.warning("Fermeture bloquée depuis %.0f s : arrêt forcé", delay)
            logging.shutdown()
        finally:
            end_process()

    t = threading.Timer(delay, force)
    t.daemon = True
    t.start()


def _other_instance_pids() -> list[int]:
    """Autres processus FSPassion.exe de cet utilisateur (application fabriquée)."""
    if sys.platform != "win32" or not config.is_frozen():
        return []
    import csv
    import io
    import subprocess

    exe = os.path.basename(sys.executable)
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10, creationflags=0x08000000,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    pids = []
    for row in csv.reader(io.StringIO(out)):
        if len(row) > 1 and row[1].isdigit() and int(row[1]) != os.getpid():
            pids.append(int(row[1]))
    return pids


def _ask_close_stuck() -> bool:
    import ctypes

    fr = (winapi.ui_language() or "").lower().startswith("fr")
    title = "FS Passion"
    text = ("FS Passion est déjà ouvert, mais il ne répond pas : il est resté en arrière-plan "
            "sans fenêtre.\n\nLe fermer et redémarrer FS Passion ?" if fr else
            "FS Passion is already running, but it does not respond: it stayed in the background "
            "without a window.\n\nClose it and restart FS Passion?")
    MB_YESNO, MB_ICONWARNING, IDYES = 0x4, 0x30, 6
    return ctypes.windll.user32.MessageBoxW(None, text, title, MB_YESNO | MB_ICONWARNING) == IDYES


def handle_stuck_instance() -> bool:
    """L'instance déjà ouverte ne répond pas. On lui laisse le temps de finir
    de se fermer ; sinon, avec l'accord de l'utilisateur, on l'arrête et on
    démarre normalement. Renvoie True si ce lancement doit continuer."""
    deadline = time.monotonic() + STUCK_WAIT_S
    while time.monotonic() < deadline:
        time.sleep(0.5)
        if acquire_single_instance():
            log.info("L'instance précédente s'est fermée : démarrage")
            return True
        if notify_existing_instance():
            return False
    pids = _other_instance_pids()
    if not pids:
        log.warning("Instance précédente sans réponse, introuvable")
        return False
    log.warning("Instance précédente sans réponse (processus %s)", ", ".join(map(str, pids)))
    if not _ask_close_stuck():
        return False
    import subprocess

    for pid in pids:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=10,
                           creationflags=0x08000000)
            log.info("Instance sans réponse arrêtée (processus %d)", pid)
        except (OSError, subprocess.SubprocessError) as exc:
            log.warning("Arrêt de l'instance %d impossible : %s", pid, exc)
    for _ in range(20):
        if acquire_single_instance():
            return True
        time.sleep(0.25)
    return False


# --------------------------------------------------------------------------
# Fenêtre
# --------------------------------------------------------------------------

def theme_background(core: Core) -> str:
    """Couleur de fond du thème choisi, pour éviter un éclair blanc à l'ouverture."""
    data = fsutil.read_json(config.ui_dir() / "themes.json", {}) or {}
    wanted = core.settings.get("theme") or config.DEFAULT_THEME
    for t in data.get("themes", []):
        if t.get("id") == wanted and isinstance(t.get("dark"), str):
            return t["dark"]
    return "#EBDBB2"


def run_window(core: Core, server: Server, args: argparse.Namespace) -> bool:
    """Ouvre la fenêtre de l'application. Renvoie False si pywebview est absent."""
    try:
        import webview  # type: ignore[import-not-found]
    except ImportError as exc:
        log.error("pywebview indisponible (%s) : interface dans le navigateur seulement", exc)
        return False

    mode = args.window_mode or core.settings.get("window_mode") or "native"
    st = core.settings.get("window") or {}
    width, height = st.get("width"), st.get("height")
    x, y = st.get("x"), st.get("y")
    try:
        screen = webview.screens[0]
        sw, sh = int(screen.width), int(screen.height)
    except Exception:  # noqa: BLE001
        sw, sh = 1920, 1080
    if not width or not height:
        width = max(1280, min(int(sw * 0.86), 2400))
        height = max(720, min(int(sh * 0.86), 1350))
        x = y = None
    if x is not None and y is not None and not rect_visible(int(x), int(y), int(width), int(height)):
        x = y = None

    window = webview.create_window(
        "FS Passion",
        server.url("window"),
        width=int(width),
        height=int(height),
        x=x,
        y=y,
        min_size=MIN_WINDOW,
        frameless=True,
        easy_drag=False,
        shadow=True,
        focus=True,
        background_color=theme_background(core),
        text_select=False,
        zoomable=False,
    )

    def on_shown() -> None:
        native.attach(window, mode)
        if st.get("maximized"):
            native.maximize()

    quitting = threading.Event()

    def save_window() -> None:
        try:
            state = native.saved_state()
            if state:
                core.settings.set("window", state)
        except Exception:  # noqa: BLE001
            log.exception("Mémorisation de la fenêtre impossible")

    # Zone de notification : la croix cache la fenêtre, « Quitter »
    # ferme l'application.
    def quit_app() -> None:
        quitting.set()
        try:
            window.destroy()
        except Exception:  # noqa: BLE001
            log.exception("Fermeture de la fenêtre impossible")

    tray = Tray(core.tray_texts, native.focus, quit_app)

    def to_tray() -> bool:
        """Cache la fenêtre si l'icône existe et si le réglage le demande."""
        # Désinstallation (--uninstall) : la croix ferme vraiment, le
        # désinstalleur attend la fin de FS Passion.
        if quitting.is_set() or core.uninstall_mode or not tray.active or not core.settings.get("close_to_tray"):
            return False
        save_window()
        if not native.hide():
            return False
        native.sleep_later()  # Dormance de l'interface cachée
        if not core.settings.get("tray_hint_shown"):
            core.settings.set("tray_hint_shown", True)
            tray.notify(core.tray_texts().get("hint") or "FS Passion")
        return True

    def close_button() -> None:
        if not to_tray():
            quit_app()

    def on_closing() -> bool:
        # Alt+F4, barre des tâches… : même règle que la croix. Renvoyer False
        # annule la fermeture (pywebview).
        if to_tray():
            return False
        save_window()
        return True

    window.events.shown += on_shown
    window.events.closing += on_closing

    server.quit_callback = quit_app
    server.focus_callback = native.focus
    server.close_callback = close_button

    if tray.start():
        core.tray = tray
        core.hide_to_tray = to_tray
        log.info("Icône de la zone de notification prête")

    webview.start(
        gui="edgechromium",
        debug=bool(args.debug),
        private_mode=True,
        storage_path=str(config.webview_storage_dir()),
    )
    tray.stop()
    core.tray = None
    core.hide_to_tray = None
    return True


# --------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------

PORT_WAIT_S = 15.0  # Attente du port libéré par l'instance précédente


def open_server(core: Core, port: int, wait_s: float = PORT_WAIT_S) -> Server:
    """Ouvre le serveur local. Un port fixe (développement) peut encore être tenu
    quelques instants par l'instance qui vient de se fermer, par exemple lors
    d'une relance en administrateur : on réessaie avant d'abandonner."""
    deadline = time.monotonic() + wait_s
    while True:
        try:
            return Server(core, port)
        except OSError as exc:
            if port == 0 or time.monotonic() >= deadline:
                raise
            log.info("Port %s encore occupé (%s) : nouvel essai", port, exc)
            time.sleep(0.5)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logs.setup(dev=args.dev)
    log.info("FS Passion %s — démarrage%s", __version__, " (développement)" if args.dev else "")
    # Droits et mode au démarrage, dans le journal (avertissement de
    # Windows ou de PowerToys sur un programme lancé en administrateur).
    try:
        log.info("Mode %s ; administrateur : %s ; réglage « Exécuter en tant qu'administrateur » : %s ; %s",
                 "portable" if config.is_portable() else ("installé" if config.is_frozen() else "développement"),
                 "oui" if winapi.is_admin() else "non", "oui" if winapi.run_as_admin_flag() else "non",
                 config.exe_dir())
    except Exception:  # noqa: BLE001
        pass

    if args.uninstall_check:
        # Désinstalleur : un jeu ouvert ? (lecture seule, sans verrou d'instance)
        running = Core(dev=False).uninstall_running()
        logging.shutdown()
        raise SystemExit(3 if running else 0)

    if not acquire_single_instance():
        log.info("Une instance tourne déjà : elle est ramenée au premier plan")
        if notify_existing_instance() or not handle_stuck_instance():
            return

    core = Core(dev=args.dev)
    if args.uninstall_quiet:
        # Désinstalleur Windows : pas de fenêtre. Les choix (suppressions en
        # plus) ont été faits dans la fenêtre du désinstalleur.
        core.uninstall_mode = True
        code = 1
        try:
            code = core.uninstall_headless([o.strip() for o in args.remove.split(",") if o.strip()])
        except Exception:  # noqa: BLE001
            log.exception("Désinstallation impossible")
        finally:
            core.shutdown()
            logging.shutdown()
            if core.stopped:
                stopuse.finish_at_exit(core.exit_cleanup)
        raise SystemExit(code)
    core.uninstall_mode = bool(args.uninstall)
    core.startup()

    info = core.app_info
    port = args.port if args.port is not None else (int(info.get("dev_port", 8765)) if args.dev else 0)
    try:
        server = open_server(core, port)
    except OSError as exc:
        log.error("Port %s indisponible : %s", port, exc)
        if args.dev:
            print(f"\nLe port {port} est déjà utilisé : FS Passion tourne peut-être déjà.\n")
        raise SystemExit(1) from exc
    server.start()
    write_instance_file(server)

    stop = threading.Event()
    if args.dev:
        # Le jeton de session n'est jamais affiché. Sans ouverture automatique,
        # l'adresse affichée est un billet à usage unique.
        print("\n  FS Passion " + __version__ + " — mode développement")
        if args.no_browser:
            print("  Interface dans le navigateur (adresse à usage unique) : " + server.url("browser"))
        else:
            print("  Interface ouverte dans le navigateur.")
        print("  Atelier de thèmes : ajouter &atelier=1 à l'adresse de l'interface.\n")
        if not args.no_browser:
            threading.Timer(0.6, lambda: webbrowser.open(server.url("browser"))).start()

    try:
        opened = False
        if not args.no_window:
            opened = run_window(core, server, args)
        if not opened:
            if not args.dev:
                webbrowser.open(server.url("browser"))
            server.quit_callback = stop.set
            try:
                while not stop.wait(0.5):
                    pass
            except KeyboardInterrupt:
                pass
    finally:
        log.info("Fermeture de FS Passion")
        start_exit_watchdog()
        if core.uninstall_mode and not core.stopped:
            # Désinstalleur fermé sans confirmer : l'override est quand même rétabli.
            try:
                core.uninstall_minimal()
            except Exception:  # noqa: BLE001
                log.exception("Désinstallation : rétablissement de l'override impossible")
        core.shutdown()
        remove_instance_file()
        try:
            server.stop()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.1)
        if core.restart_elevated:
            # « Toujours lancer FS Passion en administrateur » : la
            # nouvelle instance démarre une fois celle-ci entièrement fermée.
            winapi.release_single_instance(_mutex_handle)
            log.info("Relance de FS Passion en administrateur")
            launcher = None if config.is_frozen() else config.project_root() / "lancer_dev.bat"
            if not winapi.relaunch_elevated(launcher):
                log.warning("Relance en administrateur refusée ou annulée")
        log.info("Fermeture terminée")
        logging.shutdown()
        if core.exit_cleanup:
            # « Ne plus utiliser FS Passion » : journaux et données de la
            # fenêtre, supprimés une fois libérés.
            stopuse.finish_at_exit(core.exit_cleanup)
        elif core.stopped:
            stopuse.finish_at_exit([])
        if core.run_uninstaller is not None:
            # « Ne plus utiliser » déjà fait : le désinstalleur ne repose pas ses questions.
            winapi.startfile(str(core.run_uninstaller), args=["/FSPDONE=1"])
        end_process()
