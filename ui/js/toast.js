// Messages courts : en bas à droite, au-dessus du pied de page.
// Ils disparaissent après 6 secondes (10 pour un avertissement), et restent
// tant que la souris est dessus ; les erreurs restent jusqu'à leur fermeture.
//
// Chaque message est aussi gardé dans l'historique des notifications
// (bouton cloche de l'en-tête) : un message disparu trop vite peut être relu.

import { h, icon } from './dom.js';
import { t } from './i18n.js';

let host = null;

const HISTORY_MAX = 60;
const history = []; // du plus ancien au plus récent : { id, text, level, time, read }
const listeners = new Set();
let nextId = 1;

export function initToasts(el) {
  host = el;
}

const ICONS = { info: 'info', success: 'circle-check', warn: 'triangle-alert', error: 'circle-alert' };
const DURATION = { info: 6000, success: 6000, warn: 10000 };

export function levelIcon(level) {
  return ICONS[level] || 'info';
}

export function toast(key, params = {}, level = 'info', action = null) {
  return toastText(t(key, params), level, action);
}

function remember(text, level) {
  history.push({ id: nextId++, text, level, time: new Date(), read: false });
  while (history.length > HISTORY_MAX) history.shift();
  for (const fn of listeners) fn();
}

export function toastText(text, level = 'info', action = null) {
  remember(text, level);
  if (!host) return null;
  let timer = 0;
  const close = () => {
    clearTimeout(timer);
    el.classList.add('out');
    setTimeout(() => el.remove(), 220);
  };
  const el = h('div', { class: `toast toast-${level}`, role: level === 'error' ? 'alert' : 'status' },
    icon(levelIcon(level), 'toast-ico'),
    h('div', { class: 'toast-text', text }),
    action ? h('button', { class: 'btn btn-ghost btn-s', type: 'button', text: action.label, onclick: () => { action.run(); close(); } }) : null,
    h('button', { class: 'icon-btn icon-btn-s', type: 'button', 'data-i18n-tip': 'common.close', 'aria-label': t('common.close'), onclick: close }, icon('x')),
  );
  host.append(el);
  while (host.children.length > 4) host.firstElementChild.remove();
  if (level !== 'error') {
    const ms = DURATION[level] || 6000;
    const arm = () => {
      clearTimeout(timer);
      timer = setTimeout(close, ms);
    };
    // La souris sur le message le garde affiché.
    el.addEventListener('pointerenter', () => clearTimeout(timer));
    el.addEventListener('pointerleave', arm);
    arm();
  }
  return el;
}

// Erreur renvoyée par l'API : message traduit, jamais vide.
export function toastError(err) {
  const key = err && err.key ? err.key : 'error.unexpected';
  return toast(key, (err && err.params) || {}, 'error');
}

// -- Historique (cloche) ---------------------------------------------------

// Entrée de la cloche seulement, sans message à l'écran (mise à jour
// disponible : un repère discret, pas une notification qui surgit).
export function noteOnly(text, level = 'info') {
  remember(text, level);
}

export function notifications() {
  return history.slice().reverse();
}

export function unreadCount() {
  return history.reduce((n, x) => n + (x.read ? 0 : 1), 0);
}

export function markAllRead() {
  let changed = false;
  for (const x of history) {
    if (!x.read) {
      x.read = true;
      changed = true;
    }
  }
  if (changed) for (const fn of listeners) fn();
}

export function clearNotifications() {
  history.length = 0;
  for (const fn of listeners) fn();
}

export function onNotifications(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
