"""Versions du jeu.

La table est une donnée (data/game_versions.json), pas du code. Ce module la
charge et sait reconnaître la version du jeu à laquelle un mod est destiné.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fspassion import config, fsutil

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class GameVersion:
    id: str
    name: str
    short: str
    logo: str
    documents_folder: str
    dlc_folder: str
    dlc_icons_folder: str
    has_override: bool
    has_pending_downloads: bool
    mods_dir_fixed: bool
    prefix_codes: tuple[str, ...]
    desc_min: int | None
    desc_max: int | None
    launcher_exe: str
    game_exes: tuple[str, ...]
    available: bool
    # Exécutables cherchés à la racine du dossier du jeu, par ordre de
    # préférence (FS2013 : la version 64 bits d'abord). Vide = le lanceur seul.
    detect_exes: tuple[str, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @property
    def exe_names(self) -> set[str]:
        """Noms (en minuscules) de tous les exécutables connus de cette version."""
        names = {self.launcher_exe.lower()}
        for rel in self.game_exes:
            names.add(Path(rel.replace("\\", "/")).name.lower())
        names.update(n.lower() for n in self.detect_exes)
        return names

    @property
    def root_exes(self) -> tuple[str, ...]:
        """Exécutables qui signalent cette version à la racine d'un dossier."""
        return self.detect_exes or (self.launcher_exe,)

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "short": self.short,
            "logo": self.logo,
            "has_override": self.has_override,
            "has_pending_downloads": self.has_pending_downloads,
            "mods_dir_fixed": self.mods_dir_fixed,
            "available": self.available,
            "launcher_exe": self.launcher_exe,
        }


def _load(path: Path | None = None) -> tuple[list[GameVersion], str]:
    src = path or (config.package_data_dir() / "game_versions.json")
    if not src.is_file():
        log.error("Fichier des versions du jeu absent : %s", src)  # rien n'est chargé sans le dire
    data = fsutil.read_json(src, {})
    out: list[GameVersion] = []
    for v in data.get("versions", []):
        dv = v.get("desc_version") or {}
        out.append(
            GameVersion(
                id=v["id"],
                name=v["name"],
                short=v["short"],
                logo=v["logo"],
                documents_folder=v["documents_folder"],
                dlc_folder=v["dlc_folder"],
                dlc_icons_folder=v["dlc_icons_folder"],
                has_override=bool(v["has_override"]),
                has_pending_downloads=bool(v["has_pending_downloads"]),
                mods_dir_fixed=bool(v.get("mods_dir_fixed", False)),
                prefix_codes=tuple(v.get("prefix_codes", [])),
                desc_min=dv.get("min") if dv else None,
                desc_max=dv.get("max") if dv else None,
                launcher_exe=v["launcher_exe"],
                game_exes=tuple(v.get("game_exes", [])),
                available=bool(v.get("available", True)),
                detect_exes=tuple(v.get("detect_exes", [])),
            )
        )
    return out, data.get("default_version", "FS25")


VERSIONS, DEFAULT_VERSION = _load()
_BY_ID = {v.id: v for v in VERSIONS}


def all_versions() -> list[GameVersion]:
    return list(VERSIONS)


def get(vid: str) -> GameVersion | None:
    return _BY_ID.get(vid)


def require(vid: str) -> GameVersion:
    v = _BY_ID.get(vid)
    if v is None:
        raise KeyError(vid)
    return v


# --------------------------------------------------------------------------
# Reconnaître la version d'un mod
# --------------------------------------------------------------------------

def _prefix_regex() -> re.Pattern[str]:
    codes = sorted({c for v in VERSIONS for c in v.prefix_codes})
    return re.compile(r"^(?:FS|LS)(" + "|".join(codes) + r")(?!\d)", re.IGNORECASE)


_PREFIX_RE = _prefix_regex()
_CODE_TO_VERSION = {c: v.id for v in VERSIONS for c in v.prefix_codes}

# Préfixe affiché à retirer pour obtenir le « nom court » (FS25_, LS22_, FS2013_…)
_SHORT_PREFIX_RE = re.compile(r"^(?:FS|LS)(?:\d{2}|20\d{2})_", re.IGNORECASE)


def short_name(mod_id: str) -> str:
    """Identifiant sans le préfixe de version : « FS25_HofBergmann » → « HofBergmann »."""
    short = _SHORT_PREFIX_RE.sub("", mod_id)
    return short or mod_id


def version_from_prefix(filename: str) -> str | None:
    """Étape 1 : préfixe FS/LS + code de version + caractère non numérique."""
    m = _PREFIX_RE.match(filename)
    if not m:
        return None
    return _CODE_TO_VERSION.get(m.group(1))


def parse_desc_version(raw: str | None) -> int | None | str:
    """descVersion lu dans modDesc.xml.

    Renvoie un entier, None si l'attribut est absent, ou « invalid » s'il est
    illisible (non numérique).
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if re.fullmatch(r"\d+", s):
        return int(s)
    return "invalid"


def version_from_desc(desc: int) -> str | None:
    """Étape 2 : plage de descVersion. La dernière version déclarée est ouverte."""
    for v in VERSIONS:
        if v.desc_min is None:
            continue
        hi = v.desc_max if v.desc_max is not None else float("inf")
        if v.desc_min <= desc <= hi:
            return v.id
    return None


@dataclass
class ModVersionResult:
    version: str | None       # identifiant de version, ou None
    status: str               # ok | unknown | unsupported
    source: str               # prefix | desc | none
    warning: str | None = None  # « conflict » : préfixe et descVersion en désaccord


def detect_mod_version(filename: str, desc_raw: str | None) -> ModVersionResult:
    """Détermine la version d'un mod : nom de fichier, puis modDesc.xml."""
    by_prefix = version_from_prefix(filename)
    parsed = parse_desc_version(desc_raw)
    desc_num: int | None
    if parsed is None:
        desc_num = 1  # attribut absent → valeur 1
    elif parsed == "invalid":
        desc_num = None
    else:
        desc_num = int(parsed)

    by_desc: str | None = None
    if isinstance(desc_num, int) and desc_num >= 4:
        by_desc = version_from_desc(desc_num)

    if by_prefix:
        warning = None
        if by_desc and by_desc != by_prefix:
            warning = "conflict"
        return ModVersionResult(by_prefix, "ok", "prefix", warning)

    if desc_num is None:
        return ModVersionResult(None, "unknown", "none")
    if desc_num < 4:
        return ModVersionResult(None, "unsupported", "desc")
    if by_desc is None:
        return ModVersionResult(None, "unknown", "desc")
    return ModVersionResult(by_desc, "ok", "desc")
