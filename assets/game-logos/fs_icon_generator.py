#!/usr/bin/env python3
"""
Générateur d'icônes de version « Farming Simulator » — SVG 1024x1024, monochrome.

Toutes les couleurs utilisent `currentColor` : l'icône prend la couleur CSS `color`
de son parent (SVG inline) ou peut servir de masque (`mask-image`) colorisé par
`background-color`. Sans CSS, currentColor = noir.

Le texte est converti en tracés (pas de dépendance à la fonte dans le SVG).
L'inclinaison des bords gauche/droit de la forme est EXACTEMENT celle de
l'italique appliqué aux chiffres (même constante SLANT_DEG, même tan()).

Usage :
    python fs_icon_generator.py                       # génère 11..28 dans ./svg
    python fs_icon_generator.py 25 30 -o out          # versions au choix
    python fs_icon_generator.py --color "#ffffff"     # couleur figée (au lieu de currentColor)
    python fs_icon_generator.py --font chemin/vers/HelveticaLTStd-UltraComp.otf

Dépendance : fontTools  (pip install fonttools)
"""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

# --------------------------------------------------------------------------- #
# Paramètres du template
# --------------------------------------------------------------------------- #
SIZE = 1024                 # canevas carré (px)
SLANT_DEG = 10.0            # inclinaison commune : bords de la forme ET italique des chiffres
                            # (mesurée sur la référence FS25 : 10,07°)

SHAPE_H = 904               # hauteur du parallélogramme
SHAPE_W = 826               # largeur horizontale du parallélogramme (mesurée à hauteur constante)
CORNER_R = 112              # rayon des angles arrondis (extérieur) — bas-gauche reste pointu

BORDER = 38                 # bord fort plein (couleur du texte)
GLOW_W = 22                 # éclairage interne le long du contour (bande nette)
GLOW_OPACITY = 0.50
GLOW_SOFT_W = 40            # halo diffus qui prolonge la bande vers l'intérieur
GLOW_SOFT_OPACITY = 0.22

# Dégradé de remplissage (bas -> haut), en fraction de la hauteur intérieure
GRAD_STOPS = [              # (position depuis le BAS, opacité)
    (0.00, 0.00),
    (0.18, 0.00),           # « rien en bas »
    (1.00, 0.30),           # dégradé léger vers le haut
]

TEXT_HEIGHT_RATIO = 0.58    # hauteur des chiffres / hauteur de la forme
TRACKING = -18              # approche entre chiffres (unités de fonte, /1000 em)

DEFAULT_VERSIONS = ["11", "13", "15", "17", "19", "22", "25", "28"]
DEFAULT_FONT = "HelveticaLTStd-UltraComp.otf"

TAN = math.tan(math.radians(SLANT_DEG))


# --------------------------------------------------------------------------- #
# Géométrie
# --------------------------------------------------------------------------- #
def _sub(a, b): return (a[0] - b[0], a[1] - b[1])
def _add(a, b): return (a[0] + b[0], a[1] + b[1])
def _mul(a, k): return (a[0] * k, a[1] * k)
def _len(a): return math.hypot(*a)
def _norm(a):
    n = _len(a)
    return (a[0] / n, a[1] / n)


def parallelogram(inset: float = 0.0):
    """Sommets (SVG, y vers le bas) dans l'ordre : haut-gauche, haut-droit, bas-droit, bas-gauche.
    `inset` décale chaque côté de cette distance vers l'intérieur (offset perpendiculaire)."""
    cx, cy = 0.0, 0.0
    h = SHAPE_H / 2 - inset
    # décalage perpendiculaire d'un côté incliné -> décalage horizontal = inset / cos(angle)
    w = SHAPE_W / 2 - inset / math.cos(math.radians(SLANT_DEG))
    s = h * TAN
    return [
        (cx - w + s, cy - h),   # haut-gauche
        (cx + w + s, cy - h),   # haut-droit
        (cx + w - s, cy + h),   # bas-droit
        (cx - w - s, cy + h),   # bas-gauche (pointu)
    ]


def rounded_path(pts, radii) -> str:
    """Tracé SVG fermé, chaque sommet arrondi par un congé circulaire de rayon radii[i] (0 = pointu)."""
    n = len(pts)
    segs = []
    for i in range(n):
        p, prev, nxt = pts[i], pts[i - 1], pts[(i + 1) % n]
        r = radii[i]
        if r <= 0:
            segs.append(("pt", p))
            continue
        u1, u2 = _norm(_sub(prev, p)), _norm(_sub(nxt, p))
        theta = math.acos(max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1])))
        d = r / math.tan(theta / 2)
        a, b = _add(p, _mul(u1, d)), _add(p, _mul(u2, d))
        cross = u1[0] * u2[1] - u1[1] * u2[0]
        sweep = 0 if cross > 0 else 1
        segs.append(("arc", a, b, r, sweep))

    def start(seg): return seg[1]
    out = []
    first = segs[0]
    out.append(f"M{fmt(start(first))}")
    for i, seg in enumerate(segs):
        if seg[0] == "arc":
            _, a, b, r, sweep = seg
            if i != 0:
                out.append(f"L{fmt(a)}")
            out.append(f"A{r:.2f},{r:.2f} 0 0 {sweep} {fmt(b)}")
        else:
            if i != 0:
                out.append(f"L{fmt(seg[1])}")
    out.append("Z")
    return " ".join(out)


def fmt(p) -> str:
    return f"{p[0] + SIZE / 2:.2f},{p[1] + SIZE / 2:.2f}"


def shape_path(inset: float) -> str:
    r = max(CORNER_R - inset, 0.0)
    return rounded_path(parallelogram(inset), [r, r, r, 0.0])


# --------------------------------------------------------------------------- #
# Texte -> tracés (italique synthétique au même angle)
# --------------------------------------------------------------------------- #
def text_path(font: TTFont, text: str) -> str:
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    cap = font["OS/2"].sCapHeight or 718
    s = SHAPE_H * TEXT_HEIGHT_RATIO / cap

    def draw(pen_factory):
        x = 0.0
        for i, ch in enumerate(text):
            g = cmap[ord(ch)]
            # x' = s*(x + y*tan) ; y' = -s*y   (fonte y vers le haut -> SVG y vers le bas)
            gs[g].draw(TransformPen(pen_factory(), (s, 0, s * TAN, -s, s * x, 0)))
            x += hmtx[g][0] + (TRACKING if i < len(text) - 1 else 0)

    bp = BoundsPen(gs)
    draw(lambda: bp)
    xmin, ymin, xmax, ymax = bp.bounds
    # centrage optique : centre de la boîte englobante sur le centre de la forme
    dx = SIZE / 2 - (xmin + xmax) / 2
    dy = SIZE / 2 - (ymin + ymax) / 2

    sp = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}")
    x = 0.0
    for i, ch in enumerate(text):
        g = cmap[ord(ch)]
        gs[g].draw(TransformPen(sp, (s, 0, s * TAN, -s, s * x + dx, dy)))
        x += hmtx[g][0] + (TRACKING if i < len(text) - 1 else 0)
    return sp.getCommands()


# --------------------------------------------------------------------------- #
# Assemblage SVG
# --------------------------------------------------------------------------- #
def build_svg(font: TTFont, label: str, color: str = "currentColor") -> str:
    outer = shape_path(0)
    inner = shape_path(BORDER)
    glow_in = shape_path(BORDER + GLOW_W)
    soft_in = shape_path(BORDER + GLOW_W + GLOW_SOFT_W)

    top = SIZE / 2 - (SHAPE_H / 2 - BORDER)
    bottom = SIZE / 2 + (SHAPE_H / 2 - BORDER)
    stops = "\n      ".join(
        f'<stop offset="{p:.2f}" stop-color="{color}" stop-opacity="{o:.2f}"/>'
        for p, o in GRAD_STOPS
    )
    uid = f"fs{label}"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}" role="img" aria-label="Farming Simulator {label}">
  <title>Farming Simulator {label}</title>
  <defs>
    <linearGradient id="{uid}-grad" gradientUnits="userSpaceOnUse" x1="0" y1="{bottom:.2f}" x2="0" y2="{top:.2f}">
      {stops}
    </linearGradient>
    <filter id="{uid}-blur" x="-10%" y="-10%" width="120%" height="120%">
      <feGaussianBlur stdDeviation="{GLOW_SOFT_W / 2.5:.1f}"/>
    </filter>
    <clipPath id="{uid}-clip"><path d="{glow_in}"/></clipPath>
  </defs>
  <g fill="{color}">
    <!-- 1. remplissage : dégradé léger, rien en bas -->
    <path d="{inner}" fill="url(#{uid}-grad)"/>
    <!-- 2. éclairage interne le long du contour : halo diffus -->
    <g clip-path="url(#{uid}-clip)">
      <path d="{glow_in} {soft_in}" fill-rule="evenodd" opacity="{GLOW_SOFT_OPACITY}" filter="url(#{uid}-blur)"/>
    </g>
    <!-- 3. éclairage interne : bande nette -->
    <path d="{inner} {glow_in}" fill-rule="evenodd" opacity="{GLOW_OPACITY}"/>
    <!-- 4. bord fort (couleur du texte) -->
    <path d="{outer} {inner}" fill-rule="evenodd"/>
    <!-- 5. chiffres : HelveticaLTStd-UltraComp, italique {SLANT_DEG:g}° -->
    <path d="{text_path(font, label)}"/>
  </g>
</svg>
'''


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Générateur d'icônes de version Farming Simulator (SVG)")
    ap.add_argument("versions", nargs="*", default=DEFAULT_VERSIONS)
    ap.add_argument("-o", "--out", default=str(here / "svg"))
    ap.add_argument("--font", default=str(here / DEFAULT_FONT))
    ap.add_argument("--color", default="currentColor",
                    help="currentColor (défaut, recolorable en CSS), ou couleur figée ex. #ffffff")
    ap.add_argument("--prefix", default="fs")
    args = ap.parse_args()

    font = TTFont(args.font)
    os.makedirs(args.out, exist_ok=True)
    for v in args.versions:
        path = Path(args.out) / f"{args.prefix}{v}.svg"
        path.write_text(build_svg(font, v, args.color), encoding="utf-8")
        print("✔", path)


if __name__ == "__main__":
    main()
