// Défilement « par blocs » à la molette (0.3) : un cran de molette fait
// glisser la zone jusqu'au bloc suivant (ou précédent), avec la même animation
// que la liste 1 (170 ms, décélération). Utilisé par les Paramètres : un cran
// = une section entière.
//
// Un bloc plus haut que la zone visible n'est jamais sauté : on y avance alors
// d'une hauteur de zone à la fois.

import { reduceMotionActive } from './theme.js';

const MS = 170;

export function snapWheel(scroller, getSnaps) {
  let raf = 0;
  let target = null;
  let from = 0;
  let start = 0;
  let acc = 0;
  let last = 0;

  const stop = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    target = null;
  };

  const step = () => {
    raf = 0;
    if (target === null) return;
    const k0 = Math.min(1, Math.max(0, (performance.now() - start) / MS));
    const k = 1 - (1 - k0) ** 3;
    scroller.scrollTop = from + (target - from) * k;
    if (k0 < 1) raf = requestAnimationFrame(step);
    else target = null;
  };

  const go = (to) => {
    from = scroller.scrollTop;
    target = to;
    start = performance.now();
    if (reduceMotionActive()) {
      stop();
      scroller.scrollTop = to;
      return;
    }
    if (!raf) raf = requestAnimationFrame(step);
  };

  const onWheel = (e) => {
    if (e.ctrlKey) return;
    // 0.7.4 : une liste ouverte par-dessus (langues) défile elle-même.
    if (e.target instanceof Element && e.target.closest('[data-own-scroll]')) return;
    const unit = e.deltaMode === 1 ? 40 : e.deltaMode === 2 ? scroller.clientHeight : 1;
    const dy = e.deltaY * unit;
    if (!dy || Math.abs(e.deltaX) > Math.abs(dy)) return;
    const max = Math.max(0, scroller.scrollHeight - scroller.clientHeight);
    if (max <= 0) return;
    e.preventDefault();
    const now = performance.now();
    if (now - last > 220) acc = 0;
    last = now;
    let dir = 0;
    if (Math.abs(dy) >= 50) {
      dir = Math.sign(dy); // un cran de molette
    } else {
      // Pavé tactile ou molette fine : les petits mouvements s'additionnent.
      acc += dy;
      if (Math.abs(acc) >= 100) {
        dir = Math.sign(acc);
        acc = 0;
      }
    }
    if (!dir) return;
    const snaps = getSnaps().filter((p) => Number.isFinite(p)).sort((a, b) => a - b);
    const page = Math.max(80, scroller.clientHeight - 60);
    const base = target ?? scroller.scrollTop;
    let to;
    if (dir > 0) {
      to = snaps.find((p) => p > base + 2);
      if (to === undefined) to = max;
      if (to - base > page) to = base + page; // bloc très haut : pas de saut
    } else {
      to = 0;
      for (const p of snaps) {
        if (p < base - 2) to = p;
        else break;
      }
      if (base - to > page) to = base - page;
    }
    go(Math.max(0, Math.min(max, to)));
  };

  scroller.addEventListener('wheel', onWheel, { passive: false });
  // Barre de défilement ou clavier : l'animation en cours s'arrête.
  scroller.addEventListener('pointerdown', stop);
  scroller.addEventListener('keydown', stop);
  return () => {
    stop();
    scroller.removeEventListener('wheel', onWheel);
  };
}
