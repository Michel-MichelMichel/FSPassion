"""Fabrication de FS Passion.

    python tools/build.py [--skip-tests] [--no-installer] [--webview2 FICHIER]

Étapes, toutes dans le dossier build\\ (jamais suivi par git) :

1. icône de l'application (build\\fspassion.ico) et informations de version
   de l'exécutable (build\\version_info.txt), d'après src/fspassion/__init__.py ;
2. tests automatiques (sauf --skip-tests) ;
3. FSPassion.exe avec PyInstaller, en mode dossier (build\\dist\\FSPassion\\) ;
4. pack de démonstration (faux mods) à côté de l'exécutable ;
5. version portable : build\\release\\FSPassion-<version>-portable.zip
   (le dossier, plus « portable.txt » : les réglages restent dans data\\) ;
6. installeur Inno Setup : build\\release\\FSPassion-<version>-setup.exe, avec
   l'installation de WebView2 si besoin et le désinstalleur. Il faut
   Inno Setup 6 (ISCC.exe) ; sinon cette étape est sautée avec un message ;
7. empreintes SHA-256 : build\\release\\SHA256SUMS.txt (publiées avec les
   fichiers sur GitHub Releases, seul lieu officiel de téléchargement).

Le même script sert sur le PC (fabriquer.bat) et sur GitHub Actions
(.github/workflows/build.yml) : les deux fabrications sont identiques.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
DIST = BUILD / "dist"
APP_DIR = DIST / "FSPassion"
RELEASE = BUILD / "release"
WEBVIEW2_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"  # programme d'installation « Evergreen »
# Microsoft ne publie pas d'empreinte SHA-256 pour ce programme d'installation : il est
# signé par Microsoft, et sa signature Authenticode est vérifiée à chaque fabrication.
ISCC_PATHS = [
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
]
ICON_SOURCE = ROOT / "assets" / "brand" / "tray.png"  # même icône que la zone de notification

PORTABLE_TXT = """FS Passion — version portable

Ce fichier indique à FS Passion de garder ses réglages, ses journaux et ses
caches dans le dossier « data » à côté de FSPassion.exe, au lieu de
%APPDATA% et %LOCALAPPDATA%. Supprimez-le pour revenir au mode installé.

This file tells FS Passion to keep its settings, logs and caches in the
"data" folder next to FSPassion.exe instead of %APPDATA% and %LOCALAPPDATA%.
"""


def step(title: str) -> None:
    print(f"\n=== {title}", flush=True)


def version() -> str:
    """Seule source : src/fspassion/__init__.py."""
    text = (ROOT / "src" / "fspassion" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__ = "(\d+\.\d+\.\d+)"', text, re.M)
    if not m:
        raise SystemExit("Version illisible dans src/fspassion/__init__.py")
    v = m.group(1)
    return v


ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def _ico_bmp(img) -> bytes:
    """Image d'icône au format BMP 32 bits (couleurs + masque), celui que
    l'Explorateur lit le plus sûrement pour les petites tailles."""
    w, h = img.size
    header = (40).to_bytes(4, "little") + w.to_bytes(4, "little") + (h * 2).to_bytes(4, "little") \
        + (1).to_bytes(2, "little") + (32).to_bytes(2, "little") + bytes(24)
    px = img.tobytes("raw", "BGRA")
    rows = [px[y * w * 4:(y + 1) * w * 4] for y in range(h)]
    colour = b"".join(reversed(rows))  # BMP : de bas en haut
    mask_row = ((w + 31) // 32) * 4
    alpha = img.getchannel("A").tobytes()
    mask = bytearray()
    for y in reversed(range(h)):
        row = bytearray(mask_row)
        for x in range(w):
            if alpha[y * w + x] == 0:
                row[x // 8] |= 0x80 >> (x % 8)
        mask += row
    return header + colour + bytes(mask)


def write_ico(square, out: Path, sizes=ICON_SIZES) -> None:
    """Écrit un .ico multi-tailles : BMP jusqu'à 128 px, PNG pour 256 px
    (Pillow écrivait toutes les tailles en PNG)."""
    import io

    from PIL import Image

    entries = []
    for s in sizes:
        img = square.resize((s, s), Image.LANCZOS) if square.size != (s, s) else square.copy()
        if s >= 256:
            buf = io.BytesIO()
            img.save(buf, "PNG", optimize=True)
            data = buf.getvalue()
        else:
            data = _ico_bmp(img)
        entries.append((s, data))
    head = (0).to_bytes(2, "little") + (1).to_bytes(2, "little") + len(entries).to_bytes(2, "little")
    offset = 6 + 16 * len(entries)
    table = b""
    for s, data in entries:
        dim = 0 if s >= 256 else s
        table += bytes([dim, dim, 0, 0]) + (1).to_bytes(2, "little") + (32).to_bytes(2, "little") \
            + len(data).to_bytes(4, "little") + offset.to_bytes(4, "little")
        offset += len(data)
    out.write_bytes(head + table + b"".join(d for _, d in entries))


def make_icon() -> Path:
    """Icône Windows multi-tailles (16 à 256 px), depuis assets/brand/tray.png."""
    from PIL import Image

    src = ICON_SOURCE
    out = BUILD / "fspassion.ico"
    with Image.open(src) as im:
        im = im.convert("RGBA")
        side = max(im.size)
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        square.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
        if side < 256:
            square = square.resize((256, 256), Image.LANCZOS)
        write_ico(square, out)
    print(f"Icône : {out.name} (depuis {src.relative_to(ROOT)})")
    return out


def refresh_icon_cache() -> None:
    """L'Explorateur garde en cache l'icône d'un fichier d'après son chemin :
    après une nouvelle fabrication, il montrait encore l'ancienne icône de
    fspassion.ico et de FSPassion.exe. On lui demande de la relire."""
    if os.name != "nt":
        return
    try:
        subprocess.run(["ie4uinit.exe", "-show"], check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        import ctypes

        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)  # SHCNE_ASSOCCHANGED
    except Exception:  # noqa: BLE001
        pass


def make_version_info(v: str) -> Path:
    """Informations affichées dans Propriétés → Détails de FSPassion.exe."""
    a, b, c = (int(x) for x in v.split("."))
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({a}, {b}, {c}, 0), prodvers=({a}, {b}, {c}, 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040C04B0', [
      StringStruct('CompanyName', 'MichelMichel'),
      StringStruct('FileDescription', 'FS Passion — gestionnaire de mods pour Farming Simulator'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', 'FSPassion'),
      StringStruct('LegalCopyright', 'GPLv3 — MichelMichel'),
      StringStruct('OriginalFilename', 'FSPassion.exe'),
      StringStruct('ProductName', 'FS Passion'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [1036, 1200])])
  ]
)
"""
    out = BUILD / "version_info.txt"
    out.write_text(text, encoding="utf-8")
    return out


def run_tests() -> None:
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=ROOT, env=env, check=True)


def running_from_build() -> list[str]:
    """FS Passion lancé depuis build\\dist (ou ouvert dans la zone de
    notification) : Windows verrouille ses fichiers, la fabrication ne peut
    pas remplacer le dossier."""
    try:
        import psutil
    except ImportError:
        return []
    found = []
    root = str(APP_DIR.resolve()).lower()
    for proc in psutil.process_iter(["pid", "exe"]):
        exe = (proc.info.get("exe") or "").lower()
        if exe.startswith(root):
            found.append(f"{Path(exe).name} (n° {proc.info['pid']})")
    return found


def pyinstaller() -> None:
    busy = running_from_build()
    if busy:
        raise SystemExit(
            "FS Passion est encore ouvert depuis build\\dist\\FSPassion : " + ", ".join(busy) + ".\n"
            "Ferme-le (y compris l'icône près de l'horloge : clic droit → Quitter), puis relance la fabrication.")
    try:
        shutil.rmtree(APP_DIR)
    except FileNotFoundError:
        pass
    except PermissionError as exc:
        raise SystemExit(
            f"Impossible de remplacer {APP_DIR} : un fichier est encore utilisé ({exc.filename}).\n"
            "Ferme FS Passion s'il a été lancé depuis ce dossier (zone de notification comprise), "
            "ainsi que toute fenêtre de l'Explorateur ouverte dedans, puis relance la fabrication.") from exc
    subprocess.run([
        sys.executable, "-m", "PyInstaller", str(ROOT / "packaging" / "fspassion.spec"),
        "--noconfirm", "--clean", "--distpath", str(DIST), "--workpath", str(BUILD / "work"),
    ], cwd=ROOT, check=True)
    exe = APP_DIR / ("FSPassion.exe" if os.name == "nt" else "FSPassion")
    if not exe.is_file():
        raise SystemExit(f"Exécutable absent : {exe}")
    internal = APP_DIR / "_internal"
    for needed in ("ui/index.html", "lang/fr.json", "lang/en.json", "fspassion/data/app_info.json",
                   "assets/fonts/IosevkaEtoileCompact-Regular.woff2", "assets/FS_Passion_logo/logo.svg"):
        if not (internal / needed).is_file():
            raise SystemExit(f"Ressource absente de l'exécutable : {needed}")
    print(f"Exécutable : {exe.relative_to(ROOT)}")


def demo_pack() -> None:
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_demo_pack.py"), str(APP_DIR)], cwd=ROOT, check=True)


def portable(v: str) -> Path:
    RELEASE.mkdir(parents=True, exist_ok=True)
    out = RELEASE / f"FSPassion-{v}-portable.zip"
    out.unlink(missing_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(APP_DIR.rglob("*")):
            if path.is_file():
                z.write(path, Path("FSPassion") / path.relative_to(APP_DIR))
        z.writestr("FSPassion/portable.txt", PORTABLE_TXT)
    print(f"Portable : {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} Mo)")
    return out


def find_iscc() -> Path | None:
    env = os.environ.get("ISCC")
    if env and Path(env).is_file():
        return Path(env)
    found = shutil.which("ISCC") or shutil.which("iscc")
    if found:
        return Path(found)
    return next((p for p in ISCC_PATHS if p.is_file()), None)


def verify_webview2(path: Path) -> None:
    """Refuse un programme d'installation WebView2 qui n'est pas signé par Microsoft."""
    script = (
        "$s = Get-AuthenticodeSignature -LiteralPath $env:WV2_PATH; "
        "if ($s.Status -eq 'Valid' -and $s.SignerCertificate.Subject -like '*O=Microsoft Corporation*') "
        "{ exit 0 } else { exit 1 }"
    )
    if os.name != "nt":
        raise SystemExit("Vérification de la signature de WebView2 : Windows requis.")
    res = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "WV2_PATH": str(path)},
    )
    if res.returncode != 0:
        path.unlink(missing_ok=True)
        raise SystemExit("Signature Microsoft de WebView2 absente ou invalide : fabrication arrêtée.")


def webview2_bootstrapper(given: str | None) -> Path | None:
    """Petit programme de Microsoft (environ 2 Mo) qui installe WebView2 s'il
    manque (Windows 10). Embarqué dans l'installeur, lancé seulement si besoin."""
    if given:
        p = Path(given)
        if not p.is_file():
            return None
        verify_webview2(p)
        return p
    dest = BUILD / "MicrosoftEdgeWebview2Setup.exe"
    if dest.is_file():
        verify_webview2(dest)
        return dest
    tmp = dest.with_name(dest.name + ".part")
    try:
        print("Téléchargement du programme d'installation de WebView2…")
        with urllib.request.urlopen(WEBVIEW2_URL, timeout=60) as r:  # noqa: S310 (adresse fixe de Microsoft)
            tmp.write_bytes(r.read())
    except OSError as exc:
        print(f"WebView2 non téléchargé ({exc}) : l'installeur ne pourra pas l'installer sous Windows 10.")
        return None
    verify_webview2(tmp)
    tmp.replace(dest)
    return dest


def installer(v: str, webview2: str | None) -> Path | None:
    iscc = find_iscc()
    if iscc is None:
        print("Inno Setup 6 introuvable (ISCC.exe) : installeur non fabriqué.")
        print("Installe-le depuis https://jrsoftware.org/isdl.php, puis relance la fabrication.")
        return None
    RELEASE.mkdir(parents=True, exist_ok=True)
    args = [str(iscc), f"/DAppVersion={v}", f"/DSourceDir={APP_DIR}", f"/DOutputDir={RELEASE}",
            f"/DRootDir={ROOT}", f"/DIconFile={BUILD / 'fspassion.ico'}"]
    wv = webview2_bootstrapper(webview2)
    if wv:
        args.append(f"/DWebView2Setup={wv}")
    args.append(str(ROOT / "packaging" / "installer.iss"))
    subprocess.run(args, cwd=ROOT, check=True)
    out = RELEASE / f"FSPassion-{v}-setup.exe"
    if not out.is_file():
        raise SystemExit(f"Installeur absent : {out}")
    print(f"Installeur : {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} Mo)")
    return out


def checksums() -> Path:
    out = RELEASE / "SHA256SUMS.txt"
    lines = []
    for f in sorted(RELEASE.iterdir()):
        if f.is_file() and f.name != out.name:
            h = hashlib.sha256()
            with f.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            lines.append(f"{h.hexdigest()}  {f.name}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return out


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Fabrication de FS Passion")
    p.add_argument("--skip-tests", action="store_true")
    p.add_argument("--no-installer", action="store_true")
    p.add_argument("--webview2", help="programme d'installation de WebView2 déjà téléchargé")
    args = p.parse_args(argv)

    v = version()
    print(f"FS Passion {v}")
    BUILD.mkdir(exist_ok=True)
    shutil.rmtree(RELEASE, ignore_errors=True)
    step("1. Icône et informations de version")
    make_icon()
    make_version_info(v)
    if not args.skip_tests:
        step("2. Tests automatiques")
        run_tests()
    step("3. Exécutable (PyInstaller)")
    pyinstaller()
    step("4. Pack de démonstration")
    demo_pack()
    step("5. Version portable")
    portable(v)
    if not args.no_installer:
        step("6. Installeur (Inno Setup)")
        installer(v, args.webview2)
    step("7. Empreintes SHA-256")
    checksums()
    refresh_icon_cache()
    print(f"Terminé : {RELEASE}")


if __name__ == "__main__":
    main()
