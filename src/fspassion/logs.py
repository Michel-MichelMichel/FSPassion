"""Journaux et diagnostic (4.19).

- %LOCALAPPDATA%\\FSPassion\\logs\\fspassion.log, rotation de 5 fichiers de 1 Mo.
- Niveaux : information (opérations), avertissement, erreur (avec le détail).
- Aucune donnée personnelle : le dossier de l'utilisateur est remplacé par
  %USERPROFILE% dans les chemins.
"""

from __future__ import annotations

import collections
import logging
import logging.handlers
import os
import platform
import re
import sys
import time
from typing import Any

from fspassion import __version__, config, winapi

MAX_BYTES = 1024 * 1024
BACKUPS = 4  # fichier courant + 4 = 5 fichiers

_recent_errors: collections.deque[str] = collections.deque(maxlen=20)


# Tout dossier d'un profil Windows (C:\Users\<nom>), même celui d'un autre compte
# (relance en administrateur, lecteur réseau) : le nom d'utilisateur n'est jamais écrit.
_PROFILE_RE = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'<>|:*?]+", re.IGNORECASE)


def anonymize(text: str) -> str:
    """Remplace les dossiers d'utilisateur par %USERPROFILE%."""
    profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    if profile and len(profile) > 3:
        text = re.sub(re.escape(profile), "%USERPROFILE%", text, flags=re.IGNORECASE)
        alt = profile.replace("\\", "/")
        if alt != profile:
            text = re.sub(re.escape(alt), "%USERPROFILE%", text, flags=re.IGNORECASE)
    return _PROFILE_RE.sub("%USERPROFILE%", text)


class AnonymizingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return anonymize(super().format(record))


class RecentErrorsHandler(logging.Handler):
    """Garde les dernières erreurs pour « Copier le diagnostic »."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            _recent_errors.append(self.format(record))
        except Exception:  # noqa: BLE001
            pass


def setup(dev: bool = False) -> None:
    # Console Windows : les accents et tirets ne doivent jamais faire planter.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
    folder = config.logs_dir()
    folder.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if dev else logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    fmt = AnonymizingFormatter("%(asctime)s %(levelname)-7s %(name)s : %(message)s", "%Y-%m-%d %H:%M:%S")

    fh = logging.handlers.RotatingFileHandler(
        folder / "fspassion.log", maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    fh.setLevel(logging.INFO)
    root.addHandler(fh)

    rh = RecentErrorsHandler(level=logging.ERROR)
    rh.setFormatter(fmt)
    root.addHandler(rh)

    if (dev or not config.is_frozen()) and sys.stdout is not None:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        ch.setLevel(logging.DEBUG if dev else logging.INFO)
        root.addHandler(ch)

    # Bibliothèques bavardes
    for noisy in ("PIL", "pywebview", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def recent_errors() -> list[str]:
    return list(_recent_errors)


def diagnostic(version_states: list[dict[str, Any]], extra: dict[str, str] | None = None,
               perf: list[str] | None = None) -> str:
    """Texte prêt à coller dans un signalement GitHub (anonymisé).

    Rapport technique, en anglais neutre : il est identique quelle que soit la
    langue de l'interface.
    """
    lines = [
        f"FS Passion {__version__}",
        f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"System: {winapi.windows_version()} ({platform.machine()})",
        f"Python: {platform.python_version()}",
        f"Mode: {'portable' if config.is_portable() else 'installed'}{' (dev)' if not config.is_frozen() else ''}",
        f"Admin: {'yes' if winapi.is_admin() else 'no'}",
    ]
    for key, value in (extra or {}).items():
        lines.append(f"{key}: {value}")
    lines += ["", "Game versions:"]
    for st in version_states:
        flags = []
        if st.get("installed"):
            flags.append("installed")
        if st.get("running"):
            flags.append("running")
        if not flags and not any(st["cfg"].get(f) for f in ("game_exe", "user_dir", "mods_dir")):
            lines.append(f"- {st['id']}: not configured")
            continue
        lines.append(f"- {st['id']}" + (f" ({', '.join(flags)})" if flags else ""))
        for field in ("game_exe", "user_dir", "mods_dir"):
            check = st["checks"].get(field, {})
            lines.append(f"    {field}: {st['cfg'].get(field) or '-'} [{check.get('key', '')}]")
        checks = (st.get("storage") or {}).get("extra") or []
        for i, path in enumerate(st["cfg"].get("extra_mods_dirs") or []):
            check = checks[i] if i < len(checks) else {}
            lines.append(f"    mods_dir_{i + 2}: {path} [{check.get('key', '')}]")
        if st.get("override"):
            ov = st["override"]
            lines.append(f"    override: active={ov.get('active')} directory={ov.get('directory')}"
                         + (f" ({st['applied_kind']})" if st.get("applied_kind") else ""))
        if st.get("library"):
            lib = st["library"]
            lines.append(f"    library: {lib.get('status')} - {lib.get('count', 0)} mods")
        if st.get("parties_count") is not None:
            lines.append(f"    setups: {st['parties_count']}")
        launch = st.get("launch") or {}
        if launch.get("platform"):
            lines.append(f"    platform: {launch.get('platform')}")
    if perf:
        lines += ["", "Performance:"] + [f"    {p}" for p in perf]
    errs = recent_errors()
    lines += ["", f"Recent errors ({len(errs)}):"]
    lines += errs or ["(none)"]
    return anonymize("\n".join(lines))
