"""Zone de notification de Windows (0.2.1, demande 14.1).

- Une icône FS Passion près de l'horloge. Clic : la fenêtre revient. Clic
  droit : menu « Afficher FS Passion » / « Quitter FS Passion ».
- Avec le réglage « Fermer dans la zone de notification » (actif par défaut),
  la croix de la fenêtre cache FS Passion au lieu de le quitter ; seul
  « Quitter » (pied de page ou menu de l'icône) ferme vraiment l'application.
- Le menu suit le thème sombre de Windows 11 (coins arrondis, ombres) : c'est
  le menu natif de Windows, avec le mode sombre demandé au système.

Bibliothèque : pystray (LGPL-3.0, compatible GPLv3). Si elle est absente ou si
l'icône ne peut pas être créée, FS Passion fonctionne comme avant : la croix
quitte l'application.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable
from typing import Any

from fspassion import config

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"


def _dark_menus() -> None:
    """Menus Win32 sombres (fonctions non documentées de uxtheme.dll, utilisées
    par l'Explorateur : SetPreferredAppMode n° 135, FlushMenuThemes n° 136)."""
    if not IS_WINDOWS:
        return
    try:
        import ctypes

        ux = ctypes.WinDLL("uxtheme")
        set_mode = ux[135]  # type: ignore[index]
        set_mode.argtypes = [ctypes.c_int]
        set_mode(2)  # ForceDark
        flush = ux[136]  # type: ignore[index]
        flush()
    except Exception as exc:  # noqa: BLE001 - simple confort visuel
        log.debug("Menus sombres indisponibles : %s", exc)


class Tray:
    """Icône de la zone de notification."""

    def __init__(
        self,
        texts: Callable[[], dict[str, str]],
        on_show: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._texts = texts
        self._on_show = on_show
        self._on_quit = on_quit
        self._icon: Any = None
        self.active = False

    def _text(self, key: str) -> str:
        try:
            return self._texts().get(key) or key
        except Exception:  # noqa: BLE001
            return key

    def start(self) -> bool:
        """Crée l'icône dans un fil dédié. Renvoie False si c'est impossible."""
        if not IS_WINDOWS:
            return False
        try:
            import pystray  # type: ignore[import-not-found]
            from PIL import Image
        except ImportError as exc:
            log.warning("Zone de notification indisponible (%s)", exc)
            return False
        try:
            _dark_menus()
            image = Image.open(config.assets_dir() / "brand" / "tray.png")
            image.load()
            menu = pystray.Menu(
                pystray.MenuItem(lambda _item: self._text("show"), self._show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(lambda _item: self._text("quit"), self._quit),
            )
            self._icon = pystray.Icon("FSPassion", image, "FS Passion", menu)
        except Exception as exc:  # noqa: BLE001
            log.warning("Icône de la zone de notification impossible : %s", exc)
            return False
        ready = threading.Event()

        def run() -> None:
            def setup(icon: Any) -> None:
                icon.visible = True
                self.active = True
                ready.set()

            try:
                self._icon.run(setup=setup)
            except Exception as exc:  # noqa: BLE001
                log.warning("Zone de notification arrêtée : %s", exc)
            finally:
                self.active = False
                ready.set()

        threading.Thread(target=run, name="tray", daemon=True).start()
        ready.wait(5)
        return self.active

    def refresh(self) -> None:
        """Textes du menu dans la nouvelle langue."""
        if self._icon is not None and self.active:
            try:
                self._icon.title = self._text("tooltip") or "FS Passion"
                self._icon.update_menu()
            except Exception as exc:  # noqa: BLE001
                log.debug("Menu de l'icône non mis à jour : %s", exc)

    def notify(self, message: str, title: str = "FS Passion") -> None:
        """Bulle de Windows (une seule fois : « FS Passion reste ouvert ici »)."""
        if self._icon is not None and self.active:
            try:
                self._icon.notify(message, title)
            except Exception as exc:  # noqa: BLE001
                log.debug("Bulle impossible : %s", exc)

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:  # noqa: BLE001
                pass
        self.active = False

    def _show(self, _icon: Any = None, _item: Any = None) -> None:
        try:
            self._on_show()
        except Exception:  # noqa: BLE001
            log.exception("Affichage de la fenêtre impossible")

    def _quit(self, _icon: Any = None, _item: Any = None) -> None:
        try:
            self._on_quit()
        except Exception:  # noqa: BLE001
            log.exception("Fermeture impossible")
