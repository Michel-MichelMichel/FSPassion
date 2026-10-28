"""« Ne plus utiliser FS Passion », et désinstallation (4.18, version 0.7.0).

Le même code sert aux deux chemins :
A. le bouton « Ne plus utiliser FS Passion » des paramètres ;
B. le désinstalleur Windows, qui lance « FSPassion.exe --uninstall ».

Étapes, pour chaque version du jeu configurée (jeu fermé) :
1. la ligne d'override retrouve sa valeur d'origine, lue dans
   gameSettings.xml.original.bak ; sans cette sauvegarde (ou si la ligne
   n'existait pas), l'override est désactivé (active="false") ;
2. les dossiers de parties sont vidés lien par lien, puis supprimés : un
   fichier physique trouvé dedans est d'abord rapatrié, jamais effacé ;
3. sur demande seulement : parties.json, caches, réglages, journaux et
   langues personnelles sont supprimés.

Jamais touchés : les dossiers de stockage des mods, et les dossiers « Old
versions » et « Recovered », qui contiennent des mods.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from fspassion import config, fsutil, gamesettings, links
from fspassion.gamepaths import VersionPaths

log = logging.getLogger(__name__)

# Ce que l'utilisateur peut choisir de supprimer en plus (étape 5).
OPTIONS = ("parties", "caches", "settings", "logs", "langs")

# Fichiers de FS Passion dans FSPassion\<version>\ (choix « parties »).
PARTY_FILES = ("parties.json", "liens.json", "journal_operations.json", "a_confirmer.json")
PARTY_PATTERNS = ("parties.json.bak*", "parties.json.illisible-*", "parties.json.tmp*")


# --------------------------------------------------------------------------
# Override
# --------------------------------------------------------------------------

def override_plan(vp: VersionPaths) -> dict[str, Any]:
    """Ce que deviendra la ligne d'override : « restore » (valeur d'origine),
    « deactivate » (active="false"), « none » (rien à faire) ou « missing »
    (gameSettings.xml introuvable)."""
    gs = vp.gamesettings
    if gs is None or not gs.is_file():
        return {"action": "missing"}
    current = gamesettings.read_override(gs)
    bak = gamesettings.original_backup_path(gs)
    if bak.is_file():
        ov = gamesettings.read_override(bak)
        if ov is not None and ov.found:
            directory = ov.directory or ""
            active = bool(ov.active)
            native = gamesettings.override_dir_to_path(directory)
            if native and vp.fsp_dir is not None and _within(Path(native), vp.fsp_dir):
                # Sauvegarde prise alors que le jeu chargeait déjà un dossier de
                # FS Passion : on rend au jeu le dossier de mods.
                if vp.mods_dir is not None:
                    return {"action": "restore", "directory": str(vp.mods_dir), "active": True, "fixed": True}
                return {"action": "deactivate", "directory": directory, "active": False}
            return {"action": "restore", "directory": directory, "active": active}
    if current is None or not current.found:
        return {"action": "none"}
    if current.active is False:
        return {"action": "none"}
    # Pas de sauvegarde d'origine, ou ligne absente à l'origine : désactivé.
    directory = str(vp.mods_dir) if vp.mods_dir is not None else (current.directory or "")
    return {"action": "deactivate", "directory": directory, "active": False}


def _within(child: Path, parent: Path) -> bool:
    try:
        return fsutil.is_within(Path(os.path.normpath(child)), Path(os.path.normpath(parent)))
    except (OSError, ValueError):
        return False


def restore_override(vp: VersionPaths) -> dict[str, Any]:
    plan = override_plan(vp)
    if plan["action"] in ("restore", "deactivate"):
        assert vp.gamesettings is not None
        gamesettings.write_override(vp.gamesettings, plan["directory"], plan["active"])
        log.info("Override %s : %s (%s)", vp.version.id, plan["action"], gamesettings.game_path(plan["directory"]))
    return plan


# --------------------------------------------------------------------------
# Suppressions prudentes
# --------------------------------------------------------------------------

def remove_tree(path: Path) -> None:
    """Supprime un dossier de FS Passion sans jamais traverser un lien : un lien
    symbolique ou une jonction trouvé dedans est retiré comme un lien (I10)."""
    if not os.path.lexists(path):
        return
    if links.is_link(path):
        links.remove_link(path)
        return
    if path.is_file():
        path.unlink()
        return
    for item in list(path.iterdir()):
        if links.is_link(item):
            links.remove_link(item)
        elif item.is_dir():
            remove_tree(item)
        else:
            try:
                item.unlink()
            except PermissionError:
                os.chmod(item, 0o666)
                item.unlink()
    path.rmdir()


def remove_quietly(path: Path) -> bool:
    try:
        remove_tree(path)
        return True
    except OSError as exc:
        log.warning("Suppression impossible : %s (%s)", path, exc)
        return False


def remove_if_empty(path: Path) -> bool:
    try:
        if path.is_dir() and not links.is_link(path) and not any(path.iterdir()):
            path.rmdir()
            return True
    except OSError:
        pass
    return False


def _count_files(folder: Path) -> int:
    n = 0
    try:
        for _root, _dirs, files in os.walk(folder):
            n += len(files)
    except OSError:
        pass
    return n


def kept_folders(fsp: Path) -> list[dict[str, Any]]:
    """Dossiers qui contiennent des mods mis de côté : jamais supprimés."""
    from fspassion import apply  # import tardif : apply dépend de beaucoup de modules

    out = []
    for name in (apply.OLD_VERSIONS, apply.RECOVERED):
        p = fsp / name
        if p.is_dir() and not links.is_link(p):
            n = _count_files(p)
            if n:
                out.append({"name": name, "path": str(p), "files": n})
    return out


def remove_version_data(fsp: Path, parties: bool, caches: bool) -> dict[str, Any]:
    """FSPassion\\<version>\\ : fichiers des parties et cache, selon les choix.
    « Old versions » et « Recovered » restent toujours."""
    removed: list[str] = []
    if parties:
        for name in PARTY_FILES:
            p = fsp / name
            if p.is_file() and remove_quietly(p):
                removed.append(name)
        for pattern in PARTY_PATTERNS:
            for p in fsp.glob(pattern):
                if p.is_file() and remove_quietly(p):
                    removed.append(p.name)
    if caches:
        cache = fsp / "cache"
        if os.path.lexists(cache) and remove_quietly(cache):
            removed.append("cache")
    kept = kept_folders(fsp)
    gone = remove_if_empty(fsp)
    if gone:
        remove_if_empty(fsp.parent)  # FSPassion\ s'il ne contient plus rien
    return {"removed": removed, "kept": kept, "folder_removed": gone}


# --------------------------------------------------------------------------
# Données de l'application
# --------------------------------------------------------------------------

def app_data_now(options: set[str]) -> list[str]:
    """Supprime tout de suite ce qui n'est pas ouvert par FS Passion.
    Les journaux et les données de la fenêtre le sont jusqu'à la fermeture :
    voir exit_paths()."""
    done = []
    roaming = config.roaming_dir()
    local = config.local_dir()
    if "settings" in options:
        # Les sauvegardes « avant-import » (roaming\backups) ne sont pas des
        # réglages : elles restent.
        targets = [config.settings_path()]
        targets += list(roaming.glob("settings.json.illisible-*"))
        targets += list(roaming.glob("settings.json.tmp*"))
        # Toutes les cibles sont tentées, même après un échec.
        results = [remove_quietly(p) for p in targets if os.path.lexists(p)]
        if all(results):
            done.append("settings")
    if "langs" in options:
        if remove_quietly(config.user_lang_dir()):
            done.append("langs")
    if "caches" in options:
        ok = True
        for p in (config.dlc_cache_dir(), local / "demo"):
            if os.path.lexists(p):
                ok = remove_quietly(p) and ok
        if ok:
            done.append("caches")
    return done


def exit_paths(options: set[str]) -> list[Path]:
    """À supprimer à la fermeture de FS Passion, une fois les fichiers libérés."""
    out: list[Path] = []
    if "logs" in options:
        out.append(config.logs_dir())
    if "caches" in options:
        out.append(config.webview_storage_dir())
    return out


def finish_at_exit(paths: list[Path], wait_s: float = 4.0) -> None:
    """Appelé par app.py après la fermeture de la fenêtre et des journaux.
    Les fichiers peuvent rester verrouillés un instant (WebView2) : on réessaie."""
    deadline = time.monotonic() + wait_s
    pending = [p for p in paths if os.path.lexists(p)]
    while pending:
        pending = [p for p in pending if os.path.lexists(p) and not _try_remove(p)]
        if not pending or time.monotonic() >= deadline:
            break
        time.sleep(0.3)
    for base in (config.roaming_dir(), config.local_dir()):
        remove_if_empty(base)


def _try_remove(p: Path) -> bool:
    try:
        remove_tree(p)
        return True
    except OSError as exc:
        # Pas de repli : rmtree contournerait remove_tree, qui ne suit pas les
        # liens. Les essais suivants de finish_at_exit réessaient.
        log.warning("Suppression à la fermeture impossible : %s (%s)", p, exc)
        return not os.path.lexists(p)


def uninstaller() -> Path | None:
    """Désinstalleur Inno Setup (0.8), en mode installé seulement."""
    if not config.is_frozen() or config.is_portable():
        return None
    p = config.exe_dir() / "unins000.exe"
    return p if p.is_file() else None
