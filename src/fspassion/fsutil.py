"""Outils de fichiers : écritures atomiques, JSON, comparaison de chemins.

Règle : aucune écriture ne laisse un fichier à moitié écrit. On écrit
toujours dans un fichier temporaire du même dossier, puis on le substitue d'un
coup au fichier final (os.replace est atomique sur un même volume).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"


def _replace(src: str, dst: Path, tries: int = 6) -> None:
    """os.replace, réessayé quelques fois sous Windows : un antivirus,
    l'indexation ou une lecture en cours tiennent parfois le fichier visé un
    court instant (« Accès refusé », WinError 5)."""
    for attempt in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if os.name != "nt" or attempt == tries - 1:
                raise
            time.sleep(0.05 * (attempt + 1))


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Écrit `data` dans `path` de façon atomique."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        _replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def json_bytes(obj: Any) -> bytes:
    """Objet JSON en UTF-8, indenté (lisible dans un éditeur de texte)."""
    return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")


def atomic_write_json(path: Path, obj: Any) -> None:
    """Écrit un objet JSON (UTF-8, indenté) de façon atomique."""
    atomic_write_bytes(path, json_bytes(obj))


def read_json_strict(path: Path) -> Any:
    """Lit un fichier JSON. Lève OSError ou ValueError s'il est absent ou illisible."""
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def read_json(path: Path, default: Any = None) -> Any:
    """Lit un fichier JSON. Renvoie `default` s'il est absent ou illisible."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as exc:
        log.warning("JSON illisible %s : %s", path, exc)
        return default


def norm_path(p: str | os.PathLike[str] | None) -> str:
    """Forme normalisée d'un chemin, pour les comparaisons.

    Sous Windows : casse ignorée, barres obliques unifiées. Aucun accès disque.
    """
    if not p:
        return ""
    s = os.path.normpath(str(p))
    if IS_WINDOWS:
        s = os.path.normcase(s)
    return s.rstrip("\\/") or s


def same_path(a: str | os.PathLike[str] | None, b: str | os.PathLike[str] | None) -> bool:
    """Vrai si deux chemins désignent le même emplacement (sans accès disque)."""
    if not a or not b:
        return False
    return norm_path(a) == norm_path(b)


def is_within(child: Path, parent: Path) -> bool:
    """Vrai si `child` est dans `parent` (après résolution des chemins)."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def human_size(n: int) -> dict[str, Any]:
    """Taille à afficher : valeur et unité (l'unité est traduite par l'interface)."""
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    return {"value": round(v, 1 if i else 0), "unit": units[i]}


# --------------------------------------------------------------------------
# Déplacement vérifié d'un fichier (intégration des téléchargements,
# dossier pending_downloads)
# --------------------------------------------------------------------------

class MoveError(OSError):
    """Déplacement impossible ; `key` est une clé de langue."""

    def __init__(self, key: str, detail: str = "") -> None:
        super().__init__(detail or key)
        self.key = key
        self.detail = detail


def is_cross_device(exc: OSError) -> bool:
    """L'erreur vient d'un déplacement entre deux disques (os.rename impossible)."""
    return getattr(exc, "winerror", None) == 17 or exc.errno == 18



def relocate(src: Path, dst: Path, verify: Any = None) -> str:
    """Déplace un fichier ou un dossier vers `dst` (qui ne doit pas exister).

    Même disque : simple changement de nom. Autre disque (stockage sur
    plusieurs disques) : copie vérifiée d'un fichier (move_file). Un dossier ne
    traverse jamais les disques : MoveError (rien n'est touché).
    """
    src, dst = Path(src), Path(dst)
    if os.path.lexists(dst):
        raise MoveError("move.exists", str(dst))
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(src, dst)
        return "renamed"
    except OSError as exc:
        if not is_cross_device(exc):
            raise MoveError("move.failed", str(exc)) from exc  # même erreur que move_file
        if os.path.islink(src) or not os.path.isfile(src):
            raise MoveError("move.failed", str(exc)) from exc
    return move_file(src, dst, verify)


def move_file(src: Path, dst: Path, verify: Any = None) -> str:
    """Déplace `src` vers `dst`, qui ne doit pas exister.

    - même disque : simple changement de nom, instantané ;
    - autre disque : contrôle de l'espace libre, copie dans un fichier temporaire
      du dossier cible, vérification (taille, puis `verify(chemin)` s'il est
      donné), bascule vers le nom final, et seulement ensuite suppression de
      l'original. Une copie interrompue ne laisse qu'un fichier temporaire.

    Renvoie « renamed » ou « copied ». Lève MoveError.
    """
    import shutil

    src, dst = Path(src), Path(dst)
    if os.path.lexists(dst):
        raise MoveError("move.exists", str(dst))
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(src, dst)
        return "renamed"
    except OSError as exc:
        if not is_cross_device(exc):
            raise MoveError("move.failed", str(exc)) from exc
    size = src.stat().st_size
    try:
        free = shutil.disk_usage(dst.parent).free
    except OSError:
        free = None
    if free is not None and free < size + 64 * 1024 * 1024:
        raise MoveError("move.no_space", str(dst.parent))
    # Nom temporaire unique dans le dossier cible : un fichier homonyme déjà
    # présent n'est jamais écrasé.
    fd, tmp_name = tempfile.mkstemp(prefix=f".fsp-{dst.name}.", suffix=".tmp", dir=str(dst.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        shutil.copyfile(src, tmp)
        try:
            shutil.copystat(src, tmp)
        except OSError:
            pass
        if tmp.stat().st_size != size or (verify is not None and not verify(tmp)):
            raise MoveError("move.check_failed", str(dst))
        if os.path.lexists(dst):
            raise MoveError("move.exists", str(dst))
        os.replace(tmp, dst)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    try:
        os.unlink(src)
    except OSError as exc:
        # La copie est en place et vérifiée : l'original reste, signalé.
        log.warning("Original non supprimé après copie %s : %s", src, exc)
    return "copied"
