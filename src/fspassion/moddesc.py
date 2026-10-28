"""Lecture des mods : archives .zip et dossiers non compressés (4.4).

Invariant I9 : FS Passion n'ouvre jamais un .zip en écriture. Ce module ne fait
que lire la table des matières de l'archive et le fichier modDesc.xml.

La lecture du XML est tolérante : marque BOM, encodages anciens, petites
erreurs (« & » non échappé, caractères de contrôle). Si le XML reste
illisible, les informations essentielles sont extraites par expressions
régulières, et le mod est signalé (anomalie A3).
"""

from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

MODDESC = "moddesc.xml"
# Taille maximale lue d'un modDesc.xml : un fichier plus gros n'est pas un
# modDesc.xml réel, et il n'est pas lu en entier.
MAX_MODDESC_BYTES = 2 * 1024 * 1024
ICON_EXTS = (".dds", ".png")


# --------------------------------------------------------------------------
# Résultat de lecture
# --------------------------------------------------------------------------

@dataclass
class ModDescInfo:
    """Informations extraites d'un modDesc.xml."""

    desc_version: str | None = None
    version: str | None = None
    author: str | None = None
    titles: dict[str, str] = field(default_factory=dict)
    icon_filename: str | None = None
    is_map: bool = False
    map_titles: dict[str, str] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    # 0.7.3 : anciennes versions (FS15, FS17…), balise <SearchMods> : mods requis
    # (<mod zipName=… downloadLink=…>, aussi ajoutés à « dependencies ») et mods
    # facultatifs (<optionalMod …>), avec le lien de téléchargement de l'auteur.
    search_mods: list[dict[str, Any]] = field(default_factory=list)
    optional_mods: list[dict[str, Any]] = field(default_factory=list)
    multiplayer: bool | None = None
    xml_ok: bool = True          # False : XML invalide, lu par repli

    def to_json(self) -> dict[str, Any]:
        return {
            "desc_version": self.desc_version,
            "version": self.version,
            "author": self.author,
            "titles": self.titles,
            "icon_filename": self.icon_filename,
            "is_map": self.is_map,
            "map_titles": self.map_titles,
            "dependencies": self.dependencies,
            "search_mods": self.search_mods,
            "optional_mods": self.optional_mods,
            "multiplayer": self.multiplayer,
            "xml_ok": self.xml_ok,
        }


@dataclass
class ModReadResult:
    """Résultat de la lecture d'un élément d'un dossier de stockage."""

    ok: bool
    info: ModDescInfo | None = None
    icon_path: str | None = None      # chemin de l'icône dans l'archive (ou relatif au dossier)
    anomaly: str | None = None        # A2, A3, A4…
    detail: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Décodage et analyse tolérante du XML
# --------------------------------------------------------------------------

_DECL_RE = re.compile(rb"^\s*<\?xml[^>]*?encoding\s*=\s*[\"']([A-Za-z0-9_.\-]+)[\"']", re.IGNORECASE)
_DECL_STRIP_RE = re.compile(r"^\s*<\?xml[^>]*\?>", re.IGNORECASE)
_BAD_AMP_RE = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9A-Fa-f]+);)")
_CTRL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def decode_xml_bytes(data: bytes) -> str:
    """Décode un fichier XML : BOM, encodage déclaré, puis replis."""
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace")
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    declared = None
    m = _DECL_RE.match(data[:200])
    if m:
        declared = m.group(1).decode("ascii", errors="ignore").lower()
    candidates = []
    if declared:
        candidates.append(declared)
    candidates += ["utf-8", "cp1252", "latin-1"]
    for enc in candidates:
        try:
            return data.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("latin-1", errors="replace")


def parse_xml_tolerant(data: bytes) -> tuple[ET.Element | None, str]:
    """Analyse un XML. Renvoie (racine ou None, texte décodé)."""
    text = decode_xml_bytes(data)
    body = _DECL_STRIP_RE.sub("", text, count=1)
    attempts = [
        body,
        _CTRL_RE.sub("", body),
        _BAD_AMP_RE.sub("&amp;", _CTRL_RE.sub("", body)),
    ]
    for attempt in attempts:
        try:
            return ET.fromstring(attempt), text
        except ET.ParseError:
            continue
    return None, text


def _local(tag: Any) -> str:
    """Nom de balise sans espace de noms, en minuscules."""
    if not isinstance(tag, str):
        return ""
    if "}" in tag:
        tag = tag.split("}", 1)[1]
    return tag.lower()


def _child(el: ET.Element, name: str) -> ET.Element | None:
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _children(el: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in el if _local(c.tag) == name]


def _text(el: ET.Element | None) -> str | None:
    if el is None or el.text is None:
        return None
    t = el.text.strip()
    return t or None


def _attr(el: ET.Element, name: str) -> str | None:
    for k, v in el.attrib.items():
        if _local(k) == name.lower():
            return v
    return None


def _lang_texts(el: ET.Element | None) -> dict[str, str]:
    """Textes multilingues : <title><en>…</en><de>…</de></title>, ou texte simple."""
    out: dict[str, str] = {}
    if el is None:
        return out
    for c in el:
        tag = _local(c.tag)
        t = (c.text or "").strip()
        if tag and t:
            out[tag] = t
    if not out:
        t = (el.text or "").strip()
        if t:
            out["_"] = t
    return out


def _icon_name(el: ET.Element | None) -> str | None:
    """Nom de l'icône : texte simple, ou (FS2011, FS2013) placé dans des balises
    de langue, toutes identiques en pratique : <iconFilename><en>a.dds</en>…
    L'anglais est préféré, sinon la première langue."""
    if el is None:
        return None
    direct = _text(el)
    if direct:
        return direct
    texts = _lang_texts(el)
    return texts.get("en") or next(iter(texts.values()), None)


# --------------------------------------------------------------------------
# Traductions « $l10n_… »
# --------------------------------------------------------------------------

def _l10n_inline(root: ET.Element) -> dict[str, dict[str, str]]:
    """Textes déclarés dans <l10n><text name="x"><en>…</en></text></l10n>."""
    table: dict[str, dict[str, str]] = {}
    l10n = _child(root, "l10n")
    if l10n is None:
        return table
    for t in _children(l10n, "text"):
        name = _attr(t, "name")
        if name:
            table[name] = _lang_texts(t)
    return table


def _l10n_external(
    root: ET.Element, read_file: Any, list_files: Any
) -> dict[str, dict[str, str]]:
    """Textes des fichiers externes déclarés par <l10n filenamePrefix="…"/>."""
    table: dict[str, dict[str, str]] = {}
    l10n = _child(root, "l10n")
    if l10n is None:
        return table
    prefix = _attr(l10n, "filenamePrefix")
    if not prefix:
        return table
    prefix_norm = prefix.replace("\\", "/").lower()
    for name in list_files():
        low = name.replace("\\", "/").lower()
        if not (low.startswith(prefix_norm + "_") and low.endswith(".xml")):
            continue
        lang = low[len(prefix_norm) + 1 : -4]
        if not lang or "/" in lang:
            continue
        data = read_file(name)
        if not data:
            continue
        el, _ = parse_xml_tolerant(data)
        if el is None:
            continue
        # Formats rencontrés : <texts><text name="" text=""/></texts>
        # et <elements><e k="" v=""/></elements>
        for node in el.iter():
            tag = _local(node.tag)
            if tag == "text":
                k, v = _attr(node, "name"), _attr(node, "text")
            elif tag == "e":
                k, v = _attr(node, "k"), _attr(node, "v")
            else:
                continue
            if k and v:
                table.setdefault(k, {})[lang] = v
    return table


def _resolve_l10n(texts: dict[str, str], table: dict[str, dict[str, str]]) -> dict[str, str]:
    """Remplace les références « $l10n_nom » par leurs traductions."""
    if not texts:
        return texts
    out: dict[str, str] = {}
    for lang, value in texts.items():
        if value.startswith("$l10n_"):
            key = value[len("$l10n_"):]
            tr = table.get(key)
            if tr:
                if lang == "_":
                    out.update(tr)
                else:
                    out[lang] = tr.get(lang) or tr.get("en") or next(iter(tr.values()))
                continue
            continue  # référence introuvable : ignorée
        out[lang] = value
    return out


# --------------------------------------------------------------------------
# Extraction des informations
# --------------------------------------------------------------------------

_RX_DESC = re.compile(r"<modDesc\b[^>]*\bdescVersion\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE)
_RX_VERSION = re.compile(r"<version>\s*([^<]*?)\s*</version>", re.IGNORECASE)
_RX_AUTHOR = re.compile(r"<author>\s*([^<]*?)\s*</author>", re.IGNORECASE)
_RX_ICON = re.compile(r"<iconFilename>\s*([^<]*?)\s*</iconFilename>", re.IGNORECASE)
_RX_ICON_LANG = re.compile(r"<iconFilename>\s*<[a-z]{2}>\s*([^<]*?)\s*</[a-z]{2}>", re.IGNORECASE)
_RX_TITLE_EN = re.compile(r"<title>.*?<en>\s*([^<]*?)\s*</en>", re.IGNORECASE | re.DOTALL)
_RX_DEP = re.compile(r"<dependency>\s*([^<]*?)\s*</dependency>", re.IGNORECASE)
_RX_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_RX_SEARCH = re.compile(r"<searchMods\b[^>]*>(.*?)</searchMods>", re.IGNORECASE | re.DOTALL)
_RX_SEARCH_ITEM = re.compile(r"<(mod|optionalMod)\b([^>]*)>", re.IGNORECASE)
_RX_ATTR = re.compile(r"""\b([A-Za-z_]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")

MAX_URL = 1000


def safe_url(url: Any) -> str | None:
    """Adresse web utilisable : http ou https, avec un nom d'hôte, sans
    identifiants (« user@ »), sans espace ni caractère de contrôle. Sinon None."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    if not url or len(url) > MAX_URL or any(ord(c) < 33 or ord(c) == 127 for c in url):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    return url


def search_mod_name(zip_name: Any) -> str | None:
    """Nom d'un mod de <SearchMods> : zipName, sans dossier ni « .zip »."""
    if not isinstance(zip_name, str):
        return None
    name = zip_name.strip().replace("\\", "/").rsplit("/", 1)[-1].strip()
    if name.lower().endswith(".zip"):
        name = name[:-4].rstrip()
    return name or None


def _add_search_mod(info: ModDescInfo, tag: str, attrs: dict[str, str], seen: set[str]) -> None:
    name = search_mod_name(attrs.get("zipname"))
    if not name or name.lower() in seen:
        return
    seen.add(name.lower())
    item = {"name": name, "url": safe_url(attrs.get("downloadlink"))}
    if tag == "mod":
        info.search_mods.append(item)
        if name.lower() not in {d.lower() for d in info.dependencies}:
            info.dependencies.append(name)
    else:
        info.optional_mods.append(item)


def _search_mods_regex(info: ModDescInfo, text: str) -> None:
    seen: set[str] = set()
    for block in _RX_SEARCH.findall(text):
        for tag, raw in _RX_SEARCH_ITEM.findall(block):
            attrs = {k.lower(): (a if a else b) for k, a, b in _RX_ATTR.findall(raw)}
            _add_search_mod(info, tag.lower(), attrs, seen)


def _fallback_extract(text: str) -> ModDescInfo:
    """Extraction par expressions régulières quand le XML est invalide."""
    clean = _RX_COMMENT.sub("", text)
    info = ModDescInfo(xml_ok=False)
    m = _RX_DESC.search(clean)
    info.desc_version = m.group(1).strip() if m else None
    m = _RX_VERSION.search(clean)
    info.version = m.group(1) if m else None
    m = _RX_AUTHOR.search(clean)
    info.author = m.group(1) if m else None
    m = _RX_ICON.search(clean) or _RX_ICON_LANG.search(clean)
    info.icon_filename = (m.group(1) or None) if m else None
    m = _RX_TITLE_EN.search(clean)
    if m and m.group(1):
        info.titles = {"en": m.group(1)}
    info.is_map = re.search(r"<maps\b", clean, re.IGNORECASE) is not None
    info.dependencies = [d for d in _RX_DEP.findall(clean) if d]
    _search_mods_regex(info, clean)
    return info


def extract_info(
    data: bytes,
    read_file: Any = None,
    list_files: Any = None,
) -> ModDescInfo | None:
    """Analyse le contenu d'un modDesc.xml.

    `read_file(nom)` et `list_files()` donnent accès aux autres fichiers du mod
    (traductions externes). Renvoie None si le fichier n'est pas un modDesc.
    """
    root, text = parse_xml_tolerant(data)
    if root is None:
        if "<moddesc" not in text.lower():
            return None
        return _fallback_extract(text)
    if _local(root.tag) != "moddesc":
        return None

    info = ModDescInfo()
    info.desc_version = _attr(root, "descVersion")
    info.version = _text(_child(root, "version"))
    info.author = _text(_child(root, "author"))
    info.icon_filename = _icon_name(_child(root, "iconfilename"))

    table = _l10n_inline(root)
    if read_file is not None and list_files is not None:
        try:
            ext = _l10n_external(root, read_file, list_files)
            for k, v in ext.items():
                table.setdefault(k, {}).update(v)
        except Exception as exc:  # noqa: BLE001 - lecture best effort
            log.debug("Traductions externes illisibles : %s", exc)

    info.titles = _resolve_l10n(_lang_texts(_child(root, "title")), table)

    maps = _child(root, "maps")
    if maps is not None:
        info.is_map = True
        first = _child(maps, "map")
        if first is not None:
            info.map_titles = _resolve_l10n(_lang_texts(_child(first, "title")), table)

    deps = _child(root, "dependencies")
    if deps is not None:
        seen: set[str] = set()
        for d in _children(deps, "dependency"):
            name = _text(d)
            if name and name.lower() not in seen:
                seen.add(name.lower())
                info.dependencies.append(name)

    # 0.7.3 : <SearchMods> des anciennes versions (requis et facultatifs).
    seen_search: set[str] = set()
    for block in _children(root, "searchmods"):
        for c in block:
            tag = _local(c.tag)
            if tag in ("mod", "optionalmod"):
                attrs = {_local(k): v for k, v in c.attrib.items()}
                _add_search_mod(info, "mod" if tag == "mod" else "optional", attrs, seen_search)

    mp = _child(root, "multiplayer")
    if mp is not None:
        sup = _attr(mp, "supported")
        if sup is not None:
            info.multiplayer = sup.strip().lower() == "true"
    return info


# --------------------------------------------------------------------------
# Recherche de l'icône
# --------------------------------------------------------------------------

def _swap_ext(path: str) -> str | None:
    low = path.lower()
    if low.endswith(".dds"):
        return path[:-4] + ".png"
    if low.endswith(".png"):
        return path[:-4] + ".dds"
    return None


def find_icon(declared: str | None, names: list[str]) -> str | None:
    """Ordre de recherche (4.12) : chemin déclaré → autre extension → nom de
    fichier dans toute l'archive (deux extensions) → aucune (icône par défaut).

    `names` : chemins des fichiers du mod, séparateurs « / ».
    """
    if not declared:
        return None
    decl = declared.strip().replace("\\", "/").lstrip("./")
    if decl.startswith("$"):
        return None
    lower_map: dict[str, str] = {}
    for n in names:
        lower_map.setdefault(n.replace("\\", "/").lower(), n)

    candidates = [decl]
    swapped = _swap_ext(decl)
    if swapped:
        candidates.append(swapped)
    for c in candidates:
        hit = lower_map.get(c.lower())
        if hit:
            return hit

    base = PurePosixPath(decl).name.lower()
    stem = base.rsplit(".", 1)[0]
    wanted = {stem + ext for ext in ICON_EXTS}
    if "." not in base:
        wanted.add(base)
    for low, original in lower_map.items():
        if PurePosixPath(low).name in wanted:
            return original
    return None


# --------------------------------------------------------------------------
# Lecture d'un .zip et d'un dossier
# --------------------------------------------------------------------------

def read_zip(path: Path) -> ModReadResult:
    """Lit un mod compressé, sans jamais l'ouvrir en écriture (I9)."""
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = [i.filename for i in zf.infolist() if not i.is_dir()]
            root_desc = next(
                (n for n in names if n.replace("\\", "/").lower() == MODDESC), None
            )
            if root_desc is None:
                nested = next(
                    (
                        n
                        for n in names
                        if n.replace("\\", "/").lower().endswith("/" + MODDESC)
                    ),
                    None,
                )
                detail: dict[str, Any] = {}
                if nested:
                    detail["nested"] = nested.replace("\\", "/")
                return ModReadResult(ok=False, anomaly="A2", detail=detail)

            def read_file(name: str) -> bytes | None:
                try:
                    return zf.read(name)
                except (KeyError, zipfile.BadZipFile, OSError, RuntimeError):
                    return None

            if zf.getinfo(root_desc).file_size > MAX_MODDESC_BYTES:
                return ModReadResult(ok=False, anomaly="A3", detail={"reason": "xml"})
            data = zf.read(root_desc)
            info = extract_info(data, read_file, lambda: names)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, RuntimeError, ValueError) as exc:
        return ModReadResult(ok=False, anomaly="A3", detail={"reason": "zip", "error": str(exc)})
    except NotImplementedError as exc:  # méthode de compression inconnue
        return ModReadResult(ok=False, anomaly="A3", detail={"reason": "zip", "error": str(exc)})

    if info is None:
        return ModReadResult(ok=False, anomaly="A3", detail={"reason": "xml"})
    icon = find_icon(info.icon_filename, names)
    res = ModReadResult(ok=True, info=info, icon_path=icon)
    if not info.xml_ok:
        res.detail["xml_recovered"] = True
    return res


def _walk_names(folder: Path, limit: int = 20000) -> list[str]:
    """Liste les fichiers d'un dossier (chemins relatifs « / »), avec une limite."""
    out: list[str] = []
    base = str(folder)
    for dirpath, _dirnames, filenames in os.walk(folder):
        rel = os.path.relpath(dirpath, base)
        for fn in filenames:
            out.append(fn if rel == "." else f"{rel}/{fn}".replace("\\", "/"))
            if len(out) >= limit:
                return out
    return out


def find_moddesc_in_dir(folder: Path) -> Path | None:
    try:
        for entry in os.scandir(folder):
            if entry.is_file() and entry.name.lower() == MODDESC:
                return Path(entry.path)
    except OSError:
        return None
    return None


def read_dir(folder: Path) -> ModReadResult:
    """Lit un mod non compressé (dossier avec modDesc.xml à sa racine)."""
    desc = find_moddesc_in_dir(folder)
    if desc is None:
        return ModReadResult(ok=False, anomaly="A4")
    try:
        if desc.stat().st_size > MAX_MODDESC_BYTES:
            return ModReadResult(ok=False, anomaly="A3", detail={"reason": "xml"})
        data = desc.read_bytes()
    except OSError as exc:
        return ModReadResult(ok=False, anomaly="A3", detail={"reason": "io", "error": str(exc)})

    names_cache: list[str] | None = None

    def list_files() -> list[str]:
        nonlocal names_cache
        if names_cache is None:
            names_cache = _walk_names(folder)
        return names_cache

    def read_file(name: str) -> bytes | None:
        try:
            return (folder / name).read_bytes()
        except OSError:
            return None

    info = extract_info(data, read_file, list_files)
    if info is None:
        return ModReadResult(ok=False, anomaly="A3", detail={"reason": "xml"})

    icon = None
    if info.icon_filename:
        # Essai direct (rapide) avant de parcourir tout le dossier.
        decl = info.icon_filename.strip().replace("\\", "/").lstrip("./")
        for cand in [decl, _swap_ext(decl)]:
            if cand and (folder / cand).is_file():
                icon = cand
                break
        if icon is None:
            icon = find_icon(info.icon_filename, list_files())
    res = ModReadResult(ok=True, info=info, icon_path=icon)
    if not info.xml_ok:
        res.detail["xml_recovered"] = True
    return res


def read_icon_bytes(mod_path: Path, kind: str, icon_path: str) -> bytes | None:
    """Lit les octets de l'icône d'un mod (lecture seule)."""
    try:
        if kind == "zip":
            with zipfile.ZipFile(mod_path, "r") as zf:
                return zf.read(icon_path)
        return (mod_path / icon_path).read_bytes()
    except (KeyError, OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError):
        return None


def dir_size(folder: Path) -> int:
    total = 0
    for dirpath, _d, files in os.walk(folder):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
    return total
