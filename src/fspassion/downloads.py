"""Téléchargements et intégration.

- Dossier : downloads_dir, unique pour toutes les versions du jeu (le dossier
  Téléchargements de Windows par défaut).
- Quoi : les .zip du dossier, sans les sous-dossiers. Lire la table des matières
  d'un .zip ne prend que quelques millisecondes. Les téléchargements en cours
  sont ignorés (.crdownload, .part…, ou fichier modifié depuis moins de 10 s).
- Un .zip est un mod s'il contient modDesc.xml à sa racine.
- Destination : le dossier de mods de la version détectée (préfixe, puis
  descVersion), modifiable dans la fenêtre « Nouveaux mods trouvés ».

Intégration = déplacement du fichier : instantané sur le même disque ;
sinon copie vérifiée (taille et intégrité de l'archive), puis suppression de
l'original. Un doublon créé par le navigateur, « FS25_X (1).zip », est intégré
sous le nom « FS25_X.zip » : c'est l'annulation du suffixe du navigateur, pas
un renommage du mod (son contenu n'est jamais touché).

Remplacement : une version plus récente remplace l'ancienne, qui est mise
de côté dans « Old versions » (jamais supprimée) ; une version plus
ancienne ne remplace jamais sans confirmation (case cochée par l'utilisateur).
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
import zipfile
from pathlib import Path
from typing import Any

from fspassion import fsutil, icons, links, moddesc, versions
from fspassion.apply import OLD_VERSIONS
from fspassion.gamepaths import VersionPaths

log = logging.getLogger(__name__)

PARTIAL_SUFFIXES = (".crdownload", ".part", ".partial", ".tmp", ".opdownload", ".download")
STABLE_SECONDS = 10
MAX_IGNORED = 500

# Suffixe ajouté par un navigateur à un doublon : « FS25_X (1) », « FS25_X(2) »
_BROWSER_SUFFIX_RE = re.compile(r"\s*\(\d{1,3}\)$")
_VERSION_RE = re.compile(r"\d+")


def strip_browser_suffix(stem: str) -> str:
    return _BROWSER_SUFFIX_RE.sub("", stem)


def _version_tuple(v: str | None) -> tuple[int, ...] | None:
    if not v:
        return None
    parts = _VERSION_RE.findall(str(v))
    return tuple(int(p) for p in parts[:6]) if parts else None


def ignore_key(name: str, size: int, mtime: float) -> str:
    return f"{name.lower()}|{size}|{int(mtime)}"


def _sha1(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_ok(p: Path) -> bool:
    """Intégrité d'une archive copiée : table des matières, modDesc.xml à la
    racine, et contrôle (CRC) de chaque fichier."""
    try:
        with zipfile.ZipFile(p, "r") as zf:
            if zf.testzip() is not None:
                return False
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError):
        return False
    res = moddesc.read_zip(p)
    return bool(res.ok)


# --------------------------------------------------------------------------
# Recherche des nouveaux mods
# --------------------------------------------------------------------------

def scan_folder(folder: Path, ignored: set[str] | None = None, now: float | None = None) -> list[dict[str, Any]]:
    """Mods .zip du dossier de téléchargements (sans les sous-dossiers)."""
    ignored = ignored or set()
    now = time.time() if now is None else now
    try:
        entries = list(os.scandir(folder))
    except OSError as exc:
        log.warning("Dossier des téléchargements illisible %s : %s", folder, exc)
        return []
    names = {e.name.lower() for e in entries}
    out: list[dict[str, Any]] = []
    for e in sorted(entries, key=lambda x: x.name.lower()):
        low = e.name.lower()
        if not low.endswith(".zip") or not e.is_file(follow_symlinks=False):
            continue
        # Téléchargement en cours : « x.zip.part » à côté de « x.zip » (Firefox).
        if any(f"{low}{suf}" in names for suf in PARTIAL_SUFFIXES):
            continue
        try:
            st = e.stat()
        except OSError:
            continue
        if now - st.st_mtime < STABLE_SECONDS:
            continue
        if ignore_key(e.name, st.st_size, st.st_mtime) in ignored:
            continue
        path = Path(e.path)
        res = moddesc.read_zip(path)
        if not res.ok or res.info is None:
            continue  # pas un mod (pack à décompresser, autre archive…)
        info = res.info
        stem = e.name[:-4]
        mod_id = strip_browser_suffix(stem)
        gv = versions.detect_mod_version(mod_id, info.desc_version)
        icon = None
        if res.icon_path:
            data = moddesc.read_icon_bytes(path, "zip", res.icon_path)
            icon = icons.small_data_url(data) if data else None
        out.append({
            "file": e.name,
            "path": str(path),
            "size": st.st_size,
            "mtime": int(st.st_mtime),
            "id": mod_id,
            "suffix_removed": mod_id != stem,
            "titles": info.titles,
            "version": info.version,
            "author": info.author,
            "is_map": info.is_map,
            "map_titles": info.map_titles,
            "detected": gv.version,
            "gv_status": gv.status,
            "icon": icon,
        })
    return out


def assess(item: dict[str, Any], vp: VersionPaths | None) -> dict[str, Any]:
    """État d'un téléchargement pour une version du jeu :
    new · update (de → vers) · older · present · conflict · unconfigured."""
    if vp is None or vp.mods_dir is None or not vp.mods_dir.is_dir():
        return {"state": "unconfigured", "checked": False}
    mod_id = item["id"]
    existing: Path | None = None
    storage = 0
    for i, folder in enumerate(vp.storages):
        for cand in (folder / f"{mod_id}.zip", folder / mod_id):
            if os.path.lexists(cand):
                existing, storage = cand, i
                break
        if existing is not None:
            break
    if existing is None:
        return {"state": "new", "checked": True}
    if links.kind_of(existing) != "file":
        # Un mod non compressé porte déjà ce nom : le jeu ne saurait lequel charger.
        return {"state": "conflict", "checked": False, "storage": storage}
    res = moddesc.read_zip(existing)
    old_v = res.info.version if res.ok and res.info else None
    new_t, old_t = _version_tuple(item.get("version")), _version_tuple(old_v)
    base = {"from": old_v, "to": item.get("version"), "storage": storage}
    try:
        st = existing.stat()
    except OSError:
        return {"state": "new", "checked": True}
    if st.st_size == item["size"] and (new_t == old_t or new_t is None or old_t is None):
        try:
            if _sha1(existing) == _sha1(Path(item["path"])):
                return {"state": "present", "checked": False, **base}
        except OSError:
            pass
    if new_t is not None and old_t is not None and new_t != old_t:
        newer = new_t > old_t
    else:
        newer = item["mtime"] > int(st.st_mtime)
    if newer:
        return {"state": "update", "checked": True, **base}
    return {"state": "older", "checked": False, **base}


# --------------------------------------------------------------------------
# Intégration
# --------------------------------------------------------------------------

def _aside(fsp_dir: Path, path: Path, stamp: str) -> Path:
    """L'ancienne version d'un mod remplacé est mise de côté, jamais supprimée."""
    from fspassion.apply import migrate_aside_folders  # import tardif

    migrate_aside_folders(fsp_dir)
    base = fsp_dir / OLD_VERSIONS / stamp
    base.mkdir(parents=True, exist_ok=True)
    dst = base / path.name
    n = 2
    while os.path.lexists(dst):
        dst = base / f"{path.stem} ({n}){path.suffix}"
        n += 1
    fsutil.relocate(path, dst)  # copie vérifiée si le mod est sur un autre disque
    log.warning("Ancienne version mise de côté : %s → %s", path, dst)
    return dst


def integrate_file(src: Path, vp: VersionPaths, mod_id: str, replace_older: bool = False,
                   stamp: str | None = None, storage: int = 0) -> dict[str, Any]:
    """Déplace un téléchargement dans un dossier de stockage de `vp` : celui
    choisi (`storage`, 0 = principal) pour un mod nouveau, celui du mod déjà
    présent pour une mise à jour. Renvoie {result: new|updated|skipped, file} ;
    avec `from` et `to` pour une mise à jour, `reason` pour un saut. Lève
    fsutil.MoveError (ou OSError) en cas d'échec : rien n'est alors changé
    dans le dossier de mods. L'archive est contrôlée avant tout déplacement,
    y compris sur le même disque."""
    assert vp.mods_dir is not None
    stamp = stamp or time.strftime("%Y-%m-%d_%H%M%S")
    item = {"id": mod_id, "path": str(src), "size": src.stat().st_size, "mtime": int(src.stat().st_mtime)}
    try:
        res = moddesc.read_zip(src)
        item["version"] = res.info.version if res.ok and res.info else None
    except Exception:  # noqa: BLE001
        item["version"] = None
    state = assess(item, vp)
    folder = vp.storages[int(state.get("storage") or 0)] if state.get("storage") is not None else vp.mods_dir
    dst = folder / f"{mod_id}.zip"
    if state["state"] in ("present", "conflict", "unconfigured"):
        return {"result": "skipped", "file": dst.name, "reason": state["state"]}
    if state["state"] == "older" and not replace_older:
        return {"result": "skipped", "file": dst.name, "reason": "older"}
    if not archive_ok(src):
        raise fsutil.MoveError("downloads.failed", src.name)
    if state["state"] == "new":
        if 0 < storage < len(vp.storages) and vp.storages[storage].is_dir():
            dst = vp.storages[storage] / f"{mod_id}.zip"
        fsutil.move_file(src, dst, archive_ok)
        log.info("Téléchargement intégré : %s → %s", src, dst)
        return {"result": "new", "file": dst.name}
    # Mise à jour : le nouveau fichier d'abord à côté (copie vérifiée), puis bascule.
    tmp = dst.with_name(f".fsp-in-{dst.name}.part")
    if os.path.lexists(tmp):
        os.unlink(tmp)
    fsutil.move_file(src, tmp, archive_ok)
    fsp = vp.fsp_dir or (vp.mods_dir.parent / "FSPassion" / vp.version.id)
    try:
        _aside(fsp, dst, stamp)
    except OSError:
        fsutil.move_file(tmp, src)  # retour du fichier à sa place
        raise
    os.replace(tmp, dst)
    log.info("Mise à jour intégrée : %s → %s (%s → %s)", src, dst, state.get("from"), state.get("to"))
    return {"result": "updated", "file": dst.name, "from": state.get("from"), "to": state.get("to")}
