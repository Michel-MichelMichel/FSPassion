// Tour guidé (0.9.0) : l'ampoule de l'en-tête lance une visite de l'interface.
//
// - Toute l'interface s'assombrit ; un « puits de lumière » (un rectangle aux
//   coins arrondis entouré d'une ombre immense) se déplace d'un élément à
//   l'autre avec une animation douce.
// - À chaque étape : un titre court écrit « à la main » (police Caveat, lettre
//   par lettre), une explication, une flèche dessinée vers l'élément, et une
//   petite animation de démonstration avec de faux éléments (versions,
//   parties, mods) : l'interface d'un nouvel utilisateur est presque vide.
// - Une barre de commande en bas : Précédent (←), Rejouer (R), Suivant (→),
//   Quitter (Échap).
// - Premier lancement : après la bienvenue et la notice, l'ampoule est mise
//   en évidence une seule fois (réglage tour_hint_shown).
//
// 0.9.1 : deux étapes de plus (bouton des téléchargements ; croix de la
// fenêtre et zone de notification, avec un aperçu de la barre des tâches).
//
// Rien n'est modifié pendant le tour : les faux éléments sont dessinés
// par-dessus l'interface, qui ne reçoit ni clic ni touche.

import { api } from './api.js';
import { isDialogOpen } from './dialog.js';
import { clear, gameLogo, h, icon, reducedMotion } from './dom.js';
import { blocks, t } from './i18n.js';
import { localRect, onScale } from './scale.js';
import { activeVersion, store } from './state.js';

const NS = 'http://www.w3.org/2000/svg';
const CANCEL = Symbol('tour-cancel');
const WRITE_STEP = 34; // ms entre deux lettres du titre
const SPOT_PAD = 10;
const NOTE_GAP = 70; // distance entre la note et l'élément éclairé (place de la flèche)
const MARGIN = 22;

let app = null;
let root = null;
let els = {};
let mode = null; // 'tour' | 'hint' | null
let index = 0;
let run = null;
let resizeTimer = 0;
let lastFocus = null;

// ---------------------------------------------------------------------------
// API publique
// ---------------------------------------------------------------------------

export function initTour(appEl) {
  app = appEl;
  document.addEventListener('keydown', onKey, true);
  window.addEventListener('resize', scheduleRefresh);
  onScale(scheduleRefresh);
}

export function isTourOpen() {
  return mode !== null;
}

// Bouton « ampoule » de l'en-tête (header.js).
export function tourButton() {
  return h('button', {
    class: 'icon-btn tour-btn acc-2 no-drag', type: 'button', 'data-i18n-tip': 'tour.button',
    'aria-label': t('tour.button'), onclick: () => startTour(),
  }, icon('lightbulb'));
}

export function startTour(at = 0) {
  if (!app || isDialogOpen()) return;
  open('tour');
  go(Math.max(0, Math.min(STEPS.length - 1, at)));
}

// Premier lancement : l'ampoule est montrée une fois, après la bienvenue et la
// notice (main.js, quand aucune autre fenêtre n'est ouverte).
export function maybeShowTourHint() {
  const s = store.app && store.app.settings;
  if (!app || !s || mode || isDialogOpen() || !s.welcome_done || s.tour_hint_shown) return;
  if (store.app.app && store.app.app.uninstall_mode) return;
  if (!document.querySelector('.tour-btn')) return;
  s.tour_hint_shown = true;
  api.post('/api/settings', { tour_hint_shown: true }).catch(() => {});
  open('hint');
  showHint();
}

export function closeTour() {
  if (!mode) return;
  cancelRun();
  mode = null;
  const r = root;
  root = null;
  els = {};
  r.classList.remove('on');
  r.classList.add('out');
  // Le puits de lumière s'ouvre sur toute la fenêtre avant de disparaître.
  const spot = r.querySelector('.tour-spot');
  if (spot) setSpot(spot, null, true);
  setTimeout(() => r.remove(), reducedMotion() ? 0 : 420);
  if (lastFocus && lastFocus.focus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
  // Les fenêtres du démarrage (anomalies, téléchargements…) peuvent reprendre.
  document.dispatchEvent(new CustomEvent('fsp-dialog-closed'));
}

// ---------------------------------------------------------------------------
// Calques
// ---------------------------------------------------------------------------

function open(kind) {
  if (!root) {
    lastFocus = document.activeElement;
    const spot = h('div', { class: 'tour-spot', 'aria-hidden': 'true' });
    const stage = h('div', { class: 'tour-stage', 'aria-hidden': 'true' });
    const note = h('div', { class: 'tour-note', 'aria-live': 'polite' });
    const ctrl = h('div', { class: 'tour-ctrl' });
    const hit = h('button', { class: 'tour-hit', type: 'button', tabindex: '-1', 'aria-hidden': 'true' });
    root = h('div', { class: 'tour', role: 'dialog', 'aria-modal': 'true', 'aria-label': t('tour.title') },
      spot, stage, hit, note, ctrl);
    els = { spot, stage, note, ctrl, hit };
    // Le tour couvre toute la fenêtre : un clic dans l'ombre ne fait rien.
    root.addEventListener('pointerdown', (e) => {
      if (e.target === root || e.target === spot || e.target === stage) e.preventDefault();
    });
    hit.addEventListener('click', () => {
      if (mode === 'hint') startTour(0);
    });
    app.append(root);
    setSpot(spot, null, true);
    requestAnimationFrame(() => root && root.classList.add('on'));
  }
  mode = kind;
  root.classList.toggle('is-hint', kind === 'hint');
  root.classList.toggle('is-tour', kind === 'tour');
  if (kind === 'tour') buildCtrl();
  else clear(els.ctrl);
}

function appSize() {
  return { W: app.clientWidth, H: app.clientHeight };
}

function q(sel) {
  return document.querySelector(`#app ${sel}`);
}

function rectOf(el) {
  if (!el) return null;
  const r = localRect(el);
  if (!r.width && !r.height) return null;
  return r;
}

function union(rects, pad = SPOT_PAD) {
  const list = rects.filter(Boolean);
  if (!list.length) return null;
  const left = Math.min(...list.map((r) => r.left)) - pad;
  const top = Math.min(...list.map((r) => r.top)) - pad;
  const right = Math.max(...list.map((r) => r.right)) + pad;
  const bottom = Math.max(...list.map((r) => r.bottom)) + pad;
  return { left, top, right, bottom, width: right - left, height: bottom - top };
}

// Le puits de lumière ; sans rectangle, il couvre toute la fenêtre (aucune ombre).
function setSpot(spot, r, full = false) {
  if (!spot) return;
  if (!r) {
    const { W, H } = app ? appSize() : { W: 0, H: 0 };
    if (full) Object.assign(spot.style, { left: '-40px', top: '-40px', width: `${W + 80}px`, height: `${H + 80}px` });
    else Object.assign(spot.style, { left: `${W / 2}px`, top: `${H / 2}px`, width: '0px', height: '0px' });
    spot.classList.add('is-empty');
    return;
  }
  spot.classList.remove('is-empty');
  Object.assign(spot.style, {
    left: `${Math.round(r.left)}px`, top: `${Math.round(r.top)}px`,
    width: `${Math.round(r.width)}px`, height: `${Math.round(r.height)}px`,
  });
}

// ---------------------------------------------------------------------------
// Barre de commande
// ---------------------------------------------------------------------------

function ctrlButton(ico, label, key, run, cls = '') {
  return h('button', { class: `btn tour-cbtn ${cls}`.trim(), type: 'button', onclick: run },
    ico ? icon(ico) : null, h('span', { class: 'tour-cbtn-label', text: label }), key ? h('kbd', { class: 'tour-kbd tour-kbd-s', text: key }) : null);
}

function buildCtrl() {
  const c = els.ctrl;
  clear(c);
  const count = h('span', { class: 'tour-count' });
  const bar = h('span', { class: 'tour-progress' }, h('span', { class: 'tour-progress-fill' }));
  const prev = ctrlButton('arrow-left', t('tour.prev'), '←', () => go(index - 1), 'btn-ghost tour-prev');
  const replay = ctrlButton('rotate-ccw', t('tour.replay'), 'R', () => go(index), 'btn-ghost');
  const next = ctrlButton('arrow-right', t('tour.next'), '→', () => go(index + 1), 'btn-primary tour-next');
  const quit = h('button', {
    class: 'icon-btn tour-quit', type: 'button', 'aria-label': t('tour.quit'), 'data-tip-text': `${t('tour.quit')}\n${t('tour.key_esc')}`,
    onclick: () => closeTour(),
  }, icon('x'));
  c.append(
    h('div', { class: 'tour-ctrl-head' }, icon('lightbulb', 'tour-ctrl-ico'), h('span', { class: 'tour-ctrl-title', text: t('tour.title') }), count),
    bar,
    h('div', { class: 'tour-ctrl-btns' }, prev, replay, next, quit),
  );
  els.count = count;
  els.fill = bar.firstElementChild;
  els.prev = prev;
  els.next = next;
}

function updateCtrl() {
  if (!els.count) return;
  els.count.textContent = t('tour.count', { n: index + 1, total: STEPS.length });
  els.fill.style.width = `${((index + 1) / STEPS.length) * 100}%`;
  els.prev.setAttribute('aria-disabled', index === 0 ? 'true' : 'false');
  els.prev.disabled = index === 0;
  const last = index === STEPS.length - 1;
  els.next.querySelector('.tour-cbtn-label').textContent = last ? t('tour.finish') : t('tour.next');
}

// ---------------------------------------------------------------------------
// Clavier
// ---------------------------------------------------------------------------

function onKey(e) {
  if (!mode || !root) return;
  // Une fenêtre ouverte malgré tout (au démarrage) garde ses touches.
  if (isDialogOpen()) return;
  const k = e.key;
  if (k === 'Tab') {
    trapFocus(e);
    return;
  }
  e.stopPropagation();
  if (mode === 'hint') {
    if (k === 'Escape') {
      e.preventDefault();
      closeTour();
    } else if (k === 'Enter' && !(e.target instanceof HTMLButtonElement)) {
      e.preventDefault();
      startTour(0);
    }
    return;
  }
  const onButton = e.target instanceof HTMLButtonElement && root.contains(e.target);
  if (k === 'Escape') {
    e.preventDefault();
    closeTour();
  } else if (k === 'ArrowRight' || k === 'PageDown' || ((k === 'Enter' || k === ' ') && !onButton)) {
    e.preventDefault();
    go(index + 1);
  } else if (k === 'ArrowLeft' || k === 'PageUp' || k === 'Backspace') {
    e.preventDefault();
    go(index - 1);
  } else if (k === 'Home') {
    e.preventDefault();
    go(0);
  } else if (k === 'End') {
    e.preventDefault();
    go(STEPS.length - 1);
  } else if ((k === 'r' || k === 'R') && !e.ctrlKey && !e.metaKey && !e.altKey) {
    e.preventDefault();
    go(index);
  } else if (!onButton || (k !== 'Enter' && k !== ' ')) {
    // Aucun raccourci de l'application pendant le tour (Ctrl+A, Suppr…).
    e.preventDefault();
  }
}

function trapFocus(e) {
  const items = [...root.querySelectorAll('button:not([disabled]):not(.tour-hit)')].filter((x) => x.offsetParent !== null);
  e.preventDefault();
  e.stopPropagation();
  if (!items.length) return;
  const i = items.indexOf(document.activeElement);
  const n = e.shiftKey ? (i <= 0 ? items.length - 1 : i - 1) : (i + 1) % items.length;
  items[n].focus();
}

// ---------------------------------------------------------------------------
// Déroulement d'une étape
// ---------------------------------------------------------------------------

function cancelRun() {
  if (!run) return;
  run.alive = false;
  for (const p of run.pending) {
    clearTimeout(p.id);
    p.reject(CANCEL);
  }
  for (const id of run.frames) cancelAnimationFrame(id);
  run.pending.clear();
  run = null;
}

function scheduleRefresh() {
  if (!mode) return;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (mode === 'tour') go(index, { quiet: true });
    else if (mode === 'hint') showHint();
  }, 220);
}

function go(i, { quiet = false } = {}) {
  if (mode !== 'tour') return;
  if (i >= STEPS.length) {
    closeTour();
    return;
  }
  if (i < 0) return;
  index = i;
  updateCtrl();
  cancelRun();
  const step = STEPS[index];
  const ctx = makeCtx();
  clear(els.stage);
  els.hit.hidden = true;
  // 1. note (titre écrit à la main, explication), mesurée avant d'être placée :
  //    certaines démonstrations s'adaptent à la place qu'elle laisse.
  ctx.note = fillNote({
    caption: t(`tour.${step.id}.caption`),
    body: step.body ? step.body() : [t(`tour.${step.id}.body`)],
    quiet,
  });
  // 2. faux éléments (rectangles à éclairer en plus des cibles réelles)
  let extra = [];
  try {
    extra = (step.build && step.build(ctx)) || [];
  } catch (err) {
    console.error(err);
  }
  const targets = (step.targets ? step.targets() : []).filter(Boolean);
  const spotRect = step.spot ? step.spot(ctx) : union([...targets.map(rectOf), ...extra], step.pad ?? SPOT_PAD);
  setSpot(els.spot, spotRect);
  els.spot.classList.remove('is-pulse');
  els.spot.style.borderRadius = `${step.radius ?? 14}px`;
  // 3. placement de la note, flèche vers l'élément
  showNote(ctx.note, {
    place: step.place || ['below', 'right', 'left', 'above', 'center'],
    spot: spotRect,
    arrowTo: step.arrowTo ? step.arrowTo(ctx) : spotRect,
  });
  // 4. démonstration
  if (step.play) {
    step.play(ctx).catch((err) => {
      if (err !== CANCEL) console.error(err);
    });
  }
  if (!quiet && els.next && !root.contains(document.activeElement)) els.next.focus({ preventScroll: true });
}

function makeCtx() {
  run = { alive: true, pending: new Set(), frames: new Set() };
  const r = run;
  const reduced = reducedMotion();
  const ctx = {
    stage: els.stage,
    data: {},
    reduced,
    wait(ms) {
      return new Promise((resolve, reject) => {
        if (!r.alive) {
          reject(CANCEL);
          return;
        }
        const p = { reject };
        p.id = setTimeout(() => {
          r.pending.delete(p);
          if (r.alive) resolve();
          else reject(CANCEL);
        }, reduced ? 0 : ms);
        r.pending.add(p);
      });
    },
    frame(fn) {
      const id = requestAnimationFrame((ts) => {
        r.frames.delete(id);
        if (r.alive) fn(ts);
      });
      r.frames.add(id);
    },
  };
  // Pointeur de démonstration
  let cursor = null;
  ctx.cursorAt = (x, y) => {
    if (!cursor) {
      cursor = makeCursor();
      els.stage.append(cursor);
    }
    cursor.style.transition = 'none';
    cursor.style.transform = `translate(${x}px, ${y}px)`;
    // eslint-disable-next-line no-unused-expressions
    cursor.offsetWidth;
    cursor.classList.add('on');
  };
  ctx.move = async (x, y, ms = 560) => {
    if (!cursor) ctx.cursorAt(x, y);
    cursor.style.transition = reduced ? 'none' : `transform ${ms}ms cubic-bezier(.45, .05, .2, 1)`;
    cursor.style.transform = `translate(${x}px, ${y}px)`;
    await ctx.wait(ms + 40);
  };
  ctx.click = async () => {
    if (!cursor) return;
    cursor.classList.add('is-down');
    const ripple = h('span', { class: 'tour-ripple' });
    ripple.style.transform = cursor.style.transform;
    els.stage.append(ripple);
    setTimeout(() => ripple.remove(), 700);
    await ctx.wait(150);
    cursor.classList.remove('is-down');
    await ctx.wait(90);
  };
  ctx.keys = (list = []) => {
    if (!cursor) return;
    const box = cursor.querySelector('.tour-cursor-keys');
    clear(box);
    for (const k of list) box.append(h('kbd', { class: 'tour-kbd', text: k }));
    box.classList.toggle('on', list.length > 0);
  };
  ctx.hideCursor = () => cursor && cursor.classList.remove('on');
  // Infobulle de démonstration (même aspect que les vraies)
  ctx.tip = (text, rect, where = 'below') => {
    const el = h('div', { class: 'tooltip tour-tip', text });
    els.stage.append(el);
    const { W } = appSize();
    const tw = el.offsetWidth;
    const th = el.offsetHeight;
    let x = rect.left + rect.width / 2 - tw / 2;
    x = Math.max(12, Math.min(W - tw - 12, x));
    const y = where === 'above' ? rect.top - th - 10 : rect.bottom + 10;
    el.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
    requestAnimationFrame(() => el.classList.add('on'));
    return el;
  };
  ctx.untip = (el) => {
    if (!el) return;
    el.classList.remove('on');
    setTimeout(() => el.remove(), 200);
  };
  // Anneau lumineux posé sur un rectangle
  ctx.ring = (rect, pad = 4) => {
    const el = h('div', { class: 'tour-ring' });
    Object.assign(el.style, {
      left: `${rect.left - pad}px`, top: `${rect.top - pad}px`, width: `${rect.width + pad * 2}px`, height: `${rect.height + pad * 2}px`,
    });
    els.stage.append(el);
    requestAnimationFrame(() => el.classList.add('on'));
    return el;
  };
  // Pose un élément dans la scène, à l'emplacement d'un rectangle
  ctx.put = (el, rect, { width = true, height = false } = {}) => {
    el.style.position = 'absolute';
    el.style.left = `${rect.left}px`;
    el.style.top = `${rect.top}px`;
    el.style.margin = '0';
    if (width) el.style.width = `${rect.width}px`;
    if (height) el.style.height = `${rect.height}px`;
    els.stage.append(el);
    return el;
  };
  return ctx;
}

function makeCursor() {
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('width', '30');
  svg.setAttribute('height', '30');
  const p = document.createElementNS(NS, 'path');
  p.setAttribute('d', 'M4.5 2.5v17.2l4.6-4.3 3 6.6 3.1-1.4-3-6.5 6.3-.3z');
  svg.append(p);
  return h('div', { class: 'tour-cursor' }, svg, h('div', { class: 'tour-cursor-keys' }));
}

// ---------------------------------------------------------------------------
// Note : titre écrit à la main, explication, flèche dessinée
// ---------------------------------------------------------------------------

// « [Ctrl] + clic » : les crochets deviennent des touches de clavier.
function rich(text) {
  const out = [];
  const re = /\[([^\]]+)\]/g;
  let last = 0;
  let m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(document.createTextNode(text.slice(last, m.index)));
    out.push(h('kbd', { class: 'tour-kbd', text: m[1] }));
    last = re.lastIndex;
  }
  if (last < text.length) out.push(document.createTextNode(text.slice(last)));
  return out;
}

// Écrit le titre lettre par lettre ; renvoie la durée de l'écriture (ms).
function writeCaption(el, text, delay = 0) {
  clear(el);
  let i = 0;
  const parts = text.split(/(\s+)/);
  for (const part of parts) {
    if (!part) continue;
    if (/^\s+$/.test(part)) {
      el.append(document.createTextNode(' '));
      continue;
    }
    const word = h('span', { class: 'tw' });
    for (const ch of Array.from(part)) {
      const c = h('span', { class: 'tc', text: ch });
      c.style.animationDelay = `${delay + i * WRITE_STEP}ms`;
      word.append(c);
      i += 1;
    }
    el.append(word);
  }
  return delay + i * WRITE_STEP;
}

function underline(totalMs) {
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'tour-underline');
  svg.setAttribute('viewBox', '0 0 240 14');
  svg.setAttribute('preserveAspectRatio', 'none');
  const p = document.createElementNS(NS, 'path');
  p.setAttribute('d', 'M3 9 C 40 3, 78 12, 120 7 S 196 4, 237 8');
  p.setAttribute('pathLength', '1');
  p.style.animationDelay = `${totalMs}ms`;
  svg.append(p);
  return svg;
}

// Remplit la note (cachée) et la mesure.
function fillNote({ caption, body, quiet }) {
  const note = els.note;
  clear(note);
  note.className = 'tour-note';
  const cap = h('div', { class: `tour-caption${Array.from(caption).length > 30 ? ' is-long' : ''}` });
  const total = writeCaption(cap, caption, quiet ? 0 : 260);
  const bodyEl = h('div', { class: 'tour-body' });
  for (const part of [].concat(body)) {
    if (part instanceof Node) bodyEl.append(part);
    else for (const line of String(part).split('\n')) bodyEl.append(h('p', {}, rich(line)));
  }
  bodyEl.style.animationDelay = `${Math.min(total, 900)}ms`;
  note.append(cap, underline(total), bodyEl);
  if (quiet) note.classList.add('is-quiet');
  note.style.left = '0px';
  note.style.top = '0px';
  note.style.visibility = 'hidden';
  return { w: note.offsetWidth, h: note.offsetHeight, total };
}

// Place la note sur le premier côté libre, puis dessine la flèche.
function showNote(size, { place, spot, arrowTo }) {
  const note = els.note;
  const { w: nw, h: nh, total } = size;
  const pos = placeNote(place, spot, nw, nh);
  note.style.left = `${Math.round(pos.x)}px`;
  note.style.top = `${Math.round(pos.y)}px`;
  note.style.visibility = '';
  note.classList.remove('on');
  // eslint-disable-next-line no-unused-expressions
  note.offsetWidth;
  note.classList.add('on');
  if (arrowTo && !pos.inside) drawArrow({ left: pos.x, top: pos.y, width: nw, height: nh }, arrowTo, total);
}

function placeNote(prefs, S, nw, nh) {
  const { W, H } = appSize();
  const bottomLimit = H - (mode === 'tour' ? 118 : MARGIN);
  const clampX = (x) => Math.max(MARGIN, Math.min(W - nw - MARGIN, x));
  const clampY = (y) => Math.max(MARGIN, Math.min(bottomLimit - nh, y));
  const center = { x: (W - nw) / 2, y: Math.max(MARGIN, (bottomLimit - nh) / 2), inside: true };
  if (!S) return center;
  const cx = S.left + S.width / 2;
  const cy = S.top + S.height / 2;
  for (const p of prefs) {
    if (p === 'below') {
      const y = S.bottom + NOTE_GAP;
      if (y + nh <= bottomLimit) return { x: clampX(cx - nw / 2), y };
    } else if (p === 'above') {
      const y = S.top - NOTE_GAP - nh;
      if (y >= MARGIN) return { x: clampX(cx - nw / 2), y };
    } else if (p === 'right') {
      const x = S.right + NOTE_GAP;
      if (x + nw <= W - MARGIN) return { x, y: clampY(cy - nh / 2) };
    } else if (p === 'left') {
      const x = S.left - NOTE_GAP - nw;
      if (x >= MARGIN) return { x, y: clampY(cy - nh / 2) };
    } else if (p === 'below-left') {
      const y = S.bottom + NOTE_GAP;
      if (y + nh <= bottomLimit) return { x: clampX(S.right - nw - 40), y };
    } else if (p.startsWith('inside')) {
      const pad = 26;
      const right = p.endsWith('r');
      const top = p.includes('-t');
      const x = right ? S.right - nw - pad : S.left + pad;
      const y = top ? S.top + pad : Math.min(S.bottom, bottomLimit) - nh - pad;
      if (x >= S.left && y >= S.top - 1) return { x: clampX(x), y: clampY(y), inside: true };
    } else if (p === 'center') {
      return center;
    }
  }
  // Rien ne tient : sous l'élément, au plus près du bas.
  if (prefs.includes('below') || prefs.includes('below-left')) return { x: clampX(cx - nw / 2), y: clampY(S.bottom + 16) };
  return center;
}

// Flèche à main levée, de la note vers l'élément éclairé.
function drawArrow(note, target, delay) {
  const { W, H } = appSize();
  const nc = { x: note.left + note.width / 2, y: note.top + note.height / 2 };
  const tc = { x: target.left + target.width / 2, y: target.top + target.height / 2 };
  const a = edgePoint(note, tc, 10);
  const b = edgePoint(target, nc, 12);
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy);
  if (len < 40) return;
  // Courbe légère, toujours du même côté
  const bend = Math.min(90, len * 0.22);
  const c = { x: a.x + dx / 2 - (dy / len) * bend, y: a.y + dy / 2 + (dx / len) * bend };
  const tx = b.x - c.x;
  const ty = b.y - c.y;
  const tl = Math.hypot(tx, ty) || 1;
  const ux = tx / tl;
  const uy = ty / tl;
  const head = 15;
  const wing = (s) => ({ x: b.x - ux * head + -uy * head * 0.62 * s, y: b.y - uy * head + ux * head * 0.62 * s });
  const w1 = wing(1);
  const w2 = wing(-1);
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'tour-arrow');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('width', String(W));
  svg.setAttribute('height', String(H));
  const line = document.createElementNS(NS, 'path');
  line.setAttribute('d', `M${a.x.toFixed(1)} ${a.y.toFixed(1)} Q${c.x.toFixed(1)} ${c.y.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`);
  line.setAttribute('pathLength', '1');
  const tip = document.createElementNS(NS, 'path');
  tip.setAttribute('d', `M${w1.x.toFixed(1)} ${w1.y.toFixed(1)} L${b.x.toFixed(1)} ${b.y.toFixed(1)} L${w2.x.toFixed(1)} ${w2.y.toFixed(1)}`);
  tip.setAttribute('pathLength', '1');
  tip.setAttribute('class', 'tour-arrow-tip');
  const d0 = Math.max(0, Math.min(delay, 1100) - 200);
  line.style.animationDelay = `${d0}ms`;
  tip.style.animationDelay = `${d0 + 420}ms`;
  svg.append(line, tip);
  els.stage.prepend(svg);
}

// Point du bord d'un rectangle dans la direction d'un autre point.
function edgePoint(r, toward, gap) {
  const cx = r.left + r.width / 2;
  const cy = r.top + r.height / 2;
  const dx = toward.x - cx;
  const dy = toward.y - cy;
  if (!dx && !dy) return { x: cx, y: cy };
  const sx = dx ? (r.width / 2) / Math.abs(dx) : Infinity;
  const sy = dy ? (r.height / 2) / Math.abs(dy) : Infinity;
  const s = Math.min(sx, sy);
  const len = Math.hypot(dx, dy);
  return { x: cx + dx * s + (dx / len) * gap, y: cy + dy * s + (dy / len) * gap };
}

// ---------------------------------------------------------------------------
// Premier lancement : l'ampoule mise en évidence
// ---------------------------------------------------------------------------

function showHint() {
  cancelRun();
  makeCtx();
  clear(els.stage);
  const btn = q('.tour-btn');
  const r = rectOf(btn);
  const spot = r ? union([r], 8) : null;
  setSpot(els.spot, spot);
  els.spot.style.borderRadius = '999px';
  els.spot.classList.add('is-pulse');
  if (spot) {
    els.hit.hidden = false;
    Object.assign(els.hit.style, { left: `${spot.left}px`, top: `${spot.top}px`, width: `${spot.width}px`, height: `${spot.height}px` });
  }
  const actions = h('div', { class: 'tour-note-actions' },
    h('button', { class: 'btn btn-ghost', type: 'button', onclick: () => closeTour() }, h('span', { text: t('tour.hint.later') })),
    h('button', { class: 'btn btn-primary tour-hint-go', type: 'button', onclick: () => startTour(0) },
      icon('lightbulb'), h('span', { text: t('tour.hint.start') })));
  const size = fillNote({ caption: t('tour.hint.caption'), body: [t('tour.hint.body'), actions], quiet: false });
  showNote(size, { place: ['below-left', 'below', 'left'], spot, arrowTo: spot });
  setTimeout(() => {
    const go2 = root && root.querySelector('.tour-hint-go');
    if (go2) go2.focus({ preventScroll: true });
  }, 60);
}

// ---------------------------------------------------------------------------
// Faux éléments
// ---------------------------------------------------------------------------

// Copie d'un élément réel, posée exactement par-dessus (visible même si
// l'original est masqué : version sans parties, par exemple).
function cloneOver(ctx, el) {
  if (!el) return null;
  const r = rectOf(el);
  if (!r) return null;
  const c = el.cloneNode(true);
  c.style.visibility = 'visible';
  c.removeAttribute('id');
  c.querySelectorAll('[aria-disabled]').forEach((x) => x.removeAttribute('aria-disabled'));
  c.removeAttribute('aria-disabled');
  c.querySelectorAll('input').forEach((x) => { x.disabled = false; });
  c.classList.remove('is-disabled');
  c.classList.add('tour-clone');
  ctx.put(c, r, { width: true, height: true });
  return c;
}

function demoVersions() {
  const installed = new Set(['FS19', 'FS22', 'FS25']);
  const current = installed.has(activeVersion()) ? activeVersion() : 'FS25';
  return (store.app.versions || []).map((v) => ({
    ver: v,
    state: !v.available ? 'coming' : installed.has(v.id) ? 'installed' : 'absent',
    current: v.id === current,
  }));
}

function versionSub(state) {
  if (state === 'coming') return t('versions.coming');
  if (state === 'absent') return t('versions.not_installed');
  return t('versions.installed');
}

// ---------------------------------------------------------------------------
// Les étapes
// ---------------------------------------------------------------------------

const STEPS = [
  // 1. Versions du jeu
  {
    id: 'versions',
    targets: () => [q('.version-zone')],
    place: ['right', 'below', 'left'],
    build(ctx) {
      const btn = q('.version-btn');
      const br = rectOf(btn);
      if (!br) return [];
      const menu = h('div', { class: 'menu version-menu tour-fake' });
      const items = [];
      for (const d of demoVersions()) {
        const el = h('div', {
          class: `version-item${d.state === 'absent' ? ' is-absent' : ''}${d.state === 'coming' ? ' is-coming' : ''}`,
          'aria-current': String(d.current), 'aria-disabled': d.state === 'installed' ? null : 'true',
        }, gameLogo(d.ver.logo));
        menu.append(el);
        items.push({ ...d, el });
      }
      els.stage.append(menu);
      const { W } = appSize();
      const mw = menu.offsetWidth;
      const left = Math.max(MARGIN, Math.min(W - mw - MARGIN, br.left + br.width / 2 - mw / 2));
      Object.assign(menu.style, { left: `${left}px`, top: `${br.bottom + 6}px`, translate: 'none' });
      ctx.data.menu = menu;
      ctx.data.items = items;
      ctx.data.btn = br;
      return [rectOf(menu), br];
    },
    async play(ctx) {
      const { menu, items, btn } = ctx.data;
      if (!menu) return;
      ctx.cursorAt(btn.left + btn.width * 0.62, btn.top + btn.height * 0.62);
      await ctx.wait(500);
      menu.classList.add('on');
      await ctx.wait(450);
      let tip = null;
      for (const it of items) {
        const r = rectOf(it.el);
        await ctx.move(r.left + r.width * 0.55, r.top + r.height * 0.6, 340);
        it.el.classList.add('is-hover');
        ctx.untip(tip);
        tip = ctx.tip(`${it.ver.name}\n${versionSub(it.state)}`, r);
        await ctx.wait(it.state === 'installed' ? 820 : 560);
        it.el.classList.remove('is-hover');
      }
      ctx.untip(tip);
      // Choisir une autre version installée
      const pick = items.find((x) => x.state === 'installed' && !x.current);
      if (!pick) return;
      const r = rectOf(pick.el);
      await ctx.move(r.left + r.width * 0.55, r.top + r.height * 0.6, 520);
      pick.el.classList.add('is-hover');
      await ctx.click();
      for (const it of items) it.el.setAttribute('aria-current', String(it === pick));
      const btnLogo = gameLogo(pick.ver.logo, 'tour-btn-logo');
      const cover = h('div', { class: 'version-btn tour-fake' }, btnLogo);
      ctx.put(cover, btn, { width: true, height: true });
      tip = ctx.tip(`${pick.ver.name}\n${t('tour.versions.picked')}`, r);
      await ctx.wait(1400);
      pick.el.classList.remove('is-hover');
      ctx.untip(tip);
      ctx.hideCursor();
    },
  },
  // 2. Parties : le cœur de FS Passion
  {
    id: 'parties',
    targets: () => [q('.party-block .party-pick'), q('.party-label')],
    place: ['left', 'below'],
    build(ctx) {
      const sel = q('.party-select');
      const sr = rectOf(sel);
      if (!sr) return [];
      const names = [].concat(t('tour.demo.parties'));
      const counts = [46, 31, 58];
      const fake = h('div', { class: 'party-select tour-fake' },
        h('span', { class: 'party-ico' }, icon('map')),
        h('span', { class: 'party-name', text: names[0] || '' }),
        h('span', { class: 'menu-tag', text: t('party.applied_tag') }),
        icon('chevron-down'));
      ctx.put(fake, sr, { width: true, height: true });
      const menu = h('div', { class: 'menu party-menu tour-fake on' });
      const rows = [];
      const mk = (name, subs, ico, special) => {
        const el = h('div', { class: `menu-item${special ? ' menu-special' : ''}` },
          h('span', { class: 'party-ico' }, icon(ico)),
          h('span', { class: 'mi-text' }, h('span', { text: name }), ...subs.map((x) => h('span', { class: 'mi-sub', text: x }))),
          h('span', { class: 'tour-check' }, icon('check', 'ico-s')));
        rows.push({ el, name, special });
        return el;
      };
      names.forEach((n, i) => menu.append(mk(n, [t('tour.demo.party_sub', { count: counts[i % counts.length] })], 'map', false)));
      menu.append(h('div', { class: 'menu-sep' }),
        mk(t('party.full'), [t('party.full_count', { count: 412 }), t('party.full_tip')], 'layers', true),
        mk(t('party.empty'), [t('party.empty_sub')], 'layers', true));
      els.stage.append(menu);
      Object.assign(menu.style, { left: `${sr.left}px`, top: `${sr.bottom + 6}px`, width: `${Math.max(380, sr.width)}px` });
      rows[0].el.setAttribute('aria-current', 'true');
      ctx.data = { fake, menu, rows, sr };
      return [sr, rectOf(menu)];
    },
    async play(ctx) {
      const { fake, rows, sr } = ctx.data;
      if (!fake) return;
      const nameEl = fake.querySelector('.party-name');
      const tag = fake.querySelector('.menu-tag');
      ctx.cursorAt(sr.left + sr.width * 0.7, sr.top + sr.height * 0.55);
      await ctx.wait(700);
      const choose = async (row, ms = 900) => {
        const r = rectOf(row.el);
        await ctx.move(r.left + Math.min(220, r.width * 0.5), r.top + r.height * 0.55, 560);
        row.el.classList.add('is-active-key');
        await ctx.click();
        for (const x of rows) x.el.setAttribute('aria-current', String(x === row));
        row.el.classList.remove('is-active-key');
        nameEl.textContent = row.name;
        fake.classList.remove('tour-flash');
        // eslint-disable-next-line no-unused-expressions
        fake.offsetWidth;
        fake.classList.add('tour-flash');
        tag.hidden = row !== rows[0];
        await ctx.wait(ms);
      };
      await choose(rows[1]);
      await choose(rows[2]);
      // Partie Pleine, Partie Vide : à quoi elles servent
      const full = rows[rows.length - 2];
      const empty = rows[rows.length - 1];
      let r = rectOf(full.el);
      await ctx.move(r.left + 200, r.top + r.height * 0.5, 560);
      full.el.classList.add('is-active-key');
      let tip = ctx.tip(t('tour.parties.full_tip'), r);
      await ctx.wait(1700);
      full.el.classList.remove('is-active-key');
      ctx.untip(tip);
      r = rectOf(empty.el);
      await ctx.move(r.left + 200, r.top + r.height * 0.5, 420);
      empty.el.classList.add('is-active-key');
      tip = ctx.tip(t('tour.parties.empty_tip'), r);
      await ctx.wait(1700);
      empty.el.classList.remove('is-active-key');
      ctx.untip(tip);
      await choose(rows[0], 400);
      ctx.hideCursor();
    },
  },
  // 3. Créer, dupliquer, renommer, supprimer
  {
    id: 'tools',
    targets: () => [q('.party-tools')],
    place: ['below', 'left'],
    build(ctx) {
      ctx.data.clone = cloneOver(ctx, q('.party-tools'));
      return [];
    },
    async play(ctx) {
      const c = ctx.data.clone;
      if (!c) return;
      const keys = ['header.create', 'header.duplicate', 'header.rename', 'header.delete'];
      await ctx.wait(700);
      for (let i = 0; i < c.children.length; i++) {
        const b = c.children[i];
        b.classList.add('tour-hot');
        const tip = ctx.tip(t(keys[i] || keys[0]), rectOf(b));
        await ctx.wait(1000);
        b.classList.remove('tour-hot');
        ctx.untip(tip);
        await ctx.wait(120);
      }
    },
  },
  // 4. Mods communs
  {
    id: 'common',
    targets: () => [q('.common-switch')],
    place: ['below', 'left'],
    build(ctx) {
      ctx.data.clone = cloneOver(ctx, q('.common-switch'));
      const input = ctx.data.clone && ctx.data.clone.querySelector('input');
      if (input) input.checked = true;
      return [];
    },
    async play(ctx) {
      const c = ctx.data.clone;
      if (!c) return;
      const input = c.querySelector('input');
      const track = c.querySelector('.switch-track') || c;
      const r = rectOf(track);
      ctx.cursorAt(r.left + r.width + 40, r.bottom + 40);
      await ctx.wait(600);
      await ctx.move(r.left + r.width * 0.6, r.top + r.height * 0.6, 520);
      let tip = null;
      for (const on of [false, true]) {
        await ctx.click();
        if (input) input.checked = on;
        ctx.untip(tip);
        tip = ctx.tip(t(on ? 'tour.common.on' : 'tour.common.off'), rectOf(c));
        await ctx.wait(1600);
      }
      ctx.untip(tip);
      ctx.hideCursor();
    },
  },
  // 5. Appliquer
  {
    id: 'apply',
    targets: () => [q('.apply-btn')],
    place: ['below', 'left'],
    build(ctx) {
      const c = cloneOver(ctx, q('.apply-btn'));
      if (c) c.classList.add('btn-primary', 'is-needed');
      ctx.data.clone = c;
      return [];
    },
    async play(ctx) {
      const c = ctx.data.clone;
      if (!c) return;
      const r = rectOf(c);
      ctx.cursorAt(r.left - 60, r.bottom + 50);
      await ctx.wait(700);
      await ctx.move(r.left + r.width * 0.5, r.top + r.height * 0.6, 560);
      await ctx.click();
      c.classList.remove('btn-primary', 'is-needed');
      c.classList.add('tour-done');
      const tip = ctx.tip(t('tour.apply.done'), r);
      await ctx.wait(1800);
      ctx.untip(tip);
      ctx.hideCursor();
    },
  },
  // 6. Thème, notifications, tour guidé, paramètres
  {
    id: 'buttons',
    targets: () => [q('.theme-btn'), q('.bell-pick'), q('.tour-btn'), q('.settings-btn')],
    place: ['below', 'left'],
    async play(ctx) {
      const list = [
        [q('.theme-btn'), 'tour.buttons.theme'],
        [q('.bell-pick'), 'notifications.title'],
        [q('.tour-btn'), 'tour.button'],
        [q('.settings-btn'), 'header.settings'],
      ];
      await ctx.wait(600);
      for (const [el, key] of list) {
        const r = rectOf(el);
        if (!r) continue;
        const ring = ctx.ring(r, 2);
        const tip = ctx.tip(t(key), r);
        await ctx.wait(850);
        ring.remove();
        ctx.untip(tip);
      }
    },
  },
  // 7. Liste 1 : Tous les mods
  {
    id: 'list1',
    targets: () => [q('#list1')],
    pad: 4,
    place: ['inside-br', 'inside-bl', 'center'],
    arrowTo: () => null,
    async play(ctx) {
      const s = rectOf(q('#list1 .search'));
      if (!s) return;
      await ctx.wait(900);
      const ring = ctx.ring(s, 3);
      const tip = ctx.tip(t('tour.list1.search_tip'), s);
      await ctx.wait(2600);
      ring.remove();
      ctx.untip(tip);
    },
  },
  // 8. Liste 1 : nouveaux mods dans les téléchargements (0.9.1)
  {
    id: 'downloads',
    targets: () => [q('.find-new-btn')],
    pad: 8,
    radius: 12,
    place: ['left', 'below'],
    build: buildDownloads,
    play: playDownloads,
  },
  // 9. Liste 2 : Mods de la partie
  {
    id: 'list2',
    targets: () => [q('.side-pane[data-drop="l2"]')],
    pad: 6,
    place: ['left', 'center'],
  },
  // 10. Liste 3 : Mods communs
  {
    id: 'list3',
    targets: () => [q('.side-pane[data-drop="l3"]')],
    pad: 6,
    place: ['left', 'center'],
  },
  // 11. Sélection multiple
  {
    id: 'select',
    targets: () => [],
    pad: 2,
    place: ['below', 'right', 'center'],
    build: buildSelect,
    play: playSelect,
  },
  // 12. Glisser-déposer : copies et déplacements
  {
    id: 'move',
    targets: () => [q('.main')],
    pad: 6,
    place: ['inside-bl', 'center'],
    arrowTo: () => null,
    play: playMove,
  },
  // 13. Raccourcis clavier
  {
    id: 'keys',
    targets: () => [],
    place: ['center'],
    body: () => {
      const grid = h('div', { class: 'tour-keys-grid' });
      for (const row of blocks('tour.keys.rows')) {
        if (!row || !row.k) continue;
        grid.append(h('div', { class: 'tour-key-k' }, rich(row.k)), h('div', { class: 'tour-key-d', text: row.d || '' }));
      }
      return [t('tour.keys.body'), grid];
    },
  },
  // 14. La croix : FS Passion reste dans la zone de notification (0.9.1)
  {
    id: 'close',
    targets: () => [],
    place: ['below-left', 'below', 'left'],
    radius: 8,
    build: buildClose,
    spot: (ctx) => (ctx.data.close ? union([ctx.data.close], 6) : null),
    arrowTo: (ctx) => ctx.data.close || null,
    play: playClose,
  },
  // 15. Fin : l'ampoule pour revoir le tour
  {
    id: 'end',
    targets: () => [q('.tour-btn')],
    pad: 8,
    radius: 999,
    place: ['below-left', 'below', 'left'],
  },
];

// -- Sélection multiple ------------------------------------------------------

function buildSelect(ctx) {
  const host = rectOf(q('#list1 .grid-wrap')) || rectOf(q('#list1'));
  if (!host) return [];
  const names = [].concat(t('tour.demo.mods'));
  const icons = ['tractor', 'wheat', 'package', 'tractor', 'layers', 'map'];
  const n = host.width >= 1050 ? 6 : 5;
  const gap = 18;
  // La note se place sous les tuiles : leur taille s'adapte à la place libre.
  const { H } = appSize();
  const free = H - 118 - (host.top + 8) - NOTE_GAP - (ctx.note ? ctx.note.h : 300) - SPOT_PAD * 2 - 18 - 46 - 30;
  const size = Math.max(80, Math.min(160, free, Math.floor((host.width - 48 - gap * (n - 1)) / n)));
  const board = h('div', { class: 'tour-board' });
  const tiles = [];
  for (let i = 0; i < n; i++) {
    const tile = h('div', { class: 'tour-tile' },
      h('div', { class: 'tour-tile-art' }, icon(icons[i % icons.length])),
      h('div', { class: 'tour-tile-name', text: names[i % names.length] || '' }));
    tile.style.width = `${size}px`;
    tile.querySelector('.tour-tile-art').style.height = `${size}px`;
    board.append(tile);
    tiles.push(tile);
  }
  const counter = h('div', { class: 'tour-counter' });
  board.append(counter);
  els.stage.append(board);
  const bw = n * size + (n - 1) * gap + 48;
  const left = host.left + Math.max(0, (host.width - bw) / 2);
  Object.assign(board.style, { left: `${left}px`, top: `${host.top + 8}px`, width: `${bw}px`, gap: `${gap}px` });
  ctx.data = { board, tiles, counter };
  return [rectOf(board)];
}

async function playSelect(ctx) {
  const { tiles, counter } = ctx.data;
  if (!tiles) return;
  const selected = new Set();
  const paint = () => {
    tiles.forEach((tl, i) => tl.classList.toggle('is-selected', selected.has(i)));
    counter.textContent = selected.size ? `${selected.size} ${t('list1.selected')}` : '';
    counter.classList.toggle('on', selected.size > 0);
  };
  const at = (i) => {
    const r = rectOf(tiles[i].querySelector('.tour-tile-art'));
    return { x: r.left + r.width * 0.55, y: r.top + r.height * 0.5 };
  };
  paint();
  const first = at(0);
  ctx.cursorAt(first.x - 40, first.y + 120);
  await ctx.wait(700);
  // Clic simple : un seul mod
  let p = at(0);
  await ctx.move(p.x, p.y, 520);
  await ctx.click();
  selected.clear();
  selected.add(0);
  paint();
  await ctx.wait(700);
  // Maj + clic : toute une plage
  p = at(3);
  ctx.keys([t('tour.key_shift')]);
  await ctx.wait(450);
  await ctx.move(p.x, p.y, 640);
  await ctx.click();
  for (let i = 0; i <= 3; i++) selected.add(i);
  paint();
  await ctx.wait(900);
  ctx.keys([]);
  await ctx.wait(300);
  // Ctrl + clic : ajouter, puis retirer
  ctx.keys([t('tour.key_ctrl')]);
  await ctx.wait(450);
  const last = tiles.length - 1;
  p = at(last);
  await ctx.move(p.x, p.y, 640);
  await ctx.click();
  selected.add(last);
  paint();
  await ctx.wait(800);
  p = at(1);
  await ctx.move(p.x, p.y, 700);
  await ctx.click();
  selected.delete(1);
  paint();
  await ctx.wait(900);
  ctx.keys([]);
  // Mouvement réduit : la démonstration s'arrête sur la sélection obtenue.
  if (ctx.reduced) return;
  await ctx.wait(1400);
  // Échap : tout désélectionner
  ctx.keys([t('tour.key_esc')]);
  await ctx.wait(700);
  selected.clear();
  paint();
  await ctx.wait(900);
  ctx.keys([]);
  ctx.hideCursor();
}

// -- Glisser-déposer ---------------------------------------------------------

async function playMove(ctx) {
  const l1 = rectOf(q('#list1'));
  const l2 = rectOf(q('.side-pane[data-drop="l2"]'));
  const l3 = rectOf(q('.side-pane[data-drop="l3"]'));
  if (!l1 || !l2 || !l3) return;
  const { W, H } = appSize();
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'tour-flow');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('width', String(W));
  svg.setAttribute('height', String(H));
  els.stage.append(svg);
  const names = [].concat(t('tour.demo.mods'));

  const arrow = (pts, cls, both = false) => {
    const [a, c, b] = pts;
    const g = document.createElementNS(NS, 'g');
    g.setAttribute('class', `tour-flow-arrow ${cls}`);
    const line = document.createElementNS(NS, 'path');
    line.setAttribute('d', `M${a.x} ${a.y} Q${c.x} ${c.y} ${b.x} ${b.y}`);
    line.setAttribute('pathLength', '1');
    g.append(line);
    const heads = [[b, c]];
    if (both) heads.push([a, c]);
    for (const [end, ctl] of heads) {
      const tx = end.x - ctl.x;
      const ty = end.y - ctl.y;
      const tl = Math.hypot(tx, ty) || 1;
      const ux = tx / tl;
      const uy = ty / tl;
      const hd = 14;
      const p1 = { x: end.x - ux * hd - uy * hd * 0.6, y: end.y - uy * hd + ux * hd * 0.6 };
      const p2 = { x: end.x - ux * hd + uy * hd * 0.6, y: end.y - uy * hd - ux * hd * 0.6 };
      const head = document.createElementNS(NS, 'path');
      head.setAttribute('d', `M${p1.x} ${p1.y} L${end.x} ${end.y} L${p2.x} ${p2.y}`);
      head.setAttribute('class', 'tour-flow-head');
      g.append(head);
    }
    svg.append(g);
    requestAnimationFrame(() => g.classList.add('on'));
    return line;
  };
  const label = (text, x, y, align = 'center') => {
    const el = h('div', { class: `tour-flow-label is-${align}` }, rich(text));
    els.stage.append(el);
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
    requestAnimationFrame(() => el.classList.add('on'));
    return el;
  };
  // Petite tuile qui suit une flèche
  const fly = (path, text, keys = []) => new Promise((resolve) => {
    if (ctx.reduced) {
      resolve();
      return;
    }
    const ghost = h('div', { class: 'tour-ghost' }, icon('tractor'), h('span', { text }),
      ...keys.map((k) => h('kbd', { class: 'tour-kbd', text: k })));
    els.stage.append(ghost);
    const total = path.getTotalLength();
    const dur = 2200; // 0.9.1 : deux fois plus lent, plus facile à suivre
    let t0 = 0;
    const stepFn = (ts) => {
      if (!t0) t0 = ts;
      const k = Math.min(1, (ts - t0) / dur);
      const e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
      const pt = path.getPointAtLength(total * e);
      ghost.style.transform = `translate(${pt.x}px, ${pt.y}px) translate(-50%, -50%)`;
      ghost.style.opacity = String(k < 0.1 ? k * 10 : k > 0.9 ? (1 - k) * 10 : 1);
      if (k < 1) ctx.frame(stepFn);
      else {
        ghost.remove();
        resolve();
      }
    };
    ctx.frame(stepFn);
  });

  await ctx.wait(700);
  // Liste 1 → listes 2 et 3 : copie. Les listes 2 et 3 peuvent être courtes
  // (hauteur de leur contenu) : les flèches visent le haut de chacune.
  const sx = l1.right - 130;
  const y2 = l2.top + Math.min(64, l2.height / 2);
  const y3 = l3.top + Math.min(64, l3.height / 2);
  const mid = (sx + l2.left + 90) / 2;
  const p12 = arrow([{ x: sx, y: y2 + 70 }, { x: mid, y: y2 - 40 }, { x: l2.left + 90, y: y2 }], 'is-copy');
  label(t('tour.move.copy'), mid, y2 - 42);
  await fly(p12, names[0] || '');
  await ctx.wait(200);
  const p13 = arrow([{ x: sx, y: y3 + 70 }, { x: mid, y: y3 - 40 }, { x: l3.left + 90, y: y3 }], 'is-copy');
  label(t('tour.move.copy'), mid, y3 - 42);
  await fly(p13, names[2] || '');
  await ctx.wait(500);
  // Entre les listes 2 et 3 : déplacement (Ctrl : copie)
  const xA = l2.left + l2.width * 0.78;
  const xB = l2.left + l2.width * 0.56;
  const yTop = y2 + 40;
  const yBot = y3 - 26;
  const down = arrow([{ x: xA, y: yTop }, { x: xA + 46, y: (yTop + yBot) / 2 }, { x: xA, y: yBot }], 'is-move');
  const up = arrow([{ x: xB, y: yBot }, { x: xB - 46, y: (yTop + yBot) / 2 }, { x: xB, y: yTop }], 'is-move');
  label(t('tour.move.move'), xB - 70, (yTop + yBot) / 2 - 20, 'right');
  await fly(down, names[1] || '');
  await fly(up, names[3] || '', [t('tour.key_ctrl')]);
  await ctx.wait(500);
  // Vers la liste 1 : retirer
  const ry = Math.min(H - 190, y3 + 150);
  const back = arrow([{ x: l3.left + 80, y: ry - 30 }, { x: (l3.left + sx) / 2, y: ry + 40 }, { x: sx - 40, y: ry }], 'is-remove');
  label(t('tour.move.remove'), (l3.left + 80 + sx - 40) / 2, ry + 26);
  await fly(back, names[4] || '');
}

// -- Nouveaux mods dans les téléchargements (0.9.1) ------------------------------

const DEMO_DOWNLOADS = [
  ['FS25_Tractor6Cyl.zip', 'FS25'],
  ['FS22_HarvesterPack.zip', 'FS22'],
  ['FS25_SeedDrill6m.zip', 'FS25'],
];

function versionInfo(id) {
  return (store.app.versions || []).find((v) => v.id === id) || null;
}

function buildDownloads(ctx) {
  const btn = q('.find-new-btn');
  const br = rectOf(btn);
  if (!br) return [];
  const card = h('div', { class: 'tour-dl tour-fake' },
    h('div', { class: 'tour-dl-head' }, icon('folder-sync'), h('span', { text: t('downloads.title') })));
  const rows = [];
  for (const [file, vid] of DEMO_DOWNLOADS) {
    const v = versionInfo(vid);
    const row = h('div', { class: 'tour-dl-row' },
      icon('file', 'ico-s'), h('span', { class: 'tour-dl-name', text: file }), icon('arrow-right', 'ico-s tour-dl-to'),
      v ? gameLogo(v.logo, 'tour-dl-logo') : h('span', { text: vid }));
    card.append(row);
    rows.push(row);
  }
  els.stage.append(card);
  const { W } = appSize();
  const cw = card.offsetWidth;
  const left = Math.max(MARGIN, Math.min(W - cw - MARGIN, br.right - cw));
  Object.assign(card.style, { left: `${left}px`, top: `${br.bottom + 14}px` });
  ctx.data = { btn: br, card, rows };
  return [br, rectOf(card)];
}

async function playDownloads(ctx) {
  const { btn, card, rows } = ctx.data;
  if (!btn) return;
  ctx.cursorAt(btn.left - 90, btn.bottom + 70);
  await ctx.wait(700);
  await ctx.move(btn.left + btn.width * 0.55, btn.top + btn.height * 0.6, 620);
  const ring = ctx.ring(btn, 3);
  let tip = ctx.tip(t('list1.find_new'), btn, 'above');
  await ctx.wait(1300);
  await ctx.click();
  ctx.untip(tip);
  ring.remove();
  card.classList.add('on');
  for (const row of rows) {
    await ctx.wait(260);
    row.classList.add('on');
  }
  await ctx.wait(500);
  ctx.hideCursor();
  tip = ctx.tip(t('tour.downloads.found'), rectOf(card));
  await ctx.wait(2600);
  ctx.untip(tip);
}

// -- La croix et la zone de notification (0.9.1) -------------------------------

const SVG_ICONS = {
  // Logo de Démarrer : quatre carreaux
  start: '<rect x="3" y="3" width="8.5" height="8.5" rx=".6"/><rect x="12.5" y="3" width="8.5" height="8.5" rx=".6"/><rect x="3" y="12.5" width="8.5" height="8.5" rx=".6"/><rect x="12.5" y="12.5" width="8.5" height="8.5" rx=".6"/>',
  wifi: '<path d="M12 20h.01"/><path d="M2 8.82a15 15 0 0 1 20 0"/><path d="M5 12.86a10 10 0 0 1 14 0"/><path d="M8.5 16.43a5 5 0 0 1 7 0"/>',
  volume: '<path d="M11 4.7a.7.7 0 0 0-1.2-.5L6.4 7.6A1.4 1.4 0 0 1 5.4 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.4a1.4 1.4 0 0 1 1 .4l3.4 3.4a.7.7 0 0 0 1.2-.5z"/><path d="M16 9a5 5 0 0 1 0 6"/><path d="M19.4 18.4a9 9 0 0 0 0-12.8"/>',
};

function svgIcon(name, cls) {
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('class', cls);
  svg.innerHTML = SVG_ICONS[name];
  return svg;
}

function buildClose(ctx) {
  const { W, H } = appSize();
  // Boutons de fenêtre dessinés à leur place (les vrais n'apparaissent
  // qu'au survol de l'en-tête).
  const close = h('button', { class: 'win-btn win-close', type: 'button', tabindex: '-1' }, icon('window-close'));
  const controls = h('div', { class: 'win-controls is-near tour-fake tour-wc' },
    h('button', { class: 'win-btn', type: 'button', tabindex: '-1' }, icon('minus')),
    h('button', { class: 'win-btn', type: 'button', tabindex: '-1' }, icon('square')),
    close);
  els.stage.append(controls);
  // Aperçu de la barre des tâches de Windows : icônes cachées, horloge.
  const lang = document.documentElement.lang || undefined;
  const now = new Date();
  let time = '';
  let date = '';
  try {
    time = now.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' });
    date = now.toLocaleDateString(lang);
  } catch {
    time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  }
  const fs = h('span', { class: 'tour-tb-cell tour-tb-fs' },
    h('img', { src: '/assets/brand/tray.png', alt: '', draggable: 'false' }));
  const flyout = h('div', { class: 'tour-tb-flyout' },
    h('span', { class: 'tour-tb-cell' }, icon('shield')),
    h('span', { class: 'tour-tb-cell' }, icon('hard-drive')),
    fs,
    h('span', { class: 'tour-tb-cell' }, icon('package')));
  const chevron = h('span', { class: 'tour-tb-btn tour-tb-more' }, icon('chevron-down'));
  const bar = h('div', { class: 'tour-tb-bar' },
    h('span', { class: 'tour-tb-btn tour-tb-start' }, svgIcon('start', 'tour-tb-svg')),
    h('span', { class: 'tour-tb-gap' }),
    chevron,
    h('span', { class: 'tour-tb-btn tour-tb-sys' }, svgIcon('wifi', 'tour-tb-svg'), svgIcon('volume', 'tour-tb-svg')),
    h('span', { class: 'tour-tb-btn tour-tb-clock' }, h('span', { text: time }), h('span', { text: date })));
  const taskbar = h('div', { class: 'tour-taskbar tour-fake' }, flyout, bar);
  els.stage.append(taskbar);
  const tw = taskbar.offsetWidth;
  const th = bar.offsetHeight;
  Object.assign(taskbar.style, {
    left: `${Math.max(MARGIN, W - tw - MARGIN)}px`,
    top: `${H - 132 - th}px`,
  });
  // L'aperçu de la zone de notification s'ouvre au-dessus de la flèche.
  const cr = rectOf(chevron);
  const tr = rectOf(taskbar);
  const fw = flyout.offsetWidth;
  flyout.style.left = `${Math.round(cr.left + cr.width / 2 - fw / 2 - tr.left)}px`;
  ctx.data = { controls, close: rectOf(close), closeEl: close, taskbar, bar, flyout, chevron, fs };
  return [];
}

async function playClose(ctx) {
  const { controls, close, closeEl, taskbar, bar, flyout, chevron, fs } = ctx.data;
  if (!close) return;
  const { W } = appSize();
  ctx.cursorAt(W - 260, close.bottom + 150);
  await ctx.wait(800);
  await ctx.move(close.left + close.width * 0.5, close.top + close.height * 0.6, 640);
  closeEl.classList.add('is-hover');
  let tip = ctx.tip(t('tour.close.tip_close'), close);
  await ctx.wait(1500);
  await ctx.click();
  ctx.untip(tip);
  closeEl.classList.remove('is-hover');
  // La fenêtre se cache : la lumière glisse vers la barre des tâches.
  const arrow = els.stage.querySelector('.tour-arrow');
  if (arrow) arrow.classList.add('is-gone');
  controls.classList.add('is-gone');
  taskbar.classList.add('on');
  setSpot(els.spot, union([rectOf(bar)], 8));
  await ctx.wait(900);
  const cr = rectOf(chevron);
  await ctx.move(cr.left + cr.width * 0.55, cr.top + cr.height * 0.6, 760);
  chevron.classList.add('is-hover');
  tip = ctx.tip(t('tour.close.tip_more'), cr, 'above');
  await ctx.wait(1100);
  await ctx.click();
  ctx.untip(tip);
  chevron.classList.add('is-open');
  flyout.classList.add('on');
  setSpot(els.spot, union([rectOf(bar), rectOf(flyout)], 8));
  await ctx.wait(700);
  const fr = rectOf(fs);
  await ctx.move(fr.left + fr.width * 0.55, fr.top + fr.height * 0.6, 620);
  fs.classList.add('is-hover');
  tip = ctx.tip(t('tour.close.tip_icon'), fr, 'above');
  await ctx.wait(2800);
  ctx.untip(tip);
  fs.classList.remove('is-hover');
  ctx.hideCursor();
}
