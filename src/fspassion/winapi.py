"""Appels à l'API Windows (ctypes). Sans effet hors de Windows.

Rien n'est supposé : le dossier Mes documents, par exemple, est demandé à
Windows (il peut être sur G:\\ ou redirigé vers OneDrive).
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
import uuid
from pathlib import Path

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

FOLDERID_DOCUMENTS = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"
FOLDERID_DOWNLOADS = "{374DE290-123F-4565-9164-39C4925E467B}"

DRIVE_FIXED = 3


def known_folder(folder_id: str) -> Path | None:
    """Chemin d'un dossier connu de Windows (SHGetKnownFolderPath)."""
    if not IS_WINDOWS:
        return None
    import ctypes

    # Un GUID en mémoire = ses 16 octets au format « little-endian » de Windows.
    guid = ctypes.create_string_buffer(uuid.UUID(folder_id).bytes_le, 16)
    out = ctypes.c_wchar_p()
    try:
        shell32 = ctypes.windll.shell32  # type: ignore[attr-defined]
        ole32 = ctypes.windll.ole32  # type: ignore[attr-defined]
        hr = shell32.SHGetKnownFolderPath(guid, 0, None, ctypes.byref(out))
        if hr != 0 or not out.value:
            return None
        path = Path(out.value)
        ole32.CoTaskMemFree(out)
        return path
    except Exception as exc:  # noqa: BLE001
        log.warning("Dossier connu introuvable %s : %s", folder_id, exc)
        return None


def documents_dir() -> Path | None:
    p = known_folder(FOLDERID_DOCUMENTS)
    if p is None and not IS_WINDOWS:
        return Path.home() / "Documents"
    return p


def downloads_dir() -> Path | None:
    p = known_folder(FOLDERID_DOWNLOADS)
    if p is None:
        cand = Path.home() / "Downloads"
        return cand if cand.exists() or not IS_WINDOWS else None
    return p


def fixed_drives() -> list[Path]:
    """Racines des disques fixes (C:\\, D:\\…)."""
    if not IS_WINDOWS:
        return []
    import ctypes

    out: list[Path] = []
    try:
        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        mask = k32.GetLogicalDrives()
        for i in range(26):
            if mask & (1 << i):
                root = f"{chr(65 + i)}:\\"
                if k32.GetDriveTypeW(root) == DRIVE_FIXED:
                    out.append(Path(root))
    except Exception as exc:  # noqa: BLE001
        log.warning("Liste des disques impossible : %s", exc)
    return out


def volume_filesystem(path: str | os.PathLike[str]) -> str | None:
    """Système de fichiers du volume d'un chemin (NTFS, exFAT, FAT32…)."""
    if not IS_WINDOWS:
        return None
    import ctypes

    try:
        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        root_buf = ctypes.create_unicode_buffer(260)
        if not k32.GetVolumePathNameW(str(path), root_buf, 260):
            return None
        fs_buf = ctypes.create_unicode_buffer(64)
        ok = k32.GetVolumeInformationW(
            root_buf.value, None, 0, None, None, None, fs_buf, 64
        )
        return fs_buf.value if ok else None
    except Exception as exc:  # noqa: BLE001
        log.debug("Système de fichiers inconnu pour %s : %s", path, exc)
        return None


def onedrive_roots() -> list[str]:
    roots = []
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        v = os.environ.get(var)
        if v:
            roots.append(v)
    return roots


def is_in_onedrive(path: str) -> bool:
    from fspassion.fsutil import norm_path

    p = norm_path(path)
    for root in onedrive_roots():
        r = norm_path(root)
        if r and (p == r or p.startswith(r + os.sep)):
            return True
    return False


def is_admin() -> bool:
    if not IS_WINDOWS:
        return False
    import ctypes

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return False


def ui_language() -> str | None:
    """Langue d'affichage de Windows, au format « fr-FR »."""
    if not IS_WINDOWS:
        lang = os.environ.get("LANG", "")
        return lang.split(".")[0].replace("_", "-") or None
    import ctypes

    try:
        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        langid = k32.GetUserDefaultUILanguage()
        buf = ctypes.create_unicode_buffer(85)
        if k32.LCIDToLocaleName(langid, buf, 85, 0):
            return buf.value
    except Exception as exc:  # noqa: BLE001
        log.debug("Langue de Windows inconnue : %s", exc)
    return None


def windows_version() -> str:
    if IS_WINDOWS:
        try:
            v = sys.getwindowsversion()  # type: ignore[attr-defined]
            edition = platform.win32_edition() or ""
            name = "Windows 11" if v.build >= 22000 else "Windows 10"
            return f"{name} {edition} (build {v.build})".strip()
        except Exception:  # noqa: BLE001
            pass
    return platform.platform()


def open_folder(path: str | os.PathLike[str]) -> bool:
    """Ouvre un dossier dans l'Explorateur Windows."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        if IS_WINDOWS:
            os.startfile(str(p))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return True
    except OSError as exc:
        log.warning("Ouverture du dossier impossible %s : %s", p, exc)
        return False


def reveal(path: str | os.PathLike[str]) -> bool:
    """Ouvre l'Explorateur sur le dossier qui contient `path`, l'élément
    sélectionné (0.2.1). Repli : le dossier lui-même."""
    p = Path(path)
    if not p.exists():
        return open_folder(p.parent) if p.parent.exists() else False
    try:
        if IS_WINDOWS:
            windir = os.environ.get("WINDIR", "")
            explorer = str(Path(windir) / "explorer.exe") if windir else "explorer.exe"
            # explorer.exe attend « /select,"chemin" » en un seul argument.
            subprocess.Popen(f'"{explorer}" /select,"{p}"')
        else:
            subprocess.Popen(["xdg-open", str(p.parent)])
        return True
    except OSError as exc:
        log.warning("Ouverture de l'Explorateur impossible %s : %s", p, exc)
        return open_folder(p.parent)


def open_url(url: str) -> bool:
    """Ouvre une adresse (http, steam://…) avec le programme associé."""
    try:
        if IS_WINDOWS:
            os.startfile(url)  # type: ignore[attr-defined]
        else:
            import webbrowser

            webbrowser.open(url)
        return True
    except OSError as exc:
        log.warning("Ouverture impossible %s : %s", url, exc)
        return False


def start_via_explorer(target: str) -> bool:
    """Lance une cible par l'Explorateur Windows, donc avec des droits normaux.

    Utilisé quand FS Passion tourne en administrateur (4.3) : sinon le jeu et
    sa plateforme hériteraient des droits administrateur.
    """
    if not IS_WINDOWS:
        return open_url(target)
    try:
        windir = os.environ.get("WINDIR", "")
        explorer = str(Path(windir) / "explorer.exe") if windir else "explorer.exe"
        subprocess.Popen([explorer, target])
        return True
    except OSError as exc:
        log.warning("Lancement par l'Explorateur impossible %s : %s", target, exc)
        return False


def startfile(target: str, cwd: str | None = None, args: list[str] | None = None) -> bool:
    """Lance un exécutable ou une adresse (droits du processus courant).

    `args` : arguments de ligne de commande (0.3), uniquement pour un exécutable.
    """
    try:
        if IS_WINDOWS:
            if (cwd or args) and target.lower().endswith(".exe"):
                subprocess.Popen([target, *(args or [])], cwd=cwd, close_fds=True)
            else:
                os.startfile(target)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([target, *(args or [])], cwd=cwd)
        return True
    except OSError as exc:
        log.warning("Lancement impossible %s : %s", target, exc)
        return False


# --------------------------------------------------------------------------
# Corbeille de Windows (0.4 : « Supprimer définitivement », 4.7)
# --------------------------------------------------------------------------

FO_DELETE = 3
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_ALLOWUNDO = 0x0040
FOF_NOERRORUI = 0x0400
# Windows prévient (et demande) si un fichier ne peut pas aller dans la Corbeille
# (trop gros pour elle, par exemple) au lieu de le supprimer sans rien dire.
FOF_WANTNUKEWARNING = 0x4000


def recycle_bin_available(path: str | os.PathLike[str]) -> bool:
    """La Corbeille existe-t-elle pour le disque de `path` ? (disque fixe dont la
    Corbeille répond). Hors de Windows : non."""
    if not IS_WINDOWS:
        return False
    import ctypes
    from ctypes import wintypes

    class SHQUERYRBINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("i64Size", ctypes.c_longlong), ("i64NumItems", ctypes.c_longlong)]

    try:
        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        root = ctypes.create_unicode_buffer(260)
        if not k32.GetVolumePathNameW(str(path), root, 260):
            return False
        if k32.GetDriveTypeW(root.value) != DRIVE_FIXED:
            return False
        info = SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
        hr = ctypes.windll.shell32.SHQueryRecycleBinW(root.value, ctypes.byref(info))  # type: ignore[attr-defined]
        return hr == 0
    except Exception as exc:  # noqa: BLE001
        log.debug("Corbeille inconnue pour %s : %s", path, exc)
        return False


def send_to_recycle_bin(path: str | os.PathLike[str]) -> bool:
    """Envoie un fichier ou un dossier dans la Corbeille (SHFileOperationW).
    Renvoie True s'il y est, False sinon (rien n'est alors supprimé par cette
    fonction, sauf si Windows l'a fait après son propre avertissement)."""
    if not IS_WINDOWS:
        return False
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", ctypes.c_ushort),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    p = os.path.abspath(str(path))
    op = SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = p + "\0"  # liste terminée par deux caractères nuls
    op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT | FOF_WANTNUKEWARNING
    try:
        rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        log.warning("Corbeille indisponible pour %s : %s", p, exc)
        return False
    if rc != 0 or op.fAnyOperationsAborted:
        log.warning("Envoi à la Corbeille refusé (%s) : code %s", p, rc)
        return False
    return not os.path.lexists(p)


# --------------------------------------------------------------------------
# Droits pour les liens symboliques (0.6, stockage sur plusieurs disques, 4.20)
# --------------------------------------------------------------------------

LAYERS_KEY = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
DEV_MODE_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
RUNASADMIN = "RUNASADMIN"


def developer_mode() -> bool:
    """Le Mode développeur de Windows est-il activé ? (Paramètres → Système →
    Espace développeurs). Il autorise les liens symboliques sans droits
    administrateur."""
    if not IS_WINDOWS:
        return False
    try:
        import winreg
    except ImportError:
        return False

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, DEV_MODE_KEY) as k:
            value, _ = winreg.QueryValueEx(k, "AllowDevelopmentWithoutDevLicense")
            return int(value) == 1
    except OSError:
        return False


def elevation_type() -> int:
    """Type de jeton du processus (TokenElevationType) : 1 = par défaut (compte
    standard, ou contrôle de compte désactivé), 2 = élevé, 3 = limité (compte
    administrateur sous le contrôle de compte). 0 si inconnu."""
    if not IS_WINDOWS:
        return 0
    import ctypes
    from ctypes import wintypes

    try:
        advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        token = wintypes.HANDLE()
        if not advapi.OpenProcessToken(k32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):  # TOKEN_QUERY
            return 0
        try:
            value = ctypes.c_int(0)
            size = wintypes.DWORD(0)
            ok = advapi.GetTokenInformation(token, 18, ctypes.byref(value), ctypes.sizeof(value), ctypes.byref(size))
            return int(value.value) if ok else 0
        finally:
            k32.CloseHandle(token)
    except Exception:  # noqa: BLE001
        return 0


def is_standard_user() -> bool:
    """Compte Windows standard : obtenir les droits demande le mot de passe d'un
    AUTRE compte. FS Passion tournerait alors sous ce compte (autres Mes documents
    et %APPDATA%) : le Mode développeur est alors le seul bon choix (4.20)."""
    if not IS_WINDOWS or is_admin():
        return False
    return elevation_type() == 1


def _app_command() -> list[str]:
    """Commande qui a lancé FS Passion (programme, puis arguments)."""
    argv = list(getattr(sys, "orig_argv", None) or [sys.executable, *sys.argv])
    if argv:
        argv[0] = sys.executable
    return argv


def run_as_admin_target() -> str:
    """Programme concerné par la case « Exécuter ce programme en tant
    qu'administrateur » : FS Passion.exe, ou l'interpréteur Python en
    développement."""
    return str(Path(sys.executable).resolve()) if IS_WINDOWS else sys.executable


def run_as_admin_flag() -> bool:
    """La case « Exécuter ce programme en tant qu'administrateur » (onglet
    Compatibilité, utilisateur courant) est-elle cochée pour FS Passion ?"""
    if not IS_WINDOWS:
        return False
    try:
        import winreg
    except ImportError:
        return False

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, LAYERS_KEY) as k:
            value, _ = winreg.QueryValueEx(k, run_as_admin_target())
            return RUNASADMIN in str(value).upper().split()
    except OSError:
        return False


def set_run_as_admin_flag(enabled: bool) -> bool:
    """Coche ou décoche la case « Exécuter ce programme en tant
    qu'administrateur » pour l'utilisateur courant. Les autres réglages de
    compatibilité du programme sont conservés."""
    if not IS_WINDOWS:
        return False
    try:
        import winreg
    except ImportError:
        return False

    target = run_as_admin_target()
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, LAYERS_KEY, 0,
                                winreg.KEY_READ | winreg.KEY_WRITE) as k:
            try:
                current, _ = winreg.QueryValueEx(k, target)
            except OSError:
                current = ""
            words = [w for w in str(current).split() if w and w != "~" and w.upper() != RUNASADMIN]
            if enabled:
                words.append(RUNASADMIN)
            if words:
                winreg.SetValueEx(k, target, 0, winreg.REG_SZ, "~ " + " ".join(words))
            else:
                try:
                    winreg.DeleteValue(k, target)
                except OSError:
                    pass
        return True
    except OSError as exc:
        log.warning("Réglage « administrateur » non modifié : %s", exc)
        return False


def elevated_command(dev_launcher: Path | None = None) -> tuple[str, str, str]:
    """(programme, paramètres, dossier) de la relance en administrateur.

    Une application relancée en administrateur ne reçoit PAS l'environnement de
    celle qui la lance (Windows la démarre à neuf), et son dossier de travail
    peut devenir C:\\Windows\\System32. En développement, on relance donc
    lancer_dev.bat, qui prépare tout lui-même (0.6.1). L'application fabriquée
    (FS Passion.exe) n'a besoin de rien."""
    if dev_launcher is not None:
        comspec = os.environ.get("COMSPEC") or "cmd.exe"
        return comspec, f'/c ""{dev_launcher}""', str(dev_launcher.parent)
    argv = _app_command()
    return argv[0], subprocess.list2cmdline(argv[1:]), str(Path(argv[0]).parent)


def relaunch_elevated(dev_launcher: Path | None = None) -> bool:
    """Relance FS Passion en administrateur (Windows demande une confirmation).
    Appelé après la fermeture complète de l'instance courante."""
    if not IS_WINDOWS:
        return False
    import ctypes

    exe, params, cwd = elevated_command(dev_launcher)
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, cwd, 1)  # type: ignore[attr-defined]
        return int(rc) > 32
    except Exception as exc:  # noqa: BLE001
        log.warning("Relance en administrateur impossible : %s", exc)
        return False


def release_single_instance(handle: object) -> None:
    """Libère le verrou d'instance unique avant une relance."""
    if not IS_WINDOWS or not handle:
        return
    import ctypes

    try:
        ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(handle))  # type: ignore[attr-defined, arg-type]
    except Exception:  # noqa: BLE001
        pass


def same_volume(a: str | os.PathLike[str], b: str | os.PathLike[str]) -> bool | None:
    """Deux dossiers sont-ils sur le même disque ? None si l'un est illisible."""
    try:
        return os.stat(a).st_dev == os.stat(b).st_dev
    except OSError:
        return None
