"""Les parties et le fichier parties.json.

Une partie est une collection nommée de mods : sa map, ses mods propres, et le
choix d'inclure ou non les mods communs. Un fichier parties.json par version du
jeu, dans FSPassion\\<version>\\, à côté du dossier de mods principal.

Ce module ne gère que parties.json. Les dossiers de parties, les liens et
l'override sont l'affaire d'apply.py ; « applied_signature » mémorise,
pour chaque partie, l'empreinte de ses mods actifs à sa dernière application
(« Appliquer » est mis en évidence quand elle a changé).

Robustesse :
- écriture atomique (fichier temporaire, puis remplacement) ;
- rotation de 5 sauvegardes (parties.json.bak1 … bak5) à chaque changement de
  contenu (un simple changement de partie sélectionnée ne fait pas tourner les
  sauvegardes, pour qu'elles gardent de vraies versions précédentes) ;
- fichier illisible au démarrage : chargement de la sauvegarde valide la plus
  récente, le fichier illisible est mis de côté, et un message le dit.

Parties spéciales : « _vide » (Partie Vide) et « _pleine » (Partie Pleine).
Elles ne sont pas stockées dans la liste des parties : ni renommables, ni
modifiables, ni dupliquables, ni supprimables.
"""

from __future__ import annotations

import copy
import logging
import os
import re
import secrets
import threading
import time
import unicodedata
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from fspassion import fsutil

log = logging.getLogger(__name__)

SCHEMA = 1
EMPTY = "_vide"
FULL = "_pleine"
SPECIALS = (FULL, EMPTY)
MAX_NAME = 60
HISTORY_MAX = 10
BACKUPS = 5
MAX_IDS = 5000  # garde-fou : nombre de mods traités en une seule demande

_SPACES_RE = re.compile(r"\s+")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_ID_RE = re.compile(r"^[0-9a-f]{4,8}$")


class PartyError(Exception):
    """Erreur prévue, avec une clé de langue."""

    def __init__(self, key: str, status: int = 400, **params: Any) -> None:
        super().__init__(key)
        self.key = key
        self.status = status
        self.params = params


# --------------------------------------------------------------------------
# Noms et identifiants
# --------------------------------------------------------------------------

def clean_name(name: Any) -> str:
    """Nom affiché : libre (accents et espaces acceptés), espaces superflus retirés."""
    s = _CONTROL_RE.sub("", str(name or ""))
    return _SPACES_RE.sub(" ", s).strip()


def slugify(name: str) -> str:
    """Version ASCII du nom, pour le dossier : « Hof Bergmann » → « hof-bergmann »."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("ß", "ss").replace("æ", "ae").replace("Æ", "AE").replace("ø", "o").replace("Ø", "O")
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    s = s[:40].strip("-")
    return s or "partie"


def folder_name(name: str, pid: str) -> str:
    """Nom du dossier sur le disque : version ASCII du nom + identifiant court."""
    return f"{slugify(name)}-{pid}"


def is_special(pid: str | None) -> bool:
    return pid in SPECIALS


# --------------------------------------------------------------------------
# Listes d'identifiants de mods (comparaisons sans casse)
# --------------------------------------------------------------------------

def _dedupe(ids: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in ids:
        if not isinstance(x, str):
            continue
        s = x.strip()
        if not s or s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
    return out


def _lower_set(ids: Iterable[str]) -> set[str]:
    return {i.lower() for i in ids}


# --------------------------------------------------------------------------
# Données par défaut et contrôle d'un fichier lu
# --------------------------------------------------------------------------

def default_data(vid: str, mods_dir: str = "", extra: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "game_version": vid,
        "mods_dir": mods_dir,
        "extra_mods_dirs": list(extra or []),
        "common_mods": [],
        "parties": [],
        "selected": FULL,
        "applied": None,
        "applied_history": [],
        "applied_signature": {},
    }


def _clean_party(raw: Any, used_ids: set[str]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    pid = str(raw.get("id") or "").lower()
    name = clean_name(raw.get("name"))
    if not _ID_RE.match(pid) or pid in used_ids or not name:
        return None
    used_ids.add(pid)
    mods = _dedupe(raw.get("mods") or [])
    # Le dossier se recalcule à partir du nom et de l'identifiant : la valeur
    # lue du fichier (parties.json, import) n'est jamais utilisée sur le disque.
    # Un nom de dossier ne contient donc jamais de séparateur ni « .. ».
    folder = folder_name(name[:MAX_NAME], pid)
    map_id = raw.get("map")
    if not isinstance(map_id, str) or not map_id.strip():
        map_id = None
    created = raw.get("created")
    if not isinstance(created, str):
        created = None
    req = raw.get("required_dlc")
    return {
        "id": pid,
        "name": name[:MAX_NAME],
        "folder": folder,
        "map": map_id,
        "common_enabled": raw.get("common_enabled") is not False,
        "mods": mods,
        "required_dlc": _dedupe(req) if isinstance(req, list) else [],
        "created": created,
    }


def validate(raw: Any, vid: str) -> dict[str, Any]:
    """Contrôle un contenu lu sur le disque. Lève ValueError s'il est inutilisable.

    Les éléments abîmés (partie sans nom, identifiant en double…) sont écartés
    plutôt que de rendre tout le fichier inutilisable.
    """
    if not isinstance(raw, dict):
        raise ValueError("format inattendu")
    schema = raw.get("schema")
    if not isinstance(schema, int) or schema < 1:
        raise ValueError("schéma absent")
    if schema > SCHEMA:
        # Fichier écrit par une version plus récente de FS Passion : on ne le
        # réécrit pas avec un format plus ancien.
        raise ValueError(f"schéma {schema} plus récent")
    if not isinstance(raw.get("parties", []), list):
        raise ValueError("liste des parties invalide")
    out = default_data(vid, str(raw.get("mods_dir") or ""), [str(x) for x in raw.get("extra_mods_dirs") or [] if x])
    used: set[str] = set()
    for p in raw.get("parties", []):
        clean = _clean_party(p, used)
        if clean is not None:
            out["parties"].append(clean)
    out["common_mods"] = _dedupe(raw.get("common_mods") or [])
    known = used | set(SPECIALS)
    sel = raw.get("selected")
    out["selected"] = sel if sel in known else FULL
    applied = raw.get("applied")
    out["applied"] = applied if applied in known else None
    hist = [h for h in raw.get("applied_history") or [] if h in known]
    out["applied_history"] = list(dict.fromkeys(hist))[:HISTORY_MAX]
    sigs = raw.get("applied_signature")
    if isinstance(sigs, dict):
        out["applied_signature"] = {str(k): str(v) for k, v in sigs.items() if k in known and isinstance(v, str)}
    return out


def _content(data: dict[str, Any]) -> dict[str, Any]:
    """Contenu qui compte pour les sauvegardes (sans la partie sélectionnée)."""
    return {k: v for k, v in data.items() if k != "selected"}


# --------------------------------------------------------------------------
# Le fichier d'une version
# --------------------------------------------------------------------------

class PartiesStore:
    """parties.json d'une version du jeu. Toutes les méthodes sont protégées par
    un verrou : l'interface peut appeler depuis plusieurs fils d'exécution."""

    def __init__(self, vid: str, path: Path, mods_dir: str = "", extra_mods_dirs: list[str] | None = None) -> None:
        self.vid = vid
        self.path = path
        self._lock = threading.RLock()
        self._mods_dir = mods_dir
        self._extra = list(extra_mods_dirs or [])
        self.data: dict[str, Any] = default_data(vid, mods_dir, self._extra)
        self.exists = False
        self.recovered: str | None = None   # « bak2 » : chargé depuis une sauvegarde
        self.lost = False                   # aucune version lisible : départ à neuf
        # Fichier illisible resté en place (mise de côté impossible) : aucune
        # écriture tant qu'il n'est pas mis de côté, pour ne pas l'écraser.
        self.blocked = False
        self._saved_content: dict[str, Any] | None = None

    # -- chemins -------------------------------------------------------------

    def backup_path(self, n: int) -> Path:
        return self.path.with_name(f"{self.path.name}.bak{n}")

    # -- lecture ---------------------------------------------------------------

    def load(self) -> None:
        with self._lock:
            self.recovered = None
            self.lost = False
            self.blocked = False
            if not self.path.exists():
                self.exists = False
                self.data = default_data(self.vid, self._mods_dir, self._extra)
                self._saved_content = None
                return
            try:
                self.data = validate(fsutil.read_json_strict(self.path), self.vid)
                self.exists = True
                self._saved_content = copy.deepcopy(_content(self.data))
                self._check_storage()
                return
            except (OSError, ValueError) as exc:
                log.error("parties.json illisible (%s) : %s", self.path, exc)
            # Fichier illisible : la sauvegarde valide la plus récente.
            for n in range(1, BACKUPS + 1):
                bak = self.backup_path(n)
                if not bak.is_file():
                    continue
                try:
                    data = validate(fsutil.read_json_strict(bak), self.vid)
                except (OSError, ValueError) as exc:
                    log.warning("Sauvegarde illisible %s : %s", bak, exc)
                    continue
                self.data = data
                self.recovered = f"bak{n}"
                self.exists = True
                if self._set_aside():
                    self._write(rotate=False)
                else:
                    self.blocked = True
                log.warning("parties.json rétabli depuis %s", bak.name)
                return
            # Aucune version lisible : on repart de zéro, sans rien effacer.
            if not self._set_aside():
                self.blocked = True
            self.data = default_data(self.vid, self._mods_dir, self._extra)
            self.exists = False
            self.lost = True
            self._saved_content = None

    def _set_aside(self) -> bool:
        """Met de côté un parties.json illisible (jamais supprimé). Renvoie False
        si le fichier n'a pas pu être mis de côté."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        broken = self.path.with_name(f"{self.path.name}.illisible-{stamp}")
        try:
            self.path.replace(broken)
            log.error("parties.json illisible mis de côté : %s", broken.name)
            return True
        except OSError as exc:
            log.error("parties.json illisible non mis de côté (%s) : %s", self.path, exc)
            return False

    def _check_storage(self) -> None:
        stored = self.data.get("mods_dir") or ""
        if stored and self._mods_dir and not fsutil.same_path(stored, self._mods_dir):
            # Dossier de mods déplacé à la main : signalé dans le journal seulement.
            log.warning("parties.json %s : dossier de mods mémorisé %s, configuré %s",
                        self.vid, stored, self._mods_dir)

    # -- écriture --------------------------------------------------------------

    def _write(self, rotate: bool) -> None:
        data = self.data
        if not data.get("mods_dir"):
            data["mods_dir"] = self._mods_dir
            data["extra_mods_dirs"] = list(self._extra)
        payload = fsutil.json_bytes(data)
        if rotate and self.path.is_file():
            self._rotate()
        fsutil.atomic_write_bytes(self.path, payload)
        self.exists = True
        self._saved_content = copy.deepcopy(_content(data))

    def _rotate(self) -> None:
        """bak4 → bak5, …, bak1 → bak2, puis parties.json actuel → bak1."""
        try:
            for n in range(BACKUPS - 1, 0, -1):
                src = self.backup_path(n)
                if src.is_file():
                    os.replace(src, self.backup_path(n + 1))
            fsutil.atomic_write_bytes(self.backup_path(1), self.path.read_bytes())
        except OSError as exc:
            # Une sauvegarde manquée n'empêche pas l'enregistrement.
            log.warning("Rotation des sauvegardes de parties.json impossible : %s", exc)

    def save(self) -> None:
        with self._lock:
            if self.blocked:
                log.error("Écriture de parties.json refusée, fichier illisible non mis de côté : %s", self.path)
                raise PartyError("parties.write_failed", status=500, path=str(self.path))
            rotate = self._saved_content is None or _content(self.data) != self._saved_content
            try:
                self._write(rotate=rotate)
            except OSError as exc:
                log.error("Écriture de parties.json impossible (%s) : %s", self.path, exc)
                raise PartyError("parties.write_failed", status=500, path=str(self.path)) from exc

    def _commit(self, before: dict[str, Any]) -> None:
        """Enregistre ; en cas d'échec, l'état d'avant est rétabli."""
        try:
            self.save()
        except PartyError:
            self.data = before
            raise

    # -- accès -------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self.data)

    def party(self, pid: str) -> dict[str, Any] | None:
        for p in self.data["parties"]:
            if p["id"] == pid:
                return p
        return None

    def _require(self, pid: str) -> dict[str, Any]:
        if is_special(pid):
            raise PartyError("parties.special_locked")
        p = self.party(pid)
        if p is None:
            raise PartyError("parties.not_found", status=404)
        return p

    def known(self, pid: str | None) -> bool:
        return pid in SPECIALS or (pid is not None and self.party(pid) is not None)

    def find_by_folder(self, folder: str) -> str | None:
        low = folder.lower()
        for p in self.data["parties"]:
            if p["folder"].lower() == low:
                return str(p["id"])
        return None

    # -- noms ----------------------------------------------------------------------

    def check_name(self, name: Any, exclude: str | None = None) -> str:
        clean = clean_name(name)
        if not clean:
            raise PartyError("parties.name_empty")
        if len(clean) > MAX_NAME:
            raise PartyError("parties.name_too_long", max=MAX_NAME)
        low = clean.casefold()
        for p in self.data["parties"]:
            if p["id"] != exclude and p["name"].casefold() == low:
                raise PartyError("parties.name_taken", name=clean)
        return clean

    def _new_id(self) -> str:
        used = {p["id"] for p in self.data["parties"]}
        while True:
            pid = secrets.token_hex(2)
            if pid not in used:
                return pid

    # -- actions sur les parties -----------------------------------------------------

    def create(self, name: Any, mods: Iterable[str] = (), map_id: str | None = None,
               common_enabled: bool = True, select: bool = True) -> dict[str, Any]:
        with self._lock:
            clean = self.check_name(name)
            before = copy.deepcopy(self.data)
            pid = self._new_id()
            party = {
                "id": pid,
                "name": clean,
                "folder": folder_name(clean, pid),
                "map": map_id,
                "common_enabled": bool(common_enabled),
                "mods": _dedupe(mods),
                "required_dlc": [],
                "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            self.data["parties"].append(party)
            if select:
                self.data["selected"] = pid
            self._commit(before)
            return copy.deepcopy(party)

    def duplicate(self, pid: str, name: Any) -> dict[str, Any]:
        with self._lock:
            src = self._require(pid)
            return self.create(name, src["mods"], src["map"], src["common_enabled"])

    def rename(self, pid: str, name: Any) -> dict[str, Any]:
        with self._lock:
            party = self._require(pid)
            clean = self.check_name(name, exclude=pid)
            if clean == party["name"]:
                return copy.deepcopy(party)
            before = copy.deepcopy(self.data)
            party["name"] = clean
            # Le nom de dossier suit le nom (le dossier lui-même est renommé
            # par apply.py, avant cet enregistrement).
            party["folder"] = folder_name(clean, pid)
            self._commit(before)
            return copy.deepcopy(party)

    def delete(self, pid: str) -> dict[str, Any]:
        """Supprime une partie. Si c'était la partie appliquée, la partie appliquée
        précédente (historique) prend sa place, sinon la Partie Pleine."""
        with self._lock:
            party = self._require(pid)
            before = copy.deepcopy(self.data)
            self.data["parties"] = [p for p in self.data["parties"] if p["id"] != pid]
            self.data.get("applied_signature", {}).pop(pid, None)
            history = [h for h in self.data["applied_history"] if h != pid]
            self.data["applied_history"] = history
            was_applied = self.data["applied"] == pid
            fallback = None
            if was_applied:
                fallback = history[0] if history else FULL
                self.data["applied"] = fallback
                if not history:
                    self.data["applied_history"] = [FULL]
            if self.data["selected"] == pid:
                applied = self.data["applied"]
                self.data["selected"] = applied if self.known(applied) else FULL
            self._commit(before)
            return {"deleted": copy.deepcopy(party), "was_applied": was_applied, "fallback": fallback}

    def select(self, pid: str) -> None:
        with self._lock:
            if not self.known(pid):
                raise PartyError("parties.not_found", status=404)
            if self.data["selected"] == pid:
                return
            before = copy.deepcopy(self.data)
            self.data["selected"] = pid
            self._commit(before)

    def set_common_enabled(self, pid: str, enabled: bool) -> None:
        with self._lock:
            party = self._require(pid)
            if party["common_enabled"] == bool(enabled):
                return
            before = copy.deepcopy(self.data)
            party["common_enabled"] = bool(enabled)
            self._commit(before)

    def record_applied(self, pid: str, sig: str | None = None) -> bool:
        """Partie appliquée (celle que charge le jeu), historique des 10 dernières
        et, après « Appliquer », empreinte de ses mods actifs."""
        with self._lock:
            if not self.known(pid):
                return False
            history = [pid] + [h for h in self.data["applied_history"] if h != pid]
            sigs = self.data.setdefault("applied_signature", {})
            same_sig = sig is None or sigs.get(pid) == sig
            if self.data["applied"] == pid and history[:HISTORY_MAX] == self.data["applied_history"] and same_sig:
                return False
            before = copy.deepcopy(self.data)
            self.data["applied"] = pid
            self.data["applied_history"] = history[:HISTORY_MAX]
            if sig is not None:
                sigs[pid] = sig
            self._commit(before)
            return True

    def preview_rename(self, pid: str, name: Any) -> tuple[str, str]:
        """Nom contrôlé et nouveau nom de dossier, sans rien enregistrer."""
        with self._lock:
            party = self._require(pid)
            clean = self.check_name(name, exclude=pid)
            return clean, folder_name(clean, pid) if clean != party["name"] else party["folder"]

    def init_selection(self, pid: str | None) -> None:
        """Premier lancement : la partie sélectionnée reflète l'état réel du jeu."""
        with self._lock:
            if pid and self.known(pid):
                self.data["selected"] = pid

    # -- listes de mods ----------------------------------------------------------------

    def _list(self, target: str, pid: str | None) -> list[str]:
        if target == "common":
            return list(self.data["common_mods"])
        if target == "party" and pid is not None:
            return list(self._require(pid)["mods"])
        raise PartyError("error.bad_request")

    def _set_list(self, target: str, pid: str | None, mods: list[str]) -> None:
        if target == "common":
            self.data["common_mods"] = mods
        else:
            assert pid is not None
            self._require(pid)["mods"] = mods

    def change_mods(
        self,
        action: str,
        target: str,
        ids: Iterable[str],
        pid: str | None = None,
        source: str | None = None,
        is_map: Callable[[str], bool] | None = None,
    ) -> dict[str, int]:
        """Ajoute, retire ou déplace des mods.

        action : add | remove | move. target : party | common. Pour « move »,
        source est la liste d'origine (party | common), d'où les mods sont
        retirés. Un mod peut être à la fois dans la partie et dans les mods
        communs : il n'est jamais dupliqué dans le dossier de la partie.
        """
        wanted = _dedupe(ids)
        if len(wanted) > MAX_IDS:
            raise PartyError("error.bad_request")
        if action not in ("add", "remove", "move"):
            raise PartyError("error.bad_request")
        if action == "move" and (source not in ("party", "common") or source == target):
            raise PartyError("error.bad_request")
        with self._lock:
            before = copy.deepcopy(self.data)
            added = removed = 0
            if action == "move":
                assert source is not None
                src = self._list(source, pid)
                src_low = _lower_set(src)
                wanted = [w for w in wanted if w.lower() in src_low]
                wl = _lower_set(wanted)
                kept = [m for m in src if m.lower() not in wl]
                removed = len(src) - len(kept)
                self._set_list(source, pid, kept)
            dst = self._list(target, pid)
            dst_low = _lower_set(dst)
            if action in ("add", "move"):
                extra = [w for w in wanted if w.lower() not in dst_low]
                added = len(extra)
                self._set_list(target, pid, dst + extra)
            else:
                wl = _lower_set(wanted)
                kept = [m for m in dst if m.lower() not in wl]
                removed = len(dst) - len(kept)
                self._set_list(target, pid, kept)
            if is_map is not None:
                self._refresh_maps(is_map)
            if self.data != before:
                self._commit(before)
            return {"added": added, "removed": removed}

    def replace_mod(self, old: str, new: str, is_map: Callable[[str], bool] | None = None) -> int:
        """« Remplacer par… » : un mod renommé par son auteur reprend sa
        place dans toutes les listes. Renvoie le nombre de listes modifiées."""
        old_l, new = old.lower(), new.strip()
        if not new or old_l == new.lower():
            raise PartyError("error.bad_request")
        with self._lock:
            before = copy.deepcopy(self.data)
            touched = 0

            def swap(mods: list[str]) -> list[str]:
                nonlocal touched
                if old_l not in _lower_set(mods):
                    return mods
                touched += 1
                return _dedupe(new if m.lower() == old_l else m for m in mods)

            self.data["common_mods"] = swap(self.data["common_mods"])
            for p in self.data["parties"]:
                p["mods"] = swap(p["mods"])
                if p["map"] and p["map"].lower() == old_l:
                    p["map"] = new
            if is_map is not None:
                self._refresh_maps(is_map)
            if touched:
                self._commit(before)
            return touched

    def replace_case(self, old: str, new: str) -> int:
        """Renommage qui ne change que la casse : l'identifiant est réécrit
        partout, sans changer de mod. Renvoie le nombre de listes modifiées."""
        old_l = old.lower()
        if new.lower() != old_l:
            raise PartyError("error.bad_request")
        with self._lock:
            before = copy.deepcopy(self.data)
            touched = 0

            def fix(mods: list[str]) -> list[str]:
                nonlocal touched
                if any(m.lower() == old_l and m != new for m in mods):
                    touched += 1
                    return [new if m.lower() == old_l else m for m in mods]
                return mods

            self.data["common_mods"] = fix(self.data["common_mods"])
            for p in self.data["parties"]:
                p["mods"] = fix(p["mods"])
                if p["map"] and p["map"].lower() == old_l:
                    p["map"] = new
            if self.data != before:
                self._commit(before)
            return touched

    def remove_everywhere(self, ids: Iterable[str]) -> int:
        """Retire des mods de toutes les listes (mods communs et toutes les
        parties) : mod absent qu'on abandonne, suppression définitive.
        Renvoie le nombre de listes modifiées."""
        low = _lower_set(_dedupe(ids))
        if not low:
            return 0
        with self._lock:
            before = copy.deepcopy(self.data)
            touched = 0
            kept = [m for m in self.data["common_mods"] if m.lower() not in low]
            if len(kept) != len(self.data["common_mods"]):
                touched += 1
                self.data["common_mods"] = kept
            for p in self.data["parties"]:
                kept = [m for m in p["mods"] if m.lower() not in low]
                if len(kept) != len(p["mods"]):
                    touched += 1
                    p["mods"] = kept
                if p["map"] and p["map"].lower() in low:
                    p["map"] = None
            if touched:
                self._commit(before)
            return touched

    def _refresh_maps(self, is_map: Callable[[str], bool]) -> None:
        """Le champ « map » sert à l'icône du menu des parties. Il suit le
        contenu de la partie : la map retirée est remplacée par une autre map de
        la partie, ou par rien."""
        for p in self.data["parties"]:
            low = _lower_set(p["mods"])
            if p["map"] and p["map"].lower() in low:
                continue
            maps = sorted((m for m in p["mods"] if is_map(m)), key=str.lower)
            p["map"] = maps[0] if maps else None

    # -- état pour l'interface -----------------------------------------------------------

    def referenced(self) -> dict[str, dict[str, Any]]:
        """Chaque mod référencé (identifiant en minuscules) et où il l'est."""
        with self._lock:
            out: dict[str, dict[str, Any]] = {}
            for p in self.data["parties"]:
                for m in p["mods"]:
                    out.setdefault(m.lower(), {"id": m, "parties": [], "common": False})["parties"].append(p["name"])
            for m in self.data["common_mods"]:
                out.setdefault(m.lower(), {"id": m, "parties": [], "common": False})["common"] = True
            return out


# --------------------------------------------------------------------------
# Dépendances
# --------------------------------------------------------------------------

def resolve_dependencies(
    roots: Iterable[str],
    mods: dict[str, dict[str, Any]],
    dlc_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Dépendances de `roots`, dépendances des dépendances comprises.

    mods : identifiant en minuscules → mod de la bibliothèque (avec sa liste
    « dependencies »). Les comparaisons ignorent la casse ; une boucle de
    dépendances ne pose pas de problème.

    Renvoie :
    - present : dépendances présentes dans la bibliothèque (hors racines) ;
    - missing : dépendances absentes, par leur nom (à télécharger) ;
    - dlc : dépendances de type DLC (« pdlc_… »), informatives, avec « owned » ;
    - required_by : pour chaque dépendance (en minuscules), la racine qui
      l'a fait entrer, pour expliquer « le mod X est une dépendance de la map Y » ;
    - optional : mods facultatifs (<SearchMods><optionalMod>) des racines
      et de leurs dépendances, hors mods déjà requis : {name, id, present,
      required_by} ; « id » est l'identifiant du mod présent, sinon None ;
    - links : pour un mod absent, requis ou facultatif (en minuscules),
      le lien de téléchargement donné par l'auteur ({url, mod} : « mod » est le
      mod dont le modDesc.xml donne ce lien).
    """
    dlc_ids = {d.lower() for d in (dlc_ids or set())}
    root_list = _dedupe(roots)
    root_low = _lower_set(root_list)
    seen: set[str] = set(root_low)
    present: list[str] = []
    missing: list[str] = []
    dlc: list[dict[str, Any]] = []
    dlc_seen: set[str] = set()
    queue = [r.lower() for r in root_list]
    origin: dict[str, str] = {}
    for r in root_list:
        entry = mods.get(r.lower())
        origin[r.lower()] = str(entry["id"]) if entry else r
    required_by: dict[str, str] = {}
    while queue:
        cur = queue.pop(0)
        entry = mods.get(cur)
        if entry is None:
            continue
        for dep in entry.get("dependencies") or []:
            if not isinstance(dep, str) or not dep.strip():
                continue
            dep = dep.strip()
            low = dep.lower()
            if low.startswith("pdlc_"):
                name = dep[5:]
                if name.lower() not in dlc_seen:
                    dlc_seen.add(name.lower())
                    dlc.append({"id": name, "owned": name.lower() in dlc_ids})
                continue
            if low in seen:
                continue
            seen.add(low)
            origin[low] = origin.get(cur, cur)
            required_by[low] = origin[low]
            found = mods.get(low)
            if found is None:
                missing.append(dep)
                continue
            present.append(str(found["id"]))
            queue.append(low)
    present.sort(key=str.lower)
    missing.sort(key=str.lower)
    dlc.sort(key=lambda d: d["id"].lower())

    # Mods facultatifs et liens de téléchargement (<SearchMods>).
    visited = [r.lower() for r in root_list] + [p.lower() for p in present]
    optional: list[dict[str, Any]] = []
    opt_seen: set[str] = set()
    links: dict[str, dict[str, str]] = {}
    missing_low = {m.lower() for m in missing}
    for cur in visited:
        entry = mods.get(cur)
        if entry is None:
            continue
        src = str(entry["id"])
        for kind in ("search_mods", "optional_mods"):
            for item in entry.get(kind) or []:
                if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                    continue
                name = item["name"].strip()
                low = name.lower()
                if not name:
                    continue
                found = mods.get(low)
                url = item.get("url")
                if found is None and isinstance(url, str) and url and low not in links:
                    if kind == "optional_mods" or low in missing_low:
                        links[low] = {"url": url, "mod": src}
                if kind != "optional_mods" or low in seen or low in opt_seen:
                    continue
                opt_seen.add(low)
                optional.append({
                    "name": name,
                    "id": str(found["id"]) if found else None,
                    "present": found is not None,
                    "required_by": origin.get(cur, src),
                })
    optional.sort(key=lambda o: (not o["present"], o["name"].lower()))
    return {"present": present, "missing": missing, "dlc": dlc, "required_by": required_by,
            "optional": optional, "links": links}
