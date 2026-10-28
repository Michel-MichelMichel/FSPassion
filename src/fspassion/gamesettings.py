"""Le fichier gameSettings.xml du jeu.

Lecture de la ligne modsDirectoryOverride ; création unique de la sauvegarde
« gameSettings.xml.original.bak » (référence de l'état d'avant FS Passion,
jamais écrasée) ; écriture de cette seule ligne (« Appliquer »).

Écriture : remplacement chirurgical de la ligne, jamais une réécriture
du XML complet. Étapes : relecture → sauvegarde « gameSettings.xml.bak » →
remplacement → écriture dans un fichier temporaire puis bascule → relecture de
contrôle → restauration automatique si le contrôle échoue. Le chemin est écrit
avec des barres obliques, comme le fait le jeu (« D:/FS25_Mods/… »), et les
caractères spéciaux sont échappés. Encodage, marque BOM, guillemets et
fins de ligne du fichier d'origine sont conservés.

La ligne existe sous plusieurs formes (test) :
    <modsDirectoryOverride active="false" directory="C:/Temp" />
    <modsDirectoryOverride active="false" directory="C:/Temp"/>
    <modsDirectoryOverride active='false' directory='C:/Temp' />      (FS19)
La lecture accepte guillemets ou apostrophes, dans n'importe quel ordre.
"""

from __future__ import annotations

import html
import logging
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from fspassion import fsutil

log = logging.getLogger(__name__)

ORIGINAL_BAK_SUFFIX = ".original.bak"
BAK_SUFFIX = ".bak"

_LINE_RE = re.compile(r"<modsDirectoryOverride\b(?P<attrs>[^>]*?)/?\s*>", re.IGNORECASE)
_ATTR_RE = re.compile(r"""(?P<name>[A-Za-z_][\w.\-]*)\s*=\s*(?:"(?P<dq>[^"]*)"|'(?P<sq>[^']*)')""")


@dataclass
class Override:
    found: bool                 # la ligne existe-t-elle ?
    active: bool | None = None
    directory: str | None = None
    raw: str | None = None

    def to_json(self) -> dict[str, object]:
        return {"found": self.found, "active": self.active, "directory": self.directory}


def _decode_with(data: bytes) -> tuple[str, str, bool]:
    """Texte, encodage et présence d'une marque BOM."""
    bom = data.startswith(b"\xef\xbb\xbf")
    if bom:
        data = data[3:]
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc), enc, bom
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace"), "latin-1", bom


def _decode(data: bytes) -> str:
    return _decode_with(data)[0]


def parse_override(text: str) -> Override:
    """Extrait la ligne modsDirectoryOverride d'un contenu gameSettings.xml."""
    m = _LINE_RE.search(text)
    if not m:
        return Override(found=False)
    attrs: dict[str, str] = {}
    for a in _ATTR_RE.finditer(m.group("attrs")):
        value = a.group("dq") if a.group("dq") is not None else a.group("sq")
        attrs[a.group("name").lower()] = html.unescape(value or "")
    active_raw = attrs.get("active")
    active = None if active_raw is None else active_raw.strip().lower() == "true"
    directory = attrs.get("directory")
    return Override(found=True, active=active, directory=directory, raw=m.group(0))


def read_override(path: Path) -> Override | None:
    """Lit l'override d'un fichier gameSettings.xml. None si le fichier est illisible."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return parse_override(_decode(data))


def original_backup_path(path: Path) -> Path:
    return path.with_name(path.name + ORIGINAL_BAK_SUFFIX)


def ensure_original_backup(path: Path) -> bool:
    """Crée « gameSettings.xml.original.bak » s'il n'existe pas encore.

    Une seule fois, dès la première détection du fichier, jamais écrasé.
    Renvoie True si la sauvegarde vient d'être créée.
    """
    if not path.is_file():
        return False
    bak = original_backup_path(path)
    if bak.exists():
        return False
    try:
        data = path.read_bytes()
        fsutil.atomic_write_bytes(bak, data)
        try:
            shutil.copystat(path, bak)
        except OSError:
            pass
        log.info("Sauvegarde d'origine créée : %s", bak)
        return True
    except OSError as exc:
        log.error("Sauvegarde d'origine impossible %s : %s", bak, exc)
        return False


def override_dir_to_path(directory: str | None) -> str | None:
    """Le jeu écrit « D:/FS25_Mods/Mods » : on le convertit en chemin Windows."""
    if not directory:
        return None
    return os.path.normpath(directory)


# --------------------------------------------------------------------------
# Écriture de la ligne
# --------------------------------------------------------------------------

class WriteError(Exception):
    """Écriture impossible, avec une clé de langue."""

    def __init__(self, key: str, **params: object) -> None:
        super().__init__(key)
        self.key = key
        self.params = params


def backup_path(path: Path) -> Path:
    return path.with_name(path.name + BAK_SUFFIX)


def game_path(p: str | os.PathLike[str]) -> str:
    """Chemin au format du jeu : barres obliques (« D:/FS25_Mods/Mods »)."""
    return os.path.normpath(str(p)).replace("\\", "/")


def _escape(value: str, quote: str) -> str:
    out = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return out.replace('"', "&quot;") if quote == '"' else out.replace("'", "&apos;")


def _set_attr(tag: str, name: str, value: str, default_quote: str) -> str:
    """Remplace (ou ajoute) la valeur d'un attribut dans une balise, en gardant
    les guillemets d'origine."""
    pattern = re.compile(r"(\b" + re.escape(name) + r"""\s*=\s*)(?:"[^"]*"|'[^']*')""", re.IGNORECASE)
    m = pattern.search(tag)
    if m:
        quote = tag[m.end(1)]
        return tag[:m.start()] + f"{m.group(1)}{quote}{_escape(value, quote)}{quote}" + tag[m.end():]
    # Attribut absent : ajouté juste après le nom de la balise.
    head = re.match(r"<modsDirectoryOverride\b", tag, re.IGNORECASE)
    assert head is not None
    q = default_quote
    return tag[:head.end()] + f" {name}={q}{_escape(value, q)}{q}" + tag[head.end():]


def replace_override(text: str, directory: str, active: bool = True) -> str:
    """Contenu de gameSettings.xml avec la seule ligne d'override modifiée."""
    value_dir = game_path(directory)
    value_active = "true" if active else "false"
    m = _LINE_RE.search(text)
    if m:
        tag = m.group(0)
        quote = "'" if re.search(r"=\s*'", tag) and not re.search(r'=\s*"', tag) else '"'
        new_tag = _set_attr(tag, "active", value_active, quote)
        new_tag = _set_attr(new_tag, "directory", value_dir, quote)
        return text[:m.start()] + new_tag + text[m.end():]
    # Ligne absente : ajoutée juste après la balise d'ouverture <gameSettings …>.
    root = re.search(r"<gameSettings\b[^>]*>", text, re.IGNORECASE)
    if root is None:
        raise WriteError("override.no_root")
    newline = "\r\n" if "\r\n" in text else "\n"
    line = f'{newline}    <modsDirectoryOverride active="{value_active}" directory="{_escape(value_dir, chr(34))}"/>'
    return text[:root.end()] + line + text[root.end():]


def write_override(path: Path, directory: str, active: bool = True) -> Override:
    """Écrit l'override vers `directory`. Lève WriteError en cas d'échec ;
    le fichier d'origine est alors rétabli."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise WriteError("override.read_failed", path=str(path), detail=str(exc)) from exc
    ensure_original_backup(path)
    text, enc, bom = _decode_with(data)
    new_text = replace_override(text, directory, active)
    try:
        new_data = new_text.encode(enc)
    except UnicodeEncodeError:
        # Chemin impossible à écrire dans l'encodage du fichier : UTF-8.
        new_data = new_text.encode("utf-8")
        bom = bom or enc != "utf-8"
    if bom:
        new_data = b"\xef\xbb\xbf" + new_data
    if new_data == data:
        return parse_override(new_text)
    bak = backup_path(path)
    try:
        fsutil.atomic_write_bytes(bak, data)
    except OSError as exc:
        raise WriteError("override.backup_failed", path=str(bak), detail=str(exc)) from exc
    try:
        fsutil.atomic_write_bytes(path, new_data)
    except OSError as exc:
        raise WriteError("override.write_failed", path=str(path), detail=str(exc)) from exc
    # Relecture de contrôle ; restauration si elle échoue.
    check = read_override(path)
    expected = os.path.normcase(os.path.normpath(directory))
    ok = (check is not None and check.found and check.active is active
          and os.path.normcase(os.path.normpath(check.directory or "")) == expected)
    if not ok:
        log.error("Contrôle de l'override en échec : restauration de %s", path)
        try:
            fsutil.atomic_write_bytes(path, data)
        except OSError:
            log.exception("Restauration de gameSettings.xml impossible")
        raise WriteError("override.check_failed", path=str(path))
    log.info("Override écrit : %s → %s", path, game_path(directory))
    assert check is not None
    return check


# --------------------------------------------------------------------------
# game.xml : console de développement (arguments de lancement)
# --------------------------------------------------------------------------

GAME_XML = "game.xml"

# <development> … <controls>false</controls> : seule la valeur est lue et
# remplacée, le reste du fichier n'est jamais réécrit.
_CONTROLS_RE = re.compile(
    r"(<development\b[^>]*>\s*<controls>\s*)(true|false)(\s*</controls>)",
    re.IGNORECASE,
)


def development_controls(path: Path) -> bool | None:
    """Valeur de <development><controls> dans game.xml : True, False, ou None si
    le fichier ou la ligne est introuvable (affichée dans les paramètres)."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    m = _CONTROLS_RE.search(_decode(data))
    if m is None:
        return None
    return m.group(2).lower() == "true"


def enable_development_controls(path: Path) -> str:
    """Passe <development><controls> de false à true dans game.xml.

    Renvoie « changed » (valeur modifiée), « unchanged » (déjà true) ou
    « absent » (fichier ou ligne introuvable). Même méthode que l'override :
    sauvegarde game.xml.bak, écriture atomique, relecture de contrôle et
    restauration automatique si le contrôle échoue.
    """
    if not path.is_file():
        return "absent"
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise WriteError("override.read_failed", path=str(path), detail=str(exc)) from exc
    text, enc, bom = _decode_with(data)
    m = _CONTROLS_RE.search(text)
    if m is None:
        log.info("game.xml : <development><controls> introuvable dans %s", path)
        return "absent"
    if m.group(2).lower() == "true":
        return "unchanged"
    new_text = text[:m.start(2)] + "true" + text[m.end(2):]
    try:
        new_data = new_text.encode(enc)
    except UnicodeEncodeError:
        new_data = new_text.encode("utf-8")
        bom = bom or enc != "utf-8"
    if bom:
        new_data = b"\xef\xbb\xbf" + new_data
    try:
        fsutil.atomic_write_bytes(backup_path(path), data)
        fsutil.atomic_write_bytes(path, new_data)
    except OSError as exc:
        raise WriteError("override.write_failed", path=str(path), detail=str(exc)) from exc
    try:
        check = _CONTROLS_RE.search(_decode(path.read_bytes()))
    except OSError as exc:  # relecture impossible : même erreur que l'écriture
        raise WriteError("override.write_failed", path=str(path), detail=str(exc)) from exc
    if check is None or check.group(2).lower() != "true":
        log.error("Contrôle de game.xml en échec : restauration de %s", path)
        try:
            fsutil.atomic_write_bytes(path, data)
        except OSError:
            log.exception("Restauration de game.xml impossible")
        raise WriteError("override.check_failed", path=str(path))
    log.info("Console de développement activée dans %s", path)
    return "changed"
