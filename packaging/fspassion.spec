# -*- mode: python ; coding: utf-8 -*-
# FS Passion — fabrication de FSPassion.exe avec PyInstaller : mode « dossier »
# (onedir), plus rapide au démarrage et moins souvent signalé par les antivirus
# qu'un fichier unique.
#
# Lancé par tools/build.py (jamais directement) :
#   pyinstaller packaging/fspassion.spec --distpath build/dist --workpath build/work
#
# Résultat : build/dist/FSPassion/FSPassion.exe et son dossier _internal\
# (Python, bibliothèques, interface, langues, ressources).

import os
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 (SPECPATH est fourni par PyInstaller)
ICON = ROOT / "build" / "fspassion.ico"
VERSION_FILE = ROOT / "build" / "version_info.txt"


def tree(src: str, dest: str, skip=()):
    """Fichiers d'un dossier (récursif), pour « datas », sauf ceux de « skip »."""
    out = []
    base = ROOT / src
    for path in base.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(base)
        if any(str(rel).replace(os.sep, "/").startswith(s) for s in skip):
            continue
        out.append((str(path), str(Path(dest) / rel.parent)))
    return out


# Seules les ressources utilisées par l'application sont embarquées : pas la
# vidéo, ni les fichiers sources du logo (.psd, ancien SVG), ni le générateur
# des logos de version.
datas = []
datas += tree("ui", "ui")
datas += tree("lang", "lang")
datas += tree("src/fspassion/data", "fspassion/data")
datas += tree("assets/brand", "assets/brand")
datas += tree("assets/fonts", "assets/fonts", skip=("Typo", "IosevkaEtoileCompact-build-plan"))
datas += tree("assets/icons", "assets/icons")
datas += tree("assets/fallback", "assets/fallback")
datas += tree("assets/lang_template", "assets/lang_template")
datas += [(str(p), "assets/game-logos") for p in (ROOT / "assets" / "game-logos").glob("*.svg")]
datas += [(str(ROOT / "assets" / "FS_Passion_logo" / "logo.svg"), "assets/FS_Passion_logo")]
datas += [(str(ROOT / "LICENSE"), ".")]

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "fspassion_entry.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    # pywebview (WebView2 par pythonnet) et l'icône de la zone de notification :
    # modules chargés à la demande, que l'analyse ne voit pas toujours.
    hiddenimports=[
        "webview.platforms.edgechromium",
        "webview.platforms.winforms",
        "clr",
        "pystray._win32",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pytest", "mypy", "ruff", "PIL.AvifImagePlugin", "PIL.ImageTk", "PIL.ImageMath"],
    noarchive=False,
)
# Fichiers inutiles retirés (environ 9 Mo sur 31) :
# - PIL\_avif (7,9 Mo) : les icônes de DLC AVIF du dépôt de données ont été
#   converties en vrais JPEG ; Chromium affiche de toute façon l'AVIF seul ;
# - PIL\_imagingtk et _imagingmath : Tkinter et ImageMath, jamais utilisés ;
# - pywebview pour Android et 32 bits (FS Passion est 64 bits) ;
# - documentation XML de pythonnet, texte d'exemple de setuptools.
DROP = (
    "PIL/_avif.", "PIL/_imagingtk.", "PIL/_imagingmath.",
    "webview/lib/pywebview-android.jar",
    # PAS les dossiers webview/lib/runtimes/win-arm64 et win-x86 —
    # pywebview exige les trois au démarrage (« Cannot find win-arm64 »).
    "webview/lib/WebBrowserInterop.x86.dll",
    "clr_loader/ffi/dlls/x86/",
    "pythonnet/runtime/Python.Runtime.xml",
    "setuptools/_vendor/jaraco/text/Lorem ipsum.txt",
)


def keep(entry) -> bool:
    dest = entry[0].replace("\\", "/")
    return not any(dest.startswith(d) for d in DROP)


a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if keep(d)]

pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FSPassion",
    icon=str(ICON) if ICON.is_file() else None,
    version=str(VERSION_FILE) if VERSION_FILE.is_file() else None,
    console=False,          # application à fenêtre, sans console noire
    disable_windowed_traceback=False,
    upx=False,              # UPX compresse mais déclenche davantage d'antivirus
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FSPassion",
)
