// Glisser-déposer entre les trois listes (réponse).
//
// | Liste 1 → liste 2     | ajouter à la partie                       |
// | Liste 1 → liste 3     | ajouter aux mods communs                  |
// | Liste 2 → liste 3     | déplacer (retirer de la partie, ajouter)  |
// | Liste 3 → liste 2     | déplacer (retirer des communs, ajouter)   |
// | Liste 2 ou 3 → 1      | retirer de la liste d'origine             |
//
// Maintenir Ctrl pendant le glisser COPIE au lieu de déplacer,
// entre les listes 2 et 3 (le mod reste dans la liste d'origine). Ctrl ne change
// rien vers la liste 1, qui ne peut pas recevoir de copie.
//
// Glisser maison (événements de pointeur) : un badge suit la souris avec le
// nombre de mods déplacés ; la liste survolée s'éclaire si elle accepte le dépôt.

import { iconUrl } from './api.js';
import { h, icon } from './dom.js';
import { formatNumber } from './i18n.js';
import { toLocal } from './scale.js';
import { activeVersion, modIndex } from './state.js';

const THRESHOLD = 6;
let host = null;
let ghost = null;
let drag = null; // { src, ids, over: Element|null, ok: boolean, copy: boolean }
let opts = { accepts: () => false, drop: () => {}, over: () => {} };

export function initDnd(appEl, options) {
  host = appEl;
  opts = { ...opts, ...options };
  document.addEventListener('keydown', (e) => {
    if (drag && e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      end(null);
    }
  }, true);
}

export function isDragging() {
  return !!drag;
}

// Appui sur une tuile : glisser au-delà de quelques pixels, sinon clic.
// getIds() donne les identifiants à emporter au moment où le glisser commence.
export function trackDrag(e, src, getIds, onClick) {
  if (e.button !== 0) return;
  const sx = e.clientX;
  const sy = e.clientY;
  const pid = e.pointerId;
  let started = false;
  const move = (ev) => {
    if (ev.pointerId !== pid) return;
    if (!started) {
      if (Math.abs(ev.clientX - sx) + Math.abs(ev.clientY - sy) < THRESHOLD) return;
      const ids = getIds();
      if (!ids.length) {
        cleanup();
        return;
      }
      started = true;
      begin(src, ids);
    }
    if (drag) update(ev);
  };
  const up = (ev) => {
    if (ev.pointerId !== pid) return;
    cleanup();
    if (started) {
      if (drag) finish(ev);
    } else if (onClick) {
      onClick();
    }
  };
  const cancel = (ev) => {
    if (ev.pointerId !== pid) return;
    cleanup();
    if (drag) end(null);
  };
  function cleanup() {
    window.removeEventListener('pointermove', move, true);
    window.removeEventListener('pointerup', up, true);
    window.removeEventListener('pointercancel', cancel, true);
  }
  window.addEventListener('pointermove', move, true);
  window.addEventListener('pointerup', up, true);
  window.addEventListener('pointercancel', cancel, true);
}

function begin(src, ids) {
  drag = { src, ids, over: null, ok: false, copy: false };
  const first = modIndex().get(String(ids[0]).toLowerCase());
  const art = h('span', { class: 'dg-art' });
  if (first && first.icon) {
    art.append(h('img', { src: iconUrl(activeVersion(), first.icon, true), alt: '', draggable: 'false' }));
  } else {
    art.append(icon('package'));
  }
  ghost = h('div', { class: 'drag-ghost', 'aria-hidden': 'true' },
    ids.length > 1 ? h('span', { class: 'dg-stack' }) : null,
    art,
    h('span', { class: 'dg-count', text: formatNumber(ids.length) }));
  host.append(ghost);
  document.documentElement.classList.add('is-dragging');
}

// Ctrl maintenu : copie, sauf vers la liste 1.
function copyKey(ev) {
  return !!(ev.ctrlKey || ev.metaKey);
}

function update(ev) {
  const p = toLocal(ev.clientX, ev.clientY);
  ghost.style.translate = `${Math.round(p.x + 14)}px ${Math.round(p.y + 12)}px`;
  const hit = document.elementFromPoint(ev.clientX, ev.clientY);
  const target = hit ? hit.closest('[data-drop]') : null;
  const copy = copyKey(ev);
  if (target !== drag.over || copy !== drag.copy) {
    if (drag.over) drag.over.classList.remove('drop-ok', 'drop-no');
    drag.over = target;
    drag.copy = copy;
    drag.ok = false;
    if (target) {
      drag.ok = target.dataset.drop !== drag.src && opts.accepts(drag.src, target.dataset.drop, copy);
      if (target.dataset.drop !== drag.src) target.classList.add(drag.ok ? 'drop-ok' : 'drop-no');
    }
    opts.over(target && drag.ok ? target.dataset.drop : null);
  }
  ghost.classList.toggle('is-ok', drag.ok);
  ghost.classList.toggle('is-copy', drag.copy);
}

function finish(ev) {
  const d = drag;
  // Le relâchement ne doit pas déclencher de clic sur l'élément survolé.
  const stop = (e) => {
    e.stopPropagation();
    e.preventDefault();
  };
  window.addEventListener('click', stop, { capture: true, once: true });
  setTimeout(() => window.removeEventListener('click', stop, { capture: true }), 0);
  const copy = copyKey(ev);
  const ok = d.over && d.over.dataset.drop !== d.src && opts.accepts(d.src, d.over.dataset.drop, copy);
  end(ok ? d.over.dataset.drop : null, copy);
}

function end(dst, copy = false) {
  const d = drag;
  drag = null;
  if (d && d.over) d.over.classList.remove('drop-ok', 'drop-no');
  opts.over(null);
  document.documentElement.classList.remove('is-dragging');
  if (ghost) {
    const g = ghost;
    ghost = null;
    g.classList.add(dst ? 'out-ok' : 'out');
    setTimeout(() => g.remove(), 180);
  }
  if (d && dst) opts.drop(d.src, dst, d.ids, copy);
}
