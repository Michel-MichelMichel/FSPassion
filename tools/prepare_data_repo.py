"""Prépare le dépôt de données « FSPassion-data » avant sa publication.

Utilisation (depuis C:\\Dev\\FSPassion) :
    .venv\\Scripts\\python.exe tools\\prepare_data_repo.py            (contrôle seulement)
    .venv\\Scripts\\python.exe tools\\prepare_data_repo.py --write    (écrit le catalogue)
    .venv\\Scripts\\python.exe tools\\prepare_data_repo.py --write --pdlc

preparer_catalogue_dlc.bat fait d'abord « git pull » dans FSPassion-data,
puis lance « --write --pdlc ».

Ce que fait le script, sur C:\\Dev\\FSPassion-data\\dlc\\dlc_catalog.json :
- contrôle le catalogue avec les mêmes règles que FS Passion (dlcremote) :
  une entrée refusée ici serait ignorée par l'application ;
- calcule l'empreinte (sha256) de chaque icône présente dans icons_dlc_fsXX\\,
  pour que FS Passion écarte un fichier abîmé ou modifié ;
- signale les DLC sans icône et les icônes qui ne servent à aucun DLC ;
- passe en « released » les DLC « announced » dont la date est passée ;
- avec --pdlc : lit les dossiers pdlc des jeux configurés dans FS Passion
  (sur ce PC) et signale les DLC reconnus seulement par leurs mots-clés, ou
  pas du tout. Avec --write, un DLC reconnu par ses mots-clés reçoit le nom
  exact de son fichier (« file ») : il ne dépend plus des mots-clés ;
- avec --write : enregistre le catalogue, daté du jour (champ « updated ») ;
- avec --snapshot : copie aussi ce catalogue dans assets\\fallback\\. Plus
  nécessaire : la fabrication (tools/build.py) embarque le catalogue publié.

Ensuite : publier FSPassion-data (git add, commit, push ; commandes affichées).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fspassion import config, dlc, dlcremote, fsutil, gamepaths, versions  # noqa: E402


def icon_candidates(entry: dict) -> list[str]:
    if entry.get("icon"):
        return [entry["icon"]]
    stem = entry.get("file")
    return [f"{stem}.png", f"{stem}.jpg"] if stem else []


def release_announced(raw: dict[str, Any], today: str) -> list[str]:
    """DLC « announced » dont la date de sortie est passée → « released »."""
    out = []
    for vid, vcat in raw.get("versions", {}).items():
        for e in vcat.get("dlc") or []:
            rd = e.get("release_date")
            if e.get("status") == "announced" and isinstance(rd, str) and rd <= today:
                e["status"] = "released"
                out.append(f"{vid} {e.get('name')}")
    return out


def local_dlc_files(settings: config.Settings | None = None) -> dict[str, list[tuple[str, str]]]:
    """Fichiers DLC présents sur ce PC, par version : [(nom sans extension,
    extension)], d'après les dossiers configurés dans FS Passion."""
    settings = settings or config.Settings()
    out: dict[str, list[tuple[str, str]]] = {}
    for v in versions.VERSIONS:
        vp = gamepaths.from_cfg(v, settings.version(v.id))
        found: dict[str, tuple[str, str]] = {}
        for d in vp.dlc_dirs:
            try:
                files = [f for f in d.iterdir() if f.is_file()]
            except OSError:
                continue
            for f in files:
                if f.suffix.lower() in dlc.DLC_EXTS:
                    found.setdefault(f.stem.lower(), (f.stem, f.suffix.lower()))
        if found:
            out[v.id] = sorted(found.values(), key=lambda x: x[0].lower())
    return out


def link_local_files(raw: dict[str, Any], local: dict[str, list[tuple[str, str]]]) -> tuple[list[str], int]:
    """Compare les DLC du PC au catalogue. Une entrée à mots-clés qui
    reconnaît exactement un fichier reçoit ce nom (« file ») ; ses mots-clés
    sont retirés. Renvoie (lignes du rapport, nombre d'entrées complétées)."""
    lines: list[str] = []
    linked = 0
    for vid, files in local.items():
        vcat = raw.get("versions", {}).get(vid)
        if vcat is None:
            lines.append(f"[pdlc] {vid} : {len(files)} DLC sur ce PC, version absente du catalogue")
            continue
        entries = vcat.get("dlc") or []
        by_entry: dict[int, list[tuple[str, str]]] = {}
        for stem, ext in files:
            e = dlc.match_entry(stem, entries)
            if e is None:
                lines.append(f"[pdlc inconnu] {vid} {stem}{ext} : aucun DLC du catalogue ne le reconnaît "
                             f"(ajouter une entrée avec « file »: « {stem} »)")
            elif not e.get("file"):
                by_entry.setdefault(id(e), []).append((stem, ext))
        for e in entries:
            hits = by_entry.get(id(e))
            if not hits:
                continue
            if len(hits) > 1:
                names = ", ".join(s + x for s, x in hits)
                lines.append(f"[pdlc à trancher] {vid} « {e.get('name')} » (mots-clés {e.get('keywords')}) "
                             f"reconnaît plusieurs fichiers : {names}")
                continue
            stem, ext = hits[0]
            e["file"] = stem
            e.pop("keywords", None)
            if ext == ".zip":
                e["type"] = "zip"
            linked += 1
            lines.append(f"[pdlc nom de fichier] {vid} « {e.get('name')} » : « file »: « {stem} » "
                         f"remplace les mots-clés (enregistré avec --write)")
    return lines, linked


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=str(ROOT.parent / "FSPassion-data"), help="dossier FSPassion-data")
    p.add_argument("--write", action="store_true", help="enregistrer le catalogue complété")
    p.add_argument("--pdlc", action="store_true", help="comparer aux DLC présents sur ce PC")
    p.add_argument("--snapshot", action="store_true", help="copier aussi le catalogue dans assets\\fallback")
    args = p.parse_args(argv)

    data = Path(args.data)
    if not (data / ".git").exists():
        print(f"[ATTENTION] {data} n'est pas un clone Git : il est peut-être en retard sur GitHub "
              "(pull requests de la veille des DLC). Publier ce dossier effacerait leurs ajouts.")
    dlc_dir = data / "dlc"
    path = dlc_dir / "dlc_catalog.json"
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    problems = 0
    changed = False

    for name in release_announced(raw, time.strftime("%Y-%m-%d")):
        print(f"[sorti] {name} : « announced » → « released »")
        changed = True

    if args.pdlc:
        lines, linked = link_local_files(raw, local_dlc_files())
        print("\n".join(lines) if lines else "[pdlc] Tous les DLC de ce PC sont reconnus par leur nom de fichier.")
        changed = changed or linked > 0

    clean = dlcremote.validate_catalog(raw)
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
                    print(f"[icône manquante] {vid} {entry.get('file') or entry.get('name')}")
                if entry.pop("sha256", None) is not None:
                    changed = True
                continue
            used.add(found.name.lower())
            sha = hashlib.sha256(found.read_bytes()).hexdigest()
            if entry.get("sha256") != sha:
                entry["sha256"] = sha
                changed = True
            if found.stat().st_size > dlcremote.MAX_ICON:
                print(f"[TROP GROS] {found} : {found.stat().st_size} octets (maximum {dlcremote.MAX_ICON})")
                problems += 1
        for name, f in files.items():
            if name not in used and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                print(f"[inutilisée] {vid} {f.name}")

    print(f"\n{sum(len(v.get('dlc') or []) for v in raw['versions'].values())} DLC, {problems} problème(s).")
    if not args.write:
        print("Contrôle seulement : ajoutez --write pour enregistrer.")
    elif not changed and not args.snapshot:
        print("Catalogue inchangé : rien à enregistrer ni à publier.")
    else:
        if changed:
            raw["updated"] = time.strftime("%Y-%m-%d")
            fsutil.atomic_write_json(path, raw)
            print(f"Catalogue enregistré : {path} (updated = {raw['updated']})")
            print("\nPour le publier :\n"
                  f'  git -C "{data}" add dlc\n'
                  f'  git -C "{data}" commit -m "Catalogue des DLC du {raw["updated"]}"\n'
                  f'  git -C "{data}" push')
        if args.snapshot:
            snap = ROOT / "assets" / "fallback" / "dlc_catalog.json"
            fsutil.atomic_write_json(snap, raw)
            print(f"Copie embarquée : {snap}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
