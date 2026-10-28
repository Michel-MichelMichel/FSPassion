// Fenêtres internes (paramètres, anomalies, bienvenue, notice…), au-dessus
// de la page principale. Échap ferme ; le focus reste dans la fenêtre.

import { h, icon } from './dom.js';
import { makeDragZone } from './frame.js';
import { t } from './i18n.js';

let layer = null;
const stack = [];

export function initDialogs(el) {
  layer = el;
  document.addEventListener('keydown', (e) => {
    const top = stack[stack.length - 1];
    if (!top) return;
    if (e.key === 'Escape' && top.opts.dismissible !== false) {
      e.preventDefault();
      e.stopPropagation();
      top.close();
    } else if (e.key === 'Tab') {
      trapFocus(e, top.el);
    }
  }, true);
}

function trapFocus(e, el) {
  const items = [...el.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')]
    .filter((x) => !x.disabled && x.offsetParent !== null);
  if (!items.length) return;
  const first = items[0];
  const last = items[items.length - 1];
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault();
    first.focus();
  }
}

export function isDialogOpen() {
  return stack.length > 0;
}

// opts : { title, cls, dismissible, backdropClose, dragWindow, onClose, headerExtra }
// dragWindow (0.8.4) : tout le fond (voile et zones vides de la fenêtre
// interne) déplace la fenêtre de FS Passion, comme l'en-tête.
export function openDialog(body, opts = {}) {
  const prevFocus = document.activeElement;
  const closeBtn = opts.dismissible === false ? null
    : h('button', { class: 'icon-btn', type: 'button', 'data-i18n-tip': 'common.close', 'aria-label': t('common.close') }, icon('x'));
  const head = opts.title === undefined ? null
    : h('header', { class: 'dlg-head' },
      h('h2', { class: 'dlg-title', text: opts.title }),
      opts.headerExtra || null,
      closeBtn);
  const panel = h('div', { class: `dlg ${opts.cls || ''}`.trim(), role: 'dialog', 'aria-modal': 'true' }, head, body);
  if (opts.title) panel.setAttribute('aria-label', opts.title);
  const backdrop = h('div', { class: 'dlg-backdrop' }, panel);
  const ctrl = {
    el: panel,
    opts,
    closed: false,
    close() {
      if (ctrl.closed) return;
      ctrl.closed = true;
      const i = stack.indexOf(ctrl);
      if (i >= 0) stack.splice(i, 1);
      backdrop.classList.remove('on');
      backdrop.classList.add('out');
      setTimeout(() => backdrop.remove(), 240);
      if (opts.onClose) opts.onClose();
      if (prevFocus && prevFocus.focus) prevFocus.focus();
      layer.classList.toggle('has-dialog', stack.length > 0);
      document.dispatchEvent(new CustomEvent('fsp-dialog-closed'));
    },
  };
  if (closeBtn) closeBtn.addEventListener('click', () => ctrl.close());
  backdrop.addEventListener('pointerdown', (e) => {
    if (e.target === backdrop && opts.dismissible !== false && opts.backdropClose !== false) ctrl.close();
  });
  if (opts.dragWindow) {
    backdrop.classList.add('is-drag-zone');
    makeDragZone(backdrop);
  }
  layer.append(backdrop);
  layer.classList.add('has-dialog');
  stack.push(ctrl);
  requestAnimationFrame(() => {
    backdrop.classList.add('on');
    const focusable = panel.querySelector('[autofocus]') || panel.querySelector('button:not(.icon-btn), input, select') || closeBtn;
    if (focusable) focusable.focus({ preventScroll: true });
  });
  return ctrl;
}

// Petite fenêtre de confirmation. Renvoie une promesse (true / false).
export function confirmDialog({ title, text, ok, cancel, danger = false }) {
  return new Promise((resolve) => {
    let result = false;
    const body = h('div', { class: 'dlg-body' },
      h('p', { class: 'dlg-text', text }),
      h('div', { class: 'dlg-actions' },
        h('button', { class: 'btn btn-ghost', type: 'button', text: cancel || t('common.cancel'), onclick: () => ctrl.close() }),
        h('button', { class: `btn ${danger ? 'btn-danger' : 'btn-primary'}`, type: 'button', autofocus: true, text: ok || t('common.ok'),
          onclick: () => { result = true; ctrl.close(); } }),
      ));
    const ctrl = openDialog(body, { title, cls: 'dlg-s', onClose: () => resolve(result) });
  });
}
