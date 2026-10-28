"""Fabrique le pack de démonstration de FS Passion.

    python tools/make_demo_pack.py <dossier de sortie>

Produit FSPassion-demo.zip et FSPassion-demo.zip.sha256. L'archive contient :
- demo.json : le catalogue des faux mods (version du jeu, identifiant, titres,
  catégorie, dépendances, auteur) et la description des dossiers ;
- pour chaque version du jeu (FS25, FS22, FS19) :
    <version>/Mods/            faux mods .zip (un vrai modDesc.xml, une icône),
                               plus un mod non compressé et une anomalie ;
    <version>/Documents/       gameSettings.xml minimal, et pdlc/ (DLC vides).

Les faux mods sont inventés : aucune marque, aucun nom ni aucune image de vrai
mod. Les icônes sont des dessins simples (tracteur, remorque, moissonneuse,
bâtiment, balle, outil, carte, script) générés ici. Les DLC sont des fichiers
vides qui portent le nom de vrais DLC, pour montrer leur affichage.

Le résultat est déterministe : deux fabrications donnent le même pack.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import random
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

PACK = "FSPassion-demo.zip"
SCHEMA = 1
ICON = 512
FIXED_TIME = (2026, 10, 18, 12, 0, 0)

BRANDS = ["Brandvik", "Northwind", "Terralux", "Agrona", "Velmar", "Corvane", "Holmgard", "Ostrava",
          "Pellini", "Quarry", "Sundal", "Varenne"]
KINDS = {
    "tractor": ("Tracteur", "Tractor", "Traktor"),
    "trailer": ("Remorque", "Trailer", "Anhänger"),
    "harvester": ("Moissonneuse", "Harvester", "Mähdrescher"),
    "building": ("Hangar", "Shed", "Halle"),
    "bale": ("Presse à balles", "Baler", "Ballenpresse"),
    "tool": ("Charrue", "Plough", "Pflug"),
    "script": ("Script", "Script", "Skript"),
}
MAPS = [
    ("HollowCreek", "Hollow Creek", "Vallée de Hollow Creek", "Hollow-Creek-Tal"),
    ("ValDOrsay", "Val d'Orsay", "Val d'Orsay", "Val d'Orsay"),
    ("Kleindorf", "Kleindorf", "Kleindorf", "Kleindorf"),
    ("NorthfieldPlains", "Northfield Plains", "Plaines de Northfield", "Northfield-Ebene"),
]
PALETTES = [
    ((46, 58, 70), (24, 30, 38)), ((70, 78, 52), (34, 40, 26)), ((92, 70, 48), (44, 32, 22)),
    ((44, 72, 74), (20, 36, 38)), ((80, 56, 66), (38, 26, 32)), ((64, 66, 70), (30, 31, 34)),
    ((96, 84, 56), (46, 40, 26)), ((50, 64, 90), (22, 28, 44)),
]
VERSIONS = {
    # identifiant : (préfixe, descVersion, nombre de mods, cartes, DLC)
    "FS25": ("FS25_", 104, 56, 4, ["highlandsFishingPack", "plainsAndPrairiesPack"]),
    "FS22": ("FS22_", 79, 22, 2, []),
    "FS19": ("FS19_", 53, 12, 1, []),
}


# --------------------------------------------------------------------------
# Icônes : un fond dégradé et un pictogramme clair
# --------------------------------------------------------------------------

def _background(rnd: random.Random) -> Image.Image:
    top, bottom = PALETTES[rnd.randrange(len(PALETTES))]
    img = Image.new("RGB", (ICON, ICON))
    px = img.load()
    for y in range(ICON):
        t = y / (ICON - 1)
        for x in range(ICON):
            d = (x / (ICON - 1)) * 0.25
            k = min(1.0, t * 0.85 + d)
            px[x, y] = tuple(int(top[i] * (1 - k) + bottom[i] * k) for i in range(3))
    # Halo doux derrière le pictogramme
    glow = Image.new("L", (ICON, ICON), 0)
    ImageDraw.Draw(glow).ellipse((96, 80, 416, 400), fill=60)
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    light = Image.new("RGB", (ICON, ICON), (255, 255, 255))
    return Image.composite(light, img, glow)


def _wheel(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, ink, bg) -> None:
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ink)
    d.ellipse((cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55), fill=bg)
    d.ellipse((cx - r * 0.22, cy - r * 0.22, cx + r * 0.22, cy + r * 0.22), fill=ink)


def _draw(kind: str, d: ImageDraw.ImageDraw, ink, bg) -> None:
    if kind == "tractor":
        d.rounded_rectangle((150, 190, 300, 330), 14, fill=ink)        # cabine
        d.rectangle((168, 208, 282, 270), fill=bg)                      # vitre
        d.rounded_rectangle((280, 260, 400, 340), 12, fill=ink)        # capot
        d.rectangle((370, 228, 384, 262), fill=ink)                     # échappement
        _wheel(d, 210, 352, 70, ink, bg)
        _wheel(d, 372, 372, 44, ink, bg)
    elif kind == "trailer":
        d.polygon([(110, 200), (402, 200), (380, 320), (132, 320)], fill=ink)
        d.rectangle((402, 300, 450, 312), fill=ink)                     # timon
        _wheel(d, 200, 350, 42, ink, bg)
        _wheel(d, 300, 350, 42, ink, bg)
    elif kind == "harvester":
        d.rounded_rectangle((170, 170, 330, 320), 14, fill=ink)
        d.rectangle((188, 188, 270, 240), fill=bg)
        d.polygon([(330, 230), (430, 260), (430, 310), (330, 300)], fill=ink)   # coupe
        for x in range(345, 430, 20):
            d.line((x, 262, x, 306), fill=bg, width=5)
        d.rectangle((120, 150, 280, 168), fill=ink)                     # tube de vidange
        _wheel(d, 220, 350, 62, ink, bg)
        _wheel(d, 330, 362, 38, ink, bg)
    elif kind == "building":
        d.polygon([(120, 250), (256, 140), (392, 250)], fill=ink)
        d.rectangle((140, 250, 372, 390), fill=ink)
        d.rectangle((210, 290, 302, 390), fill=bg)
        d.line((210, 290, 302, 390), fill=ink, width=8)
        d.line((302, 290, 210, 390), fill=ink, width=8)
    elif kind == "bale":
        d.ellipse((150, 170, 362, 382), fill=ink)
        for r in (80, 52, 24):
            d.arc((256 - r, 276 - r, 256 + r, 276 + r), 20, 340, fill=bg, width=8)
        d.rectangle((150, 270, 362, 282), fill=bg)
    elif kind == "tool":
        d.rectangle((110, 200, 410, 222), fill=ink)                     # châssis
        for i, x in enumerate(range(150, 400, 70)):
            d.polygon([(x, 222), (x + 22, 222), (x - 18, 330 + i * 4), (x - 44, 318 + i * 4)], fill=ink)
        _wheel(d, 410, 300, 36, ink, bg)
    elif kind == "script":
        cx, cy = 256, 270
        teeth = 9
        pts = []
        for i in range(teeth * 2):
            a = math.pi * 2 * i / (teeth * 2)
            r = 128 if i % 2 == 0 else 104
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        d.polygon(pts, fill=ink)
        d.ellipse((cx - 46, cy - 46, cx + 46, cy + 46), fill=bg)
    elif kind == "map":
        d.ellipse((340, 120, 410, 190), fill=ink)                       # soleil
        for i in range(6):
            y = 250 + i * 26
            d.polygon([(70, y + 40), (256, y), (442, y + 40), (442, y + 52), (256, y + 12), (70, y + 52)], fill=ink)
        d.polygon([(110, 240), (190, 160), (270, 240)], fill=ink)       # colline


def make_icon(kind: str, seed: int) -> bytes:
    rnd = random.Random(seed)
    img = _background(rnd)
    bg = img.getpixel((256, 450))
    ink = (236, 232, 220)
    layer = Image.new("RGBA", (ICON, ICON), (0, 0, 0, 0))
    _draw(kind, ImageDraw.Draw(layer), ink + (255,), bg + (255,))
    shadow = layer.split()[3].filter(ImageFilter.GaussianBlur(10))
    dark = Image.new("RGB", (ICON, ICON), (0, 0, 0))
    img = Image.composite(dark, img, shadow.point(lambda v: v * 0.45))
    img.paste(layer, (0, 0), layer)
    buf = io.BytesIO()
    img.save(buf, "DDS", pixel_format="DXT1")
    return buf.getvalue()


# --------------------------------------------------------------------------
# modDesc.xml
# --------------------------------------------------------------------------

def _xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def moddesc(desc: int, titles: dict[str, str], author: str, version: str, icon: str,
            deps: list[str], is_map: bool, map_id: str = "") -> str:
    t = "".join(f"<{k}>{_xml(v)}</{k}>" for k, v in titles.items())
    dep = ""
    if deps:
        dep = "\n    <dependencies>" + "".join(f"\n        <dependency>{d}</dependency>" for d in deps) + "\n    </dependencies>"
    maps = ""
    if is_map:
        maps = (f'\n    <maps>\n        <map id="{map_id}" className="Mission00" filename="$dataS/scripts/missions/mission00.lua"'
                f' configFilename="maps/map.xml" defaultVehiclesXMLFilename="maps/vehicles.xml">'
                f"<title>{t}</title></map>\n    </maps>")
    return (
        '<?xml version="1.0" encoding="utf-8" standalone="no" ?>\n'
        f'<modDesc descVersion="{desc}">\n'
        f"    <author>{_xml(author)}</author>\n    <version>{version}</version>\n"
        f"    <title>{t}</title>\n"
        "    <description><en>FS Passion demo mod: a fictitious mod, for testing only.</en>"
        "<fr>Mod de démonstration de FS Passion : un mod fictif, pour tester seulement.</fr></description>\n"
        f"    <iconFilename>{icon}</iconFilename>\n"
        '    <multiplayer supported="true"/>'
        f"{dep}{maps}\n</modDesc>\n"
    )


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)
    return buf.getvalue()


# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------

def catalog() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for vid, (prefix, _desc, count, nmaps, _dlc) in VERSIONS.items():
        rnd = random.Random(f"fspassion-demo-{vid}")
        mods: list[dict] = []
        used: set[str] = set()
        kinds = list(KINDS)
        for i in range(count):
            kind = kinds[i % len(kinds)]
            brand = rnd.choice(BRANDS)
            model = f"{rnd.choice('ABCDEFHKMRSTVX')}{rnd.randint(1, 9)}{rnd.choice(['00', '20', '50', '80'])}"
            key = f"{brand}{KINDS[kind][1]}{model}"
            if key.lower() in used:
                continue
            used.add(key.lower())
            fr, en, de = KINDS[kind]
            mods.append({
                "id": f"{prefix}{key}", "kind": kind, "category": "mod",
                "titles": {"en": f"{brand} {model} {en}", "fr": f"{fr} {brand} {model}", "de": f"{brand} {model} {de}"},
                "author": f"{rnd.choice(['Atelier', 'Studio', 'Team'])} {rnd.choice(BRANDS)}",
                "version": f"1.{rnd.randint(0, 4)}.{rnd.randint(0, 9)}.0", "dependencies": [],
            })
        # Quelques scripts dépendent d'une bibliothèque commune.
        lib_id = f"{prefix}DemoScriptLibrary"
        mods.append({"id": lib_id, "kind": "script", "category": "mod",
                     "titles": {"en": "Demo Script Library", "fr": "Bibliothèque de scripts (démo)", "de": "Demo-Skriptbibliothek"},
                     "author": "Team FS Passion", "version": "2.0.0.0", "dependencies": []})
        for m in mods:
            if m["kind"] == "script" and m["id"] != lib_id:
                m["dependencies"] = [lib_id]
        plain = [m["id"] for m in mods if m["kind"] in ("tractor", "trailer", "harvester", "tool")]
        for j, (key, en, fr, de) in enumerate(MAPS[:nmaps]):
            deps = rnd.sample(plain, 3) + [lib_id]
            if j == 0:
                deps.append(f"{prefix}DemoMissingPack")  # dépendance absente, pour la montrer
                if vid == "FS25":
                    deps.append("pdlc_highlandsFishingPack")
            mods.insert(0, {"id": f"{prefix}{key}", "kind": "map", "category": "map",
                            "titles": {"en": en, "fr": fr, "de": de}, "author": "Team FS Passion",
                            "version": f"1.{j}.0.0", "dependencies": deps})
        out[vid] = mods
    return out


GAMESETTINGS = (
    '<?xml version="1.0" encoding="utf-8" standalone="no" ?>\n<gameSettings revision="15">\n'
    '    <modsDirectoryOverride active="false" directory="C:/Temp"/>\n'
    "    <!-- FS Passion : fichier de démonstration, il n'appartient à aucun jeu. -->\n"
    "</gameSettings>\n"
)


def build(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cat = catalog()
    files: dict[str, bytes] = {}
    manifest = {"schema": SCHEMA, "name": "FS Passion — pack de démonstration", "versions": {}}
    for vid, mods in cat.items():
        prefix, desc, _count, _maps, dlc = VERSIONS[vid]
        manifest["versions"][vid] = {"mods_dir": f"{vid}/Mods", "user_dir": f"{vid}/Documents",
                                     "mods": [{k: v for k, v in m.items()} for m in mods]}
        for m in mods:
            icon_name = "icon_" + m["id"][len(prefix):] + ".dds"
            seed = int(hashlib.sha1(m["id"].encode()).hexdigest()[:8], 16)
            xml = moddesc(desc, m["titles"], m["author"], m["version"], icon_name, m["dependencies"],
                          m["kind"] == "map", m["id"][len(prefix):])
            content = {
                "modDesc.xml": xml.encode("utf-8"),
                icon_name: make_icon(m["kind"], seed),
                "scripts/demo.lua": b"-- FS Passion : mod de demonstration, sans effet.\n",
            }
            files[f"{vid}/Mods/{m['id']}.zip"] = _zip_bytes(content)
        # Un mod non compressé (dossier) et une anomalie (.rar), pour les montrer.
        dev = f"{vid}/Mods/{prefix}DemoWorkInProgress"
        files[f"{dev}/modDesc.xml"] = moddesc(desc, {"en": "Work in progress (unpacked)", "fr": "Mod en cours (non compressé)",
                                                     "de": "In Arbeit (entpackt)"}, "Team FS Passion", "0.1.0.0",
                                              "icon.dds", [], False).encode("utf-8")
        files[f"{dev}/icon.dds"] = make_icon("script", 4242)
        files[f"{vid}/Mods/DemoArchive.rar"] = b"Rar!\x1a\x07\x00 FS Passion demo"
        files[f"{vid}/Documents/gameSettings.xml"] = GAMESETTINGS.encode("utf-8")
        for name in dlc:
            files[f"{vid}/Documents/pdlc/{name}.dlc"] = b""
    files["demo.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    files["LISEZMOI.txt"] = (
        "Pack de démonstration de FS Passion.\r\n\r\n"
        "Tous les mods de ce pack sont fictifs : ils ne fonctionnent pas dans le jeu.\r\n"
        "Ils servent à essayer FS Passion sans posséder Farming Simulator.\r\n"
    ).encode()
    pack = out_dir / PACK
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_STORED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            # Les .zip et les .dds se compressent mal : stockés tels quels.
            info.compress_type = zipfile.ZIP_STORED if name.endswith(".zip") else zipfile.ZIP_DEFLATED
            zf.writestr(info, files[name])
    digest = hashlib.sha256(pack.read_bytes()).hexdigest()
    (out_dir / f"{PACK}.sha256").write_text(f"{digest}  {PACK}\n", encoding="ascii")
    return pack


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    p = build(target)
    print(f"{p} ({p.stat().st_size / 1024 / 1024:.1f} Mo)")
