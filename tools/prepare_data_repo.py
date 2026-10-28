"""Prépare le dépôt de données « FSPassion-data » avant sa publication.

Utilisation (depuis C:\\Dev\\FSPassion) :
    .venv\\Scripts\\python.exe tools\\prepare_data_repo.py            (contrôle seulement)
    .venv\\Scripts\\python.exe tools\\prepare_data_repo.py --write    (écrit le catalogue)
    .venv\\Scripts\\python.exe tools\\prepare_data_repo.py --write --snapshot

Ce que fait le script, sur C:\\Dev\\FSPassion-data\\dlc\\dlc_catalog.json :
- contrôle le catalogue avec les mêmes règles que FS Passion (dlcremote) :
  une entrée refusée ici serait ignorée par l'application ;
- calcule l'empreinte (sha256) de chaque icône présente dans icons_dlc_fsXX\\,
  pour que FS Passion écarte un fichier abîmé ou modifié ;
- signale les DLC sans icône et les icônes qui ne servent à aucun DLC ;
- avec --write : enregistre le catalogue, daté du jour (champ « updated ») ;
- avec --snapshot : copie aussi ce catalogue dans assets\\fallback\\ (le
  catalogue embarqué, utilisé hors ligne).

Ensuite : publier le dossier sur GitHub (dépôt FSPassion-data).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fspassion import dlcremote, fsutil  # noqa: E402


def icon_candidates(entry: dict) -> list[str]:
    if entry.get("icon"):
        return [entry["icon"]]
    stem = entry.get("file")
    return [f"{stem}.png", f"{stem}.jpg"] if stem else []


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=str(ROOT.parent / "FSPassion-data"), help="dossier FSPassion-data")
    p.add_argument("--write", action="store_true", help="enregistrer le catalogue complété")
    p.add_argument("--snapshot", action="store_true", help="copier aussi le catalogue dans assets\\fallback")
    args = p.parse_args(argv)

    dlc_dir = Path(args.data) / "dlc"
    path = dlc_dir / "dlc_catalog.json"
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    clean = dlcremote.validate_catalog(raw)
    problems = 0

    for vid, vcat in raw.get("versions", {}).items():
        kept = clean["versions"].get(vid)
        if kept is None:
            print(f"[REFUSÉ] {vid} : version ignorée par FS Passion (nom de dossier d'icônes ?)")
            problems += 1
            continue
        folder = dlc_dir / vcat["icons_folder"]
        files = {f.name.lower(): f for f in folder.glob("*") if f.is_file()} if folder.is_dir() else {}
        used: set[str] = set()
        if len(kept["dlc"]) != len(vcat.get("dlc") or []):
            print(f"[REFUSÉ] {vid} : {len(vcat['dlc']) - len(kept['dlc'])} entrée(s) ignorée(s) par FS Passion")
            problems += 1
        for entry in vcat.get("dlc") or []:
            found = next((files[n.lower()] for n in icon_candidates(entry) if n.lower() in files), None)
            if found is None:
                if entry.get("status") != "announced":
                    print(f"[icône manquante] {vid} {entry.get('file')}")
                entry.pop("sha256", None)
                continue
            used.add(found.name.lower())
            entry["sha256"] = hashlib.sha256(found.read_bytes()).hexdigest()
            if found.stat().st_size > dlcremote.MAX_ICON:
                print(f"[TROP GROS] {found} : {found.stat().st_size} octets (maximum {dlcremote.MAX_ICON})")
                problems += 1
        for name, f in files.items():
            if name not in used and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                print(f"[inutilisée] {vid} {f.name}")

    raw["updated"] = time.strftime("%Y-%m-%d")
    print(f"\n{sum(len(v.get('dlc') or []) for v in raw['versions'].values())} DLC, {problems} problème(s).")
    if args.write:
        fsutil.atomic_write_json(path, raw)
        print(f"Catalogue enregistré : {path} (updated = {raw['updated']})")
        if args.snapshot:
            snap = ROOT / "assets" / "fallback" / "dlc_catalog.json"
            fsutil.atomic_write_json(snap, raw)
            print(f"Copie embarquée : {snap}")
    else:
        print("Contrôle seulement : ajoutez --write pour enregistrer.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
