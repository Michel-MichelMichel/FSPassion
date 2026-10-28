"""Archive une version complète du projet dans FSPassion-archives\\vX.Y.Z.

Usage (depuis la racine du projet) :
    python tools/archive_version.py
    python tools/archive_version.py --dest "C:\\Dev\\FSPassion-archives"

Règles :
- la version est lue dans src/fspassion/__init__.py (seule source) ;
- l'archive est une copie complète : code, interface, langues, tests, documents,
  ressources ; sont exclus la vidéo (assets\\video), les dossiers régénérables
  (.venv, caches de tests et de lint) et l'historique git ;
- une archive existante n'est jamais écrasée : le script s'arrête ;
- la copie se fait dans un dossier provisoire, renommé à la fin : une copie
  interrompue ne laisse jamais une archive incomplète sous son vrai nom ;
- le nombre de fichiers copiés est vérifié, puis noté dans ARCHIVE.txt.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT.parent / "FSPassion-archives"

# Dossiers ignorés partout : régénérables ou propres à l'outil de développement.
# « build » (fabrication, régénérable, plusieurs dizaines de Mo) aussi.
EXCLUDE_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".git", "build"}
# Dossier ignoré seulement à cet endroit : la vidéo de présentation.
EXCLUDE_VIDEO = ("assets", "video")
EXCLUDED_FILES = (".pyc", ".pyo")


def project_version(root: Path) -> str:
    text = (root / "src" / "fspassion" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("Version introuvable dans src/fspassion/__init__.py.")
    return match.group(1)


def _is_video(parent: str, name: str) -> bool:
    return (Path(parent).name, name) == EXCLUDE_VIDEO


def _ignore(parent: str, names: list[str]) -> set[str]:
    return {n for n in names if n in EXCLUDE_DIRS or n.endswith(EXCLUDED_FILES) or _is_video(parent, n)}


def count_files(root: Path) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not _is_video(dirpath, d)]
        total += sum(1 for f in filenames if not f.endswith(EXCLUDED_FILES))
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Archive une version complète de FS Passion.")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="dossier des archives")
    args = parser.parse_args(argv)

    version = project_version(ROOT)
    dest_root: Path = args.dest
    target = dest_root / f"v{version}"
    partial = dest_root / f".v{version}.partial"

    if dest_root.resolve().is_relative_to(ROOT):
        print("Refus : le dossier des archives ne doit pas être dans le projet.", file=sys.stderr)
        return 1
    if target.exists():
        print(f"Refus : {target} existe déjà. Une archive n'est jamais écrasée.", file=sys.stderr)
        return 1
    if partial.exists():
        print(f"Refus : {partial} existe (copie précédente interrompue). Supprime-le d'abord.", file=sys.stderr)
        return 1

    dest_root.mkdir(parents=True, exist_ok=True)
    print(f"Archive de la version {version} vers {target} …")
    shutil.copytree(ROOT, partial, ignore=_ignore)

    expected = count_files(ROOT)
    copied = count_files(partial)
    if copied != expected:
        print(f"Échec : {copied} fichiers copiés sur {expected} attendus. Archive non créée.", file=sys.stderr)
        shutil.rmtree(partial, ignore_errors=True)
        return 2

    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    excluded = ", ".join([*sorted(EXCLUDE_DIRS), "assets\\video"])
    (partial / "ARCHIVE.txt").write_text(
        f"FS Passion {version}\nArchivée le {stamp}\n{copied} fichiers\nExclus : {excluded}\n",
        encoding="utf-8",
    )
    partial.rename(target)
    print(f"Terminé : {copied} fichiers dans {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
