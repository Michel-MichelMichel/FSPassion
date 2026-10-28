"""« Appliquer » une partie : dossiers de parties, liens et override.

Un dossier de partie (FSPassion\\<version>\\Parties\\<dossier>\\) ne contient
que des liens vers les mods des dossiers de stockage :
- un hardlink pour un mod .zip du disque principal ;
- un lien symbolique pour un mod .zip d'un autre disque ;
- une jonction pour un mod non compressé (dossier).

Avec plusieurs dossiers de stockage, la Partie Pleine a elle aussi son
dossier de liens, « Parties\\_pleine\\ » : le jeu ne lit qu'un dossier.

Étapes d'« Appliquer » (rien n'est laissé à moitié fait) :
1. remise en ordre du dossier actuel de la partie : un fichier physique déposé
   par le jeu (mise à jour du ModHub, téléchargement en multijoueur) est
   rapatrié vers le dossier de mods, jamais supprimé ;
2. calcul des mods actifs : mods de la partie + mods communs (si le switch est
   activé), sans doublon ; les mods absents sont relevés ;
3. construction à part dans « .tmp-<id> » ;
4. bascule : l'ancien dossier devient « .old-<id> », le nouveau prend sa place,
   puis l'ancien est vidé lien par lien et supprimé ;
5. inventaire des liens (liens.json) ;
6. écriture de l'override (gameSettings.xml, avec sauvegarde) ;
7. partie appliquée et historique.

Chaque étape est notée dans journal_operations.json : au démarrage suivant,
une opération interrompue (coupure de courant…) est terminée ou annulée.

Fichiers mis de côté (jamais supprimés), dans FSPassion\\<version>\\ :
- « Old versions\\<date>\\ » : l'ancienne version d'un mod remplacé par
  une mise à jour déposée par le jeu, ou un ancien lien devenu la seule copie
  d'une version périmée ;
- « Recovered\\<date>\\ » : tout autre fichier trouvé dans un dossier de
  partie (version plus ancienne que celle du dossier de mods, fichier qui
  n'est pas un mod…).

Ici, seul le dossier de la partie traitée est remis en ordre ; la réconciliation
complète (toutes les parties, dossier pending_downloads) est faite par reconcile.py.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fspassion import fsutil, gamesettings, links, moddesc, storage
from fspassion.gamepaths import VersionPaths
from fspassion.links import Inventory, LinkError
from fspassion.parties import EMPTY, FULL, PartiesStore, is_special

log = logging.getLogger(__name__)

PARTIES = "Parties"
OLD_VERSIONS = "Old versions"
RECOVERED = "Recovered"
# Anciens noms : les dossiers existants sont renommés (vocabulaire
# anglais pour les dossiers sur le disque).
LEGACY_FOLDERS = {"Anciennes versions": OLD_VERSIONS, "Recuperes": RECOVERED}
# Versions plus anciennes déposées par le jeu, en attente de la décision de l'utilisateur.
OLDER = "a_confirmer.json"
_migrated: set[str] = set()


def migrate_aside_folders(fsp: Path) -> None:
    """Renomme « Anciennes versions » et « Recuperes » (une fois par dossier)."""
    key = fsutil.norm_path(fsp)
    if key in _migrated:
        return
    _migrated.add(key)
    for old, new in LEGACY_FOLDERS.items():
        src, dst = fsp / old, fsp / new
        if src.is_dir() and not links.is_link(src) and not os.path.lexists(dst):
            try:
                os.rename(src, dst)
                log.info("Dossier renommé : %s → %s", src, dst)
            except OSError as exc:
                log.warning("Dossier non renommé %s : %s", src, exc)


def version_text(v: tuple[int, ...] | None) -> str | None:
    return ".".join(str(x) for x in v) if v else None
JOURNAL = "journal_operations.json"
INVENTORY = "liens.json"
EMPTY_FOLDER = "_vide"
FULL_FOLDER = "_pleine"   # Partie Pleine avec plusieurs dossiers de stockage


class ApplyError(Exception):
    """Erreur prévue, avec une clé de langue."""

    def __init__(self, key: str, status: int = 400, **params: Any) -> None:
        super().__init__(key)
        self.key = key
        self.status = status
        self.params = params


def _plain_name(name: Any) -> bool:
    """Vrai pour un nom d'un seul composant : ni séparateur, ni « . », ni « .. »,
    ni lecteur (« C: »)."""
    return isinstance(name, str) and name not in ("", ".", "..") and not any(c in name for c in "/\\:")


def party_dir(parties_dir: Path, folder: Any) -> Path:
    """Dossier d'une partie, sous `parties_dir`. Refuse (ApplyError) tout nom qui
    sortirait de ce dossier : aucune opération disque avant ce contrôle."""
    if not _plain_name(folder):
        raise ApplyError("error.internal", status=500)
    return parties_dir / folder


@dataclass
class Tidy:
    """Bilan de la remise en ordre d'un dossier de partie."""
    updated: list[str] = field(default_factory=list)     # mises à jour rapatriées
    added: list[str] = field(default_factory=list)       # mods inconnus rapatriés
    set_aside: list[str] = field(default_factory=list)   # fichiers mis de côté
    old_versions: list[str] = field(default_factory=list)
    # Liens à refaire vers le mod actuel (lien orphelin retiré, mise à jour
    # rapatriée) et copies d'un mod supprimé à la main du dossier de mods.
    relink: list[str] = field(default_factory=list)
    copies: list[str] = field(default_factory=list)
    reshaped: list[str] = field(default_factory=list)   # mod décompressé ou recompressé
    older: list[str] = field(default_factory=list)      # version plus ancienne : à confirmer

    def merge(self, other: Tidy) -> None:
        self.updated += other.updated
        self.added += other.added
        self.set_aside += other.set_aside
        self.old_versions += other.old_versions
        self.relink += other.relink
        self.copies += other.copies
        self.reshaped += other.reshaped
        self.older += other.older

    def to_json(self) -> dict[str, Any]:
        return {"updated": self.updated, "added": self.added, "set_aside": self.set_aside,
                "old_versions": self.old_versions, "older": self.older}


def _version_tuple(v: str | None) -> tuple[int, ...] | None:
    if not v:
        return None
    parts = re.findall(r"\d+", str(v))
    return tuple(int(p) for p in parts[:6]) if parts else None


def mod_version(path: Path) -> tuple[int, ...] | None:
    """Version (<version> du modDesc.xml) d'un mod .zip ou dossier."""
    try:
        res = moddesc.read_zip(path) if path.is_file() else moddesc.read_dir(path)
    except Exception:  # noqa: BLE001 - archive abîmée : version inconnue
        return None
    if not res.ok or res.info is None:
        return None
    return _version_tuple(res.info.version)


def signature(mods: list[str]) -> str:
    """Empreinte de la liste des mods actifs : « Appliquer » est mis en évidence
    quand elle diffère de celle de la dernière application."""
    joined = "\n".join(sorted({m.lower() for m in mods}))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def _stamp() -> str:
    return time.strftime("%Y-%m-%d_%H%M%S")


class VersionFolders:
    """Dossiers de parties, inventaire et journal d'une version du jeu."""

    def __init__(self, vp: VersionPaths, store: PartiesStore,
                 index: Callable[[], dict[str, dict[str, Any]]],
                 symlinks: bool | None = None) -> None:
        if vp.fsp_dir is None or vp.mods_dir is None:
            raise ApplyError("parties.not_configured", game=vp.version.name)
        self.vp = vp
        self.store = store
        self.index = index
        self.fsp = vp.fsp_dir
        self.mods_dir = vp.mods_dir
        self.storages = vp.storages
        self.parties_dir = self.fsp / PARTIES
        self.journal_path = self.fsp / JOURNAL
        self.inventory = Inventory(self.fsp / INVENTORY)
        self._stamp = _stamp()
        # Plusieurs dossiers de stockage : au moins un supplémentaire existe.
        self.multi = bool(storage.active_extras(vp))
        self._symlinks = symlinks
        self._other_disk: dict[int, bool] = {}
        migrate_aside_folders(self.fsp)

    # ------------------------------------------------------------------
    # Versions plus anciennes déposées par le jeu
    # ------------------------------------------------------------------

    def remember_older(self, name: str, aside: Path, new: tuple[int, ...] | None,
                       old: tuple[int, ...] | None, target: Path) -> None:
        """Une version plus ancienne que celle de l'utilisateur a été mise de
        côté : elle attend sa décision (« Garder ma version » ou « Utiliser celle du jeu »)."""
        items = [x for x in self.older_list(check=False) if x.get("name", "").lower() != name.lower()]
        items.append({"name": name, "path": str(aside), "new": version_text(new), "old": version_text(old),
                      "target": str(target), "time": time.strftime("%Y-%m-%dT%H:%M:%S")})
        fsutil.atomic_write_json(self.fsp / OLDER, items)

    def older_list(self, check: bool = True) -> list[dict[str, Any]]:
        """Décisions en attente (fichier mis de côté encore présent)."""
        raw = fsutil.read_json(self.fsp / OLDER, [])
        items = [x for x in raw if isinstance(x, dict) and _plain_name(x.get("name")) and x.get("path")] \
            if isinstance(raw, list) else []
        if check:
            items = [x for x in items if os.path.isfile(x["path"])]
        return items

    def older_drop(self, path: str) -> None:
        items = [x for x in self.older_list(check=False) if not fsutil.same_path(x["path"], path)]
        fsutil.atomic_write_json(self.fsp / OLDER, items)

    # ------------------------------------------------------------------
    # Dossiers de stockage
    # ------------------------------------------------------------------

    @property
    def symlinks_ok(self) -> bool:
        if self._symlinks is None:
            self._symlinks = storage.symlinks_allowed()
        return self._symlinks

    def locate(self, name: str) -> Path:
        """Chemin actuel d'un mod (nom de fichier ou de dossier) : dans le premier
        dossier de stockage qui le contient, le principal d'abord (doublon).
        S'il n'est nulle part, son chemin dans le dossier principal."""
        for folder in self.storages:
            cand = folder / name
            if os.path.lexists(cand):
                return cand
        return self.mods_dir / name

    def storage_index(self, path: Path) -> int:
        """Numéro du dossier de stockage qui contient `path` (0 : principal)."""
        for i, folder in enumerate(self.storages):
            if fsutil.same_path(path.parent, folder):
                return i
        return 0

    def needs_symlink(self, index: int) -> bool:
        """Un mod .zip du stockage n° `index` demande-t-il un lien symbolique ?"""
        if index == 0:
            return False
        if index not in self._other_disk:
            try:
                self._other_disk[index] = storage.on_other_disk(self.vp, self.storages[index])
            except IndexError:
                self._other_disk[index] = False
        return self._other_disk[index]

    def _link(self, src: Path, dst: Path, index: int | None = None) -> dict[str, Any]:
        """Crée le lien qui convient et renvoie sa description pour
        l'inventaire. Lève LinkError (« apply.symlink_denied » sans les droits)."""
        if index is None:
            index = self.storage_index(src)
        if links.kind_of(src) == "dir":
            links.make_dir_link(src, dst)
            return links.describe(dst, "junction", src)
        if self.needs_symlink(index):
            if not self.symlinks_ok:
                raise LinkError("apply.symlink_denied", name=src.name)
            links.make_file_symlink(src, dst)
            return links.describe(dst, "symlink", src)
        links.make_hardlink(src, dst)
        return links.describe(dst, "hardlink", src)

    # ------------------------------------------------------------------
    # Mods actifs
    # ------------------------------------------------------------------

    def active_ids(self, pid: str) -> list[str]:
        """Mods de la partie + mods communs (si le switch est activé), sans doublon."""
        if pid == FULL:
            return [e["id"] for e in self.index().values()]
        if pid == EMPTY:
            return []
        party = self.store.party(pid)
        if party is None:
            raise ApplyError("parties.not_found", status=404)
        ids = list(party["mods"])
        if party["common_enabled"]:
            ids += self.store.data["common_mods"]
        seen: set[str] = set()
        out = []
        for i in ids:
            if i.lower() not in seen:
                seen.add(i.lower())
                out.append(i)
        return out

    def signature_of(self, pid: str) -> str:
        if pid == EMPTY or (pid == FULL and not self.multi):
            return pid
        return signature(self.active_ids(pid))

    # ------------------------------------------------------------------
    # Mise de côté (jamais de suppression)
    # ------------------------------------------------------------------

    def _aside(self, src: Path, kind: str) -> Path:
        base = self.fsp / kind / self._stamp
        base.mkdir(parents=True, exist_ok=True)
        dst = base / src.name
        n = 2
        while dst.exists() or os.path.lexists(dst):
            dst = base / f"{src.stem} ({n}){src.suffix}"
            n += 1
        # Un mod d'un autre disque est copié, vérifié, puis retiré : les
        # stockages supplémentaires ne reçoivent jamais de fichier de FS Passion.
        fsutil.relocate(src, dst)
        log.warning("Mis de côté (%s) : %s → %s", kind, src, dst)
        return dst

    def _replace(self, item: Path, target: Path) -> None:
        """Une mise à jour déposée par le jeu remplace le mod `target`, dans SON
        dossier de stockage : le nouveau fichier d'abord à côté (copie
        vérifiée s'il vient d'un autre disque), puis l'ancien est mis de côté et
        le nouveau prend sa place. Jamais de stockage sans ce mod en cas d'échec."""
        tmp = target.with_name(f".fsp-in-{target.name}.part")
        if os.path.lexists(tmp):
            self._aside(tmp, RECOVERED)
        fsutil.relocate(item, tmp)
        try:
            self.swap_in(tmp, target)
        except OSError:
            fsutil.relocate(tmp, item)  # retour du fichier à sa place
            raise

    def swap_in(self, new: Path, target: Path) -> None:
        """L'ancien `target` est mis de côté (Old versions), puis `new` prend sa
        place. Si cette bascule échoue, l'ancien fichier est remis à sa place."""
        old = self._aside(target, OLD_VERSIONS)
        try:
            os.replace(new, target)
        except OSError as exc:
            try:
                fsutil.relocate(old, target)
            except OSError as back:
                log.error("Ancien mod non remis en place %s : %s", target, back)
            raise exc

    # ------------------------------------------------------------------
    # Remise en ordre d'un dossier de partie (partie traitée seulement)
    # ------------------------------------------------------------------

    def tidy(self, folder: Path) -> Tidy:
        """Rapatrie les fichiers physiques d'un dossier de partie.

        - lien valide (même fichier que le mod du dossier de mods) : rien ;
        - lien orphelin (déjà lié par FS Passion, mais le mod a été remplacé
          depuis) : retiré s'il reste d'autres noms du fichier, sinon mis de
          côté dans « Anciennes versions » ;
        - fichier nouveau (déposé par le jeu) : il remplace le mod du dossier de
          mods (dont l'ancienne version est mise de côté), sauf s'il est plus
          ancien : il est alors mis de côté dans « Recuperes » ;
        - mod inconnu : déplacé dans le dossier de mods (et ajouté à la partie
          par l'appelant, liste « added ») ;
        - copie d'un mod supprimé à la main du dossier de mods :
          laissée en place, l'utilisateur choisit (« Restaurer dans Mods » ou
          « Supprimer définitivement »).

        « relink » liste les liens à refaire vers le mod actuel (réconciliation
        hors « Appliquer »).
        """
        out = Tidy()
        if not folder.is_dir() or links.is_link(folder):
            return out
        known = self.inventory.known_ids()
        for item in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            kind = links.kind_of(item)
            name = item.name
            if kind in ("junction", "symlink"):
                self._tidy_link(folder, item, out)
                continue
            current = self.locate(name)
            is_mod = (kind == "file" and name.lower().endswith(".zip")) or (
                kind == "dir" and (item / "modDesc.xml").is_file())
            if kind == "file":
                fid = links.file_id(item)
                sid = links.file_id(current) if links.kind_of(current) == "file" else None
                if fid is not None and fid == sid:
                    continue  # lien valide
                if fid is not None and fid in known:
                    unpacked = self.locate(name[:-4]) if name.lower().endswith(".zip") else None
                    if sid is None and not os.path.lexists(current) and unpacked is not None \
                            and links.kind_of(unpacked) == "dir":
                        # Le mod a changé de forme : décompressé dans le dossier de
                        # mods (dossier du même nom). Le lien vers l'ancienne
                        # archive est retiré (gardée si c'était la dernière copie),
                        # et une jonction vers le dossier prend sa place.
                        if links.link_count(item) >= 2:
                            os.unlink(item)
                        else:
                            self._aside(item, OLD_VERSIONS)
                            out.old_versions.append(name)
                        if not os.path.lexists(folder / unpacked.name):
                            out.relink.append(unpacked.name)
                        out.reshaped.append(name)
                        continue
                    if sid is None and not os.path.lexists(current):
                        # Mod supprimé à la main du dossier de mods, encore présent
                        # par ce lien : rien n'est touché.
                        out.copies.append(name)
                        continue
                    # Lien orphelin : le mod du dossier de mods a été remplacé.
                    if links.link_count(item) >= 2:
                        os.unlink(item)  # d'autres noms gardent le contenu
                    else:
                        self._aside(item, OLD_VERSIONS)
                        out.old_versions.append(name)
                    out.relink.append(name)
                    continue
            if not is_mod:
                self._aside(item, RECOVERED)
                out.set_aside.append(name)
                continue
            # Fichier (ou dossier) nouveau, déposé par le jeu.
            if os.path.lexists(current):
                new_v = mod_version(item)
                old_v = mod_version(current) if not links.is_link(current) else None
                if new_v is not None and old_v is not None and new_v < old_v:
                    # Numéro de version plus ancien que celui de l'utilisateur
                    # (souvent : un mod modifié, et le ModHub propose son original).
                    # Mis de côté, et FS Passion demande quoi faire.
                    dst = self._aside(item, RECOVERED)
                    self.remember_older(name, dst, new_v, old_v, current)
                    out.set_aside.append(name)
                    out.older.append(name)
                    # Le jeu a retiré le lien vers la version de l'utilisateur : il est
                    # refait, pour que la partie garde ce mod en attendant sa décision.
                    out.relink.append(name)
                    continue
                if links.is_link(current):
                    self._aside(item, RECOVERED)
                    out.set_aside.append(name)
                    continue
                # Rapatrié dans le dossier de stockage d'où venait le mod.
                self._replace(item, current)
                out.updated.append(name)
                out.relink.append(name)
            else:
                # Mod inconnu : rapatrié dans le stockage principal ; l'appelant
                # l'ajoute à la partie (Partie Vide ou Pleine : non classé).
                fsutil.relocate(item, current)
                out.added.append(name[:-4] if name.lower().endswith(".zip") else name)
                out.relink.append(name)
        return out

    def _tidy_link(self, folder: Path, item: Path, out: Tidy) -> None:
        """Jonction (mod non compressé) ou lien symbolique (mod d'un autre disque)
        d'un dossier de partie. Un tel lien vise un CHEMIN :
        - il vise le mod actuel : valide, rien à faire ;
        - le mod est ailleurs sous le même nom (déplacé, autre stockage, archive
          réécrite sous une autre forme) : le lien est refait ;
        - le mod a été recompressé (« Nom.zip ») ou décompressé (dossier « Nom ») :
          le lien est remplacé par un lien vers sa nouvelle forme. Sans cela, le jeu chargeait encore l'ancienne
          forme du mod et le ModHub ne pouvait pas le mettre à jour ;
        - sinon (mod disparu) : rien, « Appliquer » s'en chargera.
        Un lien se retire toujours comme un lien."""
        name = item.name
        target = links.link_target(item)
        current = self.locate(name)
        target_ok = target is not None and os.path.lexists(target)
        if target_ok and fsutil.same_path(target, current):
            return  # lien valide
        if os.path.lexists(current) and links.kind_of(current) in ("dir", "file"):
            links.remove_link(item)
            self.inventory.drop_entry(folder.name, name)
            out.relink.append(name)
            return
        if target_ok:
            return  # le mod existe encore à l'endroit visé (stockage écarté) : laissé
        if name.lower().endswith(".zip"):
            other = self.locate(name[:-4])
            other_kind = "dir"
        else:
            other = self.locate(f"{name}.zip")
            other_kind = "file"
        if links.kind_of(other) == other_kind and not os.path.lexists(folder / other.name):
            links.remove_link(item)
            self.inventory.drop_entry(folder.name, name)
            out.relink.append(other.name)
            out.reshaped.append(name)

    def empty(self, folder: Path) -> Tidy:
        """Vide un dossier de partie lien par lien, puis le supprime.
        Tout fichier physique est d'abord rapatrié (tidy)."""
        res = Tidy()
        if not os.path.lexists(folder):
            return res
        # Garde-fou : on ne vide jamais que des dossiers de « Parties ».
        if fsutil.norm_path(folder.parent) != fsutil.norm_path(self.parties_dir):
            raise ApplyError("error.internal", status=500)
        if links.is_link(folder):
            links.remove_link(folder)
            return res
        res.merge(self.tidy(folder))
        known = self.inventory.known_ids()
        for item in list(folder.iterdir()):
            kind = links.kind_of(item)
            if kind in ("junction", "symlink"):
                links.remove_link(item)
            elif kind == "file":
                sid = links.file_id(self.locate(item.name))
                if sid is not None and links.remove_hardlink_name(item, sid):
                    continue
                if links.link_count(item) >= 2 and links.file_id(item) in known:
                    # Un de nos liens, dont le contenu a un autre nom ailleurs
                    # (autre partie, « Anciennes versions ») : retiré comme un lien.
                    os.unlink(item)
                    continue
                self._aside(item, RECOVERED)
                res.set_aside.append(item.name)
            else:
                self._aside(item, RECOVERED)
                res.set_aside.append(item.name)
        folder.rmdir()
        return res

    def relink(self, folder: Path, names: list[str]) -> int:
        """Refait, dans un dossier de partie, les liens vers le mod actuel du
        dossier de mods (lien orphelin retiré, mise à jour rapatriée). Le reste du
        dossier n'est pas touché : il ne change qu'avec « Appliquer »."""
        done = 0
        key = folder.name
        for name in dict.fromkeys(names):
            src = self.locate(name)
            dst = folder / name
            if not os.path.lexists(src) or os.path.lexists(dst):
                continue
            try:
                entry = self._link(src, dst)
            except LinkError as exc:
                log.warning("Lien non refait %s : %s", dst, exc.key)
                continue
            self.inventory.set_entry(key, name, entry)
            done += 1
        return done

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build(self, tmp: Path, ids: list[str]) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
        """Construit le dossier de liens. Renvoie (inventaire, mods absents, mods
        bloqués). Bloqué : mod d'un autre disque, sans droits pour les liens
        symboliques ; il est listé mais n'entre pas dans la partie."""
        idx = self.index()
        entries: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        blocked: list[str] = []
        tmp.mkdir(parents=True)
        for mod_id in ids:
            e = idx.get(mod_id.lower())
            if e is None:
                missing.append(mod_id)
                continue
            n = int(e.get("storage") or 0)
            if not 0 <= n < len(self.storages):
                missing.append(mod_id)
                continue
            src = self.storages[n] / e["file"]
            if not os.path.lexists(src):
                missing.append(mod_id)
                continue
            try:
                entries[e["file"]] = self._link(src, tmp / e["file"], n)
            except LinkError as exc:
                if exc.key != "apply.symlink_denied":
                    raise
                blocked.append(mod_id)
        return entries, missing, blocked

    def _scan_inventory(self, folder: Path) -> dict[str, dict[str, Any]]:
        """Inventaire recalculé d'après le contenu d'un dossier (reprise)."""
        out: dict[str, dict[str, Any]] = {}
        if not folder.is_dir():
            return out
        for item in folder.iterdir():
            kind = links.kind_of(item)
            if kind == "junction" or kind == "symlink":
                out[item.name] = {"kind": kind, "id": None, "target": links.link_target(item)}
            elif kind == "file":
                out[item.name] = {"kind": "hardlink", "id": links.file_id(item), "target": str(self.locate(item.name))}
        return out

    # ------------------------------------------------------------------
    # Journal des opérations
    # ------------------------------------------------------------------

    def _journal(self, **data: Any) -> None:
        data["time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        fsutil.atomic_write_json(self.journal_path, data)

    def _journal_done(self) -> None:
        try:
            self.journal_path.unlink()
        except FileNotFoundError:
            pass

    def pending(self) -> dict[str, Any] | None:
        data = fsutil.read_json(self.journal_path, None)
        return data if isinstance(data, dict) and data.get("op") else None

    # ------------------------------------------------------------------
    # Appliquer
    # ------------------------------------------------------------------

    def apply(self, pid: str) -> dict[str, Any]:
        gs = self.vp.gamesettings
        if gs is None or not gs.is_file():
            raise ApplyError("apply.no_gamesettings", game=self.vp.version.name)
        if not self.mods_dir.is_dir():
            raise ApplyError("parties.not_configured", game=self.vp.version.name)
        if not self.store.known(pid):
            raise ApplyError("parties.not_found", status=404)
        self.parties_dir.mkdir(parents=True, exist_ok=True)
        report = Tidy()
        missing: list[str] = []
        blocked: list[str] = []
        count = 0

        if pid == FULL and not self.multi:
            count = len(self.index())
            target = self.mods_dir
            # Retour à un seul dossier de stockage : l'ancien dossier de liens de
            # la Partie Pleine n'a plus lieu d'être.
            leftover = self.parties_dir / FULL_FOLDER
            if os.path.lexists(leftover):
                report.merge(self.empty(leftover))
                self.inventory.drop_folder(FULL_FOLDER)
        elif pid == EMPTY:
            target = self.parties_dir / EMPTY_FOLDER
            if target.is_dir():
                report.merge(self.tidy(target))
            target.mkdir(exist_ok=True)
        else:
            if pid == FULL:
                folder = FULL_FOLDER
            else:
                party = self.store.party(pid)
                assert party is not None
                folder = party["folder"]
            final = party_dir(self.parties_dir, folder)
            tmp = self.parties_dir / f".tmp-{pid}"
            old = self.parties_dir / f".old-{pid}"
            # 1. Remise en ordre du dossier actuel (mods déposés par le jeu).
            if final.is_dir():
                tidy = self.tidy(final)
                report.merge(tidy)
                if tidy.added and pid != FULL:
                    self.store.change_mods("add", "party", tidy.added, pid=pid)
            # Restes d'une opération précédente (ne contiennent que des liens).
            for leftover in (tmp, old):
                if os.path.lexists(leftover):
                    report.merge(self.empty(leftover))
            # 2-3. Mods actifs, construction à part.
            ids = self.active_ids(pid)
            self._journal(op="apply", party=pid, folder=folder, step="build")
            try:
                entries, missing, blocked = self._build(tmp, ids)
            except LinkError as exc:
                try:
                    self.empty(tmp)
                finally:
                    self._journal_done()
                raise ApplyError(exc.key, **exc.params) from exc
            count = len(entries)
            # 4. Bascule.
            self._journal(op="apply", party=pid, folder=folder, step="swap")
            try:
                if os.path.lexists(final):
                    os.rename(final, old)
                os.rename(tmp, final)
            except OSError as exc:
                if not os.path.lexists(final) and os.path.lexists(old):
                    os.rename(old, final)  # retour à l'état d'avant
                self.empty(tmp)
                self._journal_done()
                raise ApplyError("apply.folder_busy", path=str(final), detail=str(exc)) from exc
            if os.path.lexists(old):
                report.merge(self.empty(old))
            # 5. Inventaire.
            self.inventory.set_folder(folder, entries)
            target = final

        # 6. Override, 7. partie appliquée.
        self._journal(op="apply", party=pid, folder=target.name, step="override", directory=str(target))
        self._write_override(gs, target)
        self.store.record_applied(pid, self.signature_of(pid))
        self._journal_done()
        log.info("Partie %s appliquée (%s) : %d mods, %d manquants, %d bloqués", pid, self.vp.version.id,
                 count, len(missing), len(blocked))
        return {"party": pid, "count": count, "missing": missing, "blocked": blocked, "directory": str(target),
                "tidy": report.to_json()}

    def _write_override(self, gs: Path, target: Path) -> None:
        try:
            gamesettings.write_override(gs, str(target), True)
        except gamesettings.WriteError as exc:
            raise ApplyError(exc.key, status=500, **exc.params) from exc

    # ------------------------------------------------------------------
    # Reprise après une coupure
    # ------------------------------------------------------------------

    def recover(self) -> str | None:
        """Termine ou annule une opération interrompue. Renvoie « finished »,
        « cancelled » ou None (rien à faire)."""
        job = self.pending()
        if job is None:
            return None
        step = job.get("step")
        pid = str(job.get("party") or "")
        log.warning("Opération interrompue trouvée (%s) : %s", self.vp.version.id, job)
        tmp = self.parties_dir / f".tmp-{pid}"
        old = self.parties_dir / f".old-{pid}"
        folder = str(job.get("folder") or "")
        final = self.parties_dir / folder if folder else None
        try:
            if job.get("op") == "apply" and step == "build":
                if os.path.lexists(tmp):
                    self.empty(tmp)
                self._journal_done()
                return "cancelled"
            if job.get("op") == "apply" and step == "swap" and final is not None:
                if os.path.lexists(tmp) and not os.path.lexists(final):
                    os.rename(tmp, final)
                elif os.path.lexists(tmp):
                    self.empty(tmp)  # bascule pas commencée : rien n'a changé
                    if os.path.lexists(old):
                        self.empty(old)
                    self._journal_done()
                    return "cancelled"
                if os.path.lexists(old):
                    self.empty(old)
                self.inventory.set_folder(folder, self._scan_inventory(final))
                step = "override"
                job["directory"] = str(final)
            if step == "override" and job.get("directory"):
                gs = self.vp.gamesettings
                if gs is not None and gs.is_file():
                    self._write_override(gs, Path(job["directory"]))
                if self.store.known(pid):
                    self.store.record_applied(pid, self.signature_of(pid))
                self._journal_done()
                return "finished"
            if job.get("op") == "rename":
                return self._recover_rename(job)
            if job.get("op") == "mod_rename":
                from fspassion import modops  # import tardif : modops utilise ce module

                return modops.recover_rename(self, job)
        except (OSError, ApplyError) as exc:
            log.error("Reprise de l'opération impossible : %s", exc)
            return None
        self._journal_done()
        return "cancelled"

    # ------------------------------------------------------------------
    # Renommer et supprimer un dossier de partie
    # ------------------------------------------------------------------

    def rename(self, old_folder: str, new_folder: str, applied: bool) -> None:
        """Le dossier suit le nom de la partie ; l'override suit si c'est la
        partie appliquée."""
        src = party_dir(self.parties_dir, old_folder)
        dst = party_dir(self.parties_dir, new_folder)
        if old_folder == new_folder:
            return
        if not os.path.lexists(src):
            return  # partie jamais appliquée : pas de dossier
        if os.path.lexists(dst) and old_folder.lower() != new_folder.lower():
            raise ApplyError("apply.folder_exists", path=str(dst))
        self._journal(op="rename", old=old_folder, new=new_folder, applied=applied)
        try:
            os.rename(src, dst)
        except OSError as exc:
            self._journal_done()
            raise ApplyError("apply.folder_busy", path=str(src), detail=str(exc)) from exc
        self.inventory.rename_folder(old_folder, new_folder)
        if applied:
            gs = self.vp.gamesettings
            if gs is not None and gs.is_file():
                self._write_override(gs, dst)
        self._journal_done()

    def _recover_rename(self, job: dict[str, Any]) -> str:
        src = self.parties_dir / str(job.get("old"))
        dst = self.parties_dir / str(job.get("new"))
        if os.path.lexists(src) and not os.path.lexists(dst):
            os.rename(src, dst)
        self.inventory.rename_folder(str(job.get("old")), str(job.get("new")))
        if job.get("applied") and dst.is_dir():
            gs = self.vp.gamesettings
            if gs is not None and gs.is_file():
                self._write_override(gs, dst)
        self._journal_done()
        return "finished"

    def delete(self, folder: str) -> Tidy:
        """Vide (lien par lien) et supprime le dossier d'une partie. Les
        fichiers physiques sont rapatriés, jamais supprimés."""
        path = party_dir(self.parties_dir, folder)
        res = self.empty(path) if os.path.lexists(path) else Tidy()
        self.inventory.drop_folder(folder)
        return res

    def is_stale(self, pid: str) -> bool:
        """La partie appliquée a-t-elle changé depuis sa dernière application ?
        Partie Pleine avec plusieurs stockages : un mod ajouté ou retiré
        d'un stockage la rend « à réappliquer », comme une partie ordinaire."""
        if pid == EMPTY:
            return False
        if pid == FULL and not self.multi:
            # Retour à un seul stockage alors que le jeu lit encore « _pleine ».
            return os.path.lexists(self.parties_dir / FULL_FOLDER)
        if is_special(pid) and pid != FULL:
            return False
        sig = (self.store.data.get("applied_signature") or {}).get(pid)
        try:
            return sig != self.signature_of(pid)
        except ApplyError:
            return False
