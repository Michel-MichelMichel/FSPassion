"""Dossiers de stockage multiples.

Le chemin n° 1 (`mods_dir`) est le stockage principal : il porte FSPassion\\ et
les dossiers de parties. Jusqu'à deux dossiers supplémentaires (chemins n° 2 et
n° 3), en général sur d'autres disques, ne contiennent que des mods : FS Passion
n'y écrit jamais rien d'autre.

Dans un dossier de partie, le lien vers un mod dépend de son stockage (3.6) :
- mod non compressé (dossier) : jonction, quel que soit le disque ;
- mod .zip du disque principal (ou d'un stockage supplémentaire sur le même
  disque) : hardlink, aucun droit nécessaire ;
- mod .zip d'un autre disque : lien symbolique. Windows ne l'autorise qu'avec
  le Mode développeur ou les droits administrateur.

Sans ces droits, les chemins n° 2 et n° 3 restent enregistrés : leurs mods sont
listés, mais ceux qui demandent un lien symbolique n'entrent dans aucune partie
(« blocked » dans le résultat d'« Appliquer »).
"""

from __future__ import annotations

import logging
import tempfile
import threading
from pathlib import Path
from typing import Any

from fspassion import fsutil, gamepaths, links, winapi
from fspassion.gamepaths import VersionPaths

log = logging.getLogger(__name__)

MAX_EXTRA = 2  # chemins n° 2 et n° 3

_lock = threading.Lock()
_symlinks: bool | None = None


# --------------------------------------------------------------------------
# Liens symboliques : droits
# --------------------------------------------------------------------------

def symlinks_allowed(refresh: bool = False) -> bool:
    """Les liens symboliques sont-ils possibles avec les droits actuels ? Essai
    réel (créé puis retiré dans le dossier temporaire), mémorisé jusqu'au
    prochain `refresh` : le Mode développeur peut être activé entre-temps."""
    global _symlinks
    with _lock:
        if _symlinks is None or refresh:
            _symlinks = links.can_symlink(Path(tempfile.gettempdir()) / "FSPassion")
            log.info(
                "Liens symboliques %s (administrateur : %s, Mode développeur : %s)",
                "possibles" if _symlinks else "refusés par Windows",
                "oui" if winapi.is_admin() else "non",
                "oui" if winapi.developer_mode() else "non",
            )
        return _symlinks


def set_symlinks_allowed(value: bool | None) -> None:
    """Pour les tests : impose (ou oublie, avec None) le résultat de l'essai."""
    global _symlinks
    with _lock:
        _symlinks = value


def active_extras(vp: VersionPaths) -> list[tuple[int, Path]]:
    """Stockages supplémentaires existants : (numéro dans vp.storages, chemin)."""
    out = []
    for i, p in enumerate(vp.storages):
        if i > 0 and p.is_dir():
            out.append((i, p))
    return out


def on_other_disk(vp: VersionPaths, path: Path) -> bool:
    """Le dossier `path` est-il sur un autre disque que le stockage principal ?
    (dans le doute, oui : un lien symbolique sera tenté)."""
    if vp.mods_dir is None or fsutil.same_path(path, vp.mods_dir):
        return False
    return winapi.same_volume(path, vp.mods_dir) is not True


def needs_symlinks(vp: VersionPaths) -> bool:
    """Au moins un stockage supplémentaire est sur un autre disque."""
    return any(on_other_disk(vp, p) for _, p in active_extras(vp))


def rights(needed: bool, refresh: bool = False) -> dict[str, Any]:
    """État des droits pour les liens symboliques (4.13, 4.20). L'essai réel
    n'est fait que s'il est utile (`needed`) ou demandé (`refresh`)."""
    ok: bool | None = symlinks_allowed(refresh) if (needed or refresh) else _symlinks
    return {
        "needed": needed,
        "symlinks": ok,
        "admin": winapi.is_admin(),
        "dev_mode": winapi.developer_mode(),
        "standard_user": winapi.is_standard_user(),
        "run_as_admin": winapi.run_as_admin_flag(),
        "windows": winapi.IS_WINDOWS,
    }


# --------------------------------------------------------------------------
# Chemins n° 2 et n° 3 : nettoyage et contrôle
# --------------------------------------------------------------------------

def clean_extra(values: Any) -> list[str]:
    """Liste saisie → au plus deux chemins non vides, sans guillemets."""
    if not isinstance(values, list):
        raise ValueError("liste attendue")
    out: list[str] = []
    for v in values:
        if not isinstance(v, str):
            raise ValueError("chemin attendu")
        s = v.strip().strip('"').strip()
        if s:
            out.append(s)
    if len(out) > MAX_EXTRA:
        raise ValueError("trop de chemins")
    return out


def overlap_reason(vp: VersionPaths, index: int) -> str | None:
    """Le chemin n° `index + 2` chevauche-t-il le stockage principal, le dossier
    FSPassion\\ ou un chemin précédent ? (calcul sur les chemins, sans disque)"""
    return gamepaths.extra_overlap(vp.mods_dir, vp.extra_mods_dirs, index)


def check_extra(vp: VersionPaths, index: int) -> dict[str, Any]:
    """Contrôle du chemin n° `index + 2` (`index` : 0 ou 1 dans extra_mods_dirs)."""
    try:
        p = vp.extra_mods_dirs[index]
    except IndexError:
        return {"level": "empty", "key": "path.empty", "params": {}}

    def st(level: str, key: str, **params: Any) -> dict[str, Any]:
        return {"level": level, "key": key, "params": params}

    value = str(p)
    reason = overlap_reason(vp, index)
    if reason:
        return st("error", reason)
    if not p.is_dir():
        return st("error", "path.not_found")
    if winapi.is_in_onedrive(value):
        return st("warn", "path.onedrive")
    if not on_other_disk(vp, p):
        return st("ok", "path.storage_same_disk")
    return st("ok", "path.storage_other_disk")


