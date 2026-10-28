"""Chemins d'une version du jeu : saisis, déduits et contrôlés.

Trois chemins sont saisis par version (game_exe, user_dir, mods_dir), plus
jusqu'à deux dossiers de stockage supplémentaires. Les autres en sont
déduits et affichés en lecture seule.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fspassion import detect, fsutil, winapi
from fspassion.versions import GameVersion


@dataclass
class VersionPaths:
    version: GameVersion
    game_exe: Path | None
    user_dir: Path | None
    mods_dir: Path | None
    extra_mods_dirs: list[Path] = field(default_factory=list)

    # -- chemins déduits (lecture seule) -------------------------------------

    @property
    def game_dir(self) -> Path | None:
        return detect.game_root_of_exe(self.game_exe) if self.game_exe else None

    @property
    def gamesettings(self) -> Path | None:
        if not self.version.has_override or self.user_dir is None:
            return None
        return self.user_dir / "gameSettings.xml"

    @property
    def pending_downloads(self) -> Path | None:
        if not self.version.has_pending_downloads or self.user_dir is None:
            return None
        return self.user_dir / "pending_downloads"

    @property
    def dlc_dirs(self) -> list[Path]:
        out = []
        if self.game_dir is not None:
            out.append(self.game_dir / self.version.dlc_folder)
        if self.user_dir is not None:
            out.append(self.user_dir / self.version.dlc_folder)
        return out

    @property
    def storages(self) -> list[Path]:
        """Dossiers de stockage des mods : principal, puis supplémentaires.
        Un chemin supplémentaire qui chevauche le principal, le dossier
        FSPassion\\ ou un chemin précédent est écarté (signalé dans les
        paramètres) : un mod ne doit jamais être lu deux fois."""
        if self.mods_dir is None:
            return []
        extra = [p for i, p in enumerate(self.extra_mods_dirs)
                 if extra_overlap(self.mods_dir, self.extra_mods_dirs, i) is None]
        return [self.mods_dir] + extra

    @property
    def fsp_dir(self) -> Path | None:
        """Dossier FSPassion\\<version>\\, à côté du dossier de mods principal."""
        if self.mods_dir is None:
            return None
        return self.mods_dir.parent / "FSPassion" / self.version.id

    def derived_json(self) -> list[dict[str, Any]]:
        """Chemins déduits pour l'affichage, avec leur existence."""
        items: list[dict[str, Any]] = []

        def add(key: str, p: Path | None, applicable: bool = True) -> None:
            items.append({
                "key": key,
                "path": str(p) if p else None,
                "exists": bool(p and p.exists()),
                "applicable": applicable,
            })

        add("game_dir", self.game_dir)
        add("gamesettings", self.gamesettings, self.version.has_override)
        add("pending_downloads", self.pending_downloads, self.version.has_pending_downloads)
        gd = self.game_dir
        add("dlc_game", gd / self.version.dlc_folder if gd else None)
        add("dlc_user", self.user_dir / self.version.dlc_folder if self.user_dir else None)
        return items


def _overlaps(a: str, b: str) -> bool:
    """Même dossier, ou l'un contient l'autre (sans accès disque)."""
    na, nb = fsutil.norm_path(a), fsutil.norm_path(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    sep = os.sep
    return na.startswith(nb.rstrip(sep) + sep) or nb.startswith(na.rstrip(sep) + sep)


def extra_overlap(mods_dir: Path | None, extra: list[Path], index: int) -> str | None:
    """Clé d'erreur si le chemin supplémentaire n° `index` chevauche le stockage
    principal (ou son dossier FSPassion\\), ou un chemin supplémentaire précédent."""
    value = str(extra[index])
    if mods_dir is not None:
        if _overlaps(value, str(mods_dir)) or _overlaps(value, str(mods_dir.parent / "FSPassion")):
            return "path.storage_overlap"
    for j in range(index):
        if _overlaps(value, str(extra[j])):
            return "path.storage_duplicate"
    return None


def _p(value: str | None) -> Path | None:
    return Path(value) if value else None


def from_cfg(v: GameVersion, cfg: dict[str, Any]) -> VersionPaths:
    user_dir = _p(cfg.get("user_dir"))
    mods_dir = _p(cfg.get("mods_dir"))
    if v.mods_dir_fixed and user_dir is not None:
        # FS2011 : le dossier de mods n'est pas déplaçable.
        mods_dir = user_dir / "mods"
    extra = [Path(p) for p in (cfg.get("extra_mods_dirs") or []) if p]
    return VersionPaths(v, _p(cfg.get("game_exe")), user_dir, mods_dir, extra)


# --------------------------------------------------------------------------
# Contrôle des champs (messages). Les textes sont des clés de langue.
# --------------------------------------------------------------------------

def _status(level: str, key: str, **params: Any) -> dict[str, Any]:
    return {"level": level, "key": key, "params": params}


def check_game_exe(v: GameVersion, value: str | None) -> dict[str, Any]:
    if not value:
        return _status("empty", "path.empty")
    p = Path(value)
    if not p.exists():
        return _status("error", "path.not_found")
    if not p.is_file() or p.name.lower() not in v.exe_names:
        return _status("error", "path.not_game_exe", game=v.name)
    return _status("ok", "path.found")


def check_user_dir(v: GameVersion, value: str | None) -> dict[str, Any]:
    if not value:
        return _status("empty", "path.empty")
    p = Path(value)
    if not p.is_dir():
        return _status("error", "path.not_found")
    if v.has_override and not (p / "gameSettings.xml").is_file():
        return _status("warn", "path.no_gamesettings")
    return _status("ok", "path.found")


def check_mods_dir(v: GameVersion, value: str | None) -> dict[str, Any]:
    if not value:
        return _status("empty", "path.empty")
    p = Path(value)
    if not p.is_dir():
        return _status("error", "path.not_found")
    fs = winapi.volume_filesystem(p)
    if fs is not None and fs.upper() != "NTFS" and v.has_override:
        return _status("warn", "path.not_ntfs")
    if winapi.is_in_onedrive(str(p)):
        return _status("warn", "path.onedrive")
    return _status("ok", "path.found")


def check_all(vp: VersionPaths, cfg: dict[str, Any]) -> dict[str, Any]:
    v = vp.version
    mods_value = str(vp.mods_dir) if vp.mods_dir else cfg.get("mods_dir")
    return {
        "game_exe": check_game_exe(v, cfg.get("game_exe")),
        "user_dir": check_user_dir(v, cfg.get("user_dir")),
        "mods_dir": check_mods_dir(v, mods_value),
    }


def is_installed(vp: VersionPaths) -> bool:
    """Version considérée comme installée : jeu ou dossier Mes documents présent."""
    return bool(
        (vp.game_exe and vp.game_exe.is_file()) or (vp.user_dir and vp.user_dir.is_dir())
    )


def is_ready(vp: VersionPaths) -> bool:
    """La bibliothèque peut être lue : le dossier de mods existe."""
    return bool(vp.mods_dir and vp.mods_dir.is_dir())
