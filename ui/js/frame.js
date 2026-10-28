// Fenêtre sans barre de titre (5.1) : boutons Réduire / Agrandir / Fermer,
// déplacement par l'en-tête, double-clic pour agrandir, redimensionnement par
// des zones de saisie invisibles sur les quatre bords et les quatre coins.

import { api, shell } from './api.js';
import { h, icon } from './dom.js';
import { uiScale } from './scale.js';
import { store } from './state.js';

const EDGES = ['top', 'bottom', 'left', 'right', 'top-left', 'top-right', 'bottom-left', 'bottom-right'];
let maximized = false;
let controls = null;

export function inWindow() {
  return shell === 'window';
}

function mode() {
  return (store.app && store.app.app.window_mode) || 'native';
}

async function refreshMaximized() {
  try {
    const r = await api.post('/api/window', { action: 'rect' });
    setMaximized(!!r.maximized);
  } catch {
    /* fenêtre indisponible */
  }
}

function setMaximized(v) {
  maximized = v;
  document.documentElement.classList.toggle('is-maximized', v);
  if (controls) {
    const btn = controls.querySelector('[data-act="max"]');
    btn.replaceChildren(icon(v ? 'copy' : 'square'));
    btn.dataset.i18nTip = v ? 'window.restore' : 'window.maximize';
  }
}

export async function toggleMaximize() {
  try {
    const r = await api.post('/api/window', { action: 'toggle-maximize' });
    setMaximized(!!r.maximized);
  } catch {
    /* ignoré */
  }
}

// Boutons de fenêtre, collés à l'angle haut-droit et posés au-dessus de tout
// (y compris des paramètres et de la notice). Ils apparaissent dès que la
// souris entre dans la bande de l'en-tête, même quand une fenêtre interne la
// recouvre : la position de la souris est comparée à la hauteur de l'en-tête.
export function mountWindowControls(app, topbar) {
  controls = h('div', { class: 'win-controls' },
    h('button', { class: 'win-btn', type: 'button', 'data-act': 'min', 'data-i18n-tip': 'window.minimize',
      onclick: () => api.post('/api/window', { action: 'minimize' }).catch(() => {}) }, icon('minus')),
    h('button', { class: 'win-btn', type: 'button', 'data-act': 'max', 'data-i18n-tip': maximized ? 'window.restore' : 'window.maximize',
      onclick: toggleMaximize }, icon(maximized ? 'copy' : 'square')),
    h('button', { class: 'win-btn win-close', type: 'button', 'data-act': 'close', 'data-i18n-tip': 'window.close',
      onclick: () => api.post('/api/window', { action: 'close' }).catch(() => {}) }, icon('window-close')),
  );
  if (!inWindow()) {
    controls.hidden = true;
    return controls;
  }
  app.append(controls);
  let near = false;
  const setNear = (v) => {
    if (v === near) return;
    near = v;
    controls.classList.toggle('is-near', v);
  };
  document.addEventListener('pointermove', (e) => {
    const band = topbar ? topbar.offsetHeight : 138;
    setNear(e.clientY / uiScale() <= band);
  }, { passive: true });
  document.documentElement.addEventListener('pointerleave', () => setNear(false));
  window.addEventListener('blur', () => setNear(false));
  return controls;
}

// Déplacement par l'en-tête : la fenêtre ne bouge qu'après quelques pixels,
// pour laisser passer le double-clic.
export function makeDragZone(el) {
  if (!inWindow()) return;
  const isFree = (target) => !target.closest('button, input, select, textarea, a, [role="listbox"], [role="menu"], .no-drag');
  // 0.8.4 : une barre de défilement (notice) reste une barre de défilement.
  const onScrollbar = (e) => {
    const t = e.target;
    return t instanceof HTMLElement && t.clientWidth && e.offsetX >= t.clientWidth && t.scrollHeight > t.clientHeight;
  };
  let start = null;
  el.addEventListener('pointerdown', (e) => {
    if (e.button !== 0 || !isFree(e.target) || onScrollbar(e)) return;
    start = { x: e.screenX, y: e.screenY };
  });
  el.addEventListener('pointermove', (e) => {
    if (!start || !(e.buttons & 1)) {
      start = null;
      return;
    }
    if (Math.abs(e.screenX - start.x) + Math.abs(e.screenY - start.y) > 4) {
      start = null;
      api.post('/api/window', { action: 'drag', edge: 'move' }).catch(() => {});
    }
  });
  el.addEventListener('pointerup', () => { start = null; });
  el.addEventListener('dblclick', (e) => {
    if (isFree(e.target)) toggleMaximize();
  });
}

export function buildEdges(app) {
  if (!inWindow()) return;
  const wrap = h('div', { class: 'frame-edges', 'aria-hidden': 'true' });
  for (const edge of EDGES) {
    const zone = h('div', { class: `edge edge-${edge}`, dataset: { edge } });
    zone.addEventListener('pointerdown', (e) => onEdgeDown(e, edge, zone));
    wrap.append(zone);
  }
  app.append(wrap);
  refreshMaximized();
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(refreshMaximized, 250);
  });
}
let resizeTimer = 0;

async function onEdgeDown(e, edge, zone) {
  if (e.button !== 0 || maximized) return;
  e.preventDefault();
  if (mode() !== 'script') {
    api.post('/api/window', { action: 'drag', edge }).catch(() => {});
    return;
  }
  // Technique « script » : la taille est calculée ici, puis transmise au cœur.
  zone.setPointerCapture(e.pointerId);
  let rect;
  try {
    rect = (await api.post('/api/window', { action: 'rect' })).rect;
  } catch {
    return;
  }
  if (!rect) return;
  const dpr = window.devicePixelRatio || 1;
  const sx = e.screenX;
  const sy = e.screenY;
  const minW = 960 * (rect.dpi / 96); // 0.7.2 : 1280 → 960 (comme app.py, MIN_WINDOW)
  const minH = 720 * (rect.dpi / 96);
  let pending = null;
  let busy = false;
  const send = async () => {
    if (busy || !pending) return;
    busy = true;
    const r = pending;
    pending = null;
    try {
      await api.post('/api/window', { action: 'set-rect', ...r });
    } catch {
      /* ignoré */
    }
    busy = false;
    if (pending) send();
  };
  const move = (ev) => {
    const dx = (ev.screenX - sx) * dpr;
    const dy = (ev.screenY - sy) * dpr;
    let { x, y, width, height } = rect;
    if (edge.includes('right')) width = Math.max(minW, rect.width + dx);
    if (edge.includes('bottom')) height = Math.max(minH, rect.height + dy);
    if (edge.includes('left')) {
      width = Math.max(minW, rect.width - dx);
      x = rect.x + rect.width - width;
    }
    if (edge.includes('top')) {
      height = Math.max(minH, rect.height - dy);
      y = rect.y + rect.height - height;
    }
    pending = { x: Math.round(x), y: Math.round(y), width: Math.round(width), height: Math.round(height) };
    send();
  };
  const up = () => {
    zone.removeEventListener('pointermove', move);
    zone.removeEventListener('pointerup', up);
    zone.removeEventListener('pointercancel', up);
  };
  zone.addEventListener('pointermove', move);
  zone.addEventListener('pointerup', up);
  zone.addEventListener('pointercancel', up);
}
