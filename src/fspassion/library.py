"""La bibliothèque de mods : scan des dossiers de stockage, cache, icônes.

- Scan des dossiers de stockage, sans les sous-dossiers. Chaque élément est
  classé : mod .zip, mod non compressé, ou anomalie.
- Cache : FSPassion\\<version>\\cache\\mods.json ; seuls les mods nouveaux
  ou modifiés sont relus. Les entrées des mods disparus sont purgées.
- Le premier scan se fait en arrière-plan ; l'interface est prévenue au fur et
  à mesure (les tuiles apparaissent progressivement).
- Lecture seule : rien n'est jamais écrit dans un dossier de stockage.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fspassion import anomalies, config, dlc, fsutil, icons, moddesc, versions
from fspassion.events import EventBus
from fspassion.gamepaths import VersionPaths

log = logging.getLogger(__name__)

CACHE_SCHEMA = 4  # icônes déclarées dans des balises de langue ; <SearchMods> lu
# Anciens formats relus : les mods sont relus une fois, les icônes déjà
# converties sont reprises (même nom de base).
CACHE_SCHEMAS_REREAD = (3,)
ARCHIVE_EXTS = (".rar", ".7z")
ICON_WORKERS = max(2, min(6, (os.cpu_count() or 4) // 2))
# Fichiers système qu'il est inutile de signaler.
SILENT_FILES = {"desktop.ini", "thumbs.db", ".ds_store"}


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


class Library:
    """Bibliothèque d'une version du jeu."""

    def __init__(self, vid: str, bus: EventBus, paths_provider: Callable[[], VersionPaths],
                 on_ready: Callable[[str], None] | None = None) -> None:
        self.vid = vid
        # Appelé à la fin de chaque scan réussi (réconciliation au démarrage).
        self.on_ready = on_ready
        self.version = versions.require(vid)
        self.bus = bus
        self._paths_provider = paths_provider
        self._lock = threading.RLock()
        self._scan_lock = threading.Lock()
        self._rescan_requested = False
        self.entries: dict[str, dict[str, Any]] = {}      # clé de cache → mod
        self.anomalies: list[dict[str, Any]] = []
        self.others: list[dict[str, Any]] = []
        self.dlc: list[dict[str, Any]] = []
        self.status = "idle"            # idle | scanning | ready | error
        self.error: dict[str, Any] | None = None
        self.progress = {"done": 0, "total": 0}
        self.icons_pending = 0
        self.cache_dir: Path | None = None
        self._cache: dict[str, Any] = {}
        self._signature: str | None = None
        self._last_publish = 0.0
        self._executor: ThreadPoolExecutor | None = None
        self.scanned_at: float | None = None
        # Mesures de performance (diagnostic) : durée du dernier scan
        # complet et de la dernière conversion d'icônes.
        self.perf: dict[str, Any] = {"scan_s": None, "icons_s": None, "icons_converted": 0}
        # « Ne plus utiliser FS Passion » : plus aucun scan, donc plus
        # aucune écriture dans le cache, une fois les données supprimées.
        self.disabled = False

    # ------------------------------------------------------------------
    # Accès
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            # Un identifiant n'apparaît qu'une fois : en double, c'est celui
            # de l'index qui compte, l'autre est signalé.
            mods = sorted(self.index().values(), key=lambda e: e["id"].lower())
            return {
                "version": self.vid,
                "status": self.status,
                "error": self.error,
                "progress": dict(self.progress),
                "icons_pending": self.icons_pending,
                "mods": [self._public(e) for e in mods],
                "dlc": [{k: v for k, v in d.items() if not k.startswith("_")} for d in self.dlc],
                "anomalies": list(self.anomalies),
                "others": list(self.others),
                "storages": [str(p) for p in self._paths().storages],
            }

    @staticmethod
    def _public(e: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in e.items() if not k.startswith("_")}

    def _paths(self) -> VersionPaths:
        return self._paths_provider()

    def index(self) -> dict[str, dict[str, Any]]:
        """Mods par identifiant en minuscules (le dossier principal l'emporte en
        cas de doublon entre deux dossiers de stockage, A9)."""
        with self._lock:
            # Le dossier principal l'emporte ; dans un même dossier, l'archive
            # l'emporte sur un dossier du même nom.
            entries = sorted(self.entries.values(),
                             key=lambda e: (-int(e.get("storage") or 0), e.get("kind") == "zip"))
            return {e["id"].lower(): e for e in entries}

    def dlc_ids(self) -> set[str]:
        with self._lock:
            return {str(d.get("id", "")).lower() for d in self.dlc if d.get("present", True)}

    def find(self, mod_id: str) -> dict[str, Any] | None:
        low = mod_id.lower()
        with self._lock:
            for e in self.entries.values():
                if e["id"].lower() == low:
                    return e
        return None

    def icon_file(self, name: str) -> Path | None:
        """Chemin d'un fichier d'icône du cache (protégé contre les chemins détournés)."""
        if self.cache_dir is None or "/" in name or "\\" in name or ".." in name:
            return None
        p = self.cache_dir / "icons" / name
        return p if p.is_file() else None

    def dlc_icon_file(self, name: str) -> Path | None:
        with self._lock:
            for d in self.dlc:
                if d.get("icon") == name and d.get("_icon_path"):
                    return Path(d["_icon_path"])
        return None

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _resolve_cache_dir(self, vp: VersionPaths) -> Path:
        """FSPassion\\<version>\\cache à côté du dossier de mods ; repli local si
        ce dossier n'est pas accessible en écriture."""
        preferred = vp.fsp_dir / "cache" if vp.fsp_dir else None
        if preferred is not None:
            try:
                (preferred / "icons").mkdir(parents=True, exist_ok=True)
                probe = preferred / ".ecriture"
                probe.write_bytes(b"")
                probe.unlink()
                return preferred
            except OSError as exc:
                log.warning("Cache impossible dans %s (%s) : repli local", preferred, exc)
        fallback = config.local_dir() / "cache" / self.vid
        (fallback / "icons").mkdir(parents=True, exist_ok=True)
        return fallback

    def _load_cache(self) -> None:
        assert self.cache_dir is not None
        data = fsutil.read_json(self.cache_dir / "mods.json", None)
        if isinstance(data, dict) and data.get("schema") == CACHE_SCHEMA:
            # Une icône au format de cache précédent (sans le suffixe de format)
            # est relue, pour obtenir ses variantes 300 px et 512 px.
            def stale(item: Any) -> bool:
                base = (item.get("entry") or {}).get("_icon_base") if isinstance(item, dict) else None
                return bool(base) and not str(base).endswith("-" + icons.ICON_CACHE_FORMAT)
            self._cache = {
                k: (dict(v, stamp="") if stale(v) else v)
                for k, v in (data.get("items", {}) or {}).items()
            }
        elif isinstance(data, dict) and data.get("schema") in CACHE_SCHEMAS_REREAD:
            items = data.get("items", {}) or {}
            self._cache = {
                k: dict(v, stamp="") for k, v in items.items() if isinstance(v, dict)
            }
        else:
            self._cache = {}

    def _save_cache(self) -> None:
        if self.cache_dir is None:
            return
        with self._lock:
            items = dict(self._cache)
        try:
            fsutil.atomic_write_json(
                self.cache_dir / "mods.json",
                {"schema": CACHE_SCHEMA, "version": self.vid, "items": items},
            )
        except OSError as exc:
            log.error("Écriture du cache impossible : %s", exc)

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def request_scan(self) -> None:
        """Lance un scan en arrière-plan (ou en programme un autre s'il tourne)."""
        if self.disabled:
            return
        if not self._scan_lock.acquire(blocking=False):
            self._rescan_requested = True
            return
        t = threading.Thread(target=self._scan_thread, name=f"scan-{self.vid}", daemon=True)
        t.start()

    def _scan_thread(self) -> None:
        try:
            while True:
                self._rescan_requested = False
                try:
                    self._scan()
                except Exception as exc:  # noqa: BLE001
                    log.exception("Scan %s en échec", self.vid)
                    with self._lock:
                        self.status = "error"
                        self.error = {"key": "library.error.unexpected", "params": {"error": str(exc)}}
                    self._publish(force=True)
                if not self._rescan_requested:
                    break
        finally:
            self._scan_lock.release()

    def scan_now(self) -> None:
        """Scan immédiat, dans le fil d'exécution de l'appelant (après un
        renommage ou une suppression, la bibliothèque doit être à jour avant de
        répondre à l'interface). Attend un scan déjà en cours."""
        with self._scan_lock:
            self._rescan_requested = False
            self._scan()

    def quick_check(self) -> None:
        """Scan rapide (liste, tailles, dates) : relance un scan si quelque chose a changé."""
        vp = self._paths()
        sig = self._compute_signature(vp)
        if sig != self._signature:
            self.request_scan()

    def _compute_signature(self, vp: VersionPaths) -> str:
        parts: list[str] = []
        for idx, storage in enumerate(vp.storages):
            try:
                for e in os.scandir(storage):
                    try:
                        st = e.stat()
                        stamp = f"{st.st_size}-{int(st.st_mtime)}"
                        if e.is_dir():
                            desc = moddesc.find_moddesc_in_dir(Path(e.path))
                            stamp = f"d{int(_mtime(desc))}" if desc else "d0"
                    except OSError:
                        stamp = "?"
                    parts.append(f"{idx}|{e.name.lower()}|{stamp}")
            except OSError:
                parts.append(f"{idx}|<absent>")
        for d in vp.dlc_dirs:
            try:
                parts += [f"dlc|{e.name.lower()}" for e in os.scandir(d)]
            except OSError:
                pass
        parts.sort()
        return str(hash("\n".join(parts)))

    def _scan(self) -> None:
        started = time.perf_counter()
        vp = self._paths()
        with self._lock:
            self.status = "scanning"
            self.error = None
        self._publish(force=True)

        if not vp.storages or not vp.mods_dir or not vp.mods_dir.is_dir():
            with self._lock:
                self.entries = {}
                self.anomalies = []
                self.others = []
                self.status = "error"
                self.error = {"key": "library.error.no_mods_dir", "params": {}}
            self.dlc = dlc.scan_dlc(self.version, vp.dlc_dirs)
            self._publish(force=True)
            return

        self.cache_dir = self._resolve_cache_dir(vp)
        self._load_cache()
        signature = self._compute_signature(vp)

        # 1. Inventaire des dossiers de stockage
        items: list[tuple[int, os.DirEntry[str]]] = []
        for idx, storage in enumerate(vp.storages):
            try:
                for e in os.scandir(storage):
                    items.append((idx, e))
            except OSError as exc:
                log.warning("Dossier de stockage illisible %s : %s", storage, exc)

        new_entries: dict[str, dict[str, Any]] = {}
        new_anoms: list[dict[str, Any]] = []
        others: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        total = len(items)
        with self._lock:
            self.progress = {"done": 0, "total": total}

        for n, (idx, e) in enumerate(items, 1):
            try:
                self._classify(idx, e, new_entries, new_anoms, others, seen_keys)
            except Exception as exc:  # noqa: BLE001 - un élément ne bloque pas le scan
                log.warning("Élément ignoré %s : %s", e.path, exc)
                new_anoms.append(anomalies.make("A3", e.name, idx, reason="unexpected"))
            if n % 25 == 0 or n == total:
                with self._lock:
                    self.entries = dict(new_entries)
                    self.progress = {"done": n, "total": total}
                self._publish()

        # 2. Contrôles qui demandent la vue d'ensemble
        for entry in new_entries.values():
            gv = entry.get("game_version")
            if gv and gv != self.vid:
                new_anoms.append(
                    anomalies.make("A6", entry["file"], entry["storage"], detected=gv)
                )
            if entry.get("invalid_name"):
                new_anoms.append(
                    anomalies.make(
                        "A5", entry["file"], entry["storage"],
                        suggestion=anomalies.suggest_name(entry["id"]),
                        kind=entry["kind"],
                    )
                )

        # A9 : même identifiant deux fois, dans deux dossiers de stockage ou
        # dans le même (archive « Nom.zip » et dossier « Nom » côte à côte). Le jeu
        # n'en charge qu'un, et le ModHub ne peut pas mettre ce mod à jour.
        by_id: dict[str, list[dict[str, Any]]] = {}
        for entry in new_entries.values():
            by_id.setdefault(entry["id"].lower(), []).append(entry)
        for group in by_id.values():
            if len(group) < 2:
                continue
            group.sort(key=lambda e: (int(e.get("storage") or 0), e["kind"] != "zip"))
            kinds = {e["kind"] for e in group}
            new_anoms.append(anomalies.make(
                "A9", group[0]["id"], int(group[0].get("storage") or 0),
                files=[e["file"] for e in group], storages=sorted({int(e.get("storage") or 0) for e in group}),
                zip_and_dir=kinds == {"zip", "dir"},
            ))

        # 3. Purge du cache
        with self._lock:
            for k in list(self._cache.keys()):
                if k not in seen_keys:
                    del self._cache[k]
            self.entries = new_entries
            self.anomalies = sorted(new_anoms, key=lambda a: (a["type"], a["name"].lower()))
            self.others = sorted(others, key=lambda a: a["name"].lower())
        self._purge_icons()

        # 4. DLC
        try:
            self.dlc = dlc.scan_dlc(self.version, vp.dlc_dirs)
        except Exception as exc:  # noqa: BLE001
            log.warning("Lecture des DLC impossible : %s", exc)
            self.dlc = []

        self._save_cache()
        self._signature = signature
        with self._lock:
            self.status = "ready"
            self.scanned_at = time.time()
            self.perf["scan_s"] = round(time.perf_counter() - started, 2)
        self._publish(force=True)
        log.info(
            "Scan %s : %d mods, %d anomalies, %d DLC, %d autres fichiers",
            self.vid, len(new_entries), len(new_anoms), len(self.dlc), len(others),
        )
        if self.on_ready is not None:
            try:
                self.on_ready(self.vid)
            except Exception:  # noqa: BLE001
                log.exception("Traitement après le scan en échec")

        # 5. Icônes manquantes, en arrière-plan
        self._queue_icons()

    def _classify(
        self,
        idx: int,
        e: os.DirEntry[str],
        new_entries: dict[str, dict[str, Any]],
        new_anoms: list[dict[str, Any]],
        others: list[dict[str, Any]],
        seen_keys: set[str],
    ) -> None:
        name = e.name
        low = name.lower()
        key = f"{idx}|{low}"
        path = Path(e.path)

        if e.is_dir():
            desc = moddesc.find_moddesc_in_dir(path)
            if desc is None:
                new_anoms.append(anomalies.make("A4", name, idx))
                return
            cached = self._cache.get(key)
            icon_rel = (cached or {}).get("entry", {}).get("_icon_src") if cached else None
            icon_m = _mtime(path / icon_rel) if icon_rel else 0.0
            stamp = f"d{int(_mtime(desc))}-{int(icon_m)}"
            seen_keys.add(key)
            if cached and cached.get("stamp") == stamp:
                if cached.get("anomaly"):
                    new_anoms.append(cached["anomaly"])
                else:
                    new_entries[key] = cached["entry"]
                return
            res = moddesc.read_dir(path)
            icon_size = 0
            if res.ok and res.icon_path:
                icon_m = _mtime(path / res.icon_path)
                try:
                    icon_size = (path / res.icon_path).stat().st_size
                except OSError:
                    icon_size = 0
                stamp = f"d{int(_mtime(desc))}-{int(icon_m)}"
            self._store(key, stamp, idx, name, path, "dir", res, new_entries, new_anoms,
                        size=None, mtime=_mtime(desc), icon_size=icon_size, icon_mtime=icon_m)
            return

        if not e.is_file():
            return
        ext = os.path.splitext(low)[1]
        if ext in ARCHIVE_EXTS:
            new_anoms.append(anomalies.make("A1", name, idx, ext=ext))
            return
        if ext != ".zip":
            if low not in SILENT_FILES:
                others.append({"name": name, "storage": idx})
            return

        st = e.stat()
        stamp = f"{st.st_size}-{int(st.st_mtime)}"
        seen_keys.add(key)
        cached = self._cache.get(key)
        if cached and cached.get("stamp") == stamp:
            if cached.get("anomaly"):
                new_anoms.append(cached["anomaly"])
            else:
                new_entries[key] = cached["entry"]
            return
        res = moddesc.read_zip(path)
        self._store(key, stamp, idx, name, path, "zip", res, new_entries, new_anoms,
                    size=st.st_size, mtime=st.st_mtime, icon_size=st.st_size, icon_mtime=st.st_mtime)

    def _store(
        self,
        key: str,
        stamp: str,
        idx: int,
        name: str,
        path: Path,
        kind: str,
        res: moddesc.ModReadResult,
        new_entries: dict[str, dict[str, Any]],
        new_anoms: list[dict[str, Any]],
        size: int | None,
        mtime: float,
        icon_size: int,
        icon_mtime: float,
    ) -> None:
        if not res.ok or res.info is None:
            anomaly = anomalies.make(res.anomaly or "A3", name, idx, **res.detail)
            new_anoms.append(anomaly)
            with self._lock:
                self._cache[key] = {"stamp": stamp, "anomaly": anomaly}
            return

        info = res.info
        mod_id = name[:-4] if kind == "zip" else name
        gv = versions.detect_mod_version(mod_id, info.desc_version)
        if size is None:
            size = moddesc.dir_size(path)
        old = (self._cache.get(key) or {}).get("entry") or {}
        base = None
        if res.icon_path:
            # Zip : taille et date de l'archive. Dossier : taille et date de l'icône.
            base = icons.icon_basename(mod_id, icon_size, icon_mtime)
        entry: dict[str, Any] = {
            "id": mod_id,
            "short": versions.short_name(mod_id),
            "file": name,
            "kind": kind,
            "storage": idx,
            "size": size,
            "mtime": int(mtime),
            "desc_version": info.desc_version,
            "version": info.version,
            "author": info.author,
            "titles": info.titles,
            "is_map": info.is_map,
            "map_titles": info.map_titles,
            "dependencies": info.dependencies,
            "search_mods": info.search_mods,
            "optional_mods": info.optional_mods,
            "multiplayer": info.multiplayer,
            "game_version": gv.version,
            "gv_status": gv.status,
            "gv_warning": gv.warning,
            "invalid_name": not anomalies.is_valid_mod_name(mod_id),
            "xml_recovered": bool(res.detail.get("xml_recovered")),
            "icon": None,
            "icon_state": "none" if not res.icon_path else "pending",
            "_icon_src": res.icon_path,
            "_icon_base": base,
        }
        # Icône déjà convertie (même nom de base) : on la reprend.
        if base and old.get("_icon_base") == base and old.get("icon") and self.cache_dir:
            icons_dir = self.cache_dir / "icons"
            if all((icons_dir / n).is_file() for n in icons.icon_names(base, icons.has_medium(self.vid))[:2]):
                entry["icon"] = old["icon"]
                entry["icon_state"] = "ok"
        new_entries[key] = entry
        with self._lock:
            self._cache[key] = {"stamp": stamp, "entry": entry}

    # ------------------------------------------------------------------
    # Icônes
    # ------------------------------------------------------------------

    def _purge_icons(self) -> None:
        if self.cache_dir is None:
            return
        keep: set[str] = set()
        with self._lock:
            for item in self._cache.values():
                base = (item.get("entry") or {}).get("_icon_base")
                if base:
                    # Avant FS25, plus de variante moyenne ; celles déjà
                    # créées sont effacées ici (la grande sert à leur place).
                    keep.update(icons.icon_names(base, icons.has_medium(self.vid)))
        folder = self.cache_dir / "icons"
        try:
            for e in os.scandir(folder):
                if e.is_file() and e.name.endswith(".webp") and e.name not in keep:
                    try:
                        os.unlink(e.path)
                    except OSError:
                        pass
        except OSError:
            pass

    def _queue_icons(self) -> None:
        assert self.cache_dir is not None
        todo: list[tuple[str, dict[str, Any]]] = []
        with self._lock:
            for key, entry in self.entries.items():
                if entry.get("icon_state") != "pending" or not entry.get("_icon_base"):
                    continue
                base = entry["_icon_base"]
                if all(
                    (self.cache_dir / "icons" / name).is_file()
                    for name in icons.icon_names(base, icons.has_medium(self.vid))
                ):
                    entry["icon"] = base
                    entry["icon_state"] = "ok"
                    continue
                todo.append((key, entry))
            self.icons_pending = len(todo)
        if not todo:
            self._save_cache()
            self._publish(force=True)
            return
        icons_started = time.perf_counter()
        vp = self._paths()
        storages = vp.storages
        done_batch: list[tuple[str, str | None]] = []
        batch_lock = threading.Lock()
        last_flush = [time.time()]

        def work(key: str, entry: dict[str, Any]) -> None:
            base = entry["_icon_base"]
            result: str | None = None
            try:
                storage = storages[entry["storage"]]
                mod_path = storage / entry["file"]
                data = moddesc.read_icon_bytes(mod_path, entry["kind"], entry["_icon_src"])
                if data is None:
                    raise ValueError("icône illisible")
                assert self.cache_dir is not None
                icons.convert_icon(data, self.cache_dir / "icons", base, medium=icons.has_medium(self.vid))
                result = base
            except Exception as exc:  # noqa: BLE001
                log.info("Icône par défaut pour %s : %s", entry["file"], exc)
            with self._lock:
                entry["icon"] = result
                entry["icon_state"] = "ok" if result else "failed"
                cached = self._cache.get(key)
                if cached and "entry" in cached:
                    cached["entry"]["icon"] = result
                    cached["entry"]["icon_state"] = entry["icon_state"]
                self.icons_pending -= 1
            with batch_lock:
                done_batch.append((entry["id"], result))
                if time.time() - last_flush[0] > 0.3:
                    self._flush_icons(done_batch)
                    last_flush[0] = time.time()

        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=ICON_WORKERS, thread_name_prefix=f"icons-{self.vid}")
        futures = [self._executor.submit(work, k, e) for k, e in todo]
        for f in futures:
            try:
                f.result()
            except Exception:  # noqa: BLE001
                pass
        with batch_lock:
            self._flush_icons(done_batch)
        self.perf["icons_s"] = round(time.perf_counter() - icons_started, 2)
        self.perf["icons_converted"] = len(todo)
        self._save_cache()
        self._publish(force=True)

    def _flush_icons(self, batch: list[tuple[str, str | None]]) -> None:
        if not batch:
            return
        items = [{"id": i, "icon": b} for i, b in batch]
        batch.clear()
        self.bus.publish("icons", version=self.vid, items=items, pending=self.icons_pending)

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------

    def _publish(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_publish < 0.4:
            return
        self._last_publish = now
        with self._lock:
            payload = {
                "version": self.vid,
                "status": self.status,
                "progress": dict(self.progress),
                "count": len(self.entries),
                "icons_pending": self.icons_pending,
            }
        self.bus.publish("library", **payload)


class LibraryManager:
    """Une bibliothèque par version, créée à la demande."""

    def __init__(self, bus: EventBus, paths_for: Callable[[str], VersionPaths],
                 on_ready: Callable[[str], None] | None = None) -> None:
        self.bus = bus
        self._paths_for = paths_for
        self._on_ready = on_ready
        self._libs: dict[str, Library] = {}
        self._lock = threading.Lock()
        self._disabled = False

    def get(self, vid: str) -> Library:
        with self._lock:
            lib = self._libs.get(vid)
            if lib is None:
                lib = Library(vid, self.bus, lambda: self._paths_for(vid), self._on_ready)
                lib.disabled = self._disabled
                self._libs[vid] = lib
            return lib

    def loaded(self) -> dict[str, Library]:
        """Bibliothèques déjà ouvertes (sans en créer)."""
        with self._lock:
            return dict(self._libs)

    def disable_all(self) -> None:
        """« Ne plus utiliser FS Passion » : aucune bibliothèque, actuelle
        ou future, ne relit plus les mods ni n'écrit dans son cache."""
        with self._lock:
            self._disabled = True
            for lib in self._libs.values():
                lib.disabled = True

    def drop(self, vid: str) -> None:
        """Oublie la bibliothèque d'une version (elle sera relue à la demande)."""
        with self._lock:
            self._libs.pop(vid, None)

    def reset(self, vid: str) -> Library:
        """Après un changement de chemins : la bibliothèque repart de zéro."""
        with self._lock:
            self._libs.pop(vid, None)
        lib = self.get(vid)
        lib.request_scan()
        return lib
