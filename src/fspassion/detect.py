"""Détection des installations du jeu.

Il n'existe pas de registre unique des installations : chaque plateforme tient
le sien. FS Passion interroge chaque source, puis reconnaît la version par le
nom de l'exécutable présent dans le dossier (table des versions).

| Source           | Où chercher                                                   |
| Steam            | registre, steamapps\\libraryfolders.vdf, appmanifest_*.acf      |
| Epic Games       | manifestes JSON (*.item) de %ProgramData%\\Epic\\…\\Manifests     |
| Xbox / Game Pass | <disque>:\\XboxGames\\<jeu>\\Content\\                             |
| GIANTS           | clés de désinstallation du registre (HKLM 64/32 bits, HKCU)   |
| Microsoft Store  | %LocalAppData%\\Packages\\GIANTSSoftwareGmbH.FarmingSimulator*   |
| Repli            | dossiers « Farming Simulator… » à la racine des disques fixes |
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fspassion import fsutil, gamesettings, versions, winapi
from fspassion.versions import GameVersion

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winreg
else:  # pragma: no cover - hors Windows
    winreg = None  # type: ignore[assignment]


# --------------------------------------------------------------------------
# Format VDF de Steam (libraryfolders.vdf, appmanifest_*.acf)
# --------------------------------------------------------------------------

_VDF_TOKEN_RE = re.compile(r'"((?:[^"\\]|\\.)*)"|([{}])')


def _vdf_unescape(raw: str) -> str:
    return raw.replace("\\\\", "\x00").replace('\\"', '"').replace("\x00", "\\")


def parse_vdf(text: str) -> dict[str, Any]:
    """Analyse un fichier texte VDF de Steam en dictionnaire (clés en minuscules)."""
    root: dict[str, Any] = {}
    stack: list[dict[str, Any]] = [root]
    key: str | None = None
    for m in _VDF_TOKEN_RE.finditer(text):
        brace = m.group(2)
        if brace == "{":
            new: dict[str, Any] = {}
            if key is not None:
                stack[-1][key.lower()] = new
            stack.append(new)
            key = None
        elif brace == "}":
            if len(stack) > 1:
                stack.pop()
            key = None
        else:
            value = _vdf_unescape(m.group(1))
            if key is None:
                key = value
            else:
                stack[-1][key.lower()] = value
                key = None
    return root


# --------------------------------------------------------------------------
# Reconnaître une version dans un dossier
# --------------------------------------------------------------------------

def _list_lower(folder: Path) -> dict[str, str]:
    try:
        return {e.name.lower(): e.name for e in os.scandir(folder)}
    except OSError:
        return {}


def versions_in_dir(folder: Path) -> list[GameVersion]:
    """Versions du jeu dont le lanceur se trouve à la racine de `folder`."""
    names = _list_lower(folder)
    if not names:
        return []
    return [v for v in versions.all_versions() if any(x.lower() in names for x in v.root_exes)]


def version_of_exe(path: str | Path) -> GameVersion | None:
    """Version correspondant au nom d'un exécutable (lanceur ou jeu)."""
    name = Path(path).name.lower()
    for v in versions.all_versions():
        if name in v.exe_names:
            return v
    return None


def game_root_of_exe(path: str | Path) -> Path:
    """Dossier du jeu : dossier de l'exécutable, sans x64\\ ni x86\\."""
    p = Path(path).parent
    if p.name.lower() in ("x64", "x86"):
        p = p.parent
    return p


def launcher_path(folder: Path, v: GameVersion) -> Path:
    """Exécutable à proposer : le premier de root_exes présent."""
    names = _list_lower(folder)
    for x in v.root_exes:
        if x.lower() in names:
            return folder / names[x.lower()]
    return folder / v.root_exes[0]


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------

@dataclass
class Install:
    version: str
    game_dir: Path
    exe: Path
    source: str
    info: dict[str, Any] = field(default_factory=dict)


def _reg_value(root: Any, subkey: str, name: str) -> str | None:
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(root, subkey) as k:
            value, _ = winreg.QueryValueEx(k, name)
            return str(value) if value is not None else None
    except OSError:
        return None


def steam_root() -> Path | None:
    if winreg is None:
        return None
    for root, sub, name in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ):
        v = _reg_value(root, sub, name)
        if v and Path(v).exists():
            return Path(os.path.normpath(v))
    return None


def steam_exe() -> Path | None:
    if winreg is None:
        return None
    v = _reg_value(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamExe")
    if v and Path(v).is_file():
        return Path(os.path.normpath(v))
    root = steam_root()
    if root and (root / "steam.exe").is_file():
        return root / "steam.exe"
    return None


def steam_libraries(root: Path | None = None) -> list[Path]:
    root = root or steam_root()
    if root is None:
        return []
    libs: list[Path] = [root]
    vdf = root / "steamapps" / "libraryfolders.vdf"
    try:
        data = parse_vdf(vdf.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return libs
    folders = data.get("libraryfolders") or {}
    for key, value in folders.items():
        path = None
        if isinstance(value, dict):
            path = value.get("path")
        elif isinstance(value, str) and key.isdigit():
            path = value  # ancien format : "1" "D:\\SteamLibrary"
        if path:
            p = Path(os.path.normpath(path))
            if p.exists() and not any(fsutil.same_path(p, x) for x in libs):
                libs.append(p)
    return libs


def steam_installs(libraries: list[Path] | None = None) -> list[Install]:
    out: list[Install] = []
    for lib in libraries if libraries is not None else steam_libraries():
        apps = lib / "steamapps"
        try:
            manifests = [p for p in apps.glob("appmanifest_*.acf")]
        except OSError:
            continue
        for mf in manifests:
            try:
                data = parse_vdf(mf.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            app = data.get("appstate") or {}
            name = str(app.get("name", ""))
            installdir = app.get("installdir")
            if "farming simulator" not in name.lower() or not installdir:
                continue
            game_dir = apps / "common" / str(installdir)
            for v in versions_in_dir(game_dir):
                out.append(
                    Install(v.id, game_dir, launcher_path(game_dir, v), "steam",
                            {"appid": str(app.get("appid", "")), "manifest": str(mf)})
                )
    return out


def epic_manifests_dir() -> Path | None:
    pd = os.environ.get("ProgramData")
    if not pd:
        return None
    return Path(pd) / "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"


def epic_manifests() -> list[dict[str, Any]]:
    folder = epic_manifests_dir()
    if folder is None or not folder.is_dir():
        return []
    out = []
    for item in folder.glob("*.item"):
        data = fsutil.read_json(item, None)
        if isinstance(data, dict):
            out.append(data)
    return out


def epic_installs(manifests: list[dict[str, Any]] | None = None) -> list[Install]:
    out: list[Install] = []
    for data in manifests if manifests is not None else epic_manifests():
        if "farming simulator" not in str(data.get("DisplayName", "")).lower():
            continue
        loc = data.get("InstallLocation")
        if not loc:
            continue
        game_dir = Path(os.path.normpath(loc))
        for v in versions_in_dir(game_dir):
            out.append(
                Install(v.id, game_dir, launcher_path(game_dir, v), "epic",
                        {"app_name": data.get("AppName"),
                         "namespace": data.get("CatalogNamespace"),
                         "catalog_item": data.get("CatalogItemId")})
            )
    return out


def xbox_installs(drives: list[Path] | None = None) -> list[Install]:
    out: list[Install] = []
    for drive in drives if drives is not None else winapi.fixed_drives():
        base = drive / "XboxGames"
        try:
            entries = [e for e in os.scandir(base) if e.is_dir()]
        except OSError:
            continue
        for e in entries:
            if "farming" not in e.name.lower():
                continue
            for cand in (Path(e.path) / "Content", Path(e.path)):
                for v in versions_in_dir(cand):
                    out.append(Install(v.id, cand, launcher_path(cand, v), "xbox"))
    return out


_UNINSTALL_KEYS = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
)


def uninstall_installs() -> list[Install]:
    if winreg is None:
        return []
    out: list[Install] = []
    roots = [(winreg.HKEY_LOCAL_MACHINE, k) for k in _UNINSTALL_KEYS]
    roots.append((winreg.HKEY_CURRENT_USER, _UNINSTALL_KEYS[0]))
    for root, key in roots:
        try:
            with winreg.OpenKey(root, key) as k:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(k, i)
                    except OSError:
                        break
                    i += 1
                    full = key + "\\" + sub
                    name = _reg_value(root, full, "DisplayName") or ""
                    if "farming simulator" not in name.lower():
                        continue
                    loc = _reg_value(root, full, "InstallLocation")
                    dirs: list[Path] = []
                    if loc:
                        dirs.append(Path(os.path.normpath(loc.strip('"'))))
                    unins = _reg_value(root, full, "UninstallString")
                    if unins:
                        exe = unins.strip()
                        if exe.startswith('"'):
                            exe = exe[1:].split('"', 1)[0]
                        else:
                            exe = exe.split(" /", 1)[0]
                        dirs.append(Path(os.path.normpath(exe)).parent)
                    for d in dirs:
                        for v in versions_in_dir(d):
                            out.append(Install(v.id, d, launcher_path(d, v), "giants"))
        except OSError:
            continue
    return out


def _packages_dir() -> Path | None:
    la = os.environ.get("LOCALAPPDATA")
    return Path(la) / "Packages" if la else None


def store_user_dirs() -> dict[str, Path]:
    """Microsoft Store : dossier de gameSettings.xml sous LocalState (profondeur limitée)."""
    out: dict[str, Path] = {}
    pk = _packages_dir()
    if pk is None or not pk.is_dir():
        return out
    try:
        pkgs = [e for e in os.scandir(pk) if e.is_dir() and e.name.lower().startswith("giantssoftwaregmbh.farmingsimulator")]
    except OSError:
        return out
    for e in pkgs:
        local_state = Path(e.path) / "LocalState"
        found = _find_file(local_state, "gamesettings.xml", max_depth=4)
        if not found:
            continue
        user_dir = found.parent
        vid = _version_from_text(e.name) or _version_from_text(str(user_dir))
        if vid and vid not in out:
            out[vid] = user_dir
    return out


def _find_file(folder: Path, name_lower: str, max_depth: int) -> Path | None:
    if max_depth < 0:
        return None
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return None
    for e in entries:
        if e.is_file() and e.name.lower() == name_lower:
            return Path(e.path)
    for e in entries:
        if e.is_dir():
            hit = _find_file(Path(e.path), name_lower, max_depth - 1)
            if hit:
                return hit
    return None


def _version_from_text(text: str) -> str | None:
    """« FarmingSimulator2025 », « FarmingSimulator25 »… → identifiant de version."""
    low = text.lower()
    for v in versions.all_versions():
        if v.documents_folder.lower() in low:
            return v.id
    m = re.search(r"farmingsimulator(\d{2})(?!\d)", low)
    if m:
        for v in versions.all_versions():
            if m.group(1) in v.prefix_codes:
                return v.id
    return None


def fallback_installs(drives: list[Path] | None = None) -> list[Install]:
    out: list[Install] = []
    for drive in drives if drives is not None else winapi.fixed_drives():
        bases = [drive] + [drive / n for n in ("Games", "Jeux", "Program Files", "Program Files (x86)")]
        for base in bases:
            try:
                entries = [e for e in os.scandir(base) if e.is_dir()]
            except OSError:
                continue
            for e in entries:
                low = e.name.lower()
                if low.startswith("farming simulator") or low.startswith("farmingsimulator"):
                    d = Path(e.path)
                    for v in versions_in_dir(d):
                        out.append(Install(v.id, d, launcher_path(d, v), "fallback"))
    return out


# --------------------------------------------------------------------------
# Détection complète
# --------------------------------------------------------------------------

def all_installs() -> list[Install]:
    """Toutes les installations trouvées, sans doublon (première source gardée)."""
    found: list[Install] = []
    for fn in (steam_installs, epic_installs, xbox_installs, uninstall_installs, fallback_installs):
        try:
            found.extend(fn())
        except Exception as exc:  # noqa: BLE001 - une source en échec n'empêche pas les autres
            log.warning("Détection : source %s en échec : %s", fn.__name__, exc)
    unique: list[Install] = []
    for inst in found:
        if not any(u.version == inst.version and fsutil.same_path(u.game_dir, inst.game_dir) for u in unique):
            unique.append(inst)
    return unique


def default_user_dir(v: GameVersion, documents: Path | None = None) -> Path | None:
    documents = documents or winapi.documents_dir()
    if documents is None:
        return None
    return documents / "My Games" / v.documents_folder


def suggest_mods_dir(v: GameVersion, user_dir: Path | None) -> Path | None:
    """Suggestion de mods_dir."""
    if user_dir is None:
        return None
    default = user_dir / "mods"
    if v.mods_dir_fixed or not v.has_override:
        return default
    ov = gamesettings.read_override(user_dir / "gameSettings.xml")
    if ov and ov.found and ov.active and ov.directory:
        d = Path(gamesettings.override_dir_to_path(ov.directory) or "")
        # Override vers un dossier de partie FS Passion : remonter au dossier
        # de mods physique mémorisé dans parties.json.
        parts = [p.lower() for p in d.parts]
        if "parties" in parts:
            idx = len(parts) - 1 - parts[::-1].index("parties")
            version_dir = Path(*d.parts[:idx])
            pj = fsutil.read_json(version_dir / "parties.json", None)
            if isinstance(pj, dict) and pj.get("mods_dir"):
                return Path(pj["mods_dir"])
        return d
    return default


def detect_version(v: GameVersion, installs: list[Install], store_dirs: dict[str, Path],
                   documents: Path | None) -> dict[str, Any]:
    """Résultat de la détection pour une version."""
    inst = next((i for i in installs if i.version == v.id), None)
    user_dir: Path | None = None
    std = default_user_dir(v, documents)
    if std is not None and std.is_dir():
        user_dir = std
    elif v.id in store_dirs:
        user_dir = store_dirs[v.id]
    elif inst is not None and std is not None:
        user_dir = std  # jeu installé mais jamais lancé : chemin standard
    mods_dir = suggest_mods_dir(v, user_dir)
    return {
        "version": v.id,
        "game_exe": str(inst.exe) if inst else None,
        "user_dir": str(user_dir) if user_dir else None,
        "mods_dir": str(mods_dir) if mods_dir else None,
        "source": inst.source if inst else None,
    }


def detect_all() -> dict[str, dict[str, Any]]:
    installs = all_installs()
    try:
        store_dirs = store_user_dirs()
    except Exception as exc:  # noqa: BLE001
        log.warning("Détection Microsoft Store en échec : %s", exc)
        store_dirs = {}
    documents = winapi.documents_dir()
    out = {}
    for v in versions.all_versions():
        if not v.available:
            continue
        out[v.id] = detect_version(v, installs, store_dirs, documents)
    log.info("Détection : %s", {k: (r["game_exe"] is not None, r["user_dir"] is not None) for k, r in out.items()})
    return out


# --------------------------------------------------------------------------
# Règles de préremplissage
# --------------------------------------------------------------------------

PREFILL_FIELDS = ("game_exe", "user_dir", "mods_dir")


def looks_like_other_version(value: str, vid: str) -> bool:
    """Vrai si `value` porte le modèle automatique d'une AUTRE version."""
    low = value.lower()
    for v in versions.all_versions():
        if v.id == vid:
            continue
        if v.documents_folder.lower() in re.split(r"[\\/]", low):
            return True
        if Path(low).name in v.exe_names:
            return True
    return False


def prefill(cfg: dict[str, Any], det: dict[str, Any], vid: str) -> tuple[dict[str, Any], list[str]]:
    """Applique la détection à la configuration d'une version.

    Seuls les champs vides, ou qui portent encore la valeur automatique
    précédente, ou le modèle d'une autre version, sont préremplis. Un champ
    personnalisé n'est jamais modifié. Renvoie (configuration, champs modifiés).
    """
    changed: list[str] = []
    auto = cfg.setdefault("auto", {})
    for f in PREFILL_FIELDS:
        new = det.get(f)
        if not new:
            continue
        current = cfg.get(f) or ""
        prev_auto = auto.get(f) or ""
        replaceable = (
            not current
            or fsutil.same_path(current, prev_auto)
            or looks_like_other_version(current, vid)
        )
        if replaceable and not fsutil.same_path(current, new):
            cfg[f] = new
            changed.append(f)
        auto[f] = new
    return cfg, changed


# --------------------------------------------------------------------------
# Plateforme d'un jeu installé (pour le lancement)
# --------------------------------------------------------------------------

_CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"


def publisher_id(publisher: str) -> str:
    """Identifiant d'éditeur d'un package Windows (13 caractères)."""
    digest = hashlib.sha256(publisher.encode("utf-16-le")).digest()[:8]
    bits = "".join(f"{b:08b}" for b in digest) + "0"
    return "".join(_CROCKFORD[int(bits[i : i + 5], 2)] for i in range(0, 65, 5))


def _appx_identity(game_dir: Path) -> tuple[str, str, str] | None:
    """(Name, Publisher, Application Id) lus dans appxmanifest.xml."""
    for cand in (game_dir / "appxmanifest.xml", game_dir.parent / "appxmanifest.xml"):
        if not cand.is_file():
            continue
        try:
            root = ET.parse(cand).getroot()
        except (ET.ParseError, OSError):
            continue
        name = publisher = app_id = None
        for el in root.iter():
            tag = el.tag.split("}", 1)[-1]
            if tag == "Identity":
                name = el.get("Name")
                publisher = el.get("Publisher")
            elif tag == "Application" and app_id is None:
                app_id = el.get("Id")
        if name and publisher:
            return name, publisher, app_id or "App"
    return None


def platform_of(game_exe: str) -> dict[str, Any]:
    """Plateforme d'installation d'un jeu, et de quoi le lancer par elle."""
    game_dir = game_root_of_exe(game_exe)

    # Steam : le dossier est-il dans steamapps\common d'une bibliothèque ?
    try:
        for inst in steam_installs():
            if fsutil.same_path(inst.game_dir, game_dir) and inst.info.get("appid"):
                return {"platform": "steam", "uri": f"steam://rungameid/{inst.info['appid']}"}
    except Exception as exc:  # noqa: BLE001
        log.debug("Plateforme Steam : %s", exc)

    try:
        for inst in epic_installs():
            if fsutil.same_path(inst.game_dir, game_dir) and inst.info.get("app_name"):
                return {
                    "platform": "epic",
                    "uri": f"com.epicgames.launcher://apps/{inst.info['app_name']}?action=launch&silent=true",
                }
    except Exception as exc:  # noqa: BLE001
        log.debug("Plateforme Epic : %s", exc)

    ident = _appx_identity(game_dir)
    if ident is not None or "xboxgames" in [p.lower() for p in game_dir.parts]:
        if ident is not None:
            name, publisher, app_id = ident
            pfn = f"{name}_{publisher_id(publisher)}"
            pk = _packages_dir()
            if pk and pk.is_dir():
                try:
                    for e in os.scandir(pk):
                        if e.name.lower().startswith(name.lower() + "_"):
                            pfn = e.name
                            break
                except OSError:
                    pass
            return {"platform": "xbox", "uri": f"shell:AppsFolder\\{pfn}!{app_id}"}
        return {"platform": "xbox", "uri": None}

    for dll in ("steam_api64.dll", "steam_api.dll"):
        if (game_dir / dll).is_file() or (game_dir / "x64" / dll).is_file():
            return {"platform": "steam_dependent", "uri": None}

    return {"platform": "exe", "uri": None}
