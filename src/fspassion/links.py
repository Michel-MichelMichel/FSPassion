"""Les liens d'un dossier de partie (3.6) et leur inventaire.

Trois sortes de liens :
- hardlink (« liaison permanente ») : un second nom pour le même fichier. Pour
  les mods .zip du disque principal. Aucun droit particulier ;
- jonction : un panneau indicateur vers un dossier. Pour les mods non
  compressés (dossiers). Aucun droit particulier ;
- lien symbolique : pour les mods .zip d'un dossier de stockage situé sur un
  autre disque (0.6, 4.20). Il demande le Mode développeur de Windows ou les
  droits administrateur (storage.py).

Sous Linux (tests automatiques), une jonction est remplacée par un lien
symbolique vers le dossier : le comportement vérifié est le même.

Invariant : un lien se supprime comme un lien. On ne suit jamais une
jonction ou un lien symbolique jusqu'à sa cible, et on ne supprime jamais un
fichier qui n'est pas un de nos liens. Aucune suppression récursive
n'est utilisée sur un dossier de partie.

Inventaire (liens.json, 3.6) : pour chaque dossier de partie, le nom de chaque
lien créé et l'identifiant sur le disque du fichier visé (volume + numéro de
fichier). Il permet de reconnaître, dans un dossier de partie :
- un lien valide (même identifiant que le mod actuel du dossier de stockage) ;
- un lien orphelin (identifiant connu, mais le mod de stockage a été remplacé) ;
- un fichier nouveau (identifiant inconnu : déposé par le jeu).
"""

from __future__ import annotations

import logging
import os
import stat
import sys
import threading
from pathlib import Path
from typing import Any

from fspassion import fsutil

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"
SCHEMA = 1


class LinkError(Exception):
    """Lien impossible à créer, avec une clé de langue (I7)."""

    def __init__(self, key: str, **params: Any) -> None:
        super().__init__(key)
        self.key = key
        self.params = params


# --------------------------------------------------------------------------
# Nature d'un élément (sans jamais suivre un lien)
# --------------------------------------------------------------------------

def is_junction(p: Path) -> bool:
    fn = getattr(os.path, "isjunction", None)  # Python 3.12
    if fn is not None:
        try:
            return bool(fn(p))
        except OSError:
            return False
    if not IS_WINDOWS:
        return False
    try:
        st = os.lstat(p)
    except OSError:
        return False
    tag = getattr(st, "st_reparse_tag", 0)
    return bool(getattr(st, "st_file_attributes", 0) & 0x400) and tag == 0xA0000003


def is_link(p: Path) -> bool:
    """Lien symbolique ou jonction (jamais un fichier ou un dossier ordinaire)."""
    return os.path.islink(p) or is_junction(p)


def kind_of(p: Path) -> str:
    """« junction », « symlink », « file », « dir » ou « missing »."""
    if is_junction(p):
        return "junction"
    if os.path.islink(p):
        return "symlink"
    try:
        st = os.lstat(p)
    except OSError:
        return "missing"
    if stat.S_ISDIR(st.st_mode):
        return "dir"
    return "file"


def file_id(p: Path) -> str | None:
    """Identifiant unique du fichier sur le disque (volume:numéro), sans suivre
    de lien. Deux noms d'un même hardlink ont le même identifiant."""
    try:
        st = os.lstat(p)
    except OSError:
        return None
    if not st.st_ino:
        return None
    return f"{st.st_dev}:{st.st_ino}"


def link_count(p: Path) -> int:
    try:
        return int(os.lstat(p).st_nlink)
    except OSError:
        return 0


def link_target(p: Path) -> str | None:
    """Cible d'une jonction ou d'un lien symbolique."""
    try:
        target = os.readlink(p)
    except OSError:
        return None
    if target.startswith("\\\\?\\"):
        target = target[4:]
    return target


# --------------------------------------------------------------------------
# Création et suppression
# --------------------------------------------------------------------------

def make_hardlink(src: Path, dst: Path) -> None:
    try:
        os.link(src, dst)
    except OSError as exc:
        raise LinkError(_link_error_key(exc), name=src.name, detail=str(exc)) from exc


def make_dir_link(src: Path, dst: Path) -> None:
    """Jonction vers un dossier (mod non compressé)."""
    try:
        if IS_WINDOWS:
            import _winapi  # type: ignore[import-not-found]

            _winapi.CreateJunction(str(src), str(dst))
        else:
            os.symlink(src, dst, target_is_directory=True)
    except OSError as exc:
        raise LinkError("apply.junction_failed", name=src.name, detail=str(exc)) from exc


def make_file_symlink(src: Path, dst: Path) -> None:
    """Lien symbolique vers un fichier (mod .zip d'un autre disque, 4.20).

    Sans le Mode développeur de Windows ni les droits administrateur, Windows
    refuse (erreur 1314) : clé « apply.symlink_denied »."""
    try:
        os.symlink(src, dst, target_is_directory=False)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314 or (not IS_WINDOWS and exc.errno == 1):
            raise LinkError("apply.symlink_denied", name=src.name, detail=str(exc)) from exc
        raise LinkError("apply.link_failed", name=src.name, detail=str(exc)) from exc


def can_symlink(folder: Path) -> bool:
    """Essaie de créer (puis retire) un lien symbolique de test dans `folder` :
    vrai si Windows l'accepte avec les droits actuels."""
    import tempfile

    try:
        folder.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix=".fsp-symlink-", dir=str(folder)))
    except OSError:
        return False
    target = tmp / "cible.txt"
    link = tmp / "lien.txt"
    try:
        target.write_bytes(b"FS Passion")
        os.symlink(target, link)
        return True
    except OSError:
        return False
    finally:
        for p in (link, target):
            try:
                if os.path.lexists(p):
                    os.unlink(p)
            except OSError:
                pass
        try:
            tmp.rmdir()
        except OSError:
            pass


def _link_error_key(exc: OSError) -> str:
    # 17 : ERROR_NOT_SAME_DEVICE ; EXDEV ; 1 / 50 : opération non prise en charge
    # par le système de fichiers (exFAT, FAT32…) ; 1142 : trop de liens.
    win = getattr(exc, "winerror", None)
    if win == 17 or exc.errno == 18:
        return "apply.not_same_disk"
    if win in (1, 50) or exc.errno in (1, 95):
        return "apply.no_hardlinks"
    if win == 1142 or exc.errno == 31:
        return "apply.too_many_links"
    if win == 5 or exc.errno == 13:
        return "apply.access_denied"
    return "apply.link_failed"


def remove_link(p: Path) -> None:
    """Supprime un lien COMME un lien (I10) : la cible n'est jamais touchée."""
    if is_junction(p):
        os.rmdir(p)  # retire le point de jonction, jamais le contenu visé
    elif os.path.islink(p):
        # Sous Windows, un lien symbolique vers un dossier porte l'attribut
        # « dossier » et se retire avec rmdir (même si sa cible a disparu).
        attrs = getattr(os.lstat(p), "st_file_attributes", 0)
        if IS_WINDOWS and attrs & 0x10:
            os.rmdir(p)
        else:
            os.unlink(p)
    else:
        raise ValueError(f"pas un lien : {p}")


def remove_hardlink_name(p: Path, expected_id: str) -> bool:
    """Retire un nom de hardlink s'il porte bien l'identifiant attendu et si le
    fichier a au moins un autre nom (le contenu reste dans le dossier de
    stockage). Renvoie False, sans rien toucher, dans tous les autres cas."""
    if kind_of(p) != "file":
        return False
    if file_id(p) != expected_id or link_count(p) < 2:
        return False
    os.unlink(p)
    return True


# --------------------------------------------------------------------------
# Inventaire des liens (liens.json)
# --------------------------------------------------------------------------

class Inventory:
    """liens.json d'une version : {dossier de partie: {nom: description}}."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self.data: dict[str, Any] = {"schema": SCHEMA, "folders": {}}
        self.load()

    def load(self) -> None:
        with self._lock:
            raw = fsutil.read_json(self.path, None)
            if isinstance(raw, dict) and isinstance(raw.get("folders"), dict):
                self.data = {"schema": SCHEMA, "folders": {
                    str(k): v for k, v in raw["folders"].items() if isinstance(v, dict)}}

    def save(self) -> None:
        with self._lock:
            fsutil.atomic_write_json(self.path, self.data)

    def folder(self, name: str) -> dict[str, dict[str, Any]]:
        with self._lock:
            return dict(self.data["folders"].get(name.lower()) or {})

    def set_folder(self, name: str, entries: dict[str, dict[str, Any]]) -> None:
        with self._lock:
            self.data["folders"][name.lower()] = entries
            self.save()

    def set_entry(self, folder: str, name: str, entry: dict[str, Any]) -> None:
        with self._lock:
            self.data["folders"].setdefault(folder.lower(), {})[name] = entry
            self.save()

    def drop_entry(self, folder: str, name: str) -> None:
        with self._lock:
            entries = self.data["folders"].get(folder.lower())
            if entries is not None and entries.pop(name, None) is not None:
                self.save()

    def rename_entry(self, folder: str, old: str, new: str, entry: dict[str, Any] | None = None) -> None:
        """Renommer un mod (0.4) : l'entrée du lien suit le nouveau nom."""
        with self._lock:
            entries = self.data["folders"].get(folder.lower())
            if entries is None:
                return
            cur = entries.pop(old, None)
            if cur is None:
                for k in list(entries):
                    if k.lower() == old.lower():
                        cur = entries.pop(k)
                        break
            if entry is not None:
                cur = entry
            if cur is not None:
                entries[new] = cur
                self.save()

    def drop_folder(self, name: str) -> None:
        with self._lock:
            if self.data["folders"].pop(name.lower(), None) is not None:
                self.save()

    def rename_folder(self, old: str, new: str) -> None:
        with self._lock:
            entries = self.data["folders"].pop(old.lower(), None)
            if entries is not None:
                self.data["folders"][new.lower()] = entries
                self.save()

    def known_ids(self) -> set[str]:
        """Tous les identifiants de fichiers déjà liés par FS Passion."""
        with self._lock:
            out: set[str] = set()
            for entries in self.data["folders"].values():
                for e in entries.values():
                    if isinstance(e, dict) and e.get("id"):
                        out.add(str(e["id"]))
            return out


def describe(path: Path, kind: str, target: Path) -> dict[str, Any]:
    """Description d'un lien pour l'inventaire (« hardlink », « symlink » ou
    « junction »). Seul un hardlink a un identifiant : les deux autres se lisent
    directement (cible)."""
    return {"kind": kind, "id": file_id(target) if kind == "hardlink" else None, "target": str(target)}
