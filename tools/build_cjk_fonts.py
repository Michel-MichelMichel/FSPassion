"""Polices chinoises, japonaises et coréennes de l'interface.

    python tools/build_cjk_fonts.py [dossier-des-sources]

Iosevka Etoile Compact n'a pas de caractères CJK. Ce script fabrique, à partir
de Sarasa Gothic (https://github.com/be5invis/Sarasa-Gothic), quatre polices
réduites au seul jeu de caractères utile :

    assets/fonts/FSPassionCJK-J.woff2    japonais
    assets/fonts/FSPassionCJK-K.woff2    coréen
    assets/fonts/FSPassionCJK-SC.woff2   chinois simplifié
    assets/fonts/FSPassionCJK-TC.woff2   chinois traditionnel

Sources : les fichiers SarasaGothicJ/K/SC/TC-Regular.ttf (archives
« SarasaGothicJ-TTF-Unhinted-<version>.7z », etc., de la page Releases de
Sarasa Gothic), posés tels quels ou encore dans leurs archives .7z dans le
dossier fonts-src/sarasa/ (ignoré par Git), ou dans le dossier indiqué.

Jeu de caractères de chaque police :
- un socle commun pour que les futures traductions s'affichent sans retoucher
  la police : ponctuation CJK, formes pleine chasse, et selon la langue les
  kana et les kanji du niveau 1 de JIS X 0208 (japonais), les 2 350 syllabes
  hangûl de KS X 1001 (coréen), les 3 755 caractères du niveau 1 de GB 2312
  (chinois simplifié), les 5 401 caractères courants de Big5 (chinois
  traditionnel) ;
- plus tous les caractères des fichiers lang/ja.json, lang/ko.json,
  lang/zh-Hans.json et lang/zh-Hant.json quand ils existent : relancer le
  script après l'ajout ou la modification d'une de ces traductions (le test
  tests/test_v094.py vérifie qu'aucun caractère ne manque).

Les glyphes CJK de Sarasa viennent de Source Han Sans, dont la licence SIL OFL
réserve le nom « Source » : les polices réduites sont des versions modifiées
et portent donc un autre nom, « FS Passion CJK J » (etc.). Licence :
assets/fonts/OFL-Sarasa.txt.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "fonts-src" / "sarasa"
OUT = ROOT / "assets" / "fonts"

# Variante Sarasa → (fichier produit, langue de l'interface, nom de famille)
VARIANTS = {
    "J": ("FSPassionCJK-J.woff2", "ja", "FS Passion CJK J"),
    "K": ("FSPassionCJK-K.woff2", "ko", "FS Passion CJK K"),
    "SC": ("FSPassionCJK-SC.woff2", "zh-Hans", "FS Passion CJK SC"),
    "TC": ("FSPassionCJK-TC.woff2", "zh-Hant", "FS Passion CJK TC"),
}

# Caractères communs : ponctuation et symboles CJK, formes pleine et demi-chasse.
COMMON = [*range(0x3000, 0x3040), *range(0xFF01, 0xFF61), 0x30FB, 0x30FC, 0x2026, 0x2025, 0x00B7]


def _decode_rows(codec: str, lead: range, trail: range) -> set[int]:
    """Caractères d'un jeu codé sur deux octets, rangées « lead » × « trail »."""
    chars: set[int] = set()
    for a in lead:
        for b in trail:
            try:
                text = bytes((a, b)).decode(codec)
            except UnicodeDecodeError:
                continue
            if len(text) == 1:
                chars.add(ord(text))
    return chars


def base_charset(variant: str) -> set[int]:
    chars = set(COMMON)
    if variant == "J":
        chars |= set(range(0x3041, 0x3097)) | set(range(0x309B, 0x30FF)) | set(range(0x31F0, 0x3200))
        chars |= _decode_rows("euc_jp", range(0xB0, 0xD0), range(0xA1, 0xFF))  # JIS X 0208 niveau 1
        chars |= _decode_rows("euc_jp", range(0xA1, 0xA9), range(0xA1, 0xFF))  # symboles, kana
    elif variant == "K":
        chars |= _decode_rows("euc_kr", range(0xB0, 0xC9), range(0xA1, 0xFF))  # hangûl KS X 1001
        chars |= _decode_rows("euc_kr", range(0xA1, 0xA5), range(0xA1, 0xFF))  # symboles, jamos
    elif variant == "SC":
        chars |= _decode_rows("gb2312", range(0xB0, 0xD8), range(0xA1, 0xFF))  # GB 2312 niveau 1
        chars |= _decode_rows("gb2312", range(0xA1, 0xA4), range(0xA1, 0xFF))  # symboles
    elif variant == "TC":
        chars |= _decode_rows("big5", range(0xA4, 0xC7), range(0x40, 0xFF))  # Big5 courants
        chars |= _decode_rows("big5", range(0xA1, 0xA4), range(0x40, 0xFF))  # symboles
    return chars


def text_charset(lang: str) -> set[int]:
    """Caractères non latins des textes de cette langue (lang/<langue>.json)."""
    path = ROOT / "lang" / f"{lang}.json"
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    return {ord(c) for c in text if ord(c) >= 0x2E80}


def charset(variant: str) -> set[int]:
    return base_charset(variant) | text_charset(VARIANTS[variant][1])


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _inside(name: str) -> bool:
    """Chemin d'une entrée d'archive resté sous le dossier d'extraction."""
    path = Path(name)
    return not path.is_absolute() and ".." not in path.parts and not re.match(r"^[A-Za-z]:", name)


def find_source(folder: Path, variant: str, work: Path) -> Path:
    """Fichier SarasaGothic<variante>-Regular.ttf, extrait de son .7z au besoin."""
    wanted = f"sarasagothic{variant.lower()}regularttf"
    for path in folder.rglob("*.ttf"):
        if _norm(path.name) == wanted:
            return path
    for archive in sorted(folder.rglob("*.7z")):
        import py7zr  # seulement quand une archive doit être ouverte

        with py7zr.SevenZipFile(archive) as z:
            names = [n for n in z.getnames() if _inside(n) and _norm(Path(n).name) == wanted]
            if names:
                z.extract(path=work, targets=names)
                return work / names[0]
    raise SystemExit(f"Introuvable : SarasaGothic{variant}-Regular.ttf dans {folder}")


def rename(font: TTFont, family: str, version: str) -> None:
    """Nouveau nom (licence OFL : nom réservé « Source ») ; anciens noms retirés."""
    postscript = family.replace(" ", "")
    names = {
        1: family,
        2: "Regular",
        3: f"{postscript}-Regular;{version}",
        4: family,
        5: f"Version {version}; subset of Sarasa Gothic for FS Passion",
        6: f"{postscript}-Regular",
    }
    table = font["name"]
    table.names = [n for n in table.names if n.nameID not in (1, 2, 3, 4, 5, 6, 16, 17, 18, 21, 22, 25)]
    for name_id, value in names.items():
        table.setName(value, name_id, 3, 1, 0x409)
        table.setName(value, name_id, 1, 0, 0)
    if "CFF " in font:
        font["CFF "].cff.fontNames = [f"{postscript}-Regular"]


def build(variant: str, source: Path) -> Path:
    filename, _lang, family = VARIANTS[variant]
    font = TTFont(source, fontNumber=0)
    version = font["name"].getDebugName(5) or ""
    version = re.sub(r"^Version\s*", "", version).split(";")[0].strip() or "0"
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.hinting = False
    options.notdef_outline = True
    sub = subset.Subsetter(options)
    sub.populate(unicodes=charset(variant))
    sub.subset(font)
    rename(font, family, version)
    out = OUT / filename
    font.flavor = "woff2"
    font.save(out)
    return out


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCES
    with tempfile.TemporaryDirectory() as tmp:
        for variant in VARIANTS:
            source = find_source(folder, variant, Path(tmp))
            out = build(variant, source)
            print(f"{out.relative_to(ROOT)} : {len(charset(variant))} caractères, {out.stat().st_size // 1024} Kio")


if __name__ == "__main__":
    main()
