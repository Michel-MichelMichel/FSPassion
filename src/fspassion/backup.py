"""Exporter et importer la configuration.

Un fichier d'export (« fspassion-export-AAAA-MM-JJ.json ») contient :
- les réglages de FS Passion, sans ce qui ne vaut que pour cette installation
  (taille de la fenêtre, mode démonstration…) ;
- le parties.json de chaque version du jeu (parties, mods communs) ;
- les anomalies masquées (elles font partie des réglages).

Il ne contient aucun mod : seulement leurs noms. Les mods référencés mais
absents de l'autre PC apparaissent comme « mods manquants » sur les parties.

L'import se fait en deux temps : lecture et contrôle du fichier (aperçu),
puis application après confirmation. L'option « Conserver vos chemins
actuels » (cochée par défaut) garde tous les chemins de ce PC : seuls les
parties, les mods communs et les réglages neutres (langue, thème, options)
sont repris.
"""

from __future__ import annotations

import copy
import json
import logging
import time
from pathlib import Path
from typing import Any

from fspassion import __version__, config, fsutil, parties, versions

log = logging.getLogger(__name__)

FORMAT = "fspassion-export"
SCHEMA = 1
MAX_BYTES = 20 * 1024 * 1024
KEEP_BACKUPS = 10

# Réglages jamais exportés : ils ne valent que pour cette installation.
NOT_EXPORTED = (
    "schema", "window", "window_mode", "demo", "tray_hint_shown", "first_detection_done",
    "welcome_done", "downloads_postponed",
)
# Réglages « neutres » : repris même quand les chemins actuels sont conservés.
NEUTRAL = (
    "language", "theme", "theme_loop", "light_effects", "reduce_motion", "active_version",
    "scan_downloads_at_start", "internet_access", "show_notice_at_start", "minimize_on_launch",
    "close_to_tray", "focus_after_game", "anomalies",
)
# Réglages liés aux dossiers de ce PC : repris seulement sans « Conserver vos chemins ».
PATH_KEYS = ("versions", "downloads_dir", "override_ignored", "downloads_ignored")


class BackupError(Exception):
    """Erreur prévue, avec une clé de langue."""

    def __init__(self, key: str, status: int = 400, **params: Any) -> None:
        super().__init__(key)
        self.key = key
        self.status = status
        self.params = params


def default_file_name() -> str:
    return f"fspassion-export-{time.strftime('%Y-%m-%d')}.json"


def backups_dir() -> Path:
    """Sauvegardes automatiques faites avant chaque import."""
    return config.roaming_dir() / "backups"


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------

def exported_settings(snapshot: dict[str, Any]) -> dict[str, Any]:
    out = {k: copy.deepcopy(v) for k, v in snapshot.items() if k not in NOT_EXPORTED}
    for key in config.OBSOLETE_KEYS:
        out.pop(key, None)
    return out


def build_export(snapshot: dict[str, Any], parties_by_version: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "schema": SCHEMA,
        "app_version": __version__,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "settings": exported_settings(snapshot),
        "parties": copy.deepcopy(parties_by_version),
    }


def write_export(path: Path, data: dict[str, Any]) -> None:
    fsutil.atomic_write_json(path, data)
    log.info("Configuration exportée : %s", path)


def write_safety_backup(data: dict[str, Any]) -> Path:
    """Sauvegarde automatique de l'état actuel, avant un import. Les 10
    dernières sont gardées dans %APPDATA%\\FSPassion\\backups\\."""
    folder = backups_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"avant-import-{time.strftime('%Y%m%d-%H%M%S')}.json"
    n = 1
    while path.exists():
        n += 1
        path = folder / f"avant-import-{time.strftime('%Y%m%d-%H%M%S')}-{n}.json"
    fsutil.atomic_write_json(path, data)
    olds = sorted(folder.glob("avant-import-*.json"), key=lambda p: p.name)
    for old in olds[:-KEEP_BACKUPS]:
        try:
            old.unlink()
        except OSError:
            pass
    log.info("Sauvegarde avant import : %s", path)
    return path


# --------------------------------------------------------------------------
# Lecture et contrôle d'un fichier d'export
# --------------------------------------------------------------------------

def _clean_version_cfg(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    base = config.default_version_cfg()
    out = copy.deepcopy(base)
    for key in ("game_exe", "user_dir", "mods_dir", "launch_method"):
        if isinstance(raw.get(key), str):
            out[key] = raw[key]
    extra = raw.get("extra_mods_dirs")
    if isinstance(extra, list):
        out["extra_mods_dirs"] = [x for x in extra if isinstance(x, str) and x.strip()][:2]
    args = raw.get("launch_args")
    if isinstance(args, dict):
        out["launch_args"] = {k: bool(args.get(k)) for k in base["launch_args"]}
    auto = raw.get("auto")
    if isinstance(auto, dict):
        out["auto"] = {k: auto[k] if isinstance(auto.get(k), str) else "" for k in base["auto"]}
    if out["launch_method"] not in ("auto", "platform", "exe"):
        out["launch_method"] = "auto"
    return out


def clean_settings(raw: Any) -> dict[str, Any]:
    """Réglages d'un fichier d'export : seules les clés connues, du bon type."""
    if not isinstance(raw, dict):
        return {}
    defaults = config.default_settings()
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key in NOT_EXPORTED or key in config.OBSOLETE_KEYS or key not in defaults:
            continue
        default = defaults[key]
        if key == "versions":
            if isinstance(value, dict):
                vers = {}
                for vid, cfg in value.items():
                    clean = _clean_version_cfg(cfg)
                    if versions.get(str(vid)) is not None and clean is not None:
                        vers[str(vid)] = clean
                out[key] = vers
            continue
        if key == "anomalies":
            if isinstance(value, dict):
                seen_raw = value.get("seen")
                # Anomalies déjà vues : listes de textes par version.
                seen = {str(k): [x for x in v if isinstance(x, str)]
                        for k, v in seen_raw.items() if isinstance(v, list)} if isinstance(seen_raw, dict) else {}
                out[key] = {
                    "hidden_types": [x for x in value.get("hidden_types") or [] if isinstance(x, str)],
                    "hidden_folders": {str(k): [x for x in v if isinstance(x, str)]
                                       for k, v in (value.get("hidden_folders") or {}).items()
                                       if isinstance(v, list)},
                    "seen": seen,
                }
            continue
        if default is None:
            if value is None or isinstance(value, (bool, str)):
                out[key] = value
            continue
        if isinstance(default, bool):
            if isinstance(value, bool):
                out[key] = value
            continue
        if isinstance(value, type(default)):
            out[key] = copy.deepcopy(value)
    if "active_version" in out and versions.get(out["active_version"]) is None:
        del out["active_version"]
    return out


def read_export(path: Path) -> dict[str, Any]:
    """Lit et contrôle un fichier d'export. Lève BackupError s'il est inutilisable."""
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise BackupError("backup.unreadable", path=str(path)) from exc
    if size > MAX_BYTES:
        raise BackupError("backup.too_big", path=str(path))
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise BackupError("backup.unreadable", path=str(path)) from exc
    if not isinstance(raw, dict) or raw.get("format") != FORMAT:
        raise BackupError("backup.not_export", path=str(path))
    schema = raw.get("schema")
    if not isinstance(schema, int) or schema < 1:
        raise BackupError("backup.not_export", path=str(path))
    if schema > SCHEMA:
        raise BackupError("backup.too_new", version=str(raw.get("app_version") or "?"))
    data_parties: dict[str, dict[str, Any]] = {}
    for vid, content in (raw.get("parties") or {}).items() if isinstance(raw.get("parties"), dict) else []:
        v = versions.get(str(vid))
        if v is None or not v.has_override:
            continue
        try:
            data_parties[v.id] = parties.validate(content, v.id)
        except ValueError as exc:
            log.warning("Parties %s de l'export ignorées : %s", vid, exc)
    return {
        "app_version": str(raw.get("app_version") or ""),
        "created": str(raw.get("created") or ""),
        "settings": clean_settings(raw.get("settings")),
        "parties": data_parties,
    }


def preview(data: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Ce que contient le fichier, pour la fenêtre de confirmation."""
    rows = []
    for vid, content in data["parties"].items():
        v = versions.require(vid)
        rows.append({
            "id": vid,
            "name": v.name,
            "parties": len(content.get("parties") or []),
            "common": len(content.get("common_mods") or []),
            "names": sorted((p["name"] for p in content.get("parties") or []), key=str.lower)[:12],
        })
    order = [v.id for v in versions.all_versions()]
    rows.sort(key=lambda r: order.index(r["id"]) if r["id"] in order else len(order))
    imported_versions = data["settings"].get("versions") or {}
    current_versions = current.get("versions") or {}
    paths_differ = any(
        not fsutil.same_path((cfg or {}).get("mods_dir") or "", (current_versions.get(vid) or {}).get("mods_dir") or "")
        for vid, cfg in imported_versions.items() if (cfg or {}).get("mods_dir")
    )
    return {
        "app_version": data["app_version"],
        "created": data["created"],
        "versions": rows,
        "has_paths": bool(imported_versions),
        "paths_differ": paths_differ,
    }


def settings_patch(data: dict[str, Any], keep_paths: bool) -> dict[str, Any]:
    """Réglages à reprendre du fichier."""
    imported = data["settings"]
    keys = NEUTRAL if keep_paths else NEUTRAL + PATH_KEYS
    return {k: copy.deepcopy(imported[k]) for k in keys if k in imported}
