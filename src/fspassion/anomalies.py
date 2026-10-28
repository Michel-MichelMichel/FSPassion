"""Anomalies (4.10) : non bloquantes, au ton informatif.

| A1 | .rar ou .7z dans un dossier de stockage            |
| A2 | .zip sans modDesc.xml à sa racine                  |
| A3 | .zip illisible ou modDesc.xml invalide             |
| A4 | dossier sans modDesc.xml à sa racine               |
| A5 | nom avec espaces, accents ou caractères spéciaux   |
| A6 | mod d'une autre version du jeu                     |
| A7 | mod référencé par une partie mais absent           |
| A8 | mod supprimé mais encore lié dans des parties      |
| A9 | même identifiant dans deux stockages               |
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

ALL_TYPES = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9")

# Règle confirmée : le jeu n'accepte que les lettres non accentuées, les
# chiffres et « _ ».
# fullmatch et \Z : un saut de ligne final ne compte pas pour « $ ».
_VALID_NAME_RE = re.compile(r"[A-Za-z0-9_]+")
# Suffixe ajouté par un navigateur à un doublon : « FS25_X (1) »
_BROWSER_SUFFIX_RE = re.compile(r"\s*\(\d+\)\Z")


def is_valid_mod_name(stem: str) -> bool:
    return bool(_VALID_NAME_RE.fullmatch(stem))


def suggest_name(stem: str) -> str:
    """Nom corrigé proposé pour l'anomalie A5."""
    s = _BROWSER_SUFFIX_RE.sub("", stem)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("ß", "ss").replace("Æ", "AE").replace("æ", "ae").replace("Ø", "O").replace("ø", "o")
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "mod"


def make(atype: str, name: str, storage: int, **detail: Any) -> dict[str, Any]:
    """Construit un enregistrement d'anomalie."""
    return {"type": atype, "name": name, "storage": storage, "detail": detail}


def key_of(anomaly: dict[str, Any]) -> str:
    """Clé stable d'une anomalie (pour « déjà vue »)."""
    return f"{anomaly['type']}|{anomaly['storage']}|{anomaly['name'].lower()}"


def visible(
    anomalies: list[dict[str, Any]],
    hidden_types: list[str],
    hidden_folders: list[str],
) -> list[dict[str, Any]]:
    """Anomalies à afficher, sans les types masqués ni les dossiers masqués (A4)."""
    hidden_t = set(hidden_types)
    hidden_f = {f.lower() for f in hidden_folders}
    out = []
    for a in anomalies:
        if a["type"] in hidden_t:
            continue
        if a["type"] == "A4" and a["name"].lower() in hidden_f:
            continue
        out.append(a)
    return out
