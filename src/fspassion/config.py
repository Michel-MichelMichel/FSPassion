"""Emplacements de l'application et réglages (settings.json).

Emplacements des fichiers :
- %APPDATA%\\FSPassion\\settings.json : réglages globaux, chemins par version,
  anomalies masquées ;
- %APPDATA%\\FSPassion\\lang\\ : langues personnelles ;
- %LOCALAPPDATA%\\FSPassion\\logs\\ : journaux ;
- %LOCALAPPDATA%\\FSPassion\\dlc\\ : catalogue des DLC et icônes téléchargés ;
- mode portable : si « portable.txt » est à côté de l'exécutable, tout va
  dans <dossier de l'exécutable>\\data\\.

Aucun chemin n'est écrit en dur (I6) : tout vient de l'environnement Windows.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from fspassion import fsutil

log = logging.getLogger(__name__)

APP_DIR_NAME = "FSPassion"
SETTINGS_SCHEMA = 1
# Réglages retirés, effacés de settings.json à la lecture : compteur d'ouvertures,
# invitation au don, clés de licence.
OBSOLETE_KEYS = ("launch_count", "donate_prompt", "licence_key", "licence_ok_at")
# Thèmes renommés ou retirés : le thème choisi passe au thème qui le remplace.
# Rouge → Blanc sur fond bleu (identifiant « blue »).
# Thème du premier lancement et de la réinitialisation (Gruvbox Light).
DEFAULT_THEME = "gruvbox-light"

RENAMED_THEMES = {"red": "blue"}


# --------------------------------------------------------------------------
# Emplacements
# --------------------------------------------------------------------------

def is_frozen() -> bool:
    """Vrai quand l'application tourne depuis l'exécutable fabriqué (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """Dossier racine des ressources (ui, lang, assets).

    En développement : la racine du dépôt (deux niveaux au-dessus de ce fichier).
    Exécutable : dossier interne de PyInstaller.
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def exe_dir() -> Path:
    """Dossier de l'exécutable (ou racine du projet en développement)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return project_root()


def package_data_dir() -> Path:
    return Path(__file__).resolve().parent / "data"


def ui_dir() -> Path:
    return project_root() / "ui"


def lang_dir() -> Path:
    return project_root() / "lang"


def assets_dir() -> Path:
    return project_root() / "assets"


def is_portable() -> bool:
    return (exe_dir() / "portable.txt").is_file()


def _env_dir(var: str, fallback: Path) -> Path:
    value = os.environ.get(var)
    return Path(value) if value else fallback


def roaming_dir() -> Path:
    """Équivalent de %APPDATA%\\FSPassion."""
    override = os.environ.get("FSPASSION_HOME")
    if override:
        return Path(override) / "roaming"
    if is_portable():
        return exe_dir() / "data"
    base = _env_dir("APPDATA", Path.home() / ".config")
    return base / APP_DIR_NAME


def local_dir() -> Path:
    """Équivalent de %LOCALAPPDATA%\\FSPassion."""
    override = os.environ.get("FSPASSION_HOME")
    if override:
        return Path(override) / "local"
    if is_portable():
        return exe_dir() / "data"
    base = _env_dir("LOCALAPPDATA", Path.home() / ".local" / "share")
    return base / APP_DIR_NAME


def settings_path() -> Path:
    return roaming_dir() / "settings.json"


def user_lang_dir() -> Path:
    if is_portable() and not os.environ.get("FSPASSION_HOME"):
        return exe_dir() / "data" / "lang"
    return roaming_dir() / "lang"


def logs_dir() -> Path:
    return local_dir() / "logs"


def dlc_cache_dir() -> Path:
    return local_dir() / "dlc"


def webview_storage_dir() -> Path:
    return local_dir() / "webview"


def instance_file() -> Path:
    return local_dir() / "instance.json"


def dev_data_dir() -> Path:
    """Dépôt de données voisin du dépôt de l'application (développement uniquement)."""
    return project_root().parent / "FSPassion-data"


def load_app_info() -> dict[str, Any]:
    info = fsutil.read_json(package_data_dir() / "app_info.json", {}) or {}
    return info


# Adresses web que l'interface peut ouvrir (0.6.5) : seulement celles
# d'app_info.json, désignées par une clé, en https et sur le domaine prévu.
WEB_LINK_HOSTS: dict[str, tuple[str, ...]] = {
    "github": ("github.com",),
    "buymeacoffee": ("buymeacoffee.com", "www.buymeacoffee.com"),
    "stripe": ("donate.stripe.com", "buy.stripe.com"),
}


def web_link(info: dict[str, Any], key: str) -> str | None:
    """Adresse de la clé ``key`` (github, buymeacoffee, stripe), ou None si
    elle est absente ou ne respecte pas WEB_LINK_HOSTS."""
    from urllib.parse import urlsplit

    if key not in WEB_LINK_HOSTS:
        return None
    url = info.get("github_url") if key == "github" else (info.get("donations") or {}).get(key)
    if not isinstance(url, str):
        return None
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.username or parts.password or parts.port:
        return None
    if (parts.hostname or "").lower() not in WEB_LINK_HOSTS[key]:
        return None
    return url


# --------------------------------------------------------------------------
# Réglages
# --------------------------------------------------------------------------

def default_version_cfg() -> dict[str, Any]:
    return {
        "game_exe": "",
        "user_dir": "",
        "mods_dir": "",
        "extra_mods_dirs": [],
        "launch_method": "auto",
        # Arguments de lancement (0.3), cochés par version.
        "launch_args": {"skip_start_videos": False, "cheats": False},
        # Dernières valeurs proposées par la détection, pour savoir si un
        # champ a été personnalisé (règle de préremplissage 4.13).
        "auto": {"game_exe": "", "user_dir": "", "mods_dir": ""},
    }


def default_settings() -> dict[str, Any]:
    return {
        "schema": SETTINGS_SCHEMA,
        "language": None,
        "theme": DEFAULT_THEME,
        "theme_loop": False,
        "light_effects": True,
        "reduce_motion": None,
        "active_version": "FS25",
        "downloads_dir": "",
        "scan_downloads_at_start": True,
        "internet_access": True,
        "show_notice_at_start": True,
        "welcome_done": False,
        # Tour guidé (0.9.0) : ampoule mise en évidence une seule fois.
        "tour_hint_shown": False,
        "minimize_on_launch": True,
        # Zone de notification (0.2.1)
        "close_to_tray": True,
        "focus_after_game": True,
        "tray_hint_shown": False,
        "first_detection_done": False,
        # Technique de la fenêtre sans cadre :
        # native | script | thin
        "window_mode": "native",
        "window": {"x": None, "y": None, "width": None, "height": None, "maximized": False},
        "versions": {},
        "anomalies": {"hidden_types": [], "hidden_folders": {}, "seen": {}},
        # Contrôle de l'override (3.5, 0.3) : dossier inconnu laissé tel quel
        # (« Ne rien faire »), par version.
        "override_ignored": {},
        # Téléchargements (4.8, 0.4) : fichiers à ne plus proposer (nom, taille,
        # date) et intégrations reportées à la fermeture du jeu.
        "downloads_ignored": [],
        "downloads_postponed": [],
        # Mode démonstration (14.2, 0.3) : chemins des versions dans le dossier
        # de démonstration ; les vrais chemins (« versions ») restent intacts.
        "demo": {"active": False, "versions": {}, "saved_active_version": None, "offered": False},
    }


def _merge_defaults(data: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Complète `data` avec les clés manquantes de `defaults` (récursif)."""
    out = copy.deepcopy(defaults)
    for key, value in data.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _merge_defaults(value, out[key])
        else:
            out[key] = value
    return out


class Settings:
    """Réglages persistants, partagés entre les fils d'exécution."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings_path()
        self._lock = threading.RLock()
        self._data: dict[str, Any] = default_settings()
        # « Ne plus utiliser FS Passion » (0.7.0) : une fois settings.json
        # supprimé à la demande de l'utilisateur, il n'est plus jamais réécrit.
        self.frozen = False
        # Fichier illisible resté en place (mise de côté impossible) : aucune
        # écriture tant qu'il n'est pas mis de côté, pour ne pas l'écraser.
        self._blocked = False
        self.load()

    # -- lecture / écriture du fichier --------------------------------------

    def load(self) -> None:
        with self._lock:
            self._blocked = False
            if not self.path.exists():
                self._data = default_settings()
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
                if not isinstance(raw, dict):
                    raise ValueError("format inattendu")
            except (OSError, ValueError) as exc:
                # Fichier corrompu : on le met de côté et on repart des valeurs
                # par défaut (jamais de plantage silencieux, cf. chapitre 6).
                stamp = time.strftime("%Y%m%d-%H%M%S")
                broken = self.path.with_name(f"settings.json.illisible-{stamp}")
                try:
                    self.path.replace(broken)
                    log.error("settings.json illisible (%s), mis de côté : %s", exc, broken)
                except OSError as set_aside_exc:
                    self._blocked = True
                    log.error("settings.json illisible (%s), non mis de côté (%s)", exc, set_aside_exc)
                self._data = default_settings()
                return
            for key in OBSOLETE_KEYS:
                raw.pop(key, None)
            if raw.get("theme") in RENAMED_THEMES:
                raw["theme"] = RENAMED_THEMES[raw["theme"]]
            self._data = _merge_defaults(raw, default_settings())
            for vid, cfg in list(self._data.get("versions", {}).items()):
                self._data["versions"][vid] = _merge_defaults(cfg or {}, default_version_cfg())

    def save(self) -> None:
        with self._lock:
            if self.frozen:
                return
            if self._blocked:
                log.error("Réglages non enregistrés : settings.json illisible non mis de côté (%s)", self.path)
                return
            fsutil.atomic_write_json(self.path, self._data)

    # -- accès ---------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return copy.deepcopy(self._data.get(key, default))

    def set(self, key: str, value: Any, save: bool = True) -> None:
        with self._lock:
            self._data[key] = value
            if save:
                self.save()

    def update(self, patch: dict[str, Any], save: bool = True) -> None:
        with self._lock:
            for key, value in patch.items():
                self._data[key] = value
            if save:
                self.save()

    def _versions_key(self) -> dict[str, Any]:
        """Configurations des versions en vigueur : les vraies, ou celles du
        mode démonstration (qui ne touche jamais aux vraies)."""
        demo = self._data.get("demo") or {}
        if demo.get("active"):
            return demo.setdefault("versions", {})
        return self._data.setdefault("versions", {})

    def demo_active(self) -> bool:
        with self._lock:
            return bool((self._data.get("demo") or {}).get("active"))

    def version(self, vid: str) -> dict[str, Any]:
        """Configuration d'une version (copie), avec ses valeurs par défaut."""
        with self._lock:
            cfg = self._versions_key().get(vid)
            if cfg is None:
                cfg = default_version_cfg()
            return copy.deepcopy(_merge_defaults(cfg, default_version_cfg()))

    def modify_version(self, vid: str, fn: Any, save: bool = True) -> Any:
        """Lit, modifie et écrit la configuration d'une version d'un seul bloc
        (0.7.1). `fn(cfg)` reçoit la configuration actuelle et renvoie
        (nouvelle_cfg, résultat). Évite qu'une écriture faite pendant le calcul
        (détection au démarrage, case cochée) soit écrasée par une copie ancienne."""
        with self._lock:
            cfg, result = fn(self.version(vid))
            self._versions_key()[vid] = cfg
            if save:
                self.save()
            return result

    def update_version(self, vid: str, patch: dict[str, Any], save: bool = True) -> dict[str, Any]:
        with self._lock:
            cfg = self.version(vid)
            for key, value in patch.items():
                if key == "auto" and isinstance(value, dict):
                    cfg["auto"].update(value)
                else:
                    cfg[key] = value
            self._versions_key()[vid] = cfg
            if save:
                self.save()
            return copy.deepcopy(cfg)

    def anomalies_cfg(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data["anomalies"])

    def set_anomalies_cfg(self, cfg: dict[str, Any]) -> None:
        with self._lock:
            self._data["anomalies"] = cfg
            self.save()
