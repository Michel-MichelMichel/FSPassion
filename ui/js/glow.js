// Lueur qui court le long des contours (thèmes bicolores).
//
// Les listes 1, 2 et 3 et les fenêtres internes reçoivent un petit SVG posé
// sur leur contour : un segment lumineux (et sa traîne) en fait le tour, à
// vitesse constante quelle que soit la taille du cadre. Le trait fixe reste
// dessiné par la boîte elle-même (themes.css).
//
// Le SVG n'est visible qu'avec un thème bicolore et « Effets de lumière »
// actifs ; l'animation s'arrête avec « Réduire les animations » et quand la
// fenêtre n'est pas au premier plan (themes.css). Le coût est faible : un
// trait de quelques centaines de pixels par cadre, sans flou (pas de filtre).

// Les Paramètres ont leur propre contour animé (settings.js, drawFrame).
const SELECTOR = '.pane-all, .side-pane, .dlg:not(.dlg-settings)';
const SVG_NS = 'http://www.w3.org/2000/svg';
const SPEED = 150; // pixels par seconde
const RADIUS = 10; // coins des cadres (--r-xl)

let observer = null;
let resizer = null;
let seed = 0;

function ringFor(host) {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'glow-ring');
  svg.setAttribute('aria-hidden', 'true');
  // Halo large, halo, traîne, segment lumineux : des traits superposés, sans
  // filtre de flou (un flou sur tout le cadre serait recalculé à chaque image).
  for (const cls of ['glow-tail', 'glow-halo glow-halo-wide', 'glow-halo', 'glow-spark']) {
    const r = document.createElementNS(SVG_NS, 'rect');
    r.setAttribute('class', cls);
    svg.append(r);
  }
  // Départs décalés : deux cadres ne s'allument jamais au même endroit.
  seed = (seed + 0.37) % 1;
  host.style.setProperty('--glow-phase', String(seed));
  return svg;
}

function measure(host) {
  const w = host.offsetWidth;
  const h = host.offsetHeight;
  if (!w || !h) return;
  const r = Math.min(RADIUS, w / 2, h / 2);
  const len = Math.max(40, 2 * (w + h) - (8 - 2 * Math.PI) * r - 4);
  const dur = Math.max(6, len / SPEED);
  host.style.setProperty('--glow-len', `${len.toFixed(1)}px`);
  host.style.setProperty('--glow-d', `${dur.toFixed(2)}s`);
  const phase = Number(host.style.getPropertyValue('--glow-phase')) || 0;
  host.style.setProperty('--glow-delay', `${(-phase * dur).toFixed(2)}s`);
}

function attach(host) {
  if (!(host instanceof HTMLElement) || host.querySelector(':scope > .glow-ring')) return;
  host.append(ringFor(host));
  measure(host);
  resizer?.observe(host);
}

function scan(node) {
  if (!(node instanceof HTMLElement)) return;
  if (node.matches(SELECTOR)) attach(node);
  for (const el of node.querySelectorAll(SELECTOR)) attach(el);
}

export function initGlow(root = document.getElementById('app')) {
  if (!root || observer) return;
  resizer = new ResizeObserver((entries) => {
    for (const e of entries) measure(e.target);
  });
  scan(root);
  observer = new MutationObserver((records) => {
    for (const rec of records) {
      for (const n of rec.addedNodes) scan(n);
      // Un cadre dont le contenu est reconstruit perd son SVG : on le remet.
      if (rec.removedNodes.length && rec.target instanceof HTMLElement && rec.target.matches(SELECTOR)) attach(rec.target);
    }
  });
  observer.observe(root, { childList: true, subtree: true });
}
