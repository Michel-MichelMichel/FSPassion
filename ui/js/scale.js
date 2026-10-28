// Mise à l'échelle (5.1) : en dessous d'une taille minimale, la mise en page
// ne se réorganise plus ; toute l'interface est réduite d'un même facteur.
//
// 0.7.2 : largeur minimale abaissée de 1600 à 1140 px. Entre les deux, la
// mise en page s'adapte sans rien réduire :
// - la liste 1 garde au moins 2 colonnes de tuiles de 300 px
//   (36 + 680 + 16 + 380 + 24 = 1136 px, ascenseur compris) ;
// - l'en-tête passe sur 2 lignes (header.js, fitHeader) ;
// - les marges de la fenêtre Paramètres diminuent (dialogs.css).
// Si l'en-tête sur 2 lignes demande plus de place (mode démonstration, langue
// aux textes plus longs), il donne sa largeur minimale (setContentMinWidth),
// et la réduction commence plus tôt.

export const DESIGN_MIN_W = 1140;
export const DESIGN_MIN_H = 900;

const root = document.documentElement;
let scale = 1;
let contentMinW = 0;
let update = () => {};
const listeners = new Set();

export function uiScale() {
  return scale;
}

export function onScale(fn) {
  listeners.add(fn);
}

// Largeur minimale réclamée par le contenu (px de l'interface, avant réduction).
export function minWidth() {
  return Math.max(DESIGN_MIN_W, contentMinW);
}

export function setContentMinWidth(px) {
  const next = Math.ceil(Math.max(0, Number(px) || 0));
  if (next === contentMinW) return;
  contentMinW = next;
  update();
}

export function initScale(app) {
  update = () => {
    const w = window.innerWidth;
    const hgt = window.innerHeight;
    const s = Math.min(1, w / minWidth(), hgt / DESIGN_MIN_H);
    scale = Math.round(s * 1000) / 1000;
    root.style.setProperty('--ui-scale', String(scale));
    if (scale < 1) {
      app.style.width = `${w / scale}px`;
      app.style.height = `${hgt / scale}px`;
      app.style.transform = `scale(${scale})`;
    } else {
      app.style.width = '100%';
      app.style.height = '100%';
      app.style.transform = 'none';
    }
    for (const fn of listeners) fn(scale);
  };
  window.addEventListener('resize', update);
  update();
}

// Coordonnées de la souris dans le repère de l'interface (avant réduction).
export function toLocal(clientX, clientY) {
  return { x: clientX / scale, y: clientY / scale };
}

// Rectangle d'un élément dans le repère de l'interface.
export function localRect(el) {
  const r = el.getBoundingClientRect();
  return {
    left: r.left / scale, top: r.top / scale, right: r.right / scale, bottom: r.bottom / scale,
    width: r.width / scale, height: r.height / scale,
  };
}
