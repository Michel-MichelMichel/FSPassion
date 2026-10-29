// Listes 2 (Mods de la partie) et 3 (Mods communs), à droite.
//
// - Tuiles horizontales de hauteur fixe : petite icône à gauche, nom à droite.
//   Seules les tuiles proches de la vue sont dessinées.
// - Hauteurs : 50 % chacune par défaut ; une liste courte prend la hauteur de
//   son contenu et laisse la place à l'autre. Au survol (ou pendant un
//   glisser), une liste qui déborde s'agrandit avec une animation douce.
// - Survol d'une tuile : icône agrandie à ~300 px, en vraies couleurs.
// - Défilement animé : un cran de molette fait glisser la liste de trois
//   tuiles ; un repère affiche le nom du mod au centre pendant un défilement.
//   Comme dans la liste 1, les tuiles s'affichent sans délai.
// - Mod manquant : tuile atténuée, icône d'alerte, « Remplacer par… ».

import { isDemo } from './demo.js';
import { displayName, removeMods, replaceMissing } from './actions.js';
import { iconUrl } from './api.js';
import { trackDrag } from './dnd.js';
import { clear, h, icon, reducedMotion } from './dom.js';
import { currentLang, formatNumber, modTitle, t } from './i18n.js';
import { localRect, toLocal } from './scale.js';
import {
  clearSelection, isSelected, onSelection, pressTile, rangeTo, registerList, selectedIds, selectionList,
  setActiveList, setSelection, toggle,
} from './selection.js';
import {
  EMPTY, FULL, activeVersion, membership, modIndex, partiesSupported, selectedParty, store, userParty, versionInfo,
} from './state.js';

const ROW_H = 64; // Police agrandie
const WHEEL_ROWS = 3;
const WHEEL_MS = 170;
const STABLE_MS = 100;
const HINT_DELAY = 300;
const HINT_HIDE = 400;
const PREVIEW_DELAY = 220;
const MIN_OTHER_ROWS = 2;

let side = null;
let previewEl = null;
const panes = {};
let hover = null; // liste survolée
let dragOver = null; // liste survolée pendant un glisser
let firstLayout = true;
let lastPartyKey = null;

export function initSideLists(el, previewHost) {
  side = el;
  previewEl = previewHost;
  panes.l2 = new RowList('l2');
  panes.l3 = new RowList('l3');
  side.append(panes.l2.el, panes.l3.el);
  for (const id of ['l2', 'l3']) {
    registerList(id, {
      order: () => panes[id].items.map((it) => it.key),
      idOf: (key) => (panes[id].byKey.get(key) || {}).id || key,
    });
  }
  onSelection(() => {
    panes.l2.decorateAll();
    panes.l3.decorateAll();
  });
  new ResizeObserver(() => layoutSide()).observe(side);
}

// Pendant un glisser, la liste survolée s'agrandit (si elle déborde).
export function setDragOver(list) {
  const v = list === 'l2' || list === 'l3' ? list : null;
  if (v === dragOver) return;
  dragOver = v;
  layoutSide();
}

// ---------------------------------------------------------------------------
// Une liste de tuiles horizontales
// ---------------------------------------------------------------------------

class RowList {
  constructor(id) {
    this.id = id;
    this.items = [];
    this.byKey = new Map();
    this.attached = new Map();
    this.focusKey = null;
    this.focusInside = false;
    this.wheel = { raf: 0, target: null, from: 0, start: 0, acc: 0, last: 0 };
    this.scroll = { active: false, scrolling: false, start: 0, dist: 0, lastTop: 0, stable: 0, hint: 0, hide: 0, end: -1e9 };
    this.previewTimer = 0;
    this.chrome = 0;
    this.deployFrom = 0;

    this.titleEl = h('h2', { class: 'side-title mgrad' });
    this.countEl = h('span', { class: 'side-count' });
    this.noteEl = h('span', { class: 'side-note' });
    this.head = h('div', { class: 'side-head' }, this.titleEl, this.countEl);
    this.emptyEl = h('div', { class: 'side-empty-wrap' });
    this.canvas = h('div', { class: 'side-canvas' });
    this.body = h('div', {
      class: 'side-body', role: 'listbox', tabindex: '-1', 'aria-multiselectable': 'true',
    }, this.canvas);
    this.hintEl = h('div', { class: 'scroll-hint side-hint', 'aria-hidden': 'true' }, h('div', { class: 'hint-name' }));
    this.el = h('section', { class: 'side-pane', 'data-drop': id }, this.head, this.noteEl, this.emptyEl, this.body, this.hintEl);

    this.body.addEventListener('scroll', () => this.onScroll(), { passive: true });
    this.body.addEventListener('wheel', (e) => this.onWheel(e), { passive: false });
    this.body.addEventListener('pointerdown', (e) => this.onPointerDown(e));
    this.body.addEventListener('keydown', (e) => this.onKeyDown(e));
    this.body.addEventListener('focusin', () => {
      this.focusInside = true;
      setActiveList(this.id);
    });
    this.body.addEventListener('focusout', (e) => {
      if (!this.body.contains(e.relatedTarget)) this.focusInside = false;
    });
    this.el.addEventListener('pointerenter', (e) => {
      if (e.pointerType === 'mouse') {
        hover = this.id;
        layoutSide();
      }
    });
    this.el.addEventListener('pointerleave', () => {
      if (hover === this.id) hover = null;
      layoutSide();
    });
    new ResizeObserver(() => this.render()).observe(this.body);
  }

  // -- contenu ---------------------------------------------------------------

  set({ title, count, note, items, empty, muted, animate = false }) {
    this.titleEl.textContent = title;
    this.countEl.textContent = count === null || count === undefined ? '' : formatNumber(count);
    this.noteEl.textContent = note || '';
    this.el.classList.toggle('is-muted', !!muted);
    this.items = items;
    this.byKey = new Map(items.map((it) => [it.key, it]));
    // Les tuiles inchangées restent (pas de nouveau décodage d'icône) ; les
    // autres sont refaites.
    for (const [k, el] of this.attached) {
      const it = this.byKey.get(k);
      if (!it || it.sig !== el._item.sig) this.release(k, el);
      else el._item = it;
    }
    clear(this.emptyEl);
    if (empty && !items.length) this.emptyEl.append(empty);
    this.body.hidden = !items.length;
    this.canvas.style.height = `${items.length * ROW_H}px`;
    if (animate) {
      // Nouveau contenu (changement de partie) : les tuiles apparaissent
      // les unes après les autres, avec un micro-délai.
      for (const [k, el] of this.attached) this.release(k, el);
      this.body.scrollTop = 0;
      this.deployFrom = performance.now();
    }
    this.render();
    this.deployFrom = 0;
  }

  // Hauteur de la liste entière (sans défilement).
  natural() {
    if (!this.chrome && this.head.offsetHeight) {
      const cs = getComputedStyle(this.el);
      this.chrome = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom) + this.head.offsetHeight
        + parseFloat(getComputedStyle(this.head).marginBottom);
    }
    const content = this.items.length ? this.items.length * ROW_H : this.emptyEl.offsetHeight;
    return Math.ceil((this.chrome || 74) + content);
  }

  minHeight() {
    return Math.min(this.natural(), Math.ceil((this.chrome || 74) + MIN_OTHER_ROWS * ROW_H));
  }

  // -- dessin ----------------------------------------------------------------

  makeRow(it) {
    const art = h('div', { class: 'row-art' });
    if (it.mod && it.mod.icon) {
      const img = h('img', { class: 'row-img', alt: '', draggable: 'false', decoding: 'async' });
      img.addEventListener('load', () => img.classList.add('loaded'));
      img.dataset.src = iconUrl(activeVersion(), it.mod.icon, true);
      art.append(img);
    } else {
      art.append(icon(it.missing ? 'triangle-alert' : 'package'));
    }
    const text = h('div', { class: 'row-text' }, h('span', { class: 'row-name', text: it.name }));
    if (it.missing) text.append(h('span', { class: 'row-sub', text: t('lists.missing') }));
    const el = h('div', {
      class: `row-tile${it.missing ? ' is-missing' : ''}`, role: 'option', tabindex: '-1', 'aria-label': it.name,
    }, art, text);
    if (it.mod && it.mod.is_map) el.append(h('span', { class: 'row-badge', 'data-i18n-tip': 'mod.map' }, icon('map', 'ico-s')));
    if (it.mod && isDemo()) el.append(h('span', { class: 'row-badge', 'data-i18n-tip': 'demo.badge' }, icon('flask-conical', 'ico-s')));
    // Repère posé sur la miniature, en bas à droite (comme les tuiles de la liste 1).
    el._marks = h('span', { class: 'row-marks' });
    el._marksSig = '';
    art.append(el._marks);
    if (it.missing) {
      el.dataset.tipText = t('lists.missing_tip', { name: it.id });
      el.append(h('button', {
        class: 'btn btn-s row-replace', type: 'button', tabindex: '-1',
        onclick: (e) => {
          e.stopPropagation();
          replaceMissing(it.id);
        },
      }, t('lists.replace')));
    }
    el.dataset.key = it.key;
    el._item = it;
    el.addEventListener('pointerenter', () => this.schedulePreview(el));
    el.addEventListener('pointerleave', () => hidePreview(el));
    el.addEventListener('focus', () => {
      this.focusKey = it.key;
    });
    return el;
  }

  release(key, el) {
    this.attached.delete(key);
    if (el === document.activeElement) this.body.focus({ preventScroll: true });
    el.remove();
  }

  render() {
    const n = this.items.length;
    if (!n || this.body.hidden) {
      for (const [k, el] of this.attached) this.release(k, el);
      return;
    }
    const top = this.body.scrollTop;
    const vh = this.body.clientHeight || ROW_H * 6;
    const from = Math.max(0, Math.floor((top - vh * 0.5) / ROW_H));
    const to = Math.min(n - 1, Math.ceil((top + vh * 1.5) / ROW_H));
    const wanted = new Set();
    for (let i = from; i <= to; i++) {
      const it = this.items[i];
      wanted.add(it.key);
      let el = this.attached.get(it.key);
      if (!el) {
        el = this.makeRow(it);
        this.attached.set(it.key, el);
        this.canvas.append(el);
        const img = el.querySelector('.row-img');
        if (img) img.src = img.dataset.src; // sans délai
        if (this.deployFrom && !reducedMotion()) {
          el.style.setProperty('--deploy-delay', `${Math.min(i * 15, 300)}ms`);
          el.classList.add('deploy');
          el.addEventListener('animationend', () => el.classList.remove('deploy'), { once: true });
        }
      }
      el._i = i;
      el.style.translate = `0 ${i * ROW_H}px`;
    }
    for (const [k, el] of this.attached) if (!wanted.has(k)) this.release(k, el);
    this.decorateAll();
    if (this.focusInside && this.attached.has(this.focusKey)) {
      const el = this.attached.get(this.focusKey);
      if (document.activeElement !== el) el.focus({ preventScroll: true });
    }
  }

  decorateAll() {
    const m = membership();
    let tabKey = this.attached.has(this.focusKey) ? this.focusKey : null;
    if (!tabKey) {
      let best = null;
      for (const el of this.attached.values()) {
        if (el._i * ROW_H + ROW_H > this.body.scrollTop && (!best || el._i < best._i)) best = el;
      }
      tabKey = best ? best.dataset.key : null;
    }
    for (const el of this.attached.values()) {
      const it = el._item;
      const sel = isSelected(this.id, it.key);
      el.classList.toggle('is-selected', sel);
      el.setAttribute('aria-selected', sel ? 'true' : 'false');
      el.tabIndex = it.key === tabKey ? 0 : -1;
      // Repère discret : le mod est aussi dans l'autre liste.
      const other = this.id === 'l2' ? m.common.has(it.key) : m.party.has(it.key);
      const sig = other ? 'o' : '';
      if (sig !== el._marksSig) {
        el._marksSig = sig;
        clear(el._marks);
        if (other) {
          const key = this.id === 'l2' ? 'list1.mark_common' : 'list1.mark_party';
          el._marks.append(h('span', { class: `mark ${this.id === 'l2' ? 'mark-common' : 'mark-party'}`, 'data-i18n-tip': key, 'aria-label': t(key) }));
        }
      }
    }
  }

  // -- défilement animé ----------------------------------------------------------

  onWheel(e) {
    if (e.ctrlKey || !this.items.length) return;
    const unit = e.deltaMode === 1 ? 40 : e.deltaMode === 2 ? this.body.clientHeight : 1;
    const dy = e.deltaY * unit;
    if (!dy || Math.abs(e.deltaX) > Math.abs(dy)) return;
    const max = Math.max(0, this.body.scrollHeight - this.body.clientHeight);
    if (!max) return;
    e.preventDefault();
    const w = this.wheel;
    const now = performance.now();
    if (now - w.last > 220) w.acc = 0;
    w.last = now;
    let step = 0;
    if (Math.abs(dy) >= 50) step = Math.sign(dy);
    else {
      w.acc += dy;
      if (Math.abs(w.acc) >= 100) {
        step = Math.sign(w.acc);
        w.acc = 0;
      }
    }
    if (!step) return;
    const base = w.target ?? this.body.scrollTop;
    const snapped = Math.round(base / ROW_H) * ROW_H;
    this.glideTo(Math.max(0, Math.min(max, snapped + step * WHEEL_ROWS * ROW_H)));
  }

  glideTo(target) {
    const w = this.wheel;
    w.from = this.body.scrollTop;
    w.target = target;
    w.start = performance.now();
    if (reducedMotion()) {
      this.stopWheel();
      this.body.scrollTop = target;
      return;
    }
    const step = () => {
      w.raf = 0;
      if (w.target === null) return;
      const k0 = Math.min(1, (performance.now() - w.start) / WHEEL_MS);
      this.body.scrollTop = w.from + (w.target - w.from) * (1 - (1 - k0) ** 3);
      if (k0 < 1) w.raf = requestAnimationFrame(step);
      else w.target = null;
    };
    if (!w.raf) w.raf = requestAnimationFrame(step);
  }

  stopWheel() {
    if (this.wheel.raf) cancelAnimationFrame(this.wheel.raf);
    this.wheel.raf = 0;
    this.wheel.target = null;
  }

  onScroll() {
    const s = this.scroll;
    const now = performance.now();
    const top = this.body.scrollTop;
    hidePreview();
    if (!s.active) {
      s.active = true;
      s.start = now;
      s.dist = 0;
      s.lastTop = top;
      clearTimeout(s.hint);
      if (now - s.end < HINT_HIDE) {
        s.start = now - HINT_DELAY;
        this.enterScrolling();
      } else {
        s.hint = setTimeout(() => s.active && this.enterScrolling(), HINT_DELAY);
      }
    }
    s.dist += Math.abs(top - s.lastTop);
    s.lastTop = top;
    if (!s.scrolling && s.dist > this.body.clientHeight * 1.2) this.enterScrolling();
    if (s.scrolling) this.updateHint();
    clearTimeout(s.stable);
    s.stable = setTimeout(() => this.onStable(), STABLE_MS);
    this.render();
  }

  enterScrolling() {
    const s = this.scroll;
    if (s.scrolling) return;
    s.scrolling = true;
    this.body.classList.add('is-scrolling');
    clearTimeout(s.hide);
    this.updateHint();
    this.hintEl.classList.add('on');
  }

  onStable() {
    const s = this.scroll;
    if (this.wheel.target !== null) {
      s.stable = setTimeout(() => this.onStable(), STABLE_MS);
      return;
    }
    s.active = false;
    s.end = performance.now();
    clearTimeout(s.hint);
    this.endScrolling();
  }

  endScrolling() {
    const s = this.scroll;
    if (!s.scrolling) return;
    s.scrolling = false;
    this.body.classList.remove('is-scrolling');
    clearTimeout(s.hide);
    s.hide = setTimeout(() => this.hintEl.classList.remove('on'), HINT_HIDE);
  }

  updateHint() {
    if (!this.items.length) return;
    const center = this.body.scrollTop + this.body.clientHeight / 2;
    const i = Math.max(0, Math.min(this.items.length - 1, Math.floor(center / ROW_H)));
    this.hintEl.firstChild.textContent = this.items[i].name;
  }

  // -- souris : sélection, glisser, lasso ---------------------------------------------

  onPointerDown(e) {
    if (e.button !== 0) return;
    this.stopWheel();
    setActiveList(this.id);
    hidePreview();
    if (e.target === this.body && e.offsetX >= this.body.clientWidth) return; // ascenseur
    let target = e.target;
    if (this.scroll.scrolling) {
      // Clic juste après un défilement : les tuiles redeviennent cliquables.
      this.endScrolling();
      target = document.elementFromPoint(e.clientX, e.clientY) || target;
    }
    if (target.closest('.row-replace')) return;
    const row = target.closest('.row-tile');
    if (row && row._item) {
      this.focusKey = row.dataset.key;
      const after = pressTile(e, this.id, row._item.key);
      trackDrag(e, this.id, () => (selectionList() === this.id ? selectedIds() : []), after);
      return;
    }
    this.startLasso(e);
  }

  // Lasso vertical depuis une zone vide de la liste.
  startLasso(e) {
    e.preventDefault();
    this.body.focus({ preventScroll: true });
    const additive = e.ctrlKey || e.metaKey;
    const base = additive && selectionList() === this.id ? this.items.filter((it) => isSelected(this.id, it.key)).map((it) => it.key) : [];
    const point = (ev) => {
      const p = toLocal(ev.clientX, ev.clientY);
      const r = localRect(this.canvas);
      return { x: p.x - r.left, y: p.y - r.top };
    };
    const start = point(e);
    const pid = e.pointerId;
    let box = null;
    let sig = '';
    this.body.setPointerCapture(pid);
    const move = (ev) => {
      if (ev.pointerId !== pid) return;
      if (!box && Math.abs(ev.clientX - e.clientX) + Math.abs(ev.clientY - e.clientY) < 5) return;
      const p = point(ev);
      const y1 = Math.max(0, Math.min(start.y, p.y));
      const y2 = Math.max(start.y, p.y);
      const x1 = Math.min(start.x, p.x);
      if (!box) {
        box = h('div', { class: 'lasso' });
        this.canvas.append(box);
      }
      box.style.translate = `${x1}px ${y1}px`;
      box.style.width = `${Math.abs(p.x - start.x)}px`;
      box.style.height = `${y2 - y1}px`;
      const hit = [];
      for (let i = Math.floor(y1 / ROW_H); i < this.items.length && i * ROW_H < y2; i++) hit.push(this.items[i].key);
      const keys = base.concat(hit.filter((k) => !base.includes(k)));
      const s = keys.join('|');
      if (s !== sig) {
        sig = s;
        if (keys.length) setSelection(this.id, keys, { anchor: hit[0] || null });
        else clearSelection();
      }
    };
    const up = (ev) => {
      if (ev.pointerId !== pid) return;
      this.body.removeEventListener('pointermove', move);
      this.body.removeEventListener('pointerup', up);
      this.body.removeEventListener('pointercancel', up);
      if (box) box.remove();
      else if (!additive) clearSelection();
    };
    this.body.addEventListener('pointermove', move);
    this.body.addEventListener('pointerup', up);
    this.body.addEventListener('pointercancel', up);
  }

  // -- clavier -----------------------------------------------------------------------

  focusIndex(i, extend) {
    const it = this.items[Math.max(0, Math.min(this.items.length - 1, i))];
    if (!it) return;
    this.focusKey = it.key;
    const idx = this.items.indexOf(it);
    const top = this.body.scrollTop;
    const vh = this.body.clientHeight;
    if (idx * ROW_H < top) this.body.scrollTop = idx * ROW_H;
    else if ((idx + 1) * ROW_H > top + vh) this.body.scrollTop = (idx + 1) * ROW_H - vh;
    this.render();
    const el = this.attached.get(it.key);
    if (el) el.focus({ preventScroll: true });
    if (extend) rangeTo(this.id, it.key);
  }

  onKeyDown(e) {
    if (!this.items.length || e.target.closest('button')) return;
    const cur = this.items.findIndex((it) => it.key === this.focusKey);
    const page = Math.max(1, Math.floor(this.body.clientHeight / ROW_H) - 1);
    const moves = { ArrowDown: 1, ArrowUp: -1, PageDown: page, PageUp: -page };
    if (e.key in moves) {
      e.preventDefault();
      this.focusIndex(cur < 0 ? 0 : cur + moves[e.key], e.shiftKey);
    } else if (e.key === 'Home' || e.key === 'End') {
      e.preventDefault();
      this.focusIndex(e.key === 'Home' ? 0 : this.items.length - 1, e.shiftKey);
    } else if (e.key === ' ' && cur >= 0) {
      e.preventDefault();
      if (e.shiftKey) rangeTo(this.id, this.items[cur].key);
      else toggle(this.id, this.items[cur].key);
    } else if (e.key === 'Enter' && cur >= 0 && this.items[cur].missing) {
      e.preventDefault();
      replaceMissing(this.items[cur].id);
    } else if (e.key === 'Delete' && cur >= 0) {
      // Suppr : retirer de la liste (jamais une suppression de fichier).
      e.preventDefault();
      e.stopPropagation();
      const ids = selectionList() === this.id ? selectedIds() : [this.items[cur].id];
      removeMods(this.id === 'l2' ? 'party' : 'common', ids);
    }
  }

  // -- aperçu de l'icône à ~300 px ------------------------------------------------------

  schedulePreview(el) {
    clearTimeout(this.previewTimer);
    // Un mod manquant n'a pas d'icône à agrandir.
    const cls = document.documentElement.classList;
    if (el._item.missing || this.scroll.scrolling || cls.contains('is-dragging') || cls.contains('is-resizing')) return;
    this.previewTimer = setTimeout(() => showPreview(el), PREVIEW_DELAY);
  }
}

// ---------------------------------------------------------------------------
// Aperçu
// ---------------------------------------------------------------------------

let previewFor = null;

function showPreview(el) {
  const cls = document.documentElement.classList;
  if (!previewEl || !el.isConnected || cls.contains('is-dragging') || cls.contains('is-resizing')) return;
  const it = el._item;
  previewFor = el;
  clear(previewEl);
  const art = h('div', { class: 'pv-art' });
  if (it.mod && it.mod.icon) art.append(h('img', { src: iconUrl(activeVersion(), it.mod.icon), alt: '', draggable: 'false' }));
  else art.append(icon(it.missing ? 'triangle-alert' : 'package'));
  // Nom complet, puis le nom du fichier.
  const file = it.mod ? it.mod.file : it.id;
  previewEl.append(art, h('div', { class: 'pv-name', text: it.name }));
  if (file && file !== it.name) previewEl.append(h('div', { class: 'pv-title', text: file }));
  const wasOn = previewEl.classList.contains('on');
  if (!wasOn) {
    previewEl.style.transition = 'none';
    previewEl.classList.remove('on');
  }
  const r = localRect(el);
  const host = previewEl.parentElement;
  const ph = previewEl.offsetHeight;
  const x = r.left - previewEl.offsetWidth - 22;
  let y = r.top + r.height / 2 - 150;
  y = Math.max(16, Math.min(host.clientHeight - ph - 16, y));
  previewEl.style.translate = `${Math.round(x)}px ${Math.round(y)}px`;
  if (!wasOn) {
    void previewEl.offsetWidth;
    previewEl.style.transition = '';
  }
  previewEl.classList.add('on');
}

export function hidePreview(el) {
  if (el && el !== previewFor) {
    for (const p of Object.values(panes)) clearTimeout(p.previewTimer);
    return;
  }
  for (const p of Object.values(panes)) clearTimeout(p.previewTimer);
  previewFor = null;
  if (previewEl) previewEl.classList.remove('on');
}

// ---------------------------------------------------------------------------
// Hauteurs des deux listes
// ---------------------------------------------------------------------------

function layoutSide() {
  if (!side || !panes.l2) return;
  const cs = getComputedStyle(side);
  const gap = parseFloat(cs.rowGap) || 14;
  const avail = side.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom) - gap;
  if (avail <= 0) return;
  const n2 = panes.l2.natural();
  const n3 = panes.l3.natural();
  const half = avail / 2;
  let r2 = half;
  let r3 = half;
  if (n2 <= half && n3 > half) {
    r2 = n2;
    r3 = avail - n2;
  } else if (n3 <= half && n2 > half) {
    r3 = n3;
    r2 = avail - n3;
  }
  const grow = dragOver || hover;
  if (grow === 'l2' && n2 > r2) {
    r2 = Math.max(r2, Math.min(n2, avail - panes.l3.minHeight()));
    r3 = avail - r2;
  } else if (grow === 'l3' && n3 > r3) {
    r3 = Math.max(r3, Math.min(n3, avail - panes.l2.minHeight()));
    r2 = avail - r3;
  }
  side.classList.toggle('no-anim', firstLayout);
  side.style.gridTemplateRows = `${Math.floor(r2)}px ${Math.floor(r3)}px`;
  if (firstLayout) {
    void side.offsetWidth;
    firstLayout = false;
    requestAnimationFrame(() => side.classList.remove('no-anim'));
  }
}

// ---------------------------------------------------------------------------
// Contenu des deux listes
// ---------------------------------------------------------------------------

function collator() {
  try {
    return new Intl.Collator(currentLang(), { sensitivity: 'base', numeric: true });
  } catch {
    return new Intl.Collator('en', { sensitivity: 'base', numeric: true });
  }
}

function itemsOf(ids) {
  const index = modIndex();
  const coll = collator();
  const lib = store.library;
  const ready = lib && lib.status === 'ready';
  const out = ids.map((id) => {
    const low = id.toLowerCase();
    const mod = index.get(low) || null;
    // Un mod absent n'est « manquant » qu'une fois la lecture des mods terminée.
    const missing = !mod && !!ready;
    return {
      key: low, id: mod ? mod.id : id, mod, missing, name: mod ? modTitle(mod) : displayName(id),
      sig: `${mod ? mod.icon || '' : ''}|${missing ? 1 : 0}|${mod ? modTitle(mod) : id}`,
    };
  });
  // La map (ou les maps) en tête de liste, puis l'ordre alphabétique.
  const isMap = (it) => (it.mod && it.mod.is_map ? 1 : 0);
  out.sort((a, b) => isMap(b) - isMap(a) || coll.compare(a.name, b.name));
  return out;
}

function emptyBox(ico, strong, text) {
  return h('div', { class: 'side-empty' }, icon(ico), h('div', {}, strong ? h('strong', { text: strong }) : null, text ? h('span', { text }) : null));
}

export function renderSideLists() {
  if (!side || !store.app || !panes.l2) return;
  const v = versionInfo();
  const total = store.library ? store.library.mods.length : 0;
  const p = store.parties;
  const base2 = { title: t('list2.title'), count: null, items: [] };
  const base3 = { title: t('list3.title'), count: null, items: [] };

  if (v && !v.has_override) {
    const msg = t('lists.no_parties', { game: v.name });
    panes.l2.set({ ...base2, empty: emptyBox('info', null, msg) });
    panes.l3.set({ ...base3, empty: emptyBox('info', null, msg) });
  } else if (!partiesSupported()) {
    const reason = p && p.reason ? t(p.reason.key, p.reason.params || {}) : t('list1.reading');
    panes.l2.set({ ...base2, empty: emptyBox('folder-open', null, reason) });
    panes.l3.set({ ...base3, empty: emptyBox('folder-open', null, reason) });
  } else {
    const sel = selectedParty();
    const partyKey = `${activeVersion()}|${sel.id}`;
    const animate = lastPartyKey !== null && lastPartyKey !== partyKey;
    lastPartyKey = partyKey;
    if (sel.id === FULL) {
      panes.l2.set({ ...base2, empty: emptyBox('layers', t('list2.full', { count: total }), t('list2.full_help')) });
    } else if (sel.id === EMPTY) {
      panes.l2.set({ ...base2, empty: emptyBox('layers', t('list2.empty_party'), t('list2.empty_help')) });
    } else {
      panes.l2.set({
        ...base2,
        count: sel.mods.length,
        items: itemsOf(sel.mods),
        empty: emptyBox('layers', t('list2.no_mods'), t('list2.no_mods_help')),
        animate,
      });
    }
    const party = userParty();
    const off = !!party && !party.common_enabled;
    panes.l3.set({
      ...base3,
      count: p.common_mods.length,
      items: itemsOf(p.common_mods),
      note: off ? t('list3.not_included') : '',
      muted: off,
      empty: emptyBox('layers', t('list3.empty'), t('list3.empty_help')),
    });
  }
  layoutSide();
}
