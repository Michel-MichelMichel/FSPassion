"""Générateur de faux mods pour les tests automatiques (aucun contenu GIANTS).

Les icônes sont des images abstraites générées (dégradés et formes), au format
DDS (DXT1/DXT5) ou PNG, comme dans les vrais mods.
"""

from __future__ import annotations

import io
import random
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

WORDS = [
    "Hof", "Berg", "Mann", "Field", "Farm", "Agri", "Tractor", "Trailer", "Plow", "Seeder",
    "Silo", "Barn", "Cow", "Sheep", "Grain", "Corn", "Wheat", "Mower", "Baler", "Tedder",
    "Harrow", "Cultivator", "Loader", "Pallet", "Shed", "Garage", "Fence", "Light", "Road",
    "Valley", "River", "Hill", "Forest", "Meadow", "Stone", "North", "South", "Alpine",
    "Classic", "Heavy", "Pack", "Series", "Pro", "Max", "Ultra", "Twin", "Mega", "Mini",
]


def make_icon(seed: int, size: int = 256, fmt: str = "png") -> bytes:
    """Icône abstraite déterministe (dégradé + formes)."""
    rnd = random.Random(seed)
    c1 = tuple(rnd.randint(30, 230) for _ in range(3))
    c2 = tuple(rnd.randint(30, 230) for _ in range(3))
    img = Image.new("RGB", (size, size), c1)
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / size
        col = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
        draw.line([(0, y), (size, y)], fill=col)
    for _ in range(rnd.randint(2, 5)):
        x0, y0 = rnd.randint(0, size), rnd.randint(0, size)
        r = rnd.randint(size // 10, size // 3)
        fill = tuple(rnd.randint(0, 255) for _ in range(3))
        if rnd.random() < 0.5:
            draw.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=fill)
        else:
            draw.rectangle([x0 - r, y0 - r // 2, x0 + r, y0 + r // 2], fill=fill)
    buf = io.BytesIO()
    if fmt == "dds":
        img.save(buf, "DDS", pixel_format="DXT1")
    else:
        img.save(buf, "PNG")
    return buf.getvalue()


def moddesc_xml(
    title: str,
    desc_version: int | str | None = 96,
    version: str = "1.0.0.0",
    author: str = "Test",
    icon: str = "icon.dds",
    is_map: bool = False,
    deps: list[str] | None = None,
    extra_titles: dict[str, str] | None = None,
) -> str:
    titles = {"en": title}
    titles.update(extra_titles or {})
    t = "".join(f"<{k}>{v}</{k}>" for k, v in titles.items())
    dv = f' descVersion="{desc_version}"' if desc_version is not None else ""
    dep = ""
    if deps:
        dep = "<dependencies>" + "".join(f"<dependency>{d}</dependency>" for d in deps) + "</dependencies>"
    maps = ""
    if is_map:
        maps = f'<maps><map id="m" configFilename="maps/map.xml"><title><en>{title}</en></title></map></maps>'
    return (
        '<?xml version="1.0" encoding="utf-8" standalone="no" ?>\n'
        f"<modDesc{dv}><author>{author}</author><version>{version}</version>"
        f"<title>{t}</title><iconFilename>{icon}</iconFilename>"
        f'<multiplayer supported="true"/>{dep}{maps}</modDesc>'
    )


def write_zip(path: Path, files: dict[str, bytes | str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data if isinstance(data, bytes) else data.encode("utf-8"))
    return path


def make_zip_mod(folder: Path, mod_id: str, title: str | None = None, seed: int = 0,
                 icon_fmt: str = "dds", icon_size: int = 256, **kw: object) -> Path:
    icon_name = "icon_" + mod_id.split("_", 1)[-1] + (".dds" if icon_fmt == "dds" else ".png")
    # Le modDesc déclare souvent .png alors que l'archive contient .dds.
    declared = icon_name.replace(".dds", ".png") if icon_fmt == "dds" and seed % 2 else icon_name
    files: dict[str, bytes | str] = {
        "modDesc.xml": moddesc_xml(title or mod_id, icon=declared, **kw),  # type: ignore[arg-type]
        icon_name: make_icon(seed, icon_size, icon_fmt),
        "scripts/main.lua": "-- test",
    }
    return write_zip(folder / f"{mod_id}.zip", files)


def make_dir_mod(folder: Path, mod_id: str, title: str | None = None, seed: int = 0, **kw: object) -> Path:
    d = folder / mod_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "modDesc.xml").write_text(moddesc_xml(title or mod_id, icon="icon.png", **kw), encoding="utf-8")  # type: ignore[arg-type]
    (d / "icon.png").write_bytes(make_icon(seed, 256, "png"))
    return d


def make_collection(mods_dir: Path, count: int = 60, seed: int = 1, prefix: str = "FS25_") -> dict[str, list[str]]:
    """Collection variée : mods, maps avec dépendances, mod non compressé, anomalies."""
    rnd = random.Random(seed)
    mods_dir.mkdir(parents=True, exist_ok=True)
    ids: list[str] = []
    for i in range(count):
        name = "".join(rnd.sample(WORDS, rnd.randint(1, 3)))
        mod_id = f"{prefix}{name}{i}"
        ids.append(mod_id)
        make_zip_mod(mods_dir, mod_id, title=f"{name} {i}", seed=i, icon_fmt="dds" if i % 3 else "png",
                     desc_version=rnd.randint(90, 114), version=f"1.{i % 4}.0.0", author=f"Auteur {i % 7}")
    maps = []
    for j in range(3):
        mod_id = f"{prefix}Map{WORDS[j * 5]}"
        deps = rnd.sample(ids, 3) + [f"{prefix}Absent{j}", "pdlc_vredoPack"]
        make_zip_mod(mods_dir, mod_id, title=f"Map {WORDS[j * 5]}", seed=1000 + j, is_map=True,
                     deps=deps, extra_titles={"fr": f"Carte {WORDS[j * 5]}", "de": f"Karte {WORDS[j * 5]}"})
        maps.append(mod_id)
    make_dir_mod(mods_dir, f"{prefix}DevMod", title="Mod en développement", seed=2000)
    # Anomalies
    (mods_dir / "pack.rar").write_bytes(b"Rar!")
    (mods_dir / "pack.7z").write_bytes(b"7z")
    write_zip(mods_dir / "FS25_ModPack.zip", {"readme.txt": "pack"})
    write_zip(mods_dir / "FS25_BadlyZipped.zip", {"FS25_BadlyZipped/modDesc.xml": moddesc_xml("x")})
    (mods_dir / "FS25_Broken.zip").write_bytes(b"PK\x03\x04 not a real zip")
    (mods_dir / "Dossier vide").mkdir(exist_ok=True)
    make_zip_mod(mods_dir, "FS25_Tracteur Rénové (1)", title="Tracteur", seed=3000)
    make_zip_mod(mods_dir, "FS22_OldTrailer", title="Old trailer", seed=3001, desc_version=72)
    (mods_dir / "notes.txt").write_text("notes")
    return {"ids": ids, "maps": maps}


def make_dlc(folder: Path, names: list[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for n in names:
        if n.endswith(".zip"):
            write_zip(folder / n, {"modDesc.xml": moddesc_xml(n[:-4].replace("_", " "))})
        else:
            (folder / n).write_bytes(b"\x00DLC")


# 0.8.0 : sous Windows, un lien symbolique demande le Mode développeur ou les
# droits administrateur. Sans eux, les tests du stockage sur plusieurs disques
# sont ignorés (et non en échec) : ils dépendent du PC, pas du code. Sur GitHub
# Actions (administrateur), ils tournent tous.
_SYMLINKS: bool | None = None


def symlinks_available() -> bool:
    global _SYMLINKS
    if _SYMLINKS is None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "cible"
            target.mkdir()
            try:
                os.symlink(target, Path(d) / "lien", target_is_directory=True)
                _SYMLINKS = True
            except OSError:
                _SYMLINKS = False
    return _SYMLINKS


def need_symlinks() -> None:
    import pytest

    if not symlinks_available():
        pytest.skip("liens symboliques refusés par Windows (ni Mode développeur, ni administrateur)")
