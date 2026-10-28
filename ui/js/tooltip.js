// Infobulles traduites des boutons à icône (5.2). Accessibles au clavier :
// elles apparaissent aussi quand l'élément reçoit le focus.

import { t } from './i18n.js';
import { localRect } from './scale.js';

let tipEl = null;
let timer = 0;
let target = null;

function textOf(el) {
  if (el.dataset.tipText) return el.dataset.tipText;
  if (el.dataset.i18nTip) return t(el.dataset.i18nTip);
  return '';
}

function show(el) {
  const text = textOf(el);
  if (!text) return;
  tipEl.textContent = text;
  tipEl.classList.add('on');
  const r = localRect(el);
  const app = tipEl.parentElement;
  const W = app.clientWidth;
  const H = app.clientHeight;
  const tw = tipEl.offsetWidth;
  const th = tipEl.offsetHeight;
  let x = r.left + r.width / 2 - tw / 2;
  x = Math.max(12, Math.min(W - tw - 12, x));
  let y = r.bottom + 10;
  if (y + th > H - 12) y = r.top - th - 10;
  tipEl.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
}

function hide() {
  clearTimeout(timer);
  target = null;
  if (tipEl) tipEl.classList.remove('on');
}

export function initTooltips(el) {
  tipEl = el;
  const find = (node) => node && node.closest && node.closest('[data-i18n-tip], [data-tip-text]');
  document.addEventListener('pointerover', (e) => {
    const el2 = find(e.target);
    if (el2 === target) return;
    hide();
    if (!el2) return;
    target = el2;
    timer = setTimeout(() => target === el2 && show(el2), 450);
  });
  document.addEventListener('pointerdown', hide, true);
  document.addEventListener('focusin', (e) => {
    const el2 = find(e.target);
    if (el2 && el2.matches(':focus-visible')) {
      target = el2;
      show(el2);
    }
  });
  document.addEventListener('focusout', hide);
  window.addEventListener('blur', hide);
  document.addEventListener('scroll', hide, true);
}

