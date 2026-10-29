"""Les DLC : affichage informatif en V1.

- Détection : fichiers .dlc (payants, chiffrés) et .zip (gratuits) des deux
  dossiers DLC de la version. Un DLC présent aux deux endroits n'apparaît
  qu'une fois.
- Nom : le nom du catalogue (titres du wiki Farming Simulator), pour
  un .dlc comme pour un .zip ; sinon le titre du modDesc.xml d'un .zip ;
  repli : nom de fichier rendu lisible.
- Règles par mots-clés : une entrée du catalogue avec « keywords » reconnaît
  tout DLC dont le nom de fichier contient ces mots (ex. « profarm » en FS2011).
- Icône : toujours celle du dossier icons_dlc_<version>, jamais celle du .zip.
- Catalogue : instantané embarqué (assets\\fallback) ou catalogue téléchargé
  depuis GitHub (dlcremote.py) ; le plus récent des deux l'emporte.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from fspassion import config, fsutil, icons, moddesc
from fspassion.versions import GameVersion

log = logging.getLogger(__name__)

DLC_EXTS = (".dlc", ".zip")
WIDE_RATIO = 1.6  # au-delà : tuile large (icône 460 × 215 de FS2011 / FS2013)


def prettify(stem: str) -> str:
    """« skyAgriculturePack » → « Sky Agriculture Pack »."""
    s = re.sub(r"^(?:FS|LS)\d{2}_", "", stem, flags=re.IGNORECASE)
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return " ".join(w[:1].upper() + w[1:] for w in s.split(" ")) or stem


def catalog_paths() -> list[Path]:
    """Catalogues, du plus récent (téléchargé) à l'instantané embarqué."""
    out = [config.dlc_cache_dir() / "dlc_catalog.json"]
    out.append(config.assets_dir() / "fallback" / "dlc_catalog.json")
    return out


def load_catalog() -> dict[str, Any]:
    """Le catalogue le plus récent (champ « updated ») : celui téléchargé depuis
    GitHub, ou l'instantané embarqué. À égalité, le téléchargé."""
    best: dict[str, Any] | None = None
    for i, p in enumerate(catalog_paths()):
        data = fsutil.read_json(p, None)
        if not isinstance(data, dict) or not isinstance(data.get("versions"), dict):
            continue
        if best is None or str(data.get("updated") or "") > str(best.get("updated") or ""):
            best = dict(data)
            best["_remote"] = i == 0
    return best or {"versions": {}}


def icon_dirs(folder_name: str) -> list[Path]:
    """Dossiers où chercher les icônes de DLC d'une version."""
    dirs = [config.dlc_cache_dir() / folder_name, config.assets_dir() / "fallback" / folder_name]
    if not config.is_frozen():
        # Développement : dépôt de données voisin FSPassion-data/dlc/…
        dirs.append(config.dev_data_dir() / "dlc" / folder_name)
    return dirs


def match_entry(stem: str, entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    low = stem.lower()
    for e in entries:
        if e.get("file") and str(e["file"]).lower() == low:
            return e
    for e in entries:
        if not e.get("file") and e.get("keywords"):
            kws = [str(k).lower() for k in e["keywords"]]
            if all(k in low for k in kws):
                return e
    return None


def is_released(entry: dict[str, Any], today: str) -> bool:
    """Un DLC « announced » n'est sorti qu'à sa date de sortie (AAAA-MM-JJ)."""
    if entry.get("status") != "announced":
        return True
    rd = entry.get("release_date")
    return isinstance(rd, str) and rd <= today


def find_icon(folder_name: str, stem: str, entry: dict[str, Any] | None) -> Path | None:
    wanted: list[str] = []
    if entry and entry.get("icon"):
        wanted.append(str(entry["icon"]))
    wanted += [stem + ".png", stem + ".jpg", stem + ".jpeg", stem + ".webp"]
    wanted_low = [w.lower() for w in wanted]
    for d in icon_dirs(folder_name):
        try:
            with os.scandir(d) as it:
                files = {e.name.lower(): e.path for e in it if e.is_file()}
        except OSError:
            continue
        for w in wanted_low:
            if w in files:
                return Path(files[w])
    return None


def scan_dlc(v: GameVersion, dlc_dirs: list[Path], lang: str | None = None) -> list[dict[str, Any]]:
    """Liste des DLC installés d'une version."""
    catalog = load_catalog()
    vcat = (catalog.get("versions") or {}).get(v.id) or {}
    entries = vcat.get("dlc") or []
    folder_name = vcat.get("icons_folder") or v.dlc_icons_folder

    # « fixed_order » (FS2011) — les DLC gardent l'ordre du catalogue.
    fixed = bool(vcat.get("fixed_order"))
    rank_of = {id(e): i for i, e in enumerate(entries)}

    seen: dict[str, dict[str, Any]] = {}
    matched: set[int] = set()
    for d in dlc_dirs:
        try:
            with os.scandir(d) as it:
                files = [e for e in it if e.is_file()]
        except OSError:
            continue
        for e in files:
            name = e.name
            low = name.lower()
            ext = os.path.splitext(low)[1]
            if ext not in DLC_EXTS:
                continue
            stem = name[: -len(ext)]
            key = stem.lower()
            if key in seen:
                continue
            entry = match_entry(stem, entries)
            if entry is not None:
                matched.add(id(entry))
            title_names: dict[str, str] = {}
            if ext == ".zip":
                res = moddesc.read_zip(Path(e.path))
                if res.ok and res.info is not None:
                    title_names = dict(res.info.titles)
            names: dict[str, str] = {}
            if entry and (entry.get("names") or entry.get("name")):
                if entry.get("names"):
                    names.update(entry["names"])
                if entry.get("name"):
                    names.setdefault("en", entry["name"])
                    names.setdefault("_", entry["name"])
            elif title_names:
                names.update(title_names)
            if not names:
                names["_"] = prettify(stem)
            icon = find_icon(folder_name, stem, entry)
            shape = "square"
            if icon is not None:
                size = icons.image_size(icon)
                if size and size[1] and size[0] / size[1] > WIDE_RATIO:
                    shape = "wide"
            seen[key] = {
                "id": stem,
                "file": name,
                "type": "zip" if ext == ".zip" else "dlc",
                "names": names,
                "known": entry is not None,
                "present": True,
                "icon": icon.name if icon else None,
                "_icon_path": str(icon) if icon else None,
                "shape": shape,
            }
            if fixed:
                seen[key]["rank"] = rank_of.get(id(entry), len(entries)) if entry is not None else len(entries)
    # Les DLC du catalogue absents de ce PC, affichés estompés. Un DLC pas
    # encore sorti (annoncé, date de sortie à venir ou inconnue) n'est pas montré.
    today = time.strftime("%Y-%m-%d")
    for i, entry in enumerate(entries):
        if id(entry) in matched or not entry.get("name") or not is_released(entry, today):
            continue
        names = dict(entry.get("names") or {})
        names.setdefault("en", entry["name"])
        names.setdefault("_", entry["name"])
        stem = str(entry.get("file") or "")
        icon = find_icon(folder_name, stem, entry) if (stem or entry.get("icon")) else None
        shape = "square"
        if icon is not None:
            size = icons.image_size(icon)
            if size and size[1] and size[0] / size[1] > WIDE_RATIO:
                shape = "wide"
        seen[f"catalog:{i}"] = {
            "id": stem or f"catalog-{i}",
            "file": entry.get("file"),
            "type": entry.get("type") or "dlc",
            "names": names,
            "known": True,
            "present": False,
            "icon": icon.name if icon else None,
            "_icon_path": str(icon) if icon else None,
            "shape": shape,
        }
        if fixed:
            seen[f"catalog:{i}"]["rank"] = i
    if fixed:
        return sorted(seen.values(), key=lambda x: (x["rank"], x["id"].lower()))
    return sorted(seen.values(), key=lambda x: (not x.get("present", True), x["id"].lower()))


def detected_stems(dlc_dirs: list[Path]) -> list[str]:
    """Noms (sans extension) des DLC présents, sans lire leur contenu."""
    out: dict[str, str] = {}
    for d in dlc_dirs:
        try:
            with os.scandir(d) as it:
                names = [e.name for e in it if e.is_file()]
        except OSError:
            continue
        for name in names:
            stem, ext = os.path.splitext(name)
            if ext.lower() in DLC_EXTS:
                out.setdefault(stem.lower(), stem)
    return sorted(out.values(), key=str.lower)
