"""Le cœur de l'application : état partagé et actions appelées par l'interface.

« Appliquer » écrit sur le disque de l'utilisateur, en dehors de settings.json,
du cache et de parties.json :
- les dossiers de parties (FSPassion\\<version>\\Parties\\), qui ne
  contiennent que des liens vers les mods (apply.py) ;
- la seule ligne modsDirectoryOverride de gameSettings.xml, après sauvegarde
  (gamesettings.py).
Les mods eux-mêmes ne sont jamais modifiés, et ne sont supprimés que sur
demande explicite de l'utilisateur.
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any

from fspassion import (
    __version__,
    anomalies,
    apply,
    backup,
    config,
    demo,
    detect,
    dialogs,
    dlc,
    dlcremote,
    downloads,
    fsutil,
    gamepaths,
    gamesettings,
    i18n,
    launcher,
    links,
    logs,
    moddesc,
    modops,
    reconcile,
    stopuse,
    storage,
    updates,
    versions,
    winapi,
)
from fspassion.events import EventBus
from fspassion.events import bus as default_bus
from fspassion.fsutil import same_path
from fspassion.library import LibraryManager
from fspassion.links import LinkError
from fspassion.parties import EMPTY, FULL, PartiesStore, PartyError, resolve_dependencies
from fspassion.parties import validate as parties_validate
from fspassion.window_ops import native

log = logging.getLogger(__name__)

# Réglages de thème, remis à zéro par « Réinitialiser les thèmes ».
THEME_KEYS = ("theme", "theme_loop", "light_effects", "reduce_motion")

# Réglages globaux modifiables par l'interface, et leur type attendu.
SETTABLE: dict[str, type | tuple[type, ...]] = {
    "language": str,
    "theme": str,
    "theme_loop": bool,
    "light_effects": bool,
    "reduce_motion": (bool, type(None)),
    "downloads_dir": str,
    "scan_downloads_at_start": bool,
    "internet_access": bool,
    # Recherche des mises à jour de FS Passion sur GitHub (indépendante du
    # catalogue des DLC).
    "update_check": bool,
    "show_notice_at_start": bool,
    "welcome_done": bool,
    # Tour guidé : l'ampoule a été mise en évidence au premier lancement.
    "tour_hint_shown": bool,
    "minimize_on_launch": bool,
    "close_to_tray": bool,
    "focus_after_game": bool,
    "window_mode": str,
}

PATH_FIELDS = ("game_exe", "user_dir", "mods_dir")
LAUNCH_METHODS = ("auto", "platform", "exe")


class AppError(Exception):
    """Erreur prévue, avec une clé de langue (jamais de texte en dur)."""

    def __init__(self, key: str, status: int = 400, **params: Any) -> None:
        super().__init__(key)
        self.key = key
        self.status = status
        self.params = params


class Core:
    def __init__(self, dev: bool = False, bus: EventBus | None = None) -> None:
        self.dev = dev
        self.bus = bus or default_bus
        self.settings = config.Settings()
        self.langs = i18n.Languages()
        self.libs = LibraryManager(self.bus, self.paths, on_ready=self._library_ready)
        self.monitor = launcher.GameMonitor(self.bus, self._on_game_exit)
        self.app_info = config.load_app_info()
        self.detecting = False
        self.restart_elevated = False  # relance en administrateur demandée
        self._detect_lock = threading.Lock()
        self._parties: dict[str, PartiesStore] = {}
        self._parties_lock = threading.Lock()
        self._parties_notices: dict[str, dict[str, Any]] = {}
        # Une seule opération sur les dossiers de parties à la fois, par version.
        self._apply_locks: dict[str, threading.Lock] = {}
        # Zone de notification : posée par app.py quand l'icône existe.
        self.tray: Any = None
        # Plateforme de chaque exécutable (Steam, Epic…), lue une fois.
        self._platforms: dict[str, dict[str, Any]] = {}
        # Réconciliation au démarrage : une fois par version et par session,
        # quand sa bibliothèque est lue pour la première fois.
        self._reconciled: set[str] = set()
        # Import de la configuration : fichier lu et contrôlé, en attente
        # de confirmation (jeton, contenu).
        self._import_pending: dict[str, Any] | None = None
        # Catalogue des DLC distant : une mise à jour à la fois.
        self._remote_lock = threading.Lock()
        # « Ne plus utiliser FS Passion » : fait, mode désinstallation
        # (--uninstall), suppressions à faire à la fermeture, désinstalleur.
        self.stopped = False
        self.uninstall_mode = False
        # Mesures de performance : démarrage du cœur, et mesures
        # envoyées par l'interface (affichage prêt, fluidité du défilement).
        self.started_at = time.time()
        self.ui_perf: dict[str, Any] = {}
        self.exit_cleanup: list[Path] = []
        self.run_uninstaller: Path | None = None
        # Mises à jour de FS Passion (Releases GitHub).
        self.updater = updates.Updater(
            self.app_info,
            enabled=lambda: bool(self.settings.get("update_check")) and not self.stopped,
            publish=self.bus.publish,
            downloads_dir=lambda: updates.default_downloads_dir(self.settings.get("downloads_dir")),
        )

    # ------------------------------------------------------------------
    # Démarrage
    # ------------------------------------------------------------------

    def startup(self) -> None:
        if not config.is_frozen() and winapi.run_as_admin_flag():
            # Réglage posé par erreur sur l'interpréteur Python de
            # développement : il empêche lancer_dev.bat de démarrer. Retiré.
            if winapi.set_run_as_admin_flag(False):
                log.warning("Réglage « administrateur » retiré de l'interpréteur de développement")
        s = self.settings
        if not s.get("language"):
            # Premier lancement : langue de Windows (repli : anglais).
            s.set("language", self.langs.windows_language(), save=False)
        if not s.get("downloads_dir"):
            dl = winapi.downloads_dir()
            if dl:
                s.set("downloads_dir", str(dl), save=False)
        if not versions.get(s.get("active_version") or ""):
            s.set("active_version", versions.DEFAULT_VERSION, save=False)
        if s.get("window_mode") not in ("native", "script", "thin"):
            s.set("window_mode", "native", save=False)
        s.save()
        try:
            i18n.ensure_user_lang_folder()
            self.langs.reload()
        except OSError as exc:
            log.warning("Dossier des langues personnelles indisponible : %s", exc)

        self.monitor.start()
        self._ensure_backups()
        updates.clean_old_downloads()
        if not self.uninstall_mode and updates.AUTO_CHECK:
            # Recherche au lancement, quelques secondes après l'affichage.
            self.updater.check_later(updates.STARTUP_DELAY_S)

        if not s.get("first_detection_done"):
            # Tout premier lancement : la détection s'exécute en silence.
            threading.Thread(target=self._first_detection, name="detect", daemon=True).start()
        else:
            self.libs.get(self.active_version()).request_scan()
            self.refresh_remote_data()

    def _first_detection(self) -> None:
        try:
            self.detect(None, silent=True)
        finally:
            self.settings.set("first_detection_done", True)
            self.libs.get(self.active_version()).request_scan()
            self.refresh_remote_data()

    def _ensure_backups(self) -> None:
        """gameSettings.xml.original.bak, dès la première détection du fichier."""
        for v in versions.all_versions():
            vp = self.paths(v.id)
            gs = vp.gamesettings
            if gs is not None and gs.is_file():
                if gamesettings.ensure_original_backup(gs):
                    self.bus.publish("backup", version=v.id)

    def shutdown(self) -> None:
        self.updater.stop()
        self.monitor.stop()

    # ------------------------------------------------------------------
    # Chemins et état des versions
    # ------------------------------------------------------------------

    def active_version(self) -> str:
        vid = self.settings.get("active_version") or versions.DEFAULT_VERSION
        return vid if versions.get(vid) else versions.DEFAULT_VERSION

    def paths(self, vid: str) -> gamepaths.VersionPaths:
        return gamepaths.from_cfg(versions.require(vid), self.settings.version(vid))

    def applied_state(self, vid: str) -> dict[str, Any]:
        """Partie appliquée d'après la ligne d'override (lecture seule)."""
        vp = self.paths(vid)
        v = vp.version
        if not v.has_override:
            return {"kind": "unsupported"}
        gs = vp.gamesettings
        if gs is None or not gs.is_file():
            return {"kind": "unknown"}
        ov = gamesettings.read_override(gs)
        if ov is None or not ov.found:
            return {"kind": "unknown"}
        if ov.active:
            effective = gamesettings.override_dir_to_path(ov.directory)
        else:
            effective = str(vp.user_dir / "mods") if vp.user_dir else None
        kind = "other"
        if effective and vp.mods_dir and same_path(effective, vp.mods_dir):
            kind = "full"
        elif effective and vp.fsp_dir:
            parties = vp.fsp_dir / "Parties"
            if same_path(effective, parties / "_vide"):
                kind = "empty"
            elif same_path(effective, parties / "_pleine"):
                kind = "full"
            elif same_path(Path(effective).parent, parties):
                kind = "party"
        return {"kind": kind, "directory": effective, "override": ov.to_json()}

    def version_state(self, vid: str, with_override: bool = True) -> dict[str, Any]:
        v = versions.require(vid)
        cfg = self.settings.version(vid)
        vp = gamepaths.from_cfg(v, cfg)
        lib = self.libs.get(vid)
        out = v.to_json()
        out.update({
            "cfg": {
                "game_exe": cfg.get("game_exe") or "",
                "user_dir": cfg.get("user_dir") or "",
                "mods_dir": str(vp.mods_dir) if v.mods_dir_fixed and vp.mods_dir else (cfg.get("mods_dir") or ""),
                "extra_mods_dirs": cfg.get("extra_mods_dirs") or [],
                "launch_method": cfg.get("launch_method") or "auto",
                "launch_args": {
                    "skip_start_videos": bool((cfg.get("launch_args") or {}).get("skip_start_videos")),
                    "cheats": bool((cfg.get("launch_args") or {}).get("cheats")),
                },
            },
            "checks": gamepaths.check_all(vp, cfg) if v.available else {},
            "derived": vp.derived_json() if v.available else [],
            "installed": gamepaths.is_installed(vp) if v.available else False,
            "ready": gamepaths.is_ready(vp) if v.available else False,
            "running": self.monitor.is_running(vid),
            "library": {"status": lib.status, "count": len(lib.entries)},
        })
        if v.available:
            out["launch"] = self.launch_info(vid, cfg, vp)
        if v.available and v.has_override and not v.mods_dir_fixed:
            # Stockage sur plusieurs disques : état des chemins n° 2 et 3.
            out["storage"] = {
                "max_extra": storage.MAX_EXTRA,
                "extra": [storage.check_extra(vp, i) for i in range(len(vp.extra_mods_dirs))],
                "needs_symlinks": storage.needs_symlinks(vp),
            }
        if with_override and v.available:
            out["applied"] = self.applied_state(vid)
        return out

    def state(self) -> dict[str, Any]:
        s = self.settings.snapshot()
        return {
            "app": {
                "version": __version__,
                "dev": self.dev,
                "frozen": config.is_frozen(),
                "portable": config.is_portable(),
                "admin": winapi.is_admin(),
                "info": self.app_info,
                "window": native.available,
                "window_mode": native.mode if native.available else s.get("window_mode"),
                "tray": bool(self.tray is not None and self.tray.active),
                "uninstall_mode": self.uninstall_mode,
                "stopped": self.stopped,
            },
            "settings": {k: s.get(k) for k in SETTABLE},
            "active_version": self.active_version(),
            "languages": self.langs.available(),
            "lang_rejected": self.langs.rejected,
            "versions": [self.version_state(v.id) for v in versions.all_versions()],
            "rights": self.rights_state(),
            "running": sorted(self.monitor.running),
            "detecting": self.detecting,
            "anomalies_cfg": s.get("anomalies"),
            "demo": self.demo_state(),
            "dlc_catalog": self.dlc_catalog_state(),
            "update": self.updater.state(),
        }

    # ------------------------------------------------------------------
    # Réglages
    # ------------------------------------------------------------------

    def reset_themes(self) -> dict[str, Any]:
        """Réinitialisation des thèmes : thème, boucle, effets et animations
        reviennent à leurs valeurs d'origine. En développement (hors exécutable),
        les définitions de l'atelier (ui\\themes.json) reviennent aussi à celles
        livrées avec l'application (data\\themes_default.json)."""
        defaults = config.default_settings()
        self.settings.update({k: defaults[k] for k in THEME_KEYS})
        restored = False
        if self.dev and not config.is_frozen():
            src = fsutil.read_json(config.package_data_dir() / "themes_default.json", None)
            if isinstance(src, dict) and isinstance(src.get("themes"), list):
                fsutil.atomic_write_json(config.ui_dir() / "themes.json", src)
                restored = True
        log.info("Thèmes réinitialisés (définitions restaurées : %s)", "oui" if restored else "non")
        return {"settings": {k: self.settings.get(k) for k in THEME_KEYS}, "themes_restored": restored}

    def set_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in patch.items():
            expected = SETTABLE.get(key)
            if expected is None or not isinstance(value, expected):
                raise AppError("error.bad_request")
            clean[key] = value
        if "language" in clean and not self.langs.has(clean["language"]):
            raise AppError("error.bad_request")
        if "window_mode" in clean and clean["window_mode"] not in ("native", "script", "thin"):
            raise AppError("error.bad_request")
        was_online = bool(self.settings.get("internet_access"))
        was_checking = bool(self.settings.get("update_check"))
        self.settings.update(clean)
        if "language" in clean and self.tray is not None:
            self.tray.refresh()
        if clean.get("internet_access") and not was_online:
            self.refresh_remote_data()
        if clean.get("update_check") and not was_checking and updates.AUTO_CHECK:
            self.updater.check_later(0.5)
        return {k: self.settings.get(k) for k in SETTABLE}

    def tray_texts(self) -> dict[str, str]:
        """Textes du menu de l'icône, dans la langue de l'interface."""
        strings = self.langs.strings(self.settings.get("language") or "en")
        tray = strings.get("tray") if isinstance(strings, dict) else None
        return tray if isinstance(tray, dict) else {}

    def set_active_version(self, vid: str) -> None:
        v = versions.get(vid)
        if v is None or not v.available:
            raise AppError("error.bad_request")
        self.settings.set("active_version", vid)
        lib = self.libs.get(vid)
        if lib.status in ("idle", "error"):
            lib.request_scan()
        else:
            lib.quick_check()

    def set_path(self, vid: str, field: str, value: str) -> dict[str, Any]:
        v = versions.get(vid)
        if v is None or not v.available or field not in PATH_FIELDS:
            raise AppError("error.bad_request")
        if field == "mods_dir" and v.mods_dir_fixed:
            raise AppError("error.bad_request")
        value = (value or "").strip().strip('"')
        old = self.settings.version(vid)
        self._platforms.clear()
        self.settings.update_version(vid, {field: value})
        if field == "user_dir":
            self._ensure_backups()
        if old.get(field) != value:
            self._reconciled.discard(vid)
            # Nouveau dossier de mods, de jeu (DLC) ou Mes documents : la
            # bibliothèque de cette version repart de zéro.
            if vid == self.active_version():
                self.libs.reset(vid)
            else:
                self.libs.drop(vid)
        return self.version_state(vid)

    # ------------------------------------------------------------------
    # Stockage sur plusieurs disques
    # ------------------------------------------------------------------

    def _needs_symlinks(self) -> bool:
        """Une version au moins a un stockage supplémentaire sur un autre disque."""
        for v in versions.all_versions():
            if v.available and v.has_override and self.settings.version(v.id).get("extra_mods_dirs"):
                if storage.needs_symlinks(self.paths(v.id)):
                    return True
        return False

    def rights_state(self, refresh: bool = False) -> dict[str, Any]:
        return storage.rights(self._needs_symlinks(), refresh)

    def set_storages(self, vid: str, dirs: Any) -> dict[str, Any]:
        """Chemins n° 2 et n° 3 de la version (liste de 0 à 2 chemins). Les
        mods de ces dossiers ne sont jamais déplacés : seule la liste change."""
        v = versions.get(vid)
        if v is None or not v.available or not v.has_override or v.mods_dir_fixed:
            raise AppError("error.bad_request")
        try:
            clean = storage.clean_extra(dirs)
        except ValueError as exc:
            raise AppError("error.bad_request") from exc
        old = list(self.settings.version(vid).get("extra_mods_dirs") or [])
        self.settings.update_version(vid, {"extra_mods_dirs": clean})
        if clean != old:
            log.info("Dossiers de stockage supplémentaires de %s : %s", vid, clean or "aucun")
            self._reconciled.discard(vid)
            with self._parties_lock:
                st = self._parties.get(vid)
                if st is not None:
                    st._extra = list(clean)
                    st.data["extra_mods_dirs"] = list(clean)
            if vid == self.active_version():
                self.libs.reset(vid)
            else:
                self.libs.drop(vid)
            self._changed(vid)
        out = self.version_state(vid)
        out["rights"] = self.rights_state()
        return out

    def rights_action(self, action: str) -> dict[str, Any]:
        """Droits pour les liens symboliques :
        - « check » : nouvel essai (Mode développeur activé entre-temps) ;
        - « admin » : coche « Exécuter ce programme en tant qu'administrateur »
          et demande la relance de FS Passion en administrateur ;
        - « no_admin » : décoche ce réglage (pris en compte au prochain lancement) ;
        - « dev_settings » : ouvre la page Espace développeurs de Windows."""
        if action == "check":
            return self.rights_state(refresh=True)
        if action == "admin":
            # La case « Exécuter en tant qu'administrateur » ne concerne que
            # l'application fabriquée (FS Passion.exe). En développement, elle
            # serait posée sur l'interpréteur Python et empêcherait lancer_dev.bat
            # de démarrer : FS Passion est seulement relancé en
            # administrateur, pour cette fois.
            if config.is_frozen():
                if not winapi.set_run_as_admin_flag(True):
                    raise AppError("rights.flag_failed", status=500)
            self.restart_elevated = True
            out = self.rights_state()
            out["restart"] = True
            out["once"] = not config.is_frozen()
            return out
        if action == "no_admin":
            if not winapi.set_run_as_admin_flag(False):
                raise AppError("rights.flag_failed", status=500)
            return self.rights_state()
        if action == "dev_settings":
            winapi.open_url("ms-settings:developers")
            return self.rights_state()
        raise AppError("error.bad_request")

    def set_launch_method(self, vid: str, method: str) -> dict[str, Any]:
        if versions.get(vid) is None or method not in LAUNCH_METHODS:
            raise AppError("error.bad_request")
        self.settings.update_version(vid, {"launch_method": method})
        return self.version_state(vid)

    def platform_info(self, exe: str | None) -> dict[str, Any]:
        """Plateforme d'installation d'un exécutable (mémorisée : la lecture des
        manifestes Steam et Epic prend quelques millisecondes)."""
        if not exe or not Path(exe).is_file():
            return {"platform": "exe", "uri": None}
        key = exe.lower()
        info = self._platforms.get(key)
        if info is None:
            try:
                info = detect.platform_of(exe)
            except Exception as exc:  # noqa: BLE001
                log.warning("Plateforme inconnue : %s", exc)
                info = {"platform": "exe", "uri": None}
            self._platforms[key] = info
        return info

    def launch_info(self, vid: str, cfg: dict[str, Any] | None = None,
                    vp: gamepaths.VersionPaths | None = None) -> dict[str, Any]:
        """Arguments de lancement et chemin qu'ils prennent : ajoutés par FS
        Passion (exécutable), à copier dans Steam ou Epic, ou impossibles
        (Microsoft Store / Xbox). État de la console dans game.xml."""
        cfg = cfg if cfg is not None else self.settings.version(vid)
        vp = vp if vp is not None else self.paths(vid)
        method = cfg.get("launch_method") or "auto"
        info = self.platform_info(cfg.get("game_exe")) if method != "exe" else {"platform": "exe", "uri": None}
        args = launcher.launch_args(vid, cfg.get("launch_args"))
        game_xml = vp.user_dir / gamesettings.GAME_XML if vp.user_dir else None
        controls = gamesettings.development_controls(game_xml) if game_xml is not None else None
        return {
            "platform": info.get("platform", "exe"),
            "route": launcher.route(method, info),
            "args_mode": launcher.args_mode(method, info),
            "args": args,
            "args_text": launcher.args_text(args),
            "game_xml": str(game_xml) if game_xml else None,
            "controls": controls,
        }

    def enable_console(self, vid: str) -> dict[str, Any]:
        """Bouton « Activer dans game.xml » : <development><controls> à true."""
        if versions.get(vid) is None:
            raise AppError("error.bad_request")
        state = self.version_state(vid)
        state["game_xml"] = self._enable_cheats(vid)
        state["launch"] = self.launch_info(vid)
        return state

    def set_launch_args(self, vid: str, skip_start_videos: bool, cheats: bool) -> dict[str, Any]:
        """Arguments de lancement cochés pour une version.

        Cocher la console de développement passe aussi <controls> à true dans
        game.xml (dossier du jeu) ; le résultat indique « game_xml » :
        changed | unchanged | absent | error.
        """
        if versions.get(vid) is None:
            raise AppError("error.bad_request")
        self.settings.update_version(vid, {"launch_args": {
            "skip_start_videos": bool(skip_start_videos),
            "cheats": bool(cheats),
        }})
        game_xml = self._enable_cheats(vid) if cheats else "unchanged"
        state = self.version_state(vid)
        state["game_xml"] = game_xml
        return state

    def _enable_cheats(self, vid: str) -> str:
        """Console de développement dans game.xml. Ne lève pas d'exception."""
        vp = self.paths(vid)
        if vp.user_dir is None:
            return "absent"
        try:
            return gamesettings.enable_development_controls(vp.user_dir / gamesettings.GAME_XML)
        except gamesettings.WriteError as exc:
            log.error("game.xml non modifié : %s", exc.key)
            return "error"

    def detect(self, vid: str | None, silent: bool = False) -> dict[str, Any]:
        """Détection des installations et préremplissage."""
        if self.settings.demo_active():
            raise AppError("demo.no_detect", status=409)
        if not self._detect_lock.acquire(blocking=False):
            raise AppError("detect.busy", status=409)
        self.detecting = True
        self._platforms.clear()
        self.bus.publish("detect", running=True)
        try:
            results = detect.detect_all()
            changed: dict[str, list[str]] = {}
            for v in versions.all_versions():
                if not v.available or (vid and v.id != vid):
                    continue
                det = results.get(v.id) or {}
                # Lecture et écriture en un seul bloc, pour ne pas écraser
                # une case cochée pendant la détection (cf. Settings.modify_version).
                fields = self.settings.modify_version(
                    v.id, lambda cfg, det=det, vid_=v.id: detect.prefill(cfg, det, vid_), save=False)
                if fields:
                    changed[v.id] = fields
            self.settings.save()
            self._ensure_backups()
            for v_id in changed:
                if any(f in ("mods_dir", "user_dir") for f in changed[v_id]):
                    if v_id == self.active_version():
                        self.libs.reset(v_id)
            found = [k for k, r in results.items() if (not vid or k == vid) and (r.get("game_exe") or r.get("user_dir"))]
            return {"found": found, "changed": changed, "silent": silent}
        finally:
            self.detecting = False
            self._detect_lock.release()
            self.bus.publish("detect", running=False)
            self.bus.publish("state")

    # ------------------------------------------------------------------
    # Bibliothèque et anomalies
    # ------------------------------------------------------------------

    def library(self, vid: str) -> dict[str, Any]:
        if versions.get(vid) is None:
            raise AppError("error.bad_request")
        lib = self.libs.get(vid)
        if lib.status == "idle":
            lib.request_scan()
        snap = lib.snapshot()
        store = self._store_or_none(vid)
        every = snap["anomalies"] + self._missing_anomalies(vid, store, snap)
        cfg = self.settings.anomalies_cfg()
        hidden_t = cfg.get("hidden_types", [])
        hidden_f = (cfg.get("hidden_folders") or {}).get(vid, [])
        seen = set((cfg.get("seen") or {}).get(vid, []))
        vis = anomalies.visible(every, hidden_t, hidden_f)
        for a in vis:
            a["new"] = anomalies.key_of(a) not in seen
        snap["anomalies"] = vis
        snap["anomalies_hidden"] = len(vis) != len(every)
        snap["anomalies_total"] = len(every)
        # Classement (Non classés, repères) dès que les parties sont possibles.
        snap["classification"] = store is not None
        snap["applied"] = self.applied_state(vid) if versions.require(vid).available else None
        return snap

    def _missing_anomalies(self, vid: str, store: PartiesStore | None,
                           snap: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """A7 : mods référencés par une partie ou par les mods communs, mais absents
        des dossiers de stockage. A8 : mod supprimé à la main du dossier de
        mods, mais dont une copie existe encore par ses liens dans un dossier de
        partie. Seulement quand la lecture des mods est terminée."""
        lib = self.libs.get(vid)
        if store is None or lib.status != "ready":
            return []
        mods = snap["mods"] if snap is not None else lib.snapshot()["mods"]
        present = {m["id"].lower() for m in mods}
        refs = store.referenced()
        copies = self._stray_copies(vid, store)
        out = []
        names = {p["folder"].lower(): p["name"] for p in store.data["parties"]}
        for file, folders in sorted(copies.items(), key=lambda kv: kv[0].lower()):
            mod_id = file[:-4] if file.lower().endswith(".zip") else file
            ref = refs.get(mod_id.lower()) or {"parties": [], "common": False}
            out.append(anomalies.make("A8", mod_id, 0, file=file,
                                      folders=[names.get(f.lower(), f) for f in folders],
                                      parties=ref["parties"], common=ref["common"]))
        with_copy = {(f[:-4] if f.lower().endswith(".zip") else f).lower() for f in copies}
        for low, ref in sorted(refs.items()):
            if low not in present and low not in with_copy:
                out.append(anomalies.make("A7", ref["id"], 0, parties=ref["parties"], common=ref["common"]))
        return out

    def _stray_copies(self, vid: str, store: PartiesStore) -> dict[str, list[str]]:
        try:
            folders = apply.VersionFolders(self.paths(vid), store, lambda: self._lib_index(vid))
            return reconcile.stray_copies(folders)
        except (apply.ApplyError, OSError):
            return {}

    def missing_resolve(self, vid: str, action: str, ids: Any) -> dict[str, Any]:
        """Mods absents du dossier de mods mais présents dans des parties (A7, A8),
        proposées dans la fenêtre du démarrage :
        - « remove » : retirés de toutes les listes (aucun fichier touché) ;
        - « restore » : la copie encore présente dans une partie redevient le
          mod du dossier de mods (un nom de plus pour le même fichier, lien dur ;
          si le disque ne le permet pas, le fichier est copié) ;
        - « delete » : copies supprimées (Corbeille), et retrait des listes.
        """
        if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids) or not ids:
            raise AppError("error.bad_request")
        st = self._store(vid)
        vp = self.paths(vid)
        if action == "remove":
            touched = st.remove_everywhere(ids)
            self._changed(vid)
            return {"action": action, "count": len(ids), "lists": touched, "state": self.parties_state(vid)}
        if action not in ("restore", "delete"):
            raise AppError("error.bad_request")
        self._require_stopped(vid)
        copies = self._stray_copies(vid, st)
        wanted = {i.lower() for i in ids}
        done: list[str] = []
        recycled = True
        with self._apply_lock(vid):
            folders = self._folders(vid)
            for file, where in copies.items():
                mod_id = file[:-4] if file.lower().endswith(".zip") else file
                if mod_id.lower() not in wanted:
                    continue
                paths = [folders.parties_dir / f / file for f in where]
                if action == "restore":
                    dst = vp.mods_dir / file if vp.mods_dir else None
                    if dst is None or os.path.lexists(dst):
                        continue
                    try:
                        os.link(paths[0], dst)
                    except OSError:
                        shutil.copy2(paths[0], dst)
                    log.info("A8 : %s restauré dans le dossier de mods", file)
                    done.append(mod_id)
                else:
                    for i, item in enumerate(paths):
                        folders.inventory.drop_entry(item.parent.name, file)
                        if i < len(paths) - 1 or links.link_count(item) >= 2:
                            os.unlink(item)  # un autre nom garde le contenu
                        else:
                            recycled = modops.discard(item) == "recycled" and recycled
                    done.append(mod_id)
        if action == "delete" and done:
            st.remove_everywhere(done)
            self._changed(vid)
        self.libs.get(vid).request_scan()
        return {"action": action, "done": done, "recycled": recycled, "state": self.parties_state(vid)}

    def rescan(self, vid: str, quick: bool) -> None:
        lib = self.libs.get(vid)
        if quick and lib.status == "ready":
            threading.Thread(target=lib.quick_check, daemon=True).start()
        else:
            lib.request_scan()

    def anomalies_action(self, vid: str, action: str, value: str | None) -> dict[str, Any]:
        cfg = self.settings.anomalies_cfg()
        if action == "hide_type" and value in anomalies.ALL_TYPES:
            if value not in cfg["hidden_types"]:
                cfg["hidden_types"].append(value)
        elif action == "hide_folder" and value:
            cfg.setdefault("hidden_folders", {}).setdefault(vid, [])
            if value not in cfg["hidden_folders"][vid]:
                cfg["hidden_folders"][vid].append(value)
        elif action == "reset_hidden":
            cfg["hidden_types"] = []
            cfg["hidden_folders"] = {}
        elif action == "mark_seen":
            lib = self.libs.get(vid)
            every = lib.anomalies + self._missing_anomalies(vid, self._store_or_none(vid))
            keys = sorted({anomalies.key_of(a) for a in every})
            cfg.setdefault("seen", {})[vid] = keys
        else:
            raise AppError("error.bad_request")
        self.settings.set_anomalies_cfg(cfg)
        return cfg

    # ------------------------------------------------------------------
    # Parties et classement des mods — parties.json seulement
    # ------------------------------------------------------------------

    def _store(self, vid: str) -> PartiesStore:
        """parties.json de la version, chargé à la demande."""
        if self.stopped:
            # « Ne plus utiliser FS Passion » : plus rien n'est réécrit,
            # en particulier un parties.json que l'utilisateur vient de supprimer.
            raise AppError("stop.stopped", status=409)
        v = versions.get(vid)
        if v is None or not v.available:
            raise AppError("error.bad_request")
        if not v.has_override:
            # FS2011 : pas d'override, donc pas de parties.
            raise AppError("lists.no_parties", game=v.name)
        vp = self.paths(vid)
        if vp.fsp_dir is None or vp.mods_dir is None or not vp.mods_dir.is_dir():
            raise AppError("parties.not_configured", game=v.name)
        path = vp.fsp_dir / "parties.json"
        with self._parties_lock:
            st = self._parties.get(vid)
            if st is not None and st.path == path:
                return st
            st = PartiesStore(vid, path, str(vp.mods_dir), [str(p) for p in vp.extra_mods_dirs])
            st.load()
            if not st.exists:
                # Premier lancement : la partie sélectionnée est celle qui
                # correspond à l'état réel du jeu, en général la Partie Pleine.
                st.init_selection(self._observed_applied(vid, st) or FULL)
            if st.recovered:
                self._parties_notices[vid] = {"key": "parties.recovered", "level": "warn",
                                              "params": {"game": v.name, "backup": st.recovered}}
            elif st.lost:
                self._parties_notices[vid] = {"key": "parties.lost", "level": "error", "params": {"game": v.name}}
            self._parties[vid] = st
        self._recover(vid)
        return st

    # ------------------------------------------------------------------
    # Dossiers de parties
    # ------------------------------------------------------------------

    def _apply_lock(self, vid: str) -> threading.Lock:
        with self._parties_lock:
            return self._apply_locks.setdefault(vid, threading.Lock())

    def _folders(self, vid: str) -> apply.VersionFolders:
        st = self._store(vid)
        try:
            return apply.VersionFolders(self.paths(vid), st, lambda: self._lib_index(vid))
        except apply.ApplyError as exc:
            raise AppError(exc.key, exc.status, **exc.params) from exc

    def _recover(self, vid: str) -> None:
        """Opération interrompue (coupure de courant…) : terminée ou annulée au
        démarrage, jamais pendant que le jeu tourne."""
        if self.monitor.is_running(vid):
            return
        st = self._parties.get(vid)
        vp = self.paths(vid)
        if st is None or vp.fsp_dir is None or not (vp.fsp_dir / apply.JOURNAL).is_file():
            return
        lock = self._apply_lock(vid)
        if not lock.acquire(blocking=False):
            return
        try:
            folders = apply.VersionFolders(vp, st, lambda: self._lib_index(vid))
            outcome = folders.recover()
        except apply.ApplyError:
            outcome = None
        finally:
            lock.release()
        if outcome:
            self._parties_notices[vid] = {"key": f"apply.recovered_{outcome}", "level": "warn",
                                          "params": {"game": versions.require(vid).name}}

    def _require_stopped(self, vid: str, key: str = "apply.running") -> None:
        """Rien ne touche aux dossiers de parties ni à gameSettings.xml
        pendant que le jeu tourne."""
        if self.monitor.is_running(vid):
            raise AppError(key, status=409, game=versions.require(vid).name)

    # ------------------------------------------------------------------
    # Réconciliation
    # ------------------------------------------------------------------

    def _library_ready(self, vid: str) -> None:
        """Fin d'un scan : la première fois pour cette version, réconciliation
        complète (démarrage de FS Passion, changement de version)."""
        if vid in self._reconciled:
            return
        self._reconciled.add(vid)

        def work() -> None:
            try:
                self.reconcile(vid, "startup")
            except AppError as exc:
                log.debug("Réconciliation au démarrage non faite (%s) : %s", vid, exc.key)
            except Exception:  # noqa: BLE001
                log.exception("Réconciliation au démarrage en échec")

        threading.Thread(target=work, name=f"reconcile-{vid}", daemon=True).start()

    def _reconcile_locked(self, vid: str, st: PartiesStore) -> reconcile.Report:
        """Réconciliation, verrou des dossiers de parties déjà pris."""
        vp = self.paths(vid)
        folders = apply.VersionFolders(vp, st, lambda: self._lib_index(vid))
        observed = self._observed_applied(vid, st)
        applied = observed if observed and not apply.is_special(observed) else None
        return reconcile.Reconciler(folders).run(vp.pending_downloads, applied)

    def reconcile(self, vid: str, reason: str = "manual", publish: bool = True) -> dict[str, Any]:
        """Remet en ordre tous les dossiers de parties de la version.
        Jamais pendant que le jeu tourne ; silencieux s'il n'y a rien à faire."""
        v = versions.get(vid)
        if v is None or not v.available or not v.has_override:
            raise AppError("error.bad_request")
        self._require_stopped(vid)
        st = self._store(vid)
        lock = self._apply_lock(vid)
        if not lock.acquire(blocking=False):
            raise AppError("apply.busy", status=409)
        try:
            try:
                report = self._reconcile_locked(vid, st)
            except apply.ApplyError as exc:
                raise AppError(exc.key, exc.status, **exc.params) from exc
        finally:
            lock.release()
        out = report.to_json()
        out["reason"] = reason
        if report.moved_files:
            self.libs.get(vid).request_scan()
        if report.added or report.unclassified:
            self._changed(vid)
        if publish and not report.is_empty():
            self.bus.publish("reconcile", version=vid, report=out)
        return out

    def party_apply(self, vid: str, pid: str | None = None) -> dict[str, Any]:
        """« Appliquer » : la partie sélectionnée, ou `pid`."""
        v = versions.get(vid)
        if v is None or not v.available or not v.has_override:
            raise AppError("error.bad_request")
        self._require_stopped(vid)
        st = self._store(vid)
        pid = pid or st.data["selected"]
        lib = self.libs.get(vid)
        if pid != apply.EMPTY and lib.status != "ready":
            raise AppError("apply.library_busy", status=409)
        lock = self._apply_lock(vid)
        # Une réconciliation en arrière-plan (démarrage) peut tenir le verrou un
        # instant : on l'attend un peu plutôt que de refuser.
        if not lock.acquire(timeout=15):
            raise AppError("apply.busy", status=409)
        try:
            folders = self._folders(vid)
            try:
                # Réconciliation de toutes les parties avant d'appliquer
                # (mises à jour du jeu, pending_downloads, liens orphelins).
                report = self._reconcile_locked(vid, st)
                res = folders.apply(pid)
            except apply.ApplyError as exc:
                raise AppError(exc.key, exc.status, **exc.params) from exc
            except OSError as exc:
                log.exception("Application de la partie %s impossible", pid)
                raise AppError("apply.failed", status=500, detail=str(exc)) from exc
        finally:
            lock.release()
        tidy = res["tidy"]
        tidy["updated"] = sorted(set(report.updated + tidy["updated"]), key=str.lower)
        tidy["added"] = report.added.get(pid, []) + [a for a in tidy["added"] if a not in report.added.get(pid, [])]
        tidy["set_aside"] = report.set_aside + tidy["set_aside"]
        tidy["old_versions"] = report.old_versions + tidy["old_versions"]
        tidy["unclassified"] = report.unclassified
        if tidy["updated"] or tidy["added"] or tidy["set_aside"] or tidy["old_versions"] or report.moved_files:
            lib.request_scan()  # des fichiers ont rejoint le dossier de mods
        self._changed(vid)
        self.bus.publish("state")
        res["name"] = pid
        res["state"] = self.parties_state(vid)
        return res

    def older_resolve(self, vid: str, path: Any, action: str) -> dict[str, Any]:
        """Version plus ancienne déposée par le jeu : « keep » garde la
        version de l'utilisateur (le fichier reste dans Recovered) ; « use » met la
        version du jeu à sa place, dans son dossier de stockage, l'ancienne allant dans
        Old versions, et les liens de toutes les parties suivent."""
        if not isinstance(path, str) or action not in ("keep", "use"):
            raise AppError("error.bad_request")
        self._require_stopped(vid)
        st = self._store(vid)
        lock = self._apply_lock(vid)
        if not lock.acquire(timeout=15):
            raise AppError("apply.busy", status=409)
        try:
            folders = self._folders(vid)
            entry = next((x for x in folders.older_list() if same_path(x["path"], path)), None)
            if entry is None:
                raise AppError("older.gone", status=404)
            src = Path(entry["path"])
            if not fsutil.is_within(src, folders.fsp / apply.RECOVERED):
                raise AppError("error.forbidden", status=403)
            if action == "use":
                target = folders.locate(entry["name"])
                try:
                    if os.path.lexists(target):
                        folders._replace(src, target)
                    else:
                        fsutil.relocate(src, target)
                except OSError as exc:
                    log.error("Version du jeu non mise en place (%s) : %s", entry["name"], exc)
                    raise AppError("older.failed", status=500, name=entry["name"], detail=str(exc)) from exc
                log.info("Version du jeu retenue pour %s : %s → %s", entry["name"], entry.get("new"), target)
                folders.older_drop(path)
                self._reconcile_locked(vid, st)  # les liens des parties suivent
            else:
                log.info("Version gardée pour %s (%s) ; la version du jeu reste dans %s",
                         entry["name"], entry.get("old"), src.parent)
                folders.older_drop(path)
        finally:
            lock.release()
        if action == "use":
            self.libs.get(vid).request_scan()
        self._changed(vid)
        return {"ok": True, "state": self.parties_state(vid)}

    def override_resolve(self, vid: str, action: str, directory: str | None, pid: str | None) -> dict[str, Any]:
        """Contrôle de l'override au démarrage : l'override pointe vers un
        dossier inconnu (modification à la main ou par un autre outil)."""
        if action == "adopt":
            if not directory:
                raise AppError("error.bad_request")
            self._require_stopped(vid)
            self.set_path(vid, "mods_dir", directory)
            with self._parties_lock:
                self._parties.pop(vid, None)
            return {"ok": True}
        if action == "reapply":
            return self.party_apply(vid, pid)
        if action == "ignore":
            ignored = self.settings.get("override_ignored") or {}
            ignored[vid] = directory or ""
            self.settings.set("override_ignored", ignored)
            return {"ok": True}
        raise AppError("error.bad_request")

    def _store_or_none(self, vid: str) -> PartiesStore | None:
        try:
            return self._store(vid)
        except AppError:
            return None

    def _observed_applied(self, vid: str, st: PartiesStore,
                          state: dict[str, Any] | None = None) -> str | None:
        """Partie appliquée d'après l'override : celle que le jeu charge réellement."""
        state = state or self.applied_state(vid)
        kind = state.get("kind")
        if kind == "full":
            return FULL
        if kind == "empty":
            return EMPTY
        if kind == "party" and state.get("directory"):
            return st.find_by_folder(Path(state["directory"]).name)
        return None

    def _lib_index(self, vid: str) -> dict[str, dict[str, Any]]:
        return self.libs.get(vid).index()

    def _changed(self, vid: str) -> None:
        self.bus.publish("parties", version=vid)

    def parties_state(self, vid: str) -> dict[str, Any]:
        v = versions.get(vid)
        if v is None:
            raise AppError("error.bad_request")
        out: dict[str, Any] = {"version": vid, "supported": False, "reason": None}
        try:
            st = self._store(vid)
        except AppError as exc:
            out["reason"] = {"key": exc.key, "params": exc.params}
            return out
        applied = self.applied_state(vid)
        observed = self._observed_applied(vid, st, applied)
        if observed is not None:
            # La partie appliquée est celle vers laquelle pointe l'override : on
            # la note, avec l'historique des 10 dernières.
            try:
                if st.record_applied(observed):
                    log.info("Partie appliquée %s : %s", vid, observed)
            except PartyError as exc:
                log.warning("Historique des parties non enregistré : %s", exc.key)
        snap = st.snapshot()
        stale = False
        check = None
        older: list[dict[str, Any]] = []
        try:
            folders = apply.VersionFolders(self.paths(vid), st, lambda: self._lib_index(vid))
            older = [{k: x.get(k) for k in ("name", "path", "new", "old")} for x in folders.older_list()]
            # Partie Pleine avec plusieurs stockages : dossier de liens, à
            # réappliquer quand les mods changent, comme une partie ordinaire.
            if observed and (not apply.is_special(observed) or observed == FULL) \
                    and self.libs.get(vid).status == "ready":
                stale = folders.is_stale(observed)
        except apply.ApplyError:
            pass
        kind = applied.get("kind")
        if observed is None and kind in ("other", "party") and applied.get("directory"):
            # Override vers un dossier inconnu : l'interface propose « Adopter »,
            # « Réappliquer » ou « Ne rien faire ».
            ignored = (self.settings.get("override_ignored") or {}).get(vid)
            if not ignored or not same_path(ignored, applied["directory"]):
                last = snap.get("applied")
                suggest = last if last and st.known(last) and last != FULL else snap["selected"]
                check = {"directory": applied["directory"], "suggest": suggest}
        out.update({
            "supported": True,
            "parties": snap["parties"],
            "common_mods": snap["common_mods"],
            "selected": snap["selected"],
            "applied": observed,
            "applied_kind": kind,
            "applied_directory": applied.get("directory"),
            "applied_history": snap["applied_history"],
            "applied_stale": stale,
            "needs_apply": observed != snap["selected"] or stale,
            "override_check": check,
            # Versions plus anciennes déposées par le jeu, à confirmer.
            "older": older,
            "path": str(st.path),
            "notice": self._parties_notices.pop(vid, None),
        })
        return out

    def _running_guard(self, vid: str, pid: str, key: str) -> None:
        """La partie appliquée n'est pas touchée pendant que le jeu tourne."""
        if not self.monitor.is_running(vid):
            return
        st = self._store(vid)
        if self._observed_applied(vid, st) == pid:
            raise AppError(key, status=409, game=versions.require(vid).name)

    def party_create(self, vid: str, name: Any, from_map: str | None = None,
                     optional: Any = None) -> dict[str, Any]:
        """Créer (＋), ou « ＋ Partie » depuis une map avec ses dépendances.

        Les mods facultatifs cochés (<SearchMods>, `optional`) ; seuls
        ceux de la map (ou de ses dépendances) présents dans les mods sont pris."""
        st = self._store(vid)
        mods: list[str] = []
        map_id: str | None = None
        res: dict[str, Any] = {"present": [], "missing": [], "dlc": []}
        if optional is not None and (not isinstance(optional, list) or not all(isinstance(x, str) for x in optional)):
            raise AppError("error.bad_request")
        if from_map:
            idx = self._lib_index(vid)
            entry = idx.get(str(from_map).lower())
            if entry is None:
                raise AppError("parties.map_not_found", status=404, name=str(from_map))
            res = resolve_dependencies([entry["id"]], idx, self.libs.get(vid).dlc_ids())
            mods = [entry["id"]] + res["present"]
            wanted = {x.lower() for x in optional or []}
            mods += [o["id"] for o in res.get("optional", []) if o["id"] and o["id"].lower() in wanted]
            map_id = entry["id"] if entry.get("is_map") else None
        party = st.create(name, mods, map_id)
        self._changed(vid)
        return {"party": party, "count": len(mods), "missing": res["missing"], "dlc": res["dlc"],
                "state": self.parties_state(vid)}

    def party_duplicate(self, vid: str, pid: str, name: Any) -> dict[str, Any]:
        party = self._store(vid).duplicate(pid, name)
        self._changed(vid)
        return {"party": party, "state": self.parties_state(vid)}

    def _has_folder(self, vid: str, pid: str) -> bool:
        st = self._store(vid)
        party = st.party(pid)
        vp = self.paths(vid)
        if party is None or vp.fsp_dir is None:
            return False
        return (vp.fsp_dir / apply.PARTIES / party["folder"]).exists()

    def party_rename(self, vid: str, pid: str, name: Any) -> dict[str, Any]:
        """Renommer : le dossier sur le disque est renommé, et l'override
        suit si c'est la partie appliquée."""
        self._running_guard(vid, pid, "parties.running_rename")
        st = self._store(vid)
        party = st.party(pid)
        if party is None or apply.is_special(pid):
            party = st.rename(pid, name)  # erreur prévue (partie spéciale, absente)
        clean, new_folder = st.preview_rename(pid, name)
        old_folder = party["folder"]
        if new_folder != old_folder and self._has_folder(vid, pid):
            self._require_stopped(vid, "parties.running_rename")
            applied = self._observed_applied(vid, st) == pid
            with self._apply_lock(vid):
                folders = self._folders(vid)
                try:
                    folders.rename(old_folder, new_folder, applied)
                except apply.ApplyError as exc:
                    raise AppError(exc.key, exc.status, **exc.params) from exc
                try:
                    party = st.rename(pid, clean)
                except PartyError:
                    # parties.json non enregistré : le dossier reprend son nom.
                    folders.rename(new_folder, old_folder, applied)
                    raise
        else:
            party = st.rename(pid, clean)
        self._changed(vid)
        return {"party": party, "state": self.parties_state(vid)}

    def party_delete(self, vid: str, pid: str) -> dict[str, Any]:
        """Supprimer. Si c'est la partie appliquée, la partie appliquée
        précédente est d'abord réappliquée (historique, sinon Partie Pleine) :
        jamais d'override vers un dossier supprimé. Le dossier est vidé
        lien par lien ; ses fichiers physiques sont rapatriés."""
        self._running_guard(vid, pid, "parties.running_delete")
        st = self._store(vid)
        party = st.party(pid)
        if party is None or apply.is_special(pid):
            st.delete(pid)  # erreur prévue
        assert party is not None
        has_folder = self._has_folder(vid, pid)
        was_applied = self._observed_applied(vid, st) == pid
        fallback = None
        if was_applied:
            self._require_stopped(vid, "parties.running_delete")
            history = [h for h in st.data["applied_history"] if h != pid and st.known(h)]
            fallback = history[0] if history else FULL
            self.party_apply(vid, fallback)
        tidy: dict[str, Any] = {}
        if has_folder:
            self._require_stopped(vid, "parties.running_delete")
            with self._apply_lock(vid):
                try:
                    tidy = self._folders(vid).delete(party["folder"]).to_json()
                except apply.ApplyError as exc:
                    raise AppError(exc.key, exc.status, **exc.params) from exc
                except OSError as exc:
                    log.exception("Suppression du dossier de la partie %s impossible", pid)
                    raise AppError("apply.folder_busy", status=409, path=party["folder"], detail=str(exc)) from exc
            if any(tidy.values()):
                self.libs.get(vid).request_scan()
        res = st.delete(pid)
        res["was_applied"] = was_applied
        res["fallback"] = fallback
        res["tidy"] = tidy
        self._changed(vid)
        res["state"] = self.parties_state(vid)
        return res

    def party_select(self, vid: str, pid: str) -> dict[str, Any]:
        self._store(vid).select(pid)
        self._changed(vid)
        return self.parties_state(vid)

    def party_common(self, vid: str, pid: str, enabled: bool) -> dict[str, Any]:
        self._store(vid).set_common_enabled(pid, enabled)
        self._changed(vid)
        return self.parties_state(vid)

    def party_mods(self, vid: str, action: str, target: str, ids: Any,
                   pid: str | None = None, source: str | None = None) -> dict[str, Any]:
        """Classement : ajouter, retirer ou déplacer des mods (bandeau d'actions,
        glisser-déposer, touche Suppr). Jamais une opération sur les fichiers."""
        if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
            raise AppError("error.bad_request")
        st = self._store(vid)
        idx = self._lib_index(vid)
        if action == "add":
            # Seuls les mods présents dans les dossiers de stockage s'ajoutent.
            ids = [idx[i.lower()]["id"] for i in ids if i.lower() in idx]
        res = st.change_mods(action, target, ids, pid=pid, source=source,
                             is_map=lambda m: bool((idx.get(m.lower()) or {}).get("is_map")))
        if res["added"] or res["removed"]:
            self._changed(vid)
        res["state"] = self.parties_state(vid)  # type: ignore[assignment]
        return res

    def party_replace(self, vid: str, old: str, new: str) -> dict[str, Any]:
        """« Remplacer par… » : rattache un mod manquant à un mod présent."""
        st = self._store(vid)
        idx = self._lib_index(vid)
        entry = idx.get(str(new).lower())
        if entry is None:
            raise AppError("parties.mod_not_found", status=404, name=str(new))
        touched = st.replace_mod(str(old), entry["id"],
                                 is_map=lambda m: bool((idx.get(m.lower()) or {}).get("is_map")))
        if touched:
            self._changed(vid)
        return {"lists": touched, "new": entry["id"], "state": self.parties_state(vid)}

    def resolve_deps(self, vid: str, ids: Any) -> dict[str, Any]:
        """Dépendances (et dépendances des dépendances) de mods de la bibliothèque."""
        if versions.get(vid) is None or not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
            raise AppError("error.bad_request")
        lib = self.libs.get(vid)
        return resolve_dependencies(ids, lib.index(), lib.dlc_ids())

    # ------------------------------------------------------------------
    # Téléchargements et intégration
    # ------------------------------------------------------------------

    def _downloads_folder(self) -> Path:
        if self.settings.demo_active():
            raise AppError("downloads.demo", status=409)
        folder = self.settings.get("downloads_dir") or ""
        if not folder or not Path(folder).is_dir():
            raise AppError("downloads.no_folder", status=404, path=folder)
        return Path(folder)

    def downloads_scan(self) -> dict[str, Any]:
        """Fenêtre « Nouveaux mods trouvés » : les mods du dossier de
        téléchargements, et leur état pour chaque version configurée."""
        folder = self._downloads_folder()
        ignored = {str(x.get("key")) for x in self.settings.get("downloads_ignored") or [] if isinstance(x, dict)}
        items = downloads.scan_folder(folder, ignored)
        ready = [v for v in versions.all_versions() if v.available and gamepaths.is_ready(self.paths(v.id))]
        for it in items:
            it["states"] = {v.id: downloads.assess(it, self.paths(v.id)) for v in ready}
            if not it["detected"]:
                it["detected"] = None
        active = self.active_version()
        st = self._store_or_none(active)
        party = None
        if st is not None and not apply.is_special(st.data["selected"]):
            p = st.party(st.data["selected"])
            party = {"id": p["id"], "name": p["name"]} if p else None
        return {
            "folder": str(folder),
            "items": items,
            "versions": [{"id": v.id, "name": v.name, "short": v.short, "logo": v.logo,
                          "running": self.monitor.is_running(v.id),
                          # Dossiers de stockage : colonne « Stockage » s'il y en a plusieurs.
                          "storages": [str(p) for p in self.paths(v.id).storages if p.is_dir()]}
                         for v in ready],
            "active": active,
            "party": party,
            "classification": st is not None,
        }

    def downloads_ignore(self, files: Any) -> dict[str, Any]:
        """« Ignorer ces fichiers » : ils ne seront plus proposés (nom, taille et
        date mémorisés : une nouvelle version du même nom sera proposée)."""
        if not isinstance(files, list) or not all(isinstance(x, str) for x in files):
            raise AppError("error.bad_request")
        folder = self._downloads_folder()
        cur = [x for x in self.settings.get("downloads_ignored") or [] if isinstance(x, dict)]
        keys = {x.get("key") for x in cur}
        for name in files:
            if not name or any(c in name for c in "/\\:") or name in (".", ".."):
                continue
            p = folder / name
            try:
                st = p.stat()
            except OSError:
                continue
            key = downloads.ignore_key(name, st.st_size, st.st_mtime)
            if key not in keys:
                cur.append({"key": key, "name": name})
                keys.add(key)
        self.settings.set("downloads_ignored", cur[-downloads.MAX_IGNORED:])
        return {"ignored": len(files)}

    def downloads_integrate(self, items: Any) -> dict[str, Any]:
        """« Intégrer » : déplacement vers le dossier de mods de la version
        choisie, puis classement (version active), réconciliation et nouveau
        scan. Une version dont le jeu tourne est reportée à sa fermeture."""
        if not isinstance(items, list) or not items:
            raise AppError("error.bad_request")
        folder = self._downloads_folder()
        stamp = time.strftime("%Y-%m-%d_%H%M%S")
        done: dict[str, list[dict[str, Any]]] = {}
        skipped: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        postponed: list[dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, dict):
                raise AppError("error.bad_request")
            name = str(raw.get("file") or "")
            vid = str(raw.get("version") or "")
            dest = str(raw.get("destination") or "none")
            v = versions.get(vid)
            if not name or any(c in name for c in "/\\:") or name in (".", "..") or v is None \
                    or not name.lower().endswith(".zip") or dest not in ("none", "common", "party"):
                raise AppError("error.bad_request")
            storage_n = raw.get("storage", 0)
            if not isinstance(storage_n, int) or isinstance(storage_n, bool) or not 0 <= storage_n <= storage.MAX_EXTRA:
                raise AppError("error.bad_request")
            spec = {"path": str(folder / name), "file": name, "version": vid, "destination": dest,
                    "party": raw.get("party") if isinstance(raw.get("party"), str) else None,
                    "replace_older": raw.get("replace_older") is True, "storage": storage_n}
            if self.monitor.is_running(vid):
                postponed.append(spec)
                continue
            res = self._integrate_one(spec, stamp)
            if res.get("error"):
                failed.append(res)
            elif res["result"] == "skipped":
                skipped.append(res)
            else:
                done.setdefault(vid, []).append(res)
        if postponed:
            cur = [x for x in self.settings.get("downloads_postponed") or [] if isinstance(x, dict)]
            known = {x.get("path") for x in cur}
            cur += [p for p in postponed if p["path"] not in known]
            self.settings.set("downloads_postponed", cur)
        self._after_integration(list(done))
        return {
            "done": done,
            "count": sum(len(x) for x in done.values()),
            "skipped": skipped,
            "failed": failed,
            "postponed": [{"file": p["file"], "version": p["version"]} for p in postponed],
            "state": self.parties_state(self.active_version()) if self._store_or_none(self.active_version()) else None,
        }

    def _integrate_one(self, spec: dict[str, Any], stamp: str) -> dict[str, Any]:
        src = Path(spec["path"])
        vid = spec["version"]
        vp = self.paths(vid)
        name = src.name
        out: dict[str, Any] = {"file": name, "version": vid}
        if vp.mods_dir is None or not vp.mods_dir.is_dir():
            return {**out, "error": "downloads.unconfigured"}
        if not src.is_file():
            return {**out, "error": "downloads.gone"}
        mod_id = downloads.strip_browser_suffix(name[:-4]) if name.lower().endswith(".zip") else name
        try:
            res = downloads.integrate_file(src, vp, mod_id, spec.get("replace_older") is True, stamp,
                                           int(spec.get("storage") or 0))
        except fsutil.MoveError as exc:
            log.error("Intégration de %s impossible : %s", src, exc)
            return {**out, "error": exc.key if exc.key.startswith("move.") else "downloads.failed", "detail": exc.detail}
        except OSError as exc:
            log.error("Intégration de %s impossible : %s", src, exc)
            return {**out, "error": "downloads.failed", "detail": str(exc)}
        out.update(res)
        out["id"] = mod_id
        # Classement d'un mod nouveau (colonne « Destination »).
        if res["result"] == "new" and spec["destination"] != "none":
            st = self._store_or_none(vid)
            if st is not None:
                try:
                    if spec["destination"] == "common":
                        st.change_mods("add", "common", [mod_id])
                        out["classified"] = "common"
                    elif spec.get("party") and st.party(spec["party"]) is not None:
                        st.change_mods("add", "party", [mod_id], pid=spec["party"])
                        out["classified"] = "party"
                except PartyError as exc:
                    log.warning("Classement de %s impossible : %s", mod_id, exc.key)
        return out

    def _after_integration(self, vids: list[str]) -> None:
        """Après une intégration : les liens des parties qui contiennent un mod
        remplacé sont refaits (réconciliation), puis les mods sont relus."""
        for vid in vids:
            v = versions.require(vid)
            if v.has_override and self._store_or_none(vid) is not None and not self.monitor.is_running(vid):
                try:
                    self.reconcile(vid, "integration", publish=False)
                except AppError as exc:
                    log.info("Réconciliation après intégration non faite : %s", exc.key)
            self._changed(vid)
            lib = self.libs.get(vid)
            if vid == self.active_version():
                try:
                    lib.scan_now()
                except Exception:  # noqa: BLE001
                    log.exception("Scan après intégration en échec")
            elif lib.status != "idle":
                lib.request_scan()

    def downloads_postponed(self, vid: str) -> dict[str, Any] | None:
        """Intégrations reportées parce que le jeu tournait : faites à sa
        fermeture, avec un message."""
        cur = [x for x in self.settings.get("downloads_postponed") or [] if isinstance(x, dict)]
        mine = [x for x in cur if x.get("version") == vid]
        if not mine:
            return None
        self.settings.set("downloads_postponed", [x for x in cur if x.get("version") != vid])
        stamp = time.strftime("%Y-%m-%d_%H%M%S")
        results = [self._integrate_one(spec, stamp) for spec in mine if Path(str(spec.get("path"))).is_file()]
        ok = [r for r in results if not r.get("error") and r.get("result") != "skipped"]
        self._after_integration([vid] if ok else [])
        if ok:
            self.bus.publish("toast", key="downloads.postponed_done",
                             params={"count": len(ok), "game": versions.require(vid).name}, level="success")
        return {"done": ok}

    # ------------------------------------------------------------------
    # Supprimer définitivement et renommer un mod
    # ------------------------------------------------------------------

    def _ready_library(self, vid: str) -> dict[str, dict[str, Any]]:
        lib = self.libs.get(vid)
        if lib.status != "ready":
            raise AppError("apply.library_busy", status=409)
        return lib.index()

    def _lists_of(self, st: PartiesStore | None, mod_id: str) -> dict[str, Any]:
        ref = (st.referenced().get(mod_id.lower()) if st is not None else None) or {}
        return {"parties": ref.get("parties", []), "common": bool(ref.get("common"))}

    def mods_delete_preview(self, vid: str, ids: Any) -> dict[str, Any]:
        """Fenêtre d'avertissement : les mods, les parties qui les
        contiennent, et la Corbeille (disponible ou non sur leur disque)."""
        if versions.get(vid) is None or not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
            raise AppError("error.bad_request")
        idx = self._ready_library(vid)
        st = self._store_or_none(vid)
        storages = self.paths(vid).storages
        mods = []
        recycle = True
        for i in dict.fromkeys(x.lower() for x in ids):
            e = idx.get(i)
            if e is None:
                continue
            path = storages[int(e.get("storage") or 0)] / e["file"]
            ok = winapi.recycle_bin_available(path)
            recycle = recycle and ok
            mods.append({"id": e["id"], "file": e["file"], "kind": e["kind"], "size": e.get("size"),
                         "recycle": ok, **self._lists_of(st, e["id"])})
        return {"mods": mods, "recycle": recycle and bool(mods), "running": self.monitor.is_running(vid)}

    def mods_delete(self, vid: str, ids: Any, confirm: Any) -> dict[str, Any]:
        """Supprimer définitivement : retrait de toutes les listes → retrait
        des liens dans tous les dossiers de parties → Corbeille (ou suppression
        si le disque n'en a pas). Double validation faite par l'interface
        (`confirm`). Refusé pendant que le jeu tourne."""
        if versions.get(vid) is None or confirm is not True or not isinstance(ids, list) \
                or not all(isinstance(x, str) for x in ids) or not ids:
            raise AppError("error.bad_request")
        self._require_stopped(vid, "delete.running")
        idx = self._ready_library(vid)
        vp = self.paths(vid)
        st = self._store_or_none(vid)
        entries = [idx[i.lower()] for i in dict.fromkeys(ids) if i.lower() in idx]
        if not entries:
            raise AppError("delete.nothing", status=404)
        # 1. Listes
        if st is not None:
            st.remove_everywhere([e["id"] for e in entries])
        recycled: list[str] = []
        deleted: list[str] = []
        failed: list[str] = []
        with self._apply_lock(vid):
            folders = None
            if st is not None and vp.fsp_dir is not None:
                try:
                    folders = apply.VersionFolders(vp, st, lambda: self._lib_index(vid))
                except apply.ApplyError:
                    folders = None
            for e in entries:
                path = vp.storages[int(e.get("storage") or 0)] / e["file"]
                try:
                    # 2. Liens dans les dossiers de parties (comme des liens)
                    if folders is not None:
                        modops.unlink_everywhere(folders, e["file"], path)
                    # 3. Le mod lui-même : Corbeille, sinon suppression
                    how = modops.discard(path)
                except (OSError, LinkError) as exc:
                    log.error("Suppression de %s impossible : %s", path, exc)
                    failed.append(e["id"])
                    continue
                (recycled if how == "recycled" else deleted).append(e["id"])
                log.warning("Mod supprimé (%s) : %s", how, path)
        self._changed(vid)
        try:
            self.libs.get(vid).scan_now()
        except Exception:  # noqa: BLE001
            log.exception("Scan après suppression en échec")
        return {"recycled": recycled, "deleted": deleted, "failed": failed,
                "state": self.parties_state(vid) if st is not None else None}

    def mod_rename_preview(self, vid: str, mod_id: Any) -> dict[str, Any]:
        """Fenêtre de renommage : préfixe de version conservé, noms déjà
        pris (contrôle en direct), listes et dépendances concernées."""
        if versions.get(vid) is None or not isinstance(mod_id, str):
            raise AppError("error.bad_request")
        idx = self._ready_library(vid)
        e = idx.get(mod_id.lower())
        if e is None:
            raise AppError("rename.not_found", status=404, name=mod_id)
        prefix, rest = modops.split_prefix(e["id"])
        taken = modops.storage_names(self.paths(vid).storages)
        taken.discard(e["id"].lower())
        st = self._store_or_none(vid)
        return {
            "id": e["id"], "file": e["file"], "kind": e["kind"], "prefix": prefix, "rest": rest,
            "suggestion": modops.split_prefix(anomalies.suggest_name(e["id"]))[1],
            "taken": sorted(taken), "dependents": modops.dependents(idx, e["id"]),
            "is_map": bool(e.get("is_map")), "max": modops.MAX_NAME,
            **self._lists_of(st, e["id"]),
        }

    def mod_rename(self, vid: str, mod_id: Any, new_id: Any) -> dict[str, Any]:
        """Renommer un mod : le fichier (ou le dossier) est renommé dans son
        dossier de stockage, sans toucher à son contenu ; les listes, les
        liens des dossiers de parties et l'inventaire suivent. Refusé pendant que
        le jeu tourne."""
        if versions.get(vid) is None or not isinstance(mod_id, str) or not isinstance(new_id, str):
            raise AppError("error.bad_request")
        self._require_stopped(vid, "rename.running")
        idx = self._ready_library(vid)
        e = idx.get(mod_id.lower())
        if e is None:
            raise AppError("rename.not_found", status=404, name=mod_id)
        new_id = new_id.strip()
        taken = modops.storage_names(self.paths(vid).storages)
        taken.discard(e["id"].lower())
        err = modops.check_new_name(new_id, e["id"], taken)
        if err:
            raise AppError(err, name=new_id, max=modops.MAX_NAME)
        vp = self.paths(vid)
        st = self._store_or_none(vid)
        # Listes où figure l'ancien nom, avant le renommage : l'interface demande
        # ensuite s'il doit les suivre.
        where = self._lists_of(st, e["id"])
        with self._apply_lock(vid):
            try:
                if st is not None and vp.fsp_dir is not None:
                    folders = apply.VersionFolders(vp, st, lambda: self._lib_index(vid))
                    res = modops.rename_mod(folders, e, new_id)
                else:
                    # FS2011 (pas de parties) : seul le fichier change de nom.
                    folder = vp.storages[int(e.get("storage") or 0)]
                    new_file = f"{new_id}.zip" if e["kind"] == "zip" else new_id
                    try:
                        os.rename(folder / e["file"], folder / new_file)
                    except OSError as exc:
                        raise AppError("rename.failed", status=409, name=e["file"], detail=str(exc)) from exc
                    res = {"old": e["id"], "new": new_id, "file": new_file, "links": 0, "lists": 0}
            except apply.ApplyError as exc:
                raise AppError(exc.key, exc.status, **exc.params) from exc
        res["where"] = where
        res["parties"] = len(where["parties"])
        if st is not None:
            self._changed(vid)
        try:
            self.libs.get(vid).scan_now()
        except Exception:  # noqa: BLE001
            log.exception("Scan après renommage en échec")
        res["state"] = self.parties_state(vid) if st is not None else None
        return res

    def mod_lists_rename(self, vid: str, old_id: Any, new_id: Any) -> dict[str, Any]:
        """Deuxième temps du renommage : après confirmation de
        l'utilisateur, les listes suivent le nouveau nom. Sans confirmation, elles
        gardent l'ancien nom (rien n'est changé)."""
        if versions.get(vid) is None or not isinstance(old_id, str) or not isinstance(new_id, str):
            raise AppError("error.bad_request")
        st = self._store_or_none(vid)
        if st is None:
            raise AppError("error.bad_request")
        idx = self._ready_library(vid)
        if idx.get(new_id.strip().lower()) is None:
            raise AppError("rename.not_found", status=404, name=new_id)
        with self._apply_lock(vid):
            n = modops.update_lists(st, old_id, new_id.strip())
        self._changed(vid)
        return {"old": old_id, "new": new_id.strip(), "lists": n, "state": self.parties_state(vid)}

    # ------------------------------------------------------------------
    # Jeu
    # ------------------------------------------------------------------

    def launch(self, vid: str, apply_first: bool = False) -> dict[str, Any]:
        """Lancer le jeu, après avoir appliqué la partie sélectionnée si
        l'interface le demande (« Appliquer la partie X puis lancer le jeu ? »)."""
        v = versions.get(vid)
        if v is None or not v.available:
            raise AppError("error.bad_request")
        if self.monitor.is_running(vid):
            raise AppError("launch.already_running", status=409, game=v.name)
        applied = None
        if apply_first:
            applied = self.party_apply(vid)
        cfg = self.settings.version(vid)
        if (cfg.get("launch_args") or {}).get("cheats"):
            self._enable_cheats(vid)  # idempotent : rien n'est écrit si déjà activée
        method = cfg.get("launch_method") or "auto"
        res = launcher.launch(vid, cfg, self.platform_info(cfg.get("game_exe")) if method != "exe" else None)
        if applied is not None:
            res["applied"] = {k: applied[k] for k in ("party", "count", "missing")}
        if res.get("ok") and self.settings.get("minimize_on_launch"):
            try:
                native.minimize()
                # Pendant le jeu, l'interface réduite se met en veille.
                native.sleep_later(3.0)
            except Exception:  # noqa: BLE001
                pass
        return res

    def _on_game_exit(self, vid: str) -> None:
        """À la fermeture du jeu : reprise d'une opération restée en attente,
        réconciliation (mises à jour faites dans le jeu), intégration des
        téléchargements reportés, nouveau scan rapide ; FS Passion revient au
        premier plan (réglage)."""
        if vid in self._parties:
            self._recover(vid)
        v = versions.get(vid)
        if v is not None and v.has_override and self._store_or_none(vid) is not None:
            try:
                self.reconcile(vid, "game_exit")
            except AppError as exc:
                log.info("Réconciliation après le jeu non faite : %s", exc.key)
        try:
            self.downloads_postponed(vid)
        except Exception:  # noqa: BLE001
            log.exception("Intégration des téléchargements reportés en échec")
        lib = self.libs.get(vid)
        if lib.status == "ready":
            lib.quick_check()
        if self.settings.get("focus_after_game"):
            try:
                native.focus()
            except Exception:  # noqa: BLE001
                log.debug("Retour au premier plan impossible", exc_info=True)

    # ------------------------------------------------------------------
    # Mode démonstration
    # ------------------------------------------------------------------

    def demo_state(self) -> dict[str, Any]:
        cfg = self.settings.get("demo") or {}
        avail = demo.availability(self.app_info, bool(self.settings.get("internet_access")))
        return {"active": bool(cfg.get("active")), "offered": bool(cfg.get("offered")), **avail}

    def _demo_switch(self) -> None:
        """Chemins changés d'un coup : bibliothèques et parties repartent de zéro."""
        with self._parties_lock:
            self._parties.clear()
        self._reconciled.clear()
        for v in versions.all_versions():
            self.libs.drop(v.id)
        self.libs.get(self.active_version()).request_scan()
        self.bus.publish("state")

    def demo_start(self) -> dict[str, Any]:
        """Installe le pack (vérifié) et passe en mode démonstration."""
        if self.settings.demo_active():
            return self.demo_state()
        try:
            data = demo.install(self.app_info, bool(self.settings.get("internet_access")))
        except demo.DemoError as exc:
            raise AppError(exc.key, exc.status, **exc.params) from exc
        except OSError as exc:
            log.exception("Installation du pack de démonstration impossible")
            raise AppError("demo.install_failed", status=500, detail=str(exc)) from exc
        cfgs = demo.version_cfgs(data)
        state = self.settings.get("demo") or {}
        state.update({"active": True, "offered": True, "versions": {},
                      "saved_active_version": self.active_version()})
        self.settings.set("demo", state)
        for vid, cfg in cfgs.items():
            if versions.get(vid) is None:
                continue
            self.settings.update_version(vid, cfg, save=False)
        first = "FS25" if "FS25" in cfgs else next(iter(cfgs), versions.DEFAULT_VERSION)
        self.settings.set("active_version", first, save=False)
        self.settings.save()
        # Le jeu « de démonstration » charge son dossier de mods (Partie Pleine).
        for vid in cfgs:
            if versions.get(vid) is None:
                continue
            vp = self.paths(vid)
            if vp.gamesettings is not None and vp.gamesettings.is_file() and vp.mods_dir is not None:
                try:
                    gamesettings.write_override(vp.gamesettings, str(vp.mods_dir), True)
                except gamesettings.WriteError as exc:
                    log.warning("Override de démonstration non écrit (%s) : %s", vid, exc.key)
        self._demo_switch()
        log.info("Mode démonstration activé")
        return self.demo_state()

    def demo_stop(self) -> dict[str, Any]:
        """Quitte le mode démonstration et efface tout son dossier."""
        state = self.settings.get("demo") or {}
        if not state.get("active"):
            return self.demo_state()
        back = state.get("saved_active_version")
        state.update({"active": False, "versions": {}, "saved_active_version": None})
        self.settings.set("demo", state, save=False)
        if back and versions.get(back):
            self.settings.set("active_version", back, save=False)
        self.settings.save()
        self._demo_switch()
        try:
            demo.remove()
        except (OSError, demo.DemoError) as exc:
            log.error("Dossier de démonstration non effacé : %s", exc)
            raise AppError("demo.remove_failed", status=500, path=str(demo.demo_dir())) from exc
        log.info("Mode démonstration quitté")
        return self.demo_state()

    def demo_offered(self) -> None:
        state = self.settings.get("demo") or {}
        state["offered"] = True
        self.settings.set("demo", state)

    # ------------------------------------------------------------------
    # Catalogue des DLC distant
    # ------------------------------------------------------------------

    def dlc_catalog_state(self) -> dict[str, Any]:
        try:
            return dlcremote.status(self.app_info, bool(self.settings.get("internet_access")))
        except Exception:  # noqa: BLE001 - un état d'affichage ne doit jamais bloquer
            log.debug("État du catalogue des DLC indisponible", exc_info=True)
            return {"enabled": bool(self.settings.get("internet_access")), "source_ok": False}

    def _detected_dlc(self) -> dict[str, list[str]]:
        """DLC présents sur ce PC, par version installée (noms de fichiers)."""
        out: dict[str, list[str]] = {}
        for v in versions.all_versions():
            if not v.available:
                continue
            try:
                stems = dlc.detected_stems(self.paths(v.id).dlc_dirs)
            except OSError:
                continue
            if stems:
                out[v.id] = stems
        return out

    def update_remote_data(self, force: bool = False) -> dict[str, Any]:
        """Catalogue (une fois par jour au plus, sauf `force`) puis icônes
        manquantes des DLC détectés. Rien sans l'accord « Connexion Internet »."""
        if not self.settings.get("internet_access") or self.stopped:
            return {"status": "disabled"}
        if not self._remote_lock.acquire(blocking=False):
            return {"status": "busy"}
        try:
            res = dlcremote.update_catalog(self.app_info, force=force)
            icons_res: dict[str, int] = {}
            if res["status"] not in ("no_source", "error"):
                wanted = dlcremote.wanted_icons(dlc.load_catalog(), self._detected_dlc())
                if wanted:
                    icons_res = dlcremote.download_icons(self.app_info, wanted)
            res["icons"] = icons_res
            if res["status"] == "updated" or icons_res.get("downloaded"):
                # Noms et icônes des DLC relus par les bibliothèques déjà ouvertes.
                for v in versions.all_versions():
                    if v.available and self.libs.get(v.id).status in ("ready", "error"):
                        self.libs.get(v.id).request_scan()
            self.bus.publish("state")
            return res
        finally:
            self._remote_lock.release()

    def refresh_remote_data(self, force: bool = False) -> None:
        """Même chose, en arrière-plan (démarrage, accès Internet autorisé)."""
        if not self.settings.get("internet_access"):
            return

        def work() -> None:
            try:
                self.update_remote_data(force=force)
            except Exception:  # noqa: BLE001
                log.exception("Mise à jour du catalogue des DLC en échec")

        threading.Thread(target=work, name="dlc-remote", daemon=True).start()

    # ------------------------------------------------------------------
    # Mises à jour de FS Passion
    # ------------------------------------------------------------------

    def update_state(self) -> dict[str, Any]:
        return self.updater.state()

    def update_check(self) -> dict[str, Any]:
        """« Rechercher maintenant » (Paramètres → Application)."""
        if not self.settings.get("update_check"):
            raise AppError("settings.updates.error_disabled", status=409)
        return self.updater.check()

    def update_install(self) -> dict[str, Any]:
        """Télécharge la nouvelle version et la vérifie, puis :
        - version installée : prépare l'installeur, lancé dès la fermeture
          de FS Passion (action « quit » : l'interface ferme l'application) ;
        - version portable : le .zip est rangé dans les téléchargements et
          montré dans l'Explorateur (action « revealed »)."""
        if self.monitor.running:
            # La remise en ordre des parties se fait à la fermeture du jeu :
            # FS Passion doit rester ouvert jusque-là.
            raise AppError("settings.updates.error_game_running", status=409)
        try:
            path = self.updater.download()
        except updates.UpdateError as exc:
            raise AppError(f"settings.updates.error_{exc.key}", status=409) from exc
        kind = updates.install_kind()
        if kind == "installed":
            try:
                updates.launch_installer_after_exit(path, os.getpid())
            except (OSError, updates.UpdateError) as exc:
                log.warning("Lancement de l'installeur impossible : %s", exc)
                raise AppError("settings.updates.error_launch", status=500) from exc
            log.info("Installation de %s au prochain arrêt de FS Passion", path.name)
            return {"action": "quit", "state": self.updater.state()}
        winapi.reveal(path)
        return {"action": "revealed", "file": path.name, "state": self.updater.state()}

    def update_page(self) -> bool:
        """Page de la publication sur GitHub (nouveautés, téléchargement)."""
        url = self.updater.release_page()
        if not url or config.web_link({"github_url": url}, "github") is None:
            raise AppError("error.bad_request")
        return winapi.open_url(url)

    # ------------------------------------------------------------------
    # Exporter et importer la configuration
    # ------------------------------------------------------------------

    def _no_demo(self) -> None:
        if self.settings.demo_active():
            raise AppError("backup.demo_active", status=409)

    def _parties_for_export(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for v in versions.all_versions():
            if not v.available or not v.has_override:
                continue
            vp = self.paths(v.id)
            if vp.fsp_dir is None or not (vp.fsp_dir / "parties.json").is_file():
                continue
            st = self._store_or_none(v.id)
            if st is not None:
                out[v.id] = st.snapshot()
        return out

    def export_data(self) -> dict[str, Any]:
        """Contenu d'un export : réglages et parties de toutes les versions."""
        return backup.build_export(self.settings.snapshot(), self._parties_for_export())

    def export_config(self, from_window: bool = True) -> dict[str, Any]:
        """« Exporter » : dialogue « Enregistrer sous », puis écriture du fichier."""
        self._no_demo()
        target = dialogs.save_as(
            backup.default_file_name(), [("FS Passion", "*.json")],
            title="FS Passion", window=native.window, from_window=from_window,
            initial=str(winapi.documents_dir() or ""),
        )
        if not target:
            return {"cancelled": True}
        path = Path(target)
        if path.suffix.lower() != ".json":
            path = path.with_name(path.name + ".json")
        data = self.export_data()
        try:
            backup.write_export(path, data)
        except OSError as exc:
            log.error("Export impossible (%s) : %s", path, exc)
            raise AppError("backup.write_failed", status=500, path=str(path)) from exc
        return {"path": str(path), "versions": sorted(data["parties"]),
                "parties": sum(len(p.get("parties") or []) for p in data["parties"].values())}

    def import_open(self, from_window: bool = True, path: str | None = None) -> dict[str, Any]:
        """« Importer », premier temps : choix du fichier, lecture, aperçu.
        Rien n'est encore modifié."""
        self._no_demo()
        if path is None:
            path = dialogs.browse("file", str(winapi.documents_dir() or ""), [("FS Passion", "*.json")],
                                  title="FS Passion", window=native.window, from_window=from_window)
        if not path:
            return {"cancelled": True}
        try:
            data = backup.read_export(Path(path))
        except backup.BackupError as exc:
            raise AppError(exc.key, exc.status, **exc.params) from exc
        token = os.urandom(8).hex()
        self._import_pending = {"token": token, "data": data, "path": path}
        out = backup.preview(data, self.settings.snapshot())
        out.update({"token": token, "file": Path(path).name})
        return out

    def _running_among(self, vids: list[str]) -> list[str]:
        return [versions.require(v).name for v in vids if self.monitor.is_running(v)]

    def import_apply(self, token: Any, keep_paths: Any) -> dict[str, Any]:
        """« Importer », second temps, après confirmation : sauvegarde de l'état
        actuel, réglages, puis parties des versions concernées. Rien n'est
        appliqué : les dossiers de parties sont refaits au prochain « Appliquer »."""
        self._no_demo()
        pending = self._import_pending
        if not pending or not isinstance(token, str) or token != pending["token"]:
            raise AppError("backup.expired", status=409)
        keep = keep_paths is not False
        data = pending["data"]
        targets = sorted(data["parties"])
        running = self._running_among(targets)
        if running:
            raise AppError("backup.running", status=409, game=", ".join(running))
        self._import_pending = None

        safety = backup.write_safety_backup(self.export_data())
        patch = backup.settings_patch(data, keep)
        if "language" in patch and not self.langs.has(patch["language"]):
            patch.pop("language")
        paths_changed = not keep and any(k in patch for k in backup.PATH_KEYS)
        if patch:
            self.settings.update(patch)
        if paths_changed:
            # Nouveaux chemins : bibliothèques et parties repartent de zéro.
            with self._parties_lock:
                self._parties.clear()
            self._reconciled.clear()
            for v in versions.all_versions():
                self.libs.drop(v.id)

        results = []
        for vid in targets:
            results.append(self._import_parties(vid, data["parties"][vid]))
        self.libs.get(self.active_version()).request_scan()
        if self.tray is not None and "language" in patch:
            self.tray.refresh()
        self.bus.publish("state")
        log.info("Configuration importée (%s chemins actuels) : %s", "avec" if keep else "sans",
                 ", ".join(f"{r['id']}={r.get('parties', r.get('skipped'))}" for r in results) or "aucune partie")
        return {"versions": results, "backup": str(safety), "keep_paths": keep,
                "settings": {k: self.settings.get(k) for k in SETTABLE}}

    def _import_parties(self, vid: str, content: dict[str, Any]) -> dict[str, Any]:
        """Remplace les parties d'une version par celles du fichier."""
        v = versions.require(vid)
        vp = self.paths(vid)
        if vp.fsp_dir is None or vp.mods_dir is None or not vp.mods_dir.is_dir():
            return {"id": vid, "name": v.name, "skipped": "not_configured"}
        try:
            st = self._store(vid)
        except AppError as exc:
            return {"id": vid, "name": v.name, "skipped": exc.key}
        new_folders = {p["folder"] for p in content.get("parties") or []}
        observed = self._observed_applied(vid, st)
        fallback = False
        current_party = st.party(observed) if observed and not apply.is_special(observed) else None
        if current_party is not None and current_party["folder"] not in new_folders:
            # Le jeu charge une partie qui n'existera plus : retour à la Partie
            # Pleine d'abord, jamais d'override vers un dossier supprimé.
            try:
                self.party_apply(vid, FULL)
                observed = FULL
                fallback = True
            except AppError as exc:
                log.warning("Import %s : retour à la Partie Pleine impossible (%s)", vid, exc.key)
                new_folders.add(current_party["folder"])  # dossier gardé
        with self._apply_lock(vid):
            new = dict(content)
            new["mods_dir"] = str(vp.mods_dir)
            new["extra_mods_dirs"] = [str(p) for p in vp.extra_mods_dirs]
            known = {p["id"] for p in new.get("parties") or []} | {FULL, EMPTY}
            by_folder = {p["folder"]: p["id"] for p in new.get("parties") or []}
            applied = observed if observed in (FULL, EMPTY) else None
            if current_party is not None and not fallback:
                applied = by_folder.get(current_party["folder"])
            new["applied"] = applied
            new["applied_history"] = [applied] if applied else []
            new["applied_signature"] = {}
            if new.get("selected") not in known:
                new["selected"] = applied or FULL
            with st._lock:
                st.data = parties_validate(new, vid)
                st.save()
            removed = 0
            try:
                folders = apply.VersionFolders(vp, st, lambda: self._lib_index(vid))
                keep = new_folders | {apply.EMPTY_FOLDER, apply.FULL_FOLDER}
                if folders.parties_dir.is_dir():
                    for item in sorted(folders.parties_dir.iterdir()):
                        if item.name in keep or item.name.startswith(".tmp-"):
                            continue
                        if item.is_dir() or links.is_link(item):
                            folders.delete(item.name)
                            removed += 1
            except (apply.ApplyError, OSError) as exc:
                log.warning("Import %s : dossiers de parties anciens non retirés (%s)", vid, exc)
        self._changed(vid)
        return {"id": vid, "name": v.name, "parties": len(new.get("parties") or []),
                "removed_folders": removed, "fallback": fallback}

    # ------------------------------------------------------------------
    # Ne plus utiliser FS Passion, et désinstallation
    # ------------------------------------------------------------------

    def _stop_versions(self) -> list[str]:
        """Versions qui ont une configuration réelle (hors démonstration)."""
        out = []
        for v in versions.all_versions():
            if not v.available or not v.has_override:
                continue
            vp = gamepaths.from_cfg(v, (self.settings.get("versions") or {}).get(v.id) or config.default_version_cfg())
            has_gs = vp.gamesettings is not None and vp.gamesettings.is_file()
            if has_gs or (vp.fsp_dir is not None and vp.fsp_dir.is_dir()):
                out.append(v.id)
        return out

    def _real_paths(self, vid: str) -> gamepaths.VersionPaths:
        cfg = (self.settings.get("versions") or {}).get(vid) or {}
        return gamepaths.from_cfg(versions.require(vid), config._merge_defaults(cfg, config.default_version_cfg()))

    def stop_preview(self) -> dict[str, Any]:
        """Ce que fera « Ne plus utiliser FS Passion », version par version."""
        rows = []
        for vid in self._stop_versions():
            vp = self._real_paths(vid)
            plan = stopuse.override_plan(vp)
            parties_dir = vp.fsp_dir / apply.PARTIES if vp.fsp_dir else None
            n = 0
            if parties_dir is not None and parties_dir.is_dir():
                n = sum(1 for _ in parties_dir.iterdir())
            rows.append({
                "id": vid, "name": versions.require(vid).name,
                "override": plan["action"],
                "directory": gamesettings.game_path(plan["directory"]) if plan.get("directory") else None,
                "folders": n,
                "kept": stopuse.kept_folders(vp.fsp_dir) if vp.fsp_dir and vp.fsp_dir.is_dir() else [],
                "running": self.monitor.is_running(vid),
            })
        return {
            "versions": rows,
            "running": [r["name"] for r in rows if r["running"]],
            "admin_flag": config.is_frozen() and winapi.run_as_admin_flag(),
            "uninstaller": stopuse.uninstaller() is not None and not self.uninstall_mode,
            "demo": self.settings.demo_active(),
            "options": list(stopuse.OPTIONS),
        }

    def stop_using(self, options: Any, confirm: Any) -> dict[str, Any]:
        """« Ne plus utiliser FS Passion » (étapes 3 à 5). Jeu fermé."""
        if confirm is not True:
            raise AppError("error.bad_request")
        chosen = {o for o in (options or []) if o in stopuse.OPTIONS} if isinstance(options, list) else set()
        vids = self._stop_versions()
        running = self._running_among(vids)
        if running:
            raise AppError("stop.running", status=409, game=", ".join(running))
        if self.settings.demo_active():
            try:
                self.demo_stop()
            except AppError as exc:
                log.warning("Mode démonstration non quitté avant l'arrêt : %s", exc.key)
        log.info("« Ne plus utiliser FS Passion » : %s", ", ".join(sorted(chosen)) or "aucune suppression en plus")
        # Plus aucun scan (le cache pourrait être réécrit), plus de catalogue.
        self.libs.disable_all()
        rows = []
        for vid in vids:
            rows.append(self._stop_version(vid, chosen))
        if config.is_frozen() and winapi.run_as_admin_flag():
            # Réglage « administrateur » posé par FS Passion : retiré.
            winapi.set_run_as_admin_flag(False)
        done = stopuse.app_data_now(chosen)
        if "settings" in chosen:
            self.settings.frozen = True
        self.exit_cleanup = stopuse.exit_paths(chosen)
        self.stopped = True
        self.bus.publish("state")
        errors = [r for r in rows if r.get("error")]
        return {"versions": rows, "removed": done, "errors": len(errors),
                "uninstaller": stopuse.uninstaller() is not None and not self.uninstall_mode,
                "uninstall_mode": self.uninstall_mode}

    def uninstall_minimal(self) -> list[str]:
        """Désinstalleur Windows fermé sans confirmer « Ne plus utiliser
        FS Passion » (Annuler, croix) : la ligne d'override est quand même
        rétablie (option « toujours faite »), pour que le jeu ne charge plus un
        dossier de parties d'une application désinstallée. Rien n'est supprimé.
        Une version dont le jeu tourne est laissée : il réécrirait le fichier.
        Renvoie les versions rétablies."""
        done: list[str] = []
        vids = self._stop_versions()
        try:
            running = set(launcher.running_versions())  # sans surveillance démarrée (--uninstall-quiet)
        except Exception:  # noqa: BLE001
            running = {v for v in vids if self.monitor.is_running(v)}
        for vid in vids:
            if vid in running:
                log.warning("Désinstallation : %s tourne, override non rétabli", vid)
                continue
            try:
                action = stopuse.restore_override(self._real_paths(vid))["action"]
                log.info("Désinstallation : override de %s → %s", vid, action)
                done.append(vid)
            except (gamesettings.WriteError, OSError) as exc:
                log.error("Désinstallation : override de %s non rétabli : %s", vid, exc)
        if config.is_frozen() and winapi.run_as_admin_flag():
            winapi.set_run_as_admin_flag(False)
        log.info("Désinstallation : override rétabli pour %d version(s) sur %d", len(done), len(vids))
        return done

    def _stop_version(self, vid: str, chosen: set[str]) -> dict[str, Any]:
        v = versions.require(vid)
        vp = self._real_paths(vid)
        row: dict[str, Any] = {"id": vid, "name": v.name}
        try:
            row["override"] = stopuse.restore_override(vp)["action"]
        except gamesettings.WriteError as exc:
            # Override non rétabli : les dossiers de parties restent, le jeu
            # pourrait encore en charger un.
            log.error("Override de %s non rétabli : %s", vid, exc.key)
            row.update({"override": "failed", "error": exc.key})
            return row
        removed = 0
        set_aside: list[str] = []
        if vp.fsp_dir is not None and vp.mods_dir is not None and (vp.fsp_dir / apply.PARTIES).is_dir():
            try:
                st = PartiesStore(vid, vp.fsp_dir / "parties.json", str(vp.mods_dir), [str(p) for p in vp.extra_mods_dirs])
                st.load()
                with self._apply_lock(vid):
                    folders = apply.VersionFolders(vp, st, lambda: self._lib_index(vid))
                    for item in sorted(folders.parties_dir.iterdir()):
                        if not (item.is_dir() or links.is_link(item)):
                            continue  # fichier inattendu : laissé tel quel
                        res = folders.delete(item.name)
                        set_aside += res.set_aside
                        removed += 1
                    stopuse.remove_quietly(folders.fsp / apply.INVENTORY)
                    stopuse.remove_quietly(folders.journal_path)
                    stopuse.remove_if_empty(folders.parties_dir)
            except (apply.ApplyError, OSError) as exc:
                log.error("Dossiers de parties de %s non supprimés : %s", vid, exc)
                row["error"] = "stop.folders_failed"
        row["folders"] = removed
        row["set_aside"] = set_aside
        if vp.fsp_dir is not None and vp.fsp_dir.is_dir():
            data = stopuse.remove_version_data(vp.fsp_dir, "parties" in chosen, "caches" in chosen)
            row["kept"] = data["kept"]
            row["fsp_removed"] = data["folder_removed"]
        with self._parties_lock:
            self._parties.pop(vid, None)
        return row

    def stop_quit(self, uninstaller: Any) -> None:
        """Après « Ne plus utiliser » : désinstalleur éventuel, puis fermeture."""
        if not self.stopped:
            raise AppError("error.bad_request")
        if uninstaller is True:
            self.run_uninstaller = stopuse.uninstaller()

    # ------------------------------------------------------------------
    # Divers
    # ------------------------------------------------------------------

    def browse(self, kind: str, vid: str | None, field: str | None, initial: str | None,
               from_window: bool) -> str | None:
        filters: list[tuple[str, str]] = []
        if kind == "file" and vid:
            v = versions.require(vid)
            pattern = ";".join(sorted({"*.exe"}))
            filters = [(v.name, pattern)]
        if kind not in ("file", "folder"):
            raise AppError("error.bad_request")
        return dialogs.browse(kind, initial, filters, title="FS Passion",
                              window=native.window, from_window=from_window)

    def open_link(self, key: str) -> bool:
        """Ouvre dans le navigateur une adresse d'app_info.json (GitHub, dons)."""
        url = config.web_link(self.app_info, key)
        if url is None:
            raise AppError("error.bad_request")
        return winapi.open_url(url)

    def open_mod_link(self, vid: str, mod_id: Any, url: Any) -> bool:
        """Ouvre dans le navigateur le lien de téléchargement d'un mod
        requis ou facultatif. Seule une adresse écrite dans le modDesc.xml de ce
        mod (<SearchMods>) est ouverte, en http ou https."""
        if versions.get(vid) is None or not isinstance(mod_id, str) or not isinstance(url, str):
            raise AppError("error.bad_request")
        entry = self._lib_index(vid).get(mod_id.lower())
        if entry is None:
            raise AppError("error.bad_request")
        allowed = {
            item.get("url")
            for kind in ("search_mods", "optional_mods")
            for item in entry.get(kind) or []
            if isinstance(item, dict)
        }
        safe = moddesc.safe_url(url)
        if safe is None or safe != url or url not in allowed:
            raise AppError("error.bad_request")
        return winapi.open_url(url)

    def open_folder(self, what: str, vid: str | None = None) -> bool:
        if what == "logs":
            return winapi.open_folder(config.logs_dir())
        if what == "lang":
            return winapi.open_folder(i18n.ensure_user_lang_folder())
        raise AppError("error.bad_request")

    def reveal_item(self, vid: str, storage: Any, name: Any) -> bool:
        """Montre un élément d'un dossier de stockage dans l'Explorateur
        (anomalies). Seul un nom simple de ce dossier est accepté ;
        un élément absent (mod manquant) ouvre le dossier de stockage."""
        if versions.get(vid) is None or not isinstance(name, str) or not isinstance(storage, int):
            raise AppError("error.bad_request")
        if not name or name in (".", "..") or any(c in name for c in '/\\:'):
            raise AppError("error.bad_request")
        storages = self.paths(vid).storages
        if not 0 <= storage < len(storages):
            raise AppError("error.bad_request")
        folder = storages[storage]
        target = folder / name
        if target.exists():
            return winapi.reveal(target)
        return winapi.open_folder(folder)

    # ------------------------------------------------------------------
    # Mesures de performance — diagnostic
    # ------------------------------------------------------------------

    def record_ui_perf(self, data: Any) -> dict[str, Any]:
        """Mesures envoyées par l'interface. Gardées en mémoire seulement."""
        if not isinstance(data, dict):
            raise AppError("error.bad_request")

        def num(v: Any) -> float | None:
            return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 1e9 else None

        if num(data.get("ready_ms")) is not None and "ready_ms" not in self.ui_perf:
            self.ui_perf["ready_ms"] = round(float(data["ready_ms"]))
        scroll = data.get("scroll")
        if isinstance(scroll, dict) and scroll.get("list") in ("l1", "l2", "l3"):
            frames = num(scroll.get("frames"))
            dur = num(scroll.get("ms"))
            if frames and dur:
                agg = self.ui_perf.setdefault("scroll", {}).setdefault(scroll["list"], {
                    "frames": 0, "ms": 0.0, "long": 0, "worst_ms": 0.0, "sessions": 0})
                agg["frames"] += int(frames)
                agg["ms"] += dur
                agg["long"] += int(num(scroll.get("long")) or 0)
                agg["worst_ms"] = max(agg["worst_ms"], num(scroll.get("worst_ms")) or 0.0)
                agg["sessions"] += 1
        for key in ("width", "height", "dpr"):
            if num(data.get(key)) is not None:
                self.ui_perf[key] = data[key]
        return {"ok": True}

    def perf_lines(self) -> list[str]:
        """Section « Performance » du diagnostic (texte technique, en anglais)."""
        out: list[str] = []
        if self.ui_perf.get("ready_ms") is not None:
            out.append(f"UI ready: {self.ui_perf['ready_ms']} ms after page load")
        if self.ui_perf.get("width"):
            out.append(f"Window: {self.ui_perf.get('width')} x {self.ui_perf.get('height')} px, scale {self.ui_perf.get('dpr')}")
        names = {"l1": "list 1", "l2": "list 2", "l3": "list 3"}
        for key, agg in sorted((self.ui_perf.get("scroll") or {}).items()):
            fps = agg["frames"] * 1000 / agg["ms"] if agg["ms"] else 0
            out.append(f"Scrolling {names[key]}: {agg['sessions']} times, {agg['frames']} frames, {fps:.1f} fps on average, "
                       f"{agg['long']} frames > 33 ms, worst {agg['worst_ms']:.0f} ms")
        loaded = self.libs.loaded()
        for v in versions.all_versions():
            lib = loaded.get(v.id)
            if lib is None or lib.perf.get("scan_s") is None:
                continue
            line = f"Library {v.id}: {len(lib.entries)} mods, last scan {lib.perf['scan_s']} s"
            if lib.perf.get("icons_s") is not None:
                line += f", {lib.perf['icons_converted']} icons converted in {lib.perf['icons_s']} s"
            if lib.cache_dir is not None:
                size = n = 0
                try:
                    for e in os.scandir(lib.cache_dir / "icons"):
                        if e.is_file():
                            n += 1
                            size += e.stat().st_size
                except OSError:
                    pass
                line += f", icon cache {n} files / {size / 1048576:.0f} MB"
            out.append(line)
        try:
            import psutil

            # Mémoire propre (USS) de chaque processus, pour ne pas compter
            # deux fois les pages partagées entre les processus WebView2 (RSS).
            def private_bytes(p: psutil.Process) -> int:
                try:
                    return p.memory_full_info().uss
                except (psutil.Error, OSError, AttributeError):
                    return p.memory_info().rss

            proc = psutil.Process()
            own = private_bytes(proc)
            children = 0
            for child in proc.children(recursive=True):
                try:
                    children += private_bytes(child)
                except (psutil.Error, OSError):
                    pass
            out.append(f"Memory: {own / 1048576:.0f} MB (FS Passion), {children / 1048576:.0f} MB "
                       "(window, WebView2 processes, private memory)")
        except Exception:  # noqa: BLE001 - mesure facultative
            pass
        out.append(f"Uptime: {int(time.time() - self.started_at)} s")
        return out

    def diagnostic(self) -> str:
        """« Copier le diagnostic » : version, Windows, chemins de chaque
        version, droits, catalogue des DLC, dernières erreurs. Anonymisé."""
        states = []
        for v in versions.all_versions():
            if not v.available:
                continue
            st = self.version_state(v.id)
            st["override"] = (st.get("applied") or {}).get("override")
            st["applied_kind"] = (st.get("applied") or {}).get("kind")
            if v.has_override:
                parties_st = self._parties.get(v.id)
                if parties_st is not None:
                    st["parties_count"] = len(parties_st.data.get("parties") or [])
            states.append(st)
        rights = self.rights_state()
        cat = self.dlc_catalog_state()
        upd = self.updater.state()
        s = self.settings.snapshot()

        def yn(value: Any) -> str:
            return "?" if value is None else ("yes" if value else "no")

        extra = {
            "Language": str(s.get("language") or "-"),
            "Theme": str(s.get("theme") or "-"),
            "Demo mode": yn(self.settings.demo_active()),
            "Developer mode": yn(rights.get("dev_mode")),
            "Symlinks allowed": yn(rights.get("symlinks")),
            "Run as admin flag": yn(rights.get("run_as_admin")),
            "Internet access": yn(s.get("internet_access")),
            "Update check": yn(s.get("update_check"))
                            + (f" ({upd['kind']}; latest: {upd['latest']['version'] if upd['latest'] else '-'}"
                               + (f"; last error: {upd['error']}" if upd.get("error") else "") + ")"),
            "DLC catalog": f"{cat.get('updated') or '-'} ({'downloaded' if cat.get('remote') else 'embedded'})"
                           + (f", last error: {cat['error']}" if cat.get("error") else ""),
        }
        return logs.diagnostic(states, extra, self.perf_lines())
