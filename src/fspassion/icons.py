"""Conversion des icônes des mods.

- Source : DDS (décodé par Pillow : DXT1, DXT3, DXT5, BC7, non compressé) ou PNG.
- Fichiers WebP par icône : la grande, à la résolution d'origine (plafonnée à
  512 px) ; une moyenne de 300 px pour les tuiles de la liste 1, seulement pour
  FS25 et FS28 (les icônes des versions précédentes font au plus
  256 px, la grande sert donc directement) ; une petite de 96 px pour les
  listes 2 et 3.
- Noms : <identifiant>-<taille>-<date>.webp, …-medium.webp et …-small.webp.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image, ImageOps

from fspassion import fsutil

log = logging.getLogger(__name__)

SMALL_SIZE = 96
MEDIUM_SIZE = 300        # tuiles de la liste 1 (écrans à 100 %)
BIG_SIZE = 512           # plafond de la grande variante (écrans à 125 % et plus)
# Versions dont les icônes dépassent 300 px (512 ou 1024 px) : elles seules ont
# la variante moyenne. Avant FS25, les icônes d'origine font 256 px au plus.
MEDIUM_VERSIONS = frozenset({"FS25", "FS28"})
# Suffixe du nom de base : le changer force la reconversion du cache.
ICON_CACHE_FORMAT = "r512"
WEBP_QUALITY = 92        # réglage visuellement sans perte
WEBP_QUALITY_SMALL = 90
WEBP_QUALITY_MEDIUM = 90

# Protection contre une image démesurée (fichier corrompu ou malveillant).
# Réglage global : il s'applique à toute utilisation de Pillow dans ce processus.
Image.MAX_IMAGE_PIXELS = 64 * 1024 * 1024


def icon_basename(mod_id: str, size: int, mtime: float) -> str:
    """Nom de base (sans extension) d'une icône en cache."""
    return f"{mod_id}-{size}-{int(mtime)}-{ICON_CACHE_FORMAT}"


def big_name(base: str) -> str:
    return f"{base}.webp"


def small_name(base: str) -> str:
    return f"{base}-small.webp"


def medium_name(base: str) -> str:
    return f"{base}-medium.webp"


def has_medium(vid: str) -> bool:
    """Vrai si la version a une variante moyenne (300 px) de ses icônes."""
    return vid in MEDIUM_VERSIONS


def icon_names(base: str, medium: bool = True) -> tuple[str, ...]:
    """Fichiers en cache d'une icône : grande, (moyenne), petite."""
    if medium:
        return (big_name(base), medium_name(base), small_name(base))
    return (big_name(base), small_name(base))


def _to_rgb_or_rgba(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        # Une icône entièrement opaque est enregistrée sans canal alpha (plus léger).
        alpha = img.getchannel("A")
        lo, _hi = alpha.getextrema()  # type: ignore[misc]
        if lo == 255:
            img = img.convert("RGB")
        return img
    return img.convert("RGB")


def convert_icon(data: bytes, dest_dir: Path, base: str, medium: bool = True) -> tuple[int, int]:
    """Décode une icône (DDS ou PNG) et enregistre ses variantes WebP (la
    moyenne seulement si « medium », voir MEDIUM_VERSIONS).

    Renvoie la taille d'origine (largeur, hauteur). Lève une exception en cas
    d'échec : l'appelant affiche alors l'icône par défaut et note l'erreur.
    """
    with Image.open(io.BytesIO(data)) as src:
        src.load()
        img = _to_rgb_or_rgba(src)
    width, height = img.size

    big = _fit(img, BIG_SIZE)
    buf = io.BytesIO()
    big.save(buf, "WEBP", quality=WEBP_QUALITY, method=4)
    fsutil.atomic_write_bytes(dest_dir / big_name(base), buf.getvalue())

    if medium:
        mid = _fit(img, MEDIUM_SIZE)
        buf = io.BytesIO()
        mid.save(buf, "WEBP", quality=WEBP_QUALITY_MEDIUM, method=4)
        fsutil.atomic_write_bytes(dest_dir / medium_name(base), buf.getvalue())

    small = ImageOps.contain(img, (SMALL_SIZE, SMALL_SIZE), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    small.save(buf, "WEBP", quality=WEBP_QUALITY_SMALL, method=4)
    fsutil.atomic_write_bytes(dest_dir / small_name(base), buf.getvalue())
    return width, height


def _fit(img: Image.Image, size: int) -> Image.Image:
    """Réduit à size × size (proportions gardées), sans agrandir une petite image."""
    if max(img.size) <= size:
        return img
    return ImageOps.contain(img, (size, size), Image.Resampling.LANCZOS)


def image_size(path: Path) -> tuple[int, int] | None:
    """Dimensions d'une image (lecture de l'en-tête seulement)."""
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:  # noqa: BLE001
        return None


def small_data_url(data: bytes, size: int = SMALL_SIZE) -> str | None:
    """Petite icône en adresse « data: » (fenêtre des téléchargements) :
    rien n'est écrit sur le disque pour un mod qui n'est pas encore intégré."""
    import base64

    try:
        with Image.open(io.BytesIO(data)) as src:
            src.load()
            img = _to_rgb_or_rgba(src)
        small = ImageOps.contain(img, (size, size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        small.save(buf, "WEBP", quality=WEBP_QUALITY_SMALL, method=4)
    except Exception as exc:  # noqa: BLE001
        log.debug("Icône de téléchargement illisible : %s", exc)
        return None
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
