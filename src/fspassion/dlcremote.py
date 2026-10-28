"""Catalogue des DLC distant (4.11, 7.6), version 0.7.0.

Le catalogue (dlc_catalog.json) et les icônes des DLC sont publiés dans un
dépôt GitHub public séparé, « FSPassion-data », que l'auteur met à jour
lui-même : un nouveau DLC n'oblige pas à publier une nouvelle version de
FS Passion.

Règles :
- seulement si l'accès Internet est autorisé (réglage, activé par défaut) ;
- le catalogue est téléchargé au plus une fois par jour, et gardé dans
  %LOCALAPPDATA%\\FSPassion\\dlc\\ ;
- les icônes manquantes sont téléchargées une par une : celles des DLC
  détectés sur ce PC d'abord, puis (0.8.2) celles des DLC du catalogue que
  l'on ne possède pas, affichés estompés (0.7.5) : sans elles, leurs tuiles
  restaient vides ;
- une icône qui porte une empreinte (« sha256 ») dans le catalogue est
  refusée si le fichier reçu ne lui correspond pas ;
- adresses en https, sur raw.githubusercontent.com seulement, sans
  redirection vers un autre site ; tailles limitées ; une image doit être un
  vrai PNG, JPEG, WebP ou AVIF (0.8.2 : 20 icônes du dépôt sont des AVIF
  nommés « .jpg », elles étaient refusées) ;
- aucune donnée personnelle n'est envoyée : une simple lecture de fichiers
  publics, sans identifiant ni cookie ;
- hors ligne : l'instantané embarqué (assets\\fallback\\dlc_catalog.json)
  suffit. Le plus récent des deux catalogues (champ « updated ») l'emporte.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from fspassion import config, dlc, fsutil

log = logging.getLogger(__name__)

HOST = "raw.githubusercontent.com"
CATALOG_PATH = "dlc/dlc_catalog.json"
CATALOG_SCHEMA = 1
REFRESH_S = 24 * 3600
TIMEOUT = 20
MAX_CATALOG = 2 * 1024 * 1024
MAX_ICON = 3 * 1024 * 1024
META = "catalog_meta.json"

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.()&+'-]{0,120}$")
_FOLDER_RE = re.compile(r"^icons_dlc_fs\d{2}$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


class RemoteError(Exception):
    def __init__(self, key: str, **params: Any) -> None:
        super().__init__(key)
        self.key = key
        self.params = params


# --------------------------------------------------------------------------
# Adresses
# --------------------------------------------------------------------------

def base_url(app_info: dict[str, Any]) -> str | None:
    """Adresse du dépôt de données (app_info.json → remote_data.base_url),
    seulement en https sur raw.githubusercontent.com."""
    info = app_info.get("remote_data")
    url = info.get("base_url") if isinstance(info, dict) else None
    if not isinstance(url, str) or not url:
        return None
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or (parts.hostname or "").lower() != HOST:
        return None
    if parts.username or parts.password or parts.port or parts.query or parts.fragment:
        return None
    return url if url.endswith("/") else url + "/"


def _safe_name(name: Any) -> bool:
    return isinstance(name, str) and bool(_NAME_RE.match(name)) and ".." not in name


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Aucune redirection : la réponse doit venir de l'adresse demandée."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        raise urllib.error.HTTPError(req.full_url, code, "redirection refusée", headers, fp)


_opener = urllib.request.build_opener(_NoRedirect)


def fetch(url: str, max_bytes: int) -> bytes:
    """Télécharge un fichier public. Lève RemoteError (« not_found » pour une
    adresse inexistante, « unreachable » sinon)."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or (parts.hostname or "").lower() != HOST:
        raise RemoteError("unreachable", detail="adresse refusée")
    req = urllib.request.Request(url, headers={"User-Agent": "FSPassion", "Accept": "*/*"})
    try:
        with _opener.open(req, timeout=TIMEOUT) as r:  # noqa: S310 - https vérifié ci-dessus
            data = r.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RemoteError("not_found", detail="404") from exc
        raise RemoteError("unreachable", detail=f"HTTP {exc.code}") from exc
    except (OSError, ValueError) as exc:
        raise RemoteError("unreachable", detail=str(exc)) from exc
    if len(data) > max_bytes:
        raise RemoteError("too_big")
    return data


# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------

def _clean_entry(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    out: dict[str, Any] = {}
    file = raw.get("file")
    if file is not None:
        if not _safe_name(file):
            return None
        out["file"] = file
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    out["name"] = name.strip()[:120]
    names = raw.get("names")
    if isinstance(names, dict):
        out["names"] = {str(k)[:12]: str(v)[:120] for k, v in names.items() if isinstance(v, str) and v.strip()}
    kws = raw.get("keywords")
    if isinstance(kws, list):
        out["keywords"] = [str(k).lower()[:40] for k in kws if isinstance(k, str) and k.strip()][:8]
    # 0.7.5 : une entrée sans fichier ni mot-clé (DLC non possédé) est gardée ; elle
    # s'affiche comme absente et ne reconnaît aucun fichier.
    for key in ("type", "status"):
        if isinstance(raw.get(key), str):
            out[key] = raw[key][:20]
    if isinstance(raw.get("verified"), bool):
        out["verified"] = raw["verified"]
    icon = raw.get("icon")
    if icon is not None:
        if not _safe_name(icon):
            return None
        out["icon"] = icon
    sha = raw.get("sha256")
    if isinstance(sha, str) and _SHA_RE.match(sha):
        out["sha256"] = sha.lower()
    return out


def validate_catalog(raw: Any) -> dict[str, Any]:
    """Contrôle un catalogue reçu. Lève RemoteError(« invalid ») s'il est
    inutilisable ; une entrée abîmée est seulement écartée."""
    if not isinstance(raw, dict):
        raise RemoteError("invalid")
    schema = raw.get("schema")
    if not isinstance(schema, int) or schema < 1:
        raise RemoteError("invalid")
    if schema > CATALOG_SCHEMA:
        raise RemoteError("too_new")
    vers = raw.get("versions")
    if not isinstance(vers, dict):
        raise RemoteError("invalid")
    out_versions: dict[str, Any] = {}
    for vid, vcat in vers.items():
        if not isinstance(vcat, dict) or not isinstance(vid, str) or not re.match(r"^FS\d{2,4}$", vid):
            continue
        folder = vcat.get("icons_folder")
        if not isinstance(folder, str) or not _FOLDER_RE.match(folder):
            continue
        entries = [e for e in (_clean_entry(x) for x in vcat.get("dlc") or []) if e is not None]
        out_versions[vid] = {"icons_folder": folder, "dlc": entries}
        # 0.8.5 : l'ordre imposé (FS2011) était perdu au nettoyage du catalogue
        # téléchargé, qui l'emporte sur le catalogue embarqué à date égale.
        if vcat.get("fixed_order") is True:
            out_versions[vid]["fixed_order"] = True
    updated = raw.get("updated")
    return {
        "schema": schema,
        "updated": updated if isinstance(updated, str) and _DATE_RE.match(updated) else "",
        "versions": out_versions,
    }


def meta_path() -> Path:
    return config.dlc_cache_dir() / META


def read_meta() -> dict[str, Any]:
    data = fsutil.read_json(meta_path(), {}) or {}
    return data if isinstance(data, dict) else {}


def _write_meta(meta: dict[str, Any]) -> None:
    try:
        fsutil.atomic_write_json(meta_path(), meta)
    except OSError as exc:
        log.warning("État du catalogue des DLC non enregistré : %s", exc)


def due(meta: dict[str, Any], now: float | None = None) -> bool:
    """Au plus une tentative par jour (réussie ou non)."""
    now = time.time() if now is None else now
    last = meta.get("last_try")
    return not isinstance(last, (int, float)) or now - last >= REFRESH_S or now < last


def update_catalog(app_info: dict[str, Any], force: bool = False) -> dict[str, Any]:
    """Télécharge le catalogue s'il est dû. Renvoie {"status": …}."""
    base = base_url(app_info)
    if base is None:
        return {"status": "no_source"}
    meta = read_meta()
    if not force and not due(meta):
        return {"status": "recent"}
    meta["last_try"] = time.time()
    try:
        data = fetch(base + CATALOG_PATH, MAX_CATALOG)
        try:
            raw = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise RemoteError("invalid") from exc
        catalog = validate_catalog(raw)
    except RemoteError as exc:
        meta["last_error"] = exc.key
        _write_meta(meta)
        log.info("Catalogue des DLC non téléchargé (%s%s)", exc.key,
                 f" : {exc.params['detail']}" if exc.params.get("detail") else "")
        return {"status": "error", "error": exc.key}
    target = config.dlc_cache_dir() / "dlc_catalog.json"
    changed = fsutil.read_json(target, None) != catalog
    if changed:
        fsutil.atomic_write_json(target, catalog)
    meta.update({"last_error": None, "fetched": time.time(), "updated": catalog["updated"]})
    _write_meta(meta)
    log.info("Catalogue des DLC %s (mis à jour le %s)", "téléchargé" if changed else "inchangé",
             catalog["updated"] or "?")
    return {"status": "updated" if changed else "unchanged", "updated": catalog["updated"]}


# --------------------------------------------------------------------------
# Icônes des DLC détectés
# --------------------------------------------------------------------------

def _image_ok(data: bytes) -> bool:
    """PNG, JPEG, WebP ou AVIF, reconnus à leur contenu (pas à l'extension)."""
    return (data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff")
            or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")
            or (data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis")))


def _icon_names(entry: dict[str, Any], stem: str = "") -> list[str]:
    """Noms possibles de l'icône d'une entrée du catalogue, sur le dépôt."""
    if entry.get("icon"):
        return [str(entry["icon"])]
    base = str(entry.get("file") or stem)
    return [f"{base}.png", f"{base}.jpg"] if base else []


def wanted_icons(catalog: dict[str, Any], detected: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Icônes à télécharger, dont l'icône n'est encore nulle part sur ce PC (ou
    ne correspond pas à son empreinte) : d'abord celles des DLC détectés,
    reconnus par le catalogue ; puis (0.8.2) celles de tous les autres DLC du
    catalogue, que l'on ne possède pas (tuiles estompées)."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def consider(vid: str, folder: str, entry: dict[str, Any], stem: str) -> None:
        names = _icon_names(entry, stem)
        if not names:
            return
        key = (folder, names[0].lower())
        if key in seen:
            return
        seen.add(key)
        sha = entry.get("sha256")
        cached = config.dlc_cache_dir() / folder
        found = dlc.find_icon(folder, stem or str(entry.get("file") or ""), entry)
        if found is not None:
            if not sha or found.parent != cached or _sha(found) == sha:
                return
        out.append({"version": vid, "folder": folder, "names": names, "sha256": sha})

    versions_cat = catalog.get("versions") or {}
    for vid, stems in detected.items():
        vcat = versions_cat.get(vid) or {}
        folder = vcat.get("icons_folder")
        if not folder or not stems:
            continue
        entries = vcat.get("dlc") or []
        for stem in stems:
            entry = dlc.match_entry(stem, entries)
            if entry is not None:
                consider(vid, folder, entry, stem)
    for vid, vcat in versions_cat.items():
        folder = vcat.get("icons_folder")
        if not folder:
            continue
        for entry in vcat.get("dlc") or []:
            consider(vid, folder, entry, "")
    return out


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def download_icons(app_info: dict[str, Any], items: list[dict[str, Any]], limit: int = 200) -> dict[str, int]:
    """Télécharge les icônes demandées, une par une. Renvoie les compteurs."""
    base = base_url(app_info)
    res = {"downloaded": 0, "failed": 0, "missing": 0}
    if base is None:
        return res
    for item in items[:limit]:
        folder = item["folder"]
        got = False
        for name in item["names"]:
            if not _safe_name(name) or not _FOLDER_RE.match(folder):
                continue
            url = base + "dlc/" + folder + "/" + urllib.parse.quote(name)
            try:
                data = fetch(url, MAX_ICON)
            except RemoteError as exc:
                if exc.key == "not_found":
                    continue
                res["failed"] += 1
                got = True  # erreur réseau : inutile d'essayer l'autre extension
                break
            if not _image_ok(data):
                log.warning("Icône de DLC refusée (pas une image) : %s/%s", folder, name)
                res["failed"] += 1
                got = True
                break
            if item.get("sha256") and hashlib.sha256(data).hexdigest() != item["sha256"]:
                log.warning("Icône de DLC refusée (empreinte différente) : %s/%s", folder, name)
                res["failed"] += 1
                got = True
                break
            fsutil.atomic_write_bytes(config.dlc_cache_dir() / folder / name, data)
            res["downloaded"] += 1
            got = True
            break
        if not got:
            res["missing"] += 1
    if res["downloaded"] or res["failed"]:
        log.info("Icônes de DLC : %d téléchargées, %d refusées ou en échec, %d absentes du dépôt",
                 res["downloaded"], res["failed"], res["missing"])
    return res


def status(app_info: dict[str, Any], enabled: bool) -> dict[str, Any]:
    """État affiché dans les paramètres."""
    meta = read_meta()
    current = dlc.load_catalog()
    return {
        "enabled": enabled,
        "source_ok": base_url(app_info) is not None,
        "updated": current.get("updated") or "",
        "remote": bool(current.get("_remote")),
        "fetched": meta.get("fetched"),
        "last_try": meta.get("last_try"),
        "error": meta.get("last_error"),
    }
