"""Opérations sur les fichiers des mods (0.4) : supprimer définitivement (4.7)
et renommer (4.21).

Ce sont les deux seules opérations de FS Passion qui touchent aux mods
eux-mêmes, et seulement sur demande explicite de l'utilisateur (I4, I9) :
- supprimer : retrait de toutes les listes → retrait des liens dans tous les
  dossiers de parties → envoi du mod dans la Corbeille de Windows (suppression
  définitive seulement si le disque n'a pas de Corbeille, et c'est annoncé) ;
- renommer : le fichier (ou le dossier) change de nom, son contenu jamais. Les
  listes, les liens des dossiers de parties et l'inventaire suivent.

Refusés pendant que le jeu tourne (I5) : c'est à l'appelant de le vérifier.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from fspassion import links, winapi
from fspassion.apply import ApplyError, VersionFolders
from fspassion.links import LinkError

log = logging.getLogger(__name__)

# Règle du jeu : lettres non accentuées, chiffres et « _ » seulement.
NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
MAX_NAME = 120
_PREFIX_RE = re.compile(r"^((?:FS|LS)(?:\d{2}|20\d{2})_)", re.IGNORECASE)


def split_prefix(mod_id: str) -> tuple[str, str]:
    """« FS25_HofBergmann » → (« FS25_ », « HofBergmann »). Le préfixe de version
    est conservé au renommage (4.21)."""
    m = _PREFIX_RE.match(mod_id)
    if not m:
        return "", mod_id
    return m.group(1), mod_id[m.end():]


def check_new_name(new_id: str, old_id: str, taken: set[str]) -> str | None:
    """Clé d'erreur, ou None si le nouveau nom convient. `taken` : noms (sans
    .zip, en minuscules) déjà présents dans les dossiers de stockage."""
    if not new_id:
        return "rename.empty"
    if len(new_id) > MAX_NAME:
        return "rename.too_long"
    if not NAME_RE.match(new_id):
        return "rename.invalid"
    if new_id == old_id:
        return "rename.same"
    if new_id.lower() != old_id.lower() and new_id.lower() in taken:
        return "rename.taken"
    return None


def storage_names(storages: list[Path]) -> set[str]:
    """Noms occupés dans les dossiers de stockage (sans .zip, en minuscules)."""
    out: set[str] = set()
    for folder in storages:
        try:
            for e in os.scandir(folder):
                low = e.name.lower()
                out.add(low[:-4] if low.endswith(".zip") else low)
        except OSError:
            continue
    return out


# --------------------------------------------------------------------------
# Supprimer
# --------------------------------------------------------------------------

def remove_tree(path: Path) -> None:
    """Supprime un dossier (mod non compressé) sans jamais suivre un lien ou une
    jonction qu'il contiendrait (I10) : un lien est retiré comme un lien."""
    for entry in list(path.iterdir()):
        kind = links.kind_of(entry)
        if kind in ("junction", "symlink"):
            links.remove_link(entry)
        elif kind == "dir":
            remove_tree(entry)
        else:
            try:
                os.unlink(entry)
            except PermissionError:
                os.chmod(entry, 0o666)  # fichier en lecture seule
                os.unlink(entry)
    path.rmdir()


def discard(path: Path) -> str:
    """Le mod part dans la Corbeille (« recycled ») ; sans Corbeille sur ce
    disque, il est supprimé (« deleted »). Lève OSError si rien n'a pu être fait."""
    kind = links.kind_of(path)
    if kind == "missing":
        return "deleted"
    if kind in ("junction", "symlink"):
        links.remove_link(path)
        return "deleted"
    if winapi.recycle_bin_available(path):
        if winapi.send_to_recycle_bin(path):
            return "recycled"
        if not os.path.lexists(path):
            return "deleted"  # Windows l'a supprimé après son propre avertissement
        raise OSError(f"Corbeille : suppression annulée ou refusée ({path})")
    if kind == "dir":
        remove_tree(path)
    else:
        os.unlink(path)
    return "deleted"


def unlink_everywhere(folders: VersionFolders, file: str, storage_path: Path) -> int:
    """Retire les liens vers un mod de tous les dossiers de parties (et de la
    Partie Vide). Seuls nos liens sont retirés : un hardlink du même fichier, une
    jonction. Renvoie le nombre de liens retirés."""
    base = folders.parties_dir
    if not base.is_dir():
        return 0
    sid = links.file_id(storage_path) if links.kind_of(storage_path) == "file" else None
    count = 0
    for folder in base.iterdir():
        if links.kind_of(folder) != "dir":
            continue
        item = folder / file
        kind = links.kind_of(item)
        if kind == "missing":
            continue
        if kind in ("junction", "symlink"):
            links.remove_link(item)
        elif kind == "file" and sid is not None and links.remove_hardlink_name(item, sid):
            pass
        else:
            continue  # autre chose : laissé (réconciliation)
        folders.inventory.drop_entry(folder.name, file)
        count += 1
    return count


# --------------------------------------------------------------------------
# Renommer (avec journal, I8)
# --------------------------------------------------------------------------

def rename_links(folders: VersionFolders, old_file: str, new_file: str, new_path: Path) -> int:
    """Les liens à l'ancien nom sont remplacés par des liens au nouveau nom, dans
    les mêmes dossiers de parties (4.21). Un hardlink garde le même fichier : son
    nom change simplement. Une jonction ou un lien symbolique visait l'ancien
    chemin : il est refait."""
    base = folders.parties_dir
    if not base.is_dir():
        return 0
    sid = links.file_id(new_path) if links.kind_of(new_path) == "file" else None
    count = 0
    for folder in base.iterdir():
        if links.kind_of(folder) != "dir":
            continue
        item = folder / old_file
        dst = folder / new_file
        kind = links.kind_of(item)
        if kind == "missing" or (os.path.lexists(dst) and old_file.lower() != new_file.lower()):
            continue
        if kind == "file" and sid is not None and links.file_id(item) == sid:
            os.rename(item, dst)
            folders.inventory.rename_entry(folder.name, old_file, new_file)
        elif kind in ("junction", "symlink"):
            # Jonction ou lien symbolique (mod d'un autre disque, 0.6) : ils
            # visaient l'ancien chemin, ils sont refaits vers le nouveau.
            links.remove_link(item)
            if links.kind_of(new_path) == "dir":
                links.make_dir_link(new_path, dst)
                entry = links.describe(dst, "junction", new_path)
            else:
                links.make_file_symlink(new_path, dst)
                entry = links.describe(dst, "symlink", new_path)
            folders.inventory.rename_entry(folder.name, old_file, new_file, entry)
        else:
            continue
        count += 1
    return count


def rename_mod(folders: VersionFolders, entry: dict[str, Any], new_id: str) -> dict[str, Any]:
    """Renomme un mod de la bibliothèque (4.21). `entry` : le mod (index de la
    bibliothèque). Renvoie {old, new, file, links, lists}."""
    storages = folders.vp.storages
    index = int(entry.get("storage") or 0)
    if not 0 <= index < len(storages):
        raise ApplyError("rename.not_found", status=404, name=entry.get("id"))
    folder = storages[index]
    kind = entry["kind"]
    old_id = entry["id"]
    old_file = entry["file"]
    # Même contrôle que l'interface : la règle du nom vaut aussi ici.
    taken = storage_names(storages)
    taken.discard(old_id.lower())
    err = check_new_name(new_id, old_id, taken)
    if err:
        raise ApplyError(err, name=new_id, max=MAX_NAME)
    new_file = f"{new_id}.zip" if kind == "zip" else new_id
    src = folder / old_file
    dst = folder / new_file
    if not os.path.lexists(src):
        raise ApplyError("rename.not_found", status=404, name=old_id)
    if os.path.lexists(dst) and old_file.lower() != new_file.lower():
        raise ApplyError("rename.taken", name=new_id)
    folders._journal(op="mod_rename", old_id=old_id, new_id=new_id, old_file=old_file, new_file=new_file,
                     storage=int(entry.get("storage") or 0), step="storage")
    try:
        os.rename(src, dst)
    except OSError as exc:
        folders._journal_done()
        raise ApplyError("rename.failed", status=409, name=old_file, detail=str(exc)) from exc
    log.info("Mod renommé : %s → %s", src, dst)
    res = finish_rename(folders, old_id, new_id, old_file, new_file, dst)
    folders._journal_done()
    return res


def finish_rename(folders: VersionFolders, old_id: str, new_id: str, old_file: str, new_file: str,
                  new_path: Path) -> dict[str, Any]:
    """Suite d'un renommage (aussi rejouée après une coupure, I8) : liens, puis
    listes. Chaque étape peut être refaite sans dommage."""
    folders._journal(op="mod_rename", old_id=old_id, new_id=new_id, old_file=old_file, new_file=new_file,
                     step="links")
    try:
        n_links = rename_links(folders, old_file, new_file, new_path)
    except (OSError, LinkError) as exc:
        log.error("Liens non renommés (%s → %s) : %s", old_file, new_file, exc)
        n_links = 0  # la réconciliation et « Appliquer » les referont
    # Les listes ne sont PAS modifiées ici (0.4, correction) : FS Passion demande
    # ensuite à l'utilisateur si elles doivent suivre le nouveau nom (mod_lists_rename).
    return {"old": old_id, "new": new_id, "file": new_file, "links": n_links, "lists": 0}


def update_lists(store: Any, old_id: str, new_id: str) -> int:
    """Fait suivre le nouveau nom dans toutes les listes (confirmé par l'utilisateur).
    Renvoie le nombre de listes modifiées."""
    if old_id.lower() != new_id.lower():
        return store.replace_mod(old_id, new_id)
    # Seule la casse change : la liste garde le même mod, écrit autrement.
    return store.replace_case(old_id, new_id)


def recover_rename(folders: VersionFolders, job: dict[str, Any]) -> str:
    """Reprise d'un renommage interrompu : terminé si le fichier porte déjà son
    nouveau nom, sinon annulé (rien n'avait changé)."""
    try:
        storage = folders.vp.storages[int(job.get("storage") or 0)]
    except (IndexError, ValueError):
        storage = folders.mods_dir
    new_path = storage / str(job.get("new_file"))
    old_path = storage / str(job.get("old_file"))
    if os.path.lexists(new_path) and (not os.path.lexists(old_path)
                                      or str(job.get("old_file")).lower() == str(job.get("new_file")).lower()):
        finish_rename(folders, str(job["old_id"]), str(job["new_id"]), str(job["old_file"]),
                      str(job["new_file"]), new_path)
        folders._journal_done()
        return "finished"
    folders._journal_done()
    return "cancelled"


def dependents(index: dict[str, dict[str, Any]], mod_id: str) -> list[str]:
    """Mods qui déclarent `mod_id` comme dépendance (ils le chercheront sous son
    ancien nom après un renommage)."""
    low = mod_id.lower()
    out = []
    for e in index.values():
        if any(isinstance(d, str) and d.strip().lower() == low for d in e.get("dependencies") or []):
            out.append(str(e["id"]))
    return sorted(out, key=str.lower)

