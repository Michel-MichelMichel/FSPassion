"""Réconciliation : remise en ordre des dossiers de parties.

Après une mise à jour faite par le jeu, une archive modifiée dans le dossier de
mods ou une intégration, les dossiers de parties ne correspondent plus au
dossier de mods. La réconciliation les remet en ordre, en silence, en
s'appuyant sur l'inventaire des liens (liens.json) :

1. dossier pending_downloads (jeu fermé) : les .zip qui sont des mods sont
   traités comme des mises à jour (ou comme des mods nouveaux). Le fichier
   pendingDownloadQueue.dat n'est jamais touché ;
2. chaque dossier de partie de la version (et celui de la Partie Vide) :
   - lien orphelin → retiré, puis refait vers le mod actuel ;
   - fichier nouveau (mise à jour du ModHub) → rapatrié dans le dossier de mods,
     l'ancienne version mise de côté, puis lien refait ;
   - mod inconnu (téléchargé en multijoueur) → rapatrié et ajouté à cette
     partie ; dans la Partie Vide, il devient non classé ;
   - copie d'un mod supprimé à la main du dossier de mods → laissée en place
     (anomalie A8, l'utilisateur choisit) ;
3. un mod remplacé rend orphelins ses liens dans les autres parties : les
   dossiers sont repris jusqu'à ce qu'il n'y ait plus rien à faire (reconstruction
   ciblée : seuls les liens concernés sont refaits).

Le contenu d'un dossier de partie (la liste de ses mods) ne change qu'avec
« Appliquer » : la réconciliation ne fait que réparer les liens existants.

Rien n'est jamais supprimé : les fichiers remplacés vont dans
« Old versions », les autres dans « Recovered ». Rien ne bouge pendant
que le jeu tourne : c'est à l'appelant de vérifier.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fspassion import fsutil, links, moddesc
from fspassion.apply import (
    EMPTY_FOLDER,
    FULL_FOLDER,
    RECOVERED,
    ApplyError,
    Tidy,
    VersionFolders,
    mod_version,
    party_dir,
)
from fspassion.parties import EMPTY, FULL

log = logging.getLogger(__name__)

PENDING_QUEUE = "pendingDownloadQueue.dat"
STABLE_SECONDS = 10      # un fichier modifié depuis moins longtemps est en cours d'écriture
MAX_PASSES = 4


@dataclass
class Report:
    """Bilan d'une réconciliation, pour le message discret (étape 7)."""
    updated: list[str] = field(default_factory=list)       # mises à jour récupérées
    added: dict[str, list[str]] = field(default_factory=dict)   # partie → mods inconnus ajoutés
    unclassified: list[str] = field(default_factory=list)  # nouveaux mods non classés
    set_aside: list[str] = field(default_factory=list)
    old_versions: list[str] = field(default_factory=list)
    relinked: int = 0
    pending: list[str] = field(default_factory=list)       # récupérés dans pending_downloads
    copies: dict[str, list[str]] = field(default_factory=dict)  # A8 : fichier → dossiers
    reshaped: list[str] = field(default_factory=list)      # mod décompressé ou recompressé
    older: list[str] = field(default_factory=list)         # version plus ancienne, à confirmer
    errors: list[str] = field(default_factory=list)

    @property
    def moved_files(self) -> bool:
        """Des fichiers ont rejoint ou quitté le dossier de mods : nouveau scan."""
        return bool(self.updated or self.added or self.unclassified or self.pending
                    or self.set_aside or self.old_versions)

    def is_empty(self) -> bool:
        return not (self.moved_files or self.relinked or self.errors)

    def to_json(self) -> dict[str, Any]:
        return {
            "updated": sorted(set(self.updated), key=str.lower),
            "added": {k: v for k, v in self.added.items() if v},
            "unclassified": self.unclassified,
            "set_aside": self.set_aside,
            "old_versions": self.old_versions,
            "relinked": self.relinked,
            "pending": self.pending,
            "copies": self.copies,
            "reshaped": sorted(set(self.reshaped), key=str.lower),
            "older": sorted(set(self.older), key=str.lower),
            "errors": self.errors,
        }


def _stable(p: Path, now: float) -> bool:
    try:
        return now - p.stat().st_mtime >= STABLE_SECONDS
    except OSError:
        return False


def _is_mod_zip(p: Path) -> bool:
    try:
        res = moddesc.read_zip(p)
    except Exception:  # noqa: BLE001 - archive abîmée
        return False
    return bool(res.ok and res.info is not None)


class Reconciler:
    """Réconciliation d'une version du jeu (toutes ses parties)."""

    def __init__(self, folders: VersionFolders) -> None:
        self.f = folders
        self.store = folders.store

    # ------------------------------------------------------------------
    # Dossiers à traiter
    # ------------------------------------------------------------------

    def party_folders(self) -> list[tuple[str, Path]]:
        """(identifiant de partie, dossier) des parties qui ont un dossier, plus
        la Partie Vide et, avec plusieurs stockages, la Partie Pleine. Les dossiers inconnus et les restes « .tmp-/.old- » ne
        sont pas touchés (ils le seront par « Appliquer » ou la reprise)."""
        out: list[tuple[str, Path]] = []
        base = self.f.parties_dir
        for p in self.store.data["parties"]:
            try:
                folder = party_dir(base, p["folder"])  # jamais hors de « Parties »
            except ApplyError:
                continue
            if folder.is_dir() and not links.is_link(folder):
                out.append((p["id"], folder))
        for pid, name in ((EMPTY, EMPTY_FOLDER), (FULL, FULL_FOLDER)):
            special = base / name
            if special.is_dir() and not links.is_link(special):
                out.append((pid, special))
        return out

    # ------------------------------------------------------------------
    # pending_downloads (étape 6)
    # ------------------------------------------------------------------

    def pending(self, pending_dir: Path | None, applied: str | None, report: Report) -> None:
        if pending_dir is None or not pending_dir.is_dir():
            return
        now = time.time()
        try:
            items = sorted(pending_dir.iterdir(), key=lambda p: p.name.lower())
        except OSError as exc:
            log.warning("pending_downloads illisible : %s", exc)
            return
        for item in items:
            name = item.name
            if name.lower() == PENDING_QUEUE.lower() or not name.lower().endswith(".zip"):
                continue
            if links.kind_of(item) != "file" or not _stable(item, now) or not _is_mod_zip(item):
                continue
            # Une mise à jour rejoint le stockage d'où vient le mod ; un
            # mod nouveau, le stockage principal.
            storage = self.f.locate(name)
            try:
                if os.path.lexists(storage):
                    if links.kind_of(storage) != "file":
                        self.f._aside(item, RECOVERED)  # même nom qu'un mod non compressé
                        report.set_aside.append(name)
                        continue
                    new_v, old_v = mod_version(item), mod_version(storage)
                    if new_v is not None and old_v is not None and new_v < old_v:
                        dst = self._aside_move(item, RECOVERED)
                        self.f.remember_older(name, dst, new_v, old_v, storage)
                        report.set_aside.append(name)
                        report.older.append(name)
                        continue
                    # D'abord le nouveau fichier à côté (copie vérifiée s'il vient
                    # d'un autre disque), puis bascule : jamais de dossier de mods
                    # sans ce mod si la copie échoue.
                    tmp = storage.with_name(f".fsp-in-{name}.part")
                    if os.path.lexists(tmp):
                        self.f._aside(tmp, RECOVERED)
                    fsutil.move_file(item, tmp, _is_mod_zip)
                    self.f.swap_in(tmp, storage)  # ancien mod remis en place si la bascule échoue
                    report.updated.append(name)
                    report.pending.append(name)
                else:
                    fsutil.move_file(item, storage, _is_mod_zip)
                    report.pending.append(name)
                    mod_id = name[:-4]
                    if applied and self.store.party(applied) is not None:
                        self.store.change_mods("add", "party", [mod_id], pid=applied)
                        report.added.setdefault(applied, []).append(mod_id)
                    else:
                        report.unclassified.append(mod_id)
                log.info("pending_downloads : %s récupéré", name)
            except OSError as exc:
                log.error("pending_downloads : %s non récupéré (%s)", name, exc)
                report.errors.append(name)

    def _aside_move(self, item: Path, kind: str) -> Path:
        """Mise de côté d'un fichier qui peut être sur un autre disque."""
        base = self.f.fsp / kind / self.f._stamp
        dst = base / item.name
        n = 2
        while os.path.lexists(dst):
            dst = base / f"{item.stem} ({n}){item.suffix}"
            n += 1
        fsutil.move_file(item, dst)
        log.warning("Mis de côté (%s) : %s → %s", kind, item, dst)
        return dst

    # ------------------------------------------------------------------
    # Dossiers de parties (étapes 1 à 5)
    # ------------------------------------------------------------------

    def folders(self, report: Report) -> None:
        for _ in range(MAX_PASSES):
            changed = False
            copies: dict[str, list[str]] = {}
            for pid, folder in self.party_folders():
                try:
                    tidy: Tidy = self.f.tidy(folder)
                except OSError as exc:
                    log.error("Réconciliation de %s impossible : %s", folder, exc)
                    report.errors.append(folder.name)
                    continue
                if tidy.added:
                    if pid in (EMPTY, FULL):
                        report.unclassified += tidy.added
                    else:
                        self.store.change_mods("add", "party", tidy.added, pid=pid)
                        report.added.setdefault(pid, []).extend(tidy.added)
                report.updated += tidy.updated
                report.set_aside += tidy.set_aside
                report.old_versions += tidy.old_versions
                report.reshaped += tidy.reshaped
                report.older += tidy.older
                for name in tidy.copies:
                    copies.setdefault(name, []).append(folder.name)
                relinked = self.f.relink(folder, tidy.relink) if tidy.relink else 0
                report.relinked += relinked
                if tidy.updated or tidy.relink or tidy.added or tidy.old_versions:
                    changed = True
            report.copies = copies
            if not changed:
                break

    def run(self, pending_dir: Path | None = None, applied: str | None = None) -> Report:
        report = Report()
        if not self.f.mods_dir.is_dir():
            return report
        self.pending(pending_dir, applied, report)
        if self.f.parties_dir.is_dir():
            self.folders(report)
        if not report.is_empty():
            log.info("Réconciliation %s : %s", self.f.vp.version.id, report.to_json())
        return report


def stray_copies(folders: VersionFolders) -> dict[str, list[str]]:
    """Copies, dans des dossiers de parties, de mods supprimés à la main du
    dossier de mods : nom du fichier → dossiers de parties. Lecture seule."""
    out: dict[str, list[str]] = {}
    base = folders.parties_dir
    if not base.is_dir():
        return out
    known = folders.inventory.known_ids()
    rec = Reconciler(folders)
    for _pid, folder in rec.party_folders():
        try:
            items = list(folder.iterdir())
        except OSError:
            continue
        for item in items:
            if links.kind_of(item) != "file":
                continue
            if os.path.lexists(folders.locate(item.name)):
                continue
            if item.name.lower().endswith(".zip") and links.kind_of(folders.locate(item.name[:-4])) == "dir":
                continue  # décompressé dans le dossier de mods : pas un mod supprimé
            fid = links.file_id(item)
            if fid is not None and fid in known:
                out.setdefault(item.name, []).append(folder.name)
    return out
