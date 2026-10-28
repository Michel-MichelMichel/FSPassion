"""Fenêtre sans barre de titre ni bordure visible.

Exigences : redimensionnable par ses quatre bords et ses quatre coins,
déplaçable par l'en-tête, double-clic = agrandir/restaurer, raccourcis de
placement de Windows conservés si possible, taille et position mémorisées.

La page web couvre toute la fenêtre : Windows ne « voit » donc jamais les
bords. L'interface place des zones de saisie invisibles de quelques pixels sur
les bords ; quand la souris y est enfoncée, elle prévient le cœur, qui confie
le redimensionnement (ou le déplacement) à Windows lui-même. C'est la technique
des applications à cadre personnalisé (Electron, Tauri).

Trois techniques, choisies par le réglage « window_mode » :
- « native » (par défaut) : style WS_THICKFRAME ajouté et cadre masqué
  (WM_NCCALCSIZE). Redimensionnement et déplacement natifs, ancrage Windows,
  agrandissement natif qui respecte la barre des tâches.
- « script » : redimensionnement calculé par l'interface (repli si la
  technique native échoue).
- « thin » : cadre natif très fin (solution de repli).
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

MODES = ("native", "script", "thin")

# Codes de zones (WM_NCHITTEST)
HT = {
    "move": 2, "left": 10, "right": 11, "top": 12, "top-left": 13, "top-right": 14,
    "bottom": 15, "bottom-left": 16, "bottom-right": 17,
}

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    dwmapi = ctypes.WinDLL("dwmapi")

    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    user32.CallWindowProcW.restype = LRESULT
    user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SetWindowLongPtrW.restype = ctypes.c_void_p
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    user32.GetWindowLongPtrW.restype = ctypes.c_void_p
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = LRESULT
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.MonitorFromWindow.restype = wintypes.HMONITOR
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromRect.restype = wintypes.HMONITOR
    user32.MonitorFromRect.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD]
    user32.IsZoomed.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.GetDpiForWindow.argtypes = [wintypes.HWND]
    user32.GetDpiForWindow.restype = wintypes.UINT

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    class NCCALCSIZE_PARAMS(ctypes.Structure):
        _fields_ = [("rgrc", wintypes.RECT * 3), ("lppos", ctypes.c_void_p)]

    class WINDOWPLACEMENT(ctypes.Structure):
        _fields_ = [("length", wintypes.UINT), ("flags", wintypes.UINT), ("showCmd", wintypes.UINT),
                    ("ptMinPosition", wintypes.POINT), ("ptMaxPosition", wintypes.POINT),
                    ("rcNormalPosition", wintypes.RECT)]

    user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
    user32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWPLACEMENT)]

GWL_STYLE = -16
GWLP_WNDPROC = -4
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WM_NCCALCSIZE = 0x0083
WM_NCLBUTTONDOWN = 0x00A1
WM_SYSCOMMAND = 0x0112
SC_CLOSE = 0xF060
SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_FRAMECHANGED, SWP_NOACTIVATE = 0x1, 0x2, 0x4, 0x20, 0x10
SW_MAXIMIZE, SW_RESTORE, SW_MINIMIZE = 3, 9, 6
SW_HIDE, SW_SHOW = 0, 5
MONITOR_DEFAULTTONULL, MONITOR_DEFAULTTONEAREST = 0, 2
SM_CXFRAME, SM_CYFRAME, SM_CXPADDEDBORDER = 32, 33, 92


def rect_visible(x: int, y: int, w: int, h: int) -> bool:
    """Vrai si le rectangle touche un écran (avant de restaurer une position)."""
    if not IS_WINDOWS:
        return True
    r = wintypes.RECT(x, y, x + max(w, 100), y + max(h, 100))
    return bool(user32.MonitorFromRect(ctypes.byref(r), MONITOR_DEFAULTTONULL))


class NativeWindow:
    """Opérations sur la fenêtre de l'application (sans effet hors Windows)."""

    def __init__(self) -> None:
        self.window: Any = None       # fenêtre pywebview
        self.hwnd: int = 0
        self.mode = "native"
        self._old_proc: Any = None
        self._proc_ref: Any = None
        self._pseudo_max = False
        self._restore_rect: tuple[int, int, int, int] | None = None
        self._lock = threading.Lock()
        # Dormance : interface suspendue quand la fenêtre est cachée.
        self.asleep = False
        self._sleep_timer: threading.Timer | None = None
        self._form_hooked = False

    # ------------------------------------------------------------------
    # Mise en place
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return IS_WINDOWS and self.window is not None and bool(self.hwnd)

    def attach(self, window: Any, mode: str) -> None:
        """Appelé quand la fenêtre est affichée."""
        self.window = window
        self.mode = mode if mode in MODES else "native"
        if not IS_WINDOWS:
            return
        try:
            self.hwnd = int(window.native.Handle.ToInt64())
        except Exception as exc:  # noqa: BLE001
            log.error("Fenêtre : poignée introuvable (%s)", exc)
            return
        try:
            self._on_ui(self._setup)
        except Exception as exc:  # noqa: BLE001
            log.error("Fenêtre : préparation impossible (%s) ; technique « script »", exc)
            self.mode = "script"
        try:
            self._on_ui(self._hook_form)
        except Exception as exc:  # noqa: BLE001
            log.warning("Fenêtre : réveil automatique indisponible (%s)", exc)

    def _on_ui(self, fn: Callable[[], None], wait: bool = True) -> None:
        """Exécute `fn` dans le fil de l'interface Windows (obligatoire pour
        certaines opérations, comme la capture de la souris)."""
        form = self.window.native
        try:
            from System import Func, Type  # type: ignore[import-not-found]
        except Exception:  # noqa: BLE001
            fn()
            return

        def wrapped() -> None:
            try:
                fn()
            except Exception:  # noqa: BLE001
                log.exception("Fenêtre : opération en échec")

        if wait:
            form.Invoke(Func[Type](wrapped))
        else:
            form.BeginInvoke(Func[Type](wrapped))

    def _setup(self) -> None:
        hwnd = self.hwnd
        style = int(user32.GetWindowLongPtrW(hwnd, GWL_STYLE) or 0)
        if self.mode == "thin":
            # Cadre natif très fin : bordure redimensionnable, sans barre de titre.
            style |= WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
            user32.SetWindowLongPtrW(hwnd, GWL_STYLE, style)
        elif self.mode == "native":
            style |= WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
            user32.SetWindowLongPtrW(hwnd, GWL_STYLE, style)
            self._proc_ref = WNDPROC(self._wndproc)
            self._old_proc = user32.SetWindowLongPtrW(
                hwnd, GWLP_WNDPROC, ctypes.cast(self._proc_ref, ctypes.c_void_p)
            )
            if not self._old_proc:
                raise OSError(ctypes.get_last_error(), "SetWindowLongPtrW")
        else:  # script
            style |= WS_MINIMIZEBOX | WS_SYSMENU
            user32.SetWindowLongPtrW(hwnd, GWL_STYLE, style)
        # Coins arrondis de Windows 11 (sans effet sous Windows 10).
        try:
            pref = ctypes.c_int(2)
            dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), 4)
        except Exception:  # noqa: BLE001
            pass
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED | SWP_NOACTIVATE)
        log.info("Fenêtre prête (technique « %s »)", self.mode)

    def _wndproc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == WM_NCCALCSIZE and wparam:
            # Toute la fenêtre devient zone cliente : le cadre est masqué, mais
            # Windows garde le redimensionnement et l'ancrage.
            if user32.IsZoomed(hwnd):
                try:
                    dpi = user32.GetDpiForWindow(hwnd) or 96
                    fx = user32.GetSystemMetricsForDpi(SM_CXFRAME, dpi) + user32.GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi)
                    fy = user32.GetSystemMetricsForDpi(SM_CYFRAME, dpi) + user32.GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi)
                    params = ctypes.cast(lparam, ctypes.POINTER(NCCALCSIZE_PARAMS)).contents
                    r = params.rgrc[0]
                    r.left += fx
                    r.right -= fx
                    r.top += fy
                    r.bottom -= fy
                    params.rgrc[0] = r
                except Exception:  # noqa: BLE001
                    pass
            return 0
        return int(user32.CallWindowProcW(self._old_proc, hwnd, msg, wparam, lparam))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def minimize(self) -> None:
        if self.available:
            user32.ShowWindow(self.hwnd, SW_MINIMIZE)
        elif self.window is not None:
            self.window.minimize()

    def is_maximized(self) -> bool:
        if not self.available:
            return False
        if self.mode == "script":
            return self._pseudo_max
        return bool(user32.IsZoomed(self.hwnd))

    def toggle_maximize(self) -> bool:
        if not self.available:
            return False
        if self.mode == "script":
            self._toggle_pseudo_max()
            return self._pseudo_max
        if user32.IsZoomed(self.hwnd):
            user32.ShowWindow(self.hwnd, SW_RESTORE)
            return False
        user32.ShowWindow(self.hwnd, SW_MAXIMIZE)
        return True

    def maximize(self) -> None:
        if self.available and not self.is_maximized():
            self.toggle_maximize()

    def _work_area(self) -> tuple[int, int, int, int]:
        mon = user32.MonitorFromWindow(self.hwnd, MONITOR_DEFAULTTONEAREST)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(mon, ctypes.byref(mi))
        w = mi.rcWork
        return w.left, w.top, w.right - w.left, w.bottom - w.top

    def _toggle_pseudo_max(self) -> None:
        if self._pseudo_max and self._restore_rect:
            x, y, w, h = self._restore_rect
            user32.SetWindowPos(self.hwnd, None, x, y, w, h, SWP_NOZORDER)
            self._pseudo_max = False
            return
        r = wintypes.RECT()
        user32.GetWindowRect(self.hwnd, ctypes.byref(r))
        self._restore_rect = (r.left, r.top, r.right - r.left, r.bottom - r.top)
        x, y, w, h = self._work_area()
        user32.SetWindowPos(self.hwnd, None, x, y, w, h, SWP_NOZORDER)
        self._pseudo_max = True

    def close(self) -> None:
        if self.available:
            user32.PostMessageW(self.hwnd, WM_SYSCOMMAND, SC_CLOSE, 0)
        elif self.window is not None:
            self.window.destroy()

    def focus(self) -> None:
        """Ramène la fenêtre au premier plan (seconde instance, icône de la
        zone de notification et fin du jeu), même si elle était cachée."""
        if not self.available:
            return

        def do() -> None:
            self._wake_now()
            if not user32.IsWindowVisible(self.hwnd):
                user32.ShowWindow(self.hwnd, SW_SHOW)
            if user32.IsIconic(self.hwnd):
                user32.ShowWindow(self.hwnd, SW_RESTORE)
            user32.SetForegroundWindow(self.hwnd)

        self._on_ui(do, wait=False)

    def hide(self) -> bool:
        """Cache la fenêtre (zone de notification). Asynchrone : peut
        être appelé pendant l'événement de fermeture sans bloquer l'interface."""
        if not self.available:
            return False
        user32.ShowWindowAsync(self.hwnd, SW_HIDE)
        return True

    def is_hidden(self) -> bool:
        return self.available and not user32.IsWindowVisible(self.hwnd)

    # ------------------------------------------------------------------
    # Dormance
    # ------------------------------------------------------------------
    #
    # Fenêtre cachée (zone de notification) ou réduite au lancement du jeu :
    # l'interface WebView2 est rendue invisible, sa mémoire visée passe à
    # « Low » et elle est suspendue (TrySuspend : scripts, minuteries et
    # dessin arrêtés, comme un onglet en veille d'Edge). Le cœur Python
    # continue : surveillance du jeu, téléchargements, zone de notification.
    # Elle se réveille dès que la fenêtre revient (clic sur l'icône, barre des
    # tâches, fin du jeu) et demande à l'interface de se remettre à jour.

    def _webview(self) -> Any:
        try:
            return self.window.native.browser.webview
        except Exception:  # noqa: BLE001
            return None

    def _hook_form(self) -> None:
        """Réveil quand Windows réaffiche la fenêtre sans passer par focus()
        (bouton de la barre des tâches, Alt+Tab…)."""
        if self._form_hooked:
            return
        form = self.window.native

        def on_show(_sender: Any, _args: Any) -> None:
            if self.asleep and not user32.IsIconic(self.hwnd) and user32.IsWindowVisible(self.hwnd):
                self._wake_now()

        form.Activated += on_show
        form.Resize += on_show
        form.VisibleChanged += on_show
        self._form_on_show = on_show  # référence gardée
        self._form_hooked = True

    def sleep_later(self, delay: float = 2.0) -> None:
        """Met l'interface en dormance après `delay` secondes, si la fenêtre est
        toujours cachée ou réduite à ce moment-là."""
        if not self.available:
            return
        if self._sleep_timer is not None:
            self._sleep_timer.cancel()
        t = threading.Timer(delay, lambda: self._on_ui(self._sleep_now, wait=False))
        t.daemon = True
        self._sleep_timer = t
        t.start()

    def _sleep_now(self) -> None:
        if self.asleep:
            return
        if user32.IsWindowVisible(self.hwnd) and not user32.IsIconic(self.hwnd):
            return  # la fenêtre est revenue entre-temps
        wv = self._webview()
        core = getattr(wv, "CoreWebView2", None) if wv is not None else None
        if core is None:
            return
        try:
            from Microsoft.Web.WebView2.Core import CoreWebView2MemoryUsageTargetLevel  # type: ignore[import-not-found]

            core.MemoryUsageTargetLevel = CoreWebView2MemoryUsageTargetLevel.Low
        except Exception as exc:  # noqa: BLE001
            log.debug("Dormance : niveau de mémoire non réglé (%s)", exc)
        self.asleep = True
        try:
            wv.Visible = False  # TrySuspend exige une interface invisible
            core.TrySuspendAsync()
        except Exception as exc:  # noqa: BLE001
            log.info("Dormance : suspension refusée (%s)", exc)
        log.info("Dormance : interface mise en veille")
        trim_memory_later()

    def _wake_now(self) -> None:
        if self._sleep_timer is not None:
            self._sleep_timer.cancel()
            self._sleep_timer = None
        if not self.asleep:
            return
        self.asleep = False
        wv = self._webview()
        core = getattr(wv, "CoreWebView2", None) if wv is not None else None
        if wv is None or core is None:
            return
        try:
            wv.Visible = True
            from Microsoft.Web.WebView2.Core import CoreWebView2MemoryUsageTargetLevel  # type: ignore[import-not-found]

            core.MemoryUsageTargetLevel = CoreWebView2MemoryUsageTargetLevel.Normal
            if core.IsSuspended:
                core.Resume()
            # Les événements reçus pendant la veille ont pu se perdre : l'interface
            # se reconnecte et relit l'état (ui/js/main.js).
            core.ExecuteScriptAsync("document.dispatchEvent(new Event('fsp-wake'))")
        except Exception as exc:  # noqa: BLE001
            log.warning("Dormance : réveil incomplet (%s)", exc)
        log.info("Dormance : interface réveillée")

    def begin_drag(self, edge: str) -> bool:
        """Confie à Windows le déplacement (« move ») ou le redimensionnement."""
        if not self.available or (self.mode == "script" and edge != "move"):
            return False
        ht = HT.get(edge)
        if ht is None:
            return False
        if edge != "move" and self.is_maximized():
            return False

        def do() -> None:
            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            lparam = (pt.y & 0xFFFF) << 16 | (pt.x & 0xFFFF)
            user32.ReleaseCapture()
            user32.SendMessageW(self.hwnd, WM_NCLBUTTONDOWN, ht, lparam)

        self._on_ui(do, wait=False)
        return True

    def set_rect(self, x: int, y: int, w: int, h: int) -> None:
        """Technique « script » : position et taille en pixels physiques."""
        if self.available:
            user32.SetWindowPos(self.hwnd, None, int(x), int(y), int(w), int(h), SWP_NOZORDER | SWP_NOACTIVATE)

    def rect(self) -> dict[str, int] | None:
        if not self.available:
            return None
        r = wintypes.RECT()
        user32.GetWindowRect(self.hwnd, ctypes.byref(r))
        return {"x": r.left, "y": r.top, "width": r.right - r.left, "height": r.bottom - r.top,
                "dpi": int(user32.GetDpiForWindow(self.hwnd) or 96)}

    def saved_state(self) -> dict[str, Any] | None:
        """Taille, position (pixels logiques) et état agrandi, pour les réglages."""
        if not self.available:
            return None
        maximized = self.is_maximized()
        dpi = int(user32.GetDpiForWindow(self.hwnd) or 96)
        if self.mode == "script" and self._pseudo_max and self._restore_rect:
            x, y, w, h = self._restore_rect
        elif maximized:
            # Position « normale » mémorisée par Windows pour une fenêtre agrandie.
            wp = WINDOWPLACEMENT()
            wp.length = ctypes.sizeof(WINDOWPLACEMENT)
            user32.GetWindowPlacement(self.hwnd, ctypes.byref(wp))
            n = wp.rcNormalPosition
            x, y, w, h = n.left, n.top, n.right - n.left, n.bottom - n.top
        else:
            r = self.rect() or {}
            x, y, w, h = r["x"], r["y"], r["width"], r["height"]
        scale = dpi / 96
        return {"x": round(x / scale), "y": round(y / scale), "width": round(w / scale),
                "height": round(h / scale), "maximized": maximized}


def trim_memory_later(delay: float = 1.5) -> None:
    """Rend à Windows la mémoire inutilisée du cœur Python (dormance).
    Sans effet sur ce qui tourne : les pages reviennent à la demande."""
    if not IS_WINDOWS:
        return

    def run() -> None:
        import gc

        gc.collect()
        try:
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            k32.SetProcessWorkingSetSize.argtypes = [wintypes.HANDLE, ctypes.c_size_t, ctypes.c_size_t]
            k32.SetProcessWorkingSetSize(k32.GetCurrentProcess(), ctypes.c_size_t(-1), ctypes.c_size_t(-1))
        except Exception:  # noqa: BLE001
            log.debug("Dormance : mémoire non rendue", exc_info=True)

    t = threading.Timer(delay, run)
    t.daemon = True
    t.start()


native = NativeWindow()
