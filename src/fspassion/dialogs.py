"""Dialogues Windows natifs (« Chercher… », « Enregistrer sous »).

Ils sont ouverts par le cœur, au premier plan, que l'interface soit dans la
fenêtre de l'application ou dans le navigateur :
- depuis la fenêtre : dialogue de pywebview, rattaché à la fenêtre ;
- depuis le navigateur (développement) : dialogue Tk « toujours au premier
  plan », sinon il s'ouvrirait derrière le navigateur.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_lock = threading.Lock()


def _initial(initial: str | None) -> str:
    if not initial:
        return ""
    p = Path(initial)
    if p.is_file():
        return str(p.parent)
    while not p.exists() and p.parent != p:
        p = p.parent
    return str(p) if p.exists() else ""


def _with_pywebview(window: Any, kind: str, initial: str, filters: list[tuple[str, str]]) -> str | None:
    import webview  # type: ignore[import-not-found]

    if kind == "folder":
        res = window.create_file_dialog(webview.FileDialog.FOLDER, directory=initial)
    else:
        types = tuple(f"{label} ({pattern})" for label, pattern in filters) or ()
        res = window.create_file_dialog(webview.FileDialog.OPEN, directory=initial, file_types=types)
    if not res:
        return None
    return str(res[0] if isinstance(res, (list, tuple)) else res)


def _with_tk(kind: str, initial: str, filters: list[tuple[str, str]], title: str) -> str | None:
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    try:
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        if kind == "folder":
            res = filedialog.askdirectory(parent=root, initialdir=initial or None, title=title, mustexist=True)
        else:
            ft = [(label, pattern.replace(";", " ")) for label, pattern in filters] or [("*", "*.*")]
            res = filedialog.askopenfilename(parent=root, initialdir=initial or None, title=title, filetypes=ft)
    finally:
        root.destroy()
    return os.path.normpath(res) if res else None


def browse(
    kind: str,
    initial: str | None,
    filters: list[tuple[str, str]] | None = None,
    title: str = "",
    window: Any = None,
    from_window: bool = True,
) -> str | None:
    """Ouvre un dialogue « dossier » ou « fichier ». Renvoie le chemin ou None."""
    filters = filters or []
    start = _initial(initial)
    with _lock:
        if window is not None and from_window:
            try:
                return _with_pywebview(window, kind, start, filters)
            except Exception as exc:  # noqa: BLE001
                log.warning("Dialogue pywebview impossible : %s", exc)
        try:
            return _with_tk(kind, start, filters, title)
        except Exception as exc:  # noqa: BLE001
            log.warning("Dialogue Tk impossible : %s", exc)
        if window is not None:
            try:
                return _with_pywebview(window, kind, start, filters)
            except Exception as exc:  # noqa: BLE001
                log.error("Aucun dialogue disponible : %s", exc)
    return None


# --------------------------------------------------------------------------
# « Enregistrer sous » (export de la configuration)
# --------------------------------------------------------------------------

def _save_with_pywebview(window: Any, initial: str, name: str, filters: list[tuple[str, str]]) -> str | None:
    import webview  # type: ignore[import-not-found]

    types = tuple(f"{label} ({pattern})" for label, pattern in filters) or ()
    res = window.create_file_dialog(webview.FileDialog.SAVE, directory=initial, save_filename=name, file_types=types)
    if not res:
        return None
    return str(res[0] if isinstance(res, (list, tuple)) else res)


def _save_with_tk(initial: str, name: str, filters: list[tuple[str, str]], title: str) -> str | None:
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    try:
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        ft = [(label, pattern.replace(";", " ")) for label, pattern in filters] or [("*", "*.*")]
        ext = os.path.splitext(name)[1]
        res = filedialog.asksaveasfilename(parent=root, initialdir=initial or None, initialfile=name,
                                           title=title, filetypes=ft, defaultextension=ext)
    finally:
        root.destroy()
    return os.path.normpath(res) if res else None


def save_as(
    name: str,
    filters: list[tuple[str, str]] | None = None,
    title: str = "",
    window: Any = None,
    from_window: bool = True,
    initial: str | None = None,
) -> str | None:
    """Dialogue « Enregistrer sous » natif. Renvoie le chemin choisi, ou None."""
    filters = filters or []
    start = _initial(initial)
    with _lock:
        if window is not None and from_window:
            try:
                return _save_with_pywebview(window, start, name, filters)
            except Exception as exc:  # noqa: BLE001
                log.warning("Dialogue « Enregistrer sous » pywebview impossible : %s", exc)
        try:
            return _save_with_tk(start, name, filters, title)
        except Exception as exc:  # noqa: BLE001
            log.warning("Dialogue « Enregistrer sous » Tk impossible : %s", exc)
        if window is not None:
            try:
                return _save_with_pywebview(window, start, name, filters)
            except Exception as exc:  # noqa: BLE001
                log.error("Aucun dialogue « Enregistrer sous » disponible : %s", exc)
    return None

