"""Langues.

- Toutes les chaînes viennent de fichiers lang/<code>.json.
- Langues personnelles : %APPDATA%\\FSPassion\\lang\\ (ou data\\lang\\ en mode
  portable). C'est l'utilisateur qui nomme sa langue dans le fichier
  (_meta.name). Un fichier personnel qui porte le code d'une langue fournie la
  remplace.
- Sécurité : un fichier de langue ne peut rien exécuter. L'interface affiche
  toujours ses textes comme du texte brut. Taille limitée, fichier invalide
  ignoré (avec un message).
- Une clé absente est remplacée par l'anglais.
"""

from __future__ import annotations

import copy
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from fspassion import config, winapi

log = logging.getLogger(__name__)

REFERENCE = "en"
# Taille maximale d'un fichier de langue personnel. Assez grande pour une copie
# corrigée d'une langue fournie (russe, japonais, chinois…, 2 à 3 octets par
# caractère en UTF-8).
MAX_USER_LANG_BYTES = 300 * 1024
TEMPLATE_NAME = "_modele_en.json"


def _read_lang_file(path: Path, limit: int | None) -> tuple[dict[str, Any] | None, str | None]:
    """Lit un fichier de langue. Renvoie (données, motif de refus)."""
    try:
        size = path.stat().st_size
        if limit is not None and size > limit:
            return None, "too_big"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None, "invalid"
    if not isinstance(data, dict):
        return None, "invalid"
    meta = data.get("_meta")
    # Code et nom doivent être des textes non vides : une liste ferait échouer
    # le chargement de toutes les langues.
    if not isinstance(meta, dict) or not _is_text(meta.get("code")) or not _is_text(meta.get("name")):
        return None, "no_meta"
    if not _only_strings(data):
        return None, "invalid"
    return data, None


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _only_strings(node: Any) -> bool:
    """Un fichier de langue ne contient que des textes (et des listes de textes)."""
    if isinstance(node, str):
        return True
    if isinstance(node, list):
        return all(_only_strings(x) for x in node)
    if isinstance(node, dict):
        return all(isinstance(k, str) and _only_strings(v) for k, v in node.items())
    return False


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict) and not _is_plural(v):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _is_plural(node: dict[str, Any]) -> bool:
    return "other" in node and all(k in ("zero", "one", "two", "few", "many", "other") for k in node)


def _flatten(node: dict[str, Any], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for k, v in node.items():
        if k == "_meta":
            continue
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict) and not _is_plural(v):
            keys |= _flatten(v, full)
        else:
            keys.add(full)
    return keys


class Languages:
    def __init__(self) -> None:
        self.builtin: dict[str, dict[str, Any]] = {}
        self.user: dict[str, dict[str, Any]] = {}
        self.rejected: list[dict[str, str]] = []
        self.reload()

    def reload(self) -> None:
        self.builtin = {}
        for p in sorted(config.lang_dir().glob("*.json")):
            data, why = _read_lang_file(p, None)
            if data is not None:
                self.builtin[data["_meta"]["code"]] = data
            else:
                log.error("Fichier de langue fourni invalide %s (%s)", p.name, why)
        self.user = {}
        self.rejected = []
        folder = config.user_lang_dir()
        if folder.is_dir():
            for p in sorted(folder.glob("*.json")):
                if p.name.startswith("_"):
                    continue  # modèle (_modele_en.json) et fichiers mis de côté
                data, why = _read_lang_file(p, MAX_USER_LANG_BYTES)
                if data is not None:
                    self.user[data["_meta"]["code"]] = data
                else:
                    self.rejected.append({"file": p.name, "reason": why or "invalid"})
                    log.warning("Langue personnelle ignorée %s (%s)", p.name, why)

    def available(self) -> list[dict[str, Any]]:
        codes = dict(self.builtin)
        codes.update(self.user)
        out = []
        for code, data in codes.items():
            meta = data["_meta"]
            out.append({
                "code": code,
                "name": meta.get("name", code),
                "personal": code in self.user,
            })
        out.sort(key=lambda x: x["name"].lower())
        return out

    def strings(self, code: str) -> dict[str, Any]:
        """Textes d'une langue, complétés par l'anglais pour les clés absentes."""
        base = self.builtin.get(REFERENCE, {})
        over = self.user.get(code) or self.builtin.get(code) or {}
        if code in self.user and code in self.builtin:
            over = _deep_merge(self.builtin[code], self.user[code])
        return _deep_merge(base, over)

    def missing_keys(self, code: str) -> list[str]:
        """Clés absentes d'une langue (aide aux traducteurs)."""
        ref = _flatten(self.builtin.get(REFERENCE, {}))
        data = self.user.get(code) or self.builtin.get(code) or {}
        return sorted(ref - _flatten(data))

    def has(self, code: str) -> bool:
        return code in self.builtin or code in self.user

    def best_match(self, locale_name: str | None) -> str:
        """Langue à proposer d'après la langue de Windows (repli : anglais)."""
        if not locale_name:
            return REFERENCE
        loc = locale_name.replace("_", "-")
        low = loc.lower()
        lang = low.split("-")[0]
        region = low.split("-")[1] if "-" in low else ""
        candidates: list[str] = []
        if lang == "pt":
            # À défaut de la variante exacte, l'autre portugais.
            candidates += ["pt-BR", "pt-PT"] if region == "br" else ["pt-PT", "pt-BR"]
        elif lang == "zh":
            candidates.append("zh-Hant" if region in ("tw", "hk", "mo", "hant") else "zh-Hans")
        elif lang == "es":
            candidates.append("es" if region in ("es", "") else "es-419")
        elif lang in ("nb", "nn", "no"):
            candidates.append("nb")
        candidates += [loc, lang]
        for c in candidates:
            for code in list(self.user) + list(self.builtin):
                if code.lower() == c.lower():
                    return code
        return REFERENCE

    def windows_language(self) -> str:
        return self.best_match(winapi.ui_language())


def ensure_user_lang_folder() -> Path:
    """Crée le dossier des langues personnelles, avec un modèle et un mode d'emploi."""
    folder = config.user_lang_dir()
    folder.mkdir(parents=True, exist_ok=True)
    # Modèle : copie de en.json, toujours à jour. Les fichiers dont le nom
    # commence par « _ » ne sont pas chargés comme langues.
    template = folder / TEMPLATE_NAME
    src = config.lang_dir() / "en.json"
    try:
        if not template.exists() or template.read_bytes() != src.read_bytes():
            shutil.copyfile(src, template)
    except OSError as exc:
        log.warning("Modèle de langue non copié : %s", exc)
    readme_src = config.assets_dir() / "lang_template" / "LISEZMOI.txt"
    readme = folder / "LISEZMOI.txt"
    if readme_src.is_file():
        try:
            if not readme.exists() or readme.read_bytes() != readme_src.read_bytes():
                shutil.copyfile(readme_src, readme)
        except OSError:
            pass
    return folder
