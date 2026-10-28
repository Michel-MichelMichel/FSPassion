"""Pack de démonstration : essayer FS Passion sans posséder le jeu.

Une seule archive, FSPassion-demo.zip (fabriquée par tools/make_demo_pack.py),
contient de faux mods pour plusieurs versions du jeu. Elle est :
1. trouvée sur le disque (développement : FSPassion-data\\demo\\ ; version
   installée : à côté de l'exécutable), ou téléchargée depuis les « Releases »
   du projet GitHub, après accord ;
2. vérifiée (empreinte SHA-256 connue d'avance) : une archive différente est
   refusée ;
3. décompressée dans %LOCALAPPDATA%\\FSPassion\\demo\\.

En mode démonstration, les chemins des versions du jeu pointent vers ce
dossier (settings.json garde les vrais chemins à part, intacts) : créer,
appliquer, supprimer… fonctionnent pour de vrai, mais jamais dans le jeu.
Quitter le mode démonstration efface tout ce dossier.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from fspassion import config, fsutil, links

log = logging.getLogger(__name__)

PACK = "FSPassion-demo.zip"
MAX_FILES = 5000
MAX_BYTES = 300 * 1024 * 1024
TIMEOUT = 30


class DemoError(Exception):
    def __init__(self, key: str, status: int = 400, **params: Any) -> None:
        super().__init__(key)
        self.key = key
        self.status = status
        self.params = params


def demo_dir() -> Path:
    return config.local_dir() / "demo"


def _pack_info(app_info: dict[str, Any]) -> dict[str, Any]:
    info = app_info.get("demo_pack")
    return info if isinstance(info, dict) else {}


def _sidecar_sha(pack: Path) -> str | None:
    side = pack.with_name(pack.name + ".sha256")
    try:
        text = side.read_text(encoding="ascii").strip()
    except OSError:
        return None
    digest = text.split()[0].lower() if text else ""
    return digest if len(digest) == 64 else None


def local_pack(app_info: dict[str, Any]) -> tuple[Path, str] | None:
    """Archive présente sur le disque, avec son empreinte attendue."""
    candidates = [config.dev_data_dir() / "demo" / PACK, config.exe_dir() / PACK]
    expected = str(_pack_info(app_info).get("sha256") or "").lower() or None
    for p in candidates:
        if p.is_file():
            sha = expected or _sidecar_sha(p)
            if sha:
                return p, sha
    return None


def availability(app_info: dict[str, Any], internet: bool) -> dict[str, Any]:
    info = _pack_info(app_info)
    local = local_pack(app_info)
    url = info.get("url") if internet and info.get("url") and info.get("sha256") else None
    return {
        "local": bool(local),
        "download": bool(url),
        "size": info.get("size"),
        "available": bool(local or url),
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    if not url.startswith("https://"):
        raise DemoError("demo.download_failed", detail="https")
    req = urllib.request.Request(url, headers={"User-Agent": "FSPassion"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r, open(dest, "wb") as f:  # noqa: S310
            total = 0
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    raise DemoError("demo.bad_pack")
                f.write(chunk)
    except OSError as exc:
        raise DemoError("demo.download_failed", detail=str(exc)) from exc


def _extract(pack: Path, dest: Path) -> None:
    """Décompression prudente : aucun chemin absolu ni « .. », taille limitée."""
    with zipfile.ZipFile(pack) as zf:
        members = zf.infolist()
        if len(members) > MAX_FILES or sum(m.file_size for m in members) > MAX_BYTES:
            raise DemoError("demo.bad_pack")
        root = dest.resolve()
        written = 0  # octets réellement copiés (les tailles des en-têtes ZIP peuvent mentir)
        for m in members:
            name = m.filename.replace("\\", "/")
            if name.startswith("/") or ":" in name or any(part == ".." for part in name.split("/")):
                raise DemoError("demo.bad_pack")
            target = (dest / name).resolve()
            if not fsutil.is_within(target, root) and target != root:
                raise DemoError("demo.bad_pack")
            if m.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(m) as src, open(target, "wb") as out:
                while True:
                    chunk = src.read(1024 * 256)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_BYTES:
                        raise DemoError("demo.bad_pack")
                    out.write(chunk)


def install(app_info: dict[str, Any], internet: bool) -> dict[str, Any]:
    """Prépare le dossier de démonstration. Renvoie le manifeste (demo.json)."""
    base = config.local_dir()
    base.mkdir(parents=True, exist_ok=True)
    local = local_pack(app_info)
    tmp_pack = base / "demo-download.zip"
    pack: Path | None = None
    try:
        if local is not None:
            pack, expected = local
        else:
            info = _pack_info(app_info)
            if not (internet and info.get("url") and info.get("sha256")):
                raise DemoError("demo.unavailable")
            # Le téléchargement est dans le bloc try : un fichier partiel est
            # effacé même si le téléchargement échoue.
            pack = tmp_pack
            _download(str(info["url"]), tmp_pack)
            expected = str(info["sha256"]).lower()
        if _sha256(pack) != expected:
            log.error("Pack de démonstration refusé : empreinte inattendue (%s)", pack)
            raise DemoError("demo.bad_pack")
        target = demo_dir()
        staging = base / "demo.new"
        for leftover in (staging, target):
            if leftover.exists():
                remove_tree(leftover)
        staging.mkdir()
        try:
            _extract(pack, staging)
        except (OSError, zipfile.BadZipFile, DemoError) as exc:
            remove_tree(staging)
            if isinstance(exc, DemoError):
                raise
            raise DemoError("demo.bad_pack", detail=str(exc)) from exc
        os.replace(staging, target)
    finally:
        if pack == tmp_pack:
            try:
                tmp_pack.unlink()
            except OSError:
                pass
    data = fsutil.read_json(target / "demo.json", None)
    if not isinstance(data, dict) or not isinstance(data.get("versions"), dict):
        remove_tree(target)
        raise DemoError("demo.bad_pack")
    log.info("Pack de démonstration installé : %s", target)
    return data


def manifest() -> dict[str, Any] | None:
    data = fsutil.read_json(demo_dir() / "demo.json", None)
    return data if isinstance(data, dict) else None


def _inside_demo(rel: str) -> bool:
    """Chemin relatif sans « .. », sans lecteur ni racine."""
    parts = rel.replace("\\", "/").split("/")
    return not (rel.startswith(("/", "\\")) or ":" in rel or ".." in parts)


def version_cfgs(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Chemins de chaque version du jeu dans le dossier de démonstration."""
    root = demo_dir()
    out: dict[str, dict[str, Any]] = {}
    for vid, v in (data.get("versions") or {}).items():
        if not isinstance(v, dict):
            continue
        user_rel = str(v.get("user_dir") or f"{vid}/Documents")
        mods_rel = str(v.get("mods_dir") or f"{vid}/Mods")
        if not _inside_demo(user_rel) or not _inside_demo(mods_rel):
            continue  # chemin qui sortirait du dossier de démonstration
        user = root / user_rel
        mods = root / mods_rel
        out[str(vid)] = {"game_exe": "", "user_dir": str(user), "mods_dir": str(mods)}
    return out


def remove_tree(root: Path) -> None:
    """Efface un dossier de démonstration. Les liens (jonctions, liens
    symboliques) sont retirés comme des liens, sans suivre leur cible."""
    base = config.local_dir().resolve()
    if not fsutil.is_within(root, base) or root.resolve() == base:
        raise DemoError("error.forbidden", status=403)
    if links.is_link(root):
        links.remove_link(root)
        return
    for entry in os.scandir(root):
        p = Path(entry.path)
        if links.is_link(p):
            links.remove_link(p)
        elif entry.is_dir(follow_symlinks=False):
            remove_tree(p)
        else:
            try:
                os.unlink(p)
            except PermissionError:
                os.chmod(p, 0o666)
                os.unlink(p)
    os.rmdir(root)


def remove(attempts: int = 5) -> None:
    """Efface tout le dossier de démonstration. Quelques essais, car la
    conversion d'icônes en cours peut encore y écrire un instant après le
    retour aux vrais chemins (sinon « Quitter » échouait de temps en temps)."""
    target = demo_dir()
    for attempt in range(attempts):
        if not (target.exists() or os.path.lexists(target)):
            return
        try:
            remove_tree(target)
            log.info("Dossier de démonstration effacé : %s", target)
            return
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.4)
