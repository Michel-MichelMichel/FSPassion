// Liste 1 — Tous les mods.
// Grille de tuiles de ~300 px, catégories (Non classés, DLC, Maps, Autres
// mods), recherche, défilement d'une rangée par cran de molette, repère
// alphabétique. Seules les tuiles proches de la vue sont dessinées : 2 000 mods
// défilent sans ralentir.
//
// Affichage sans délai : une tuile qui entre pendant un défilement
// s'affiche tout de suite, avec son icône (chargée dès qu'elle approche de la
// vue). Le déploiement des tuiles les unes après les autres reste réservé à
// l'ouverture de la liste et aux changements de contenu (recherche, version).
//
// Sélection : clic, Ctrl+clic, Maj+clic, lasso depuis une zone vide,
// Ctrl+A, Échap, flèches et Espace. Glisser-déposer vers les listes 2 et 3.

import { demoBadge, isDemo } from './demo.js';
import { plusParty } from './actions.js';
import { api, dlcIconUrl, iconUrl } from './api.js';
import { trackDrag } from './dnd.js';
import { clear, debounce, h, icon, reducedMotion } from './dom.js';
import { openDownloads } from './downloads.js';
import { hideCard, scheduleCard, showCard, togglePin } from './hovercard.js';
import { currentLang, formatNumber, modTitle, pickName, t } from './i18n.js';
import { openRename } from './modops.js';
import { localRect, toLocal } from './scale.js';
import {
  clearSelection, isSelected, onSelection, pressTile, rangeTo, registerList, selectedIds, selectionList,
  selectionSize, setActiveList, setSelection, toggle,
} from './selection.js';
import { activeCount, activeVersion, membership, modIndex, partiesSupported, store, versionInfo } from './state.js';
import { toast } from './toast.js';

const TILE_W = 300;
const ART_H = 300;
const WIDE_H = 140;
const NAME_H = 76; // nom sur 2 lignes de 30 px (police agrandie)
const GAP_Y = 30;
const HEAD_H = 64;
const CAT_SPACE = 10;
const MIN_GAP_X = 28;
const MAX_GAP_X = 64;
const PAD_X = 16; // marge à gauche et à droite de la grille
const STABLE_MS = 100; // fin du défilement : ~100 ms sans mouvement
const HINT_DELAY = 300; // repère seulement si le défilement dure (plus d'un cran)
const HINT_HIDE = 400;
const WHEEL_MS = 170; // durée du glissement d'une rangée
const DEPLOY_STEP = 15; // micro-délai entre deux tuiles
const DEPLOY_MAX = 300;
const DECODE_WAIT = 160; // attente maximale du décodage des icônes avant le déploiement
const DETACHED_MAX = 160;
const LASSO_EDGE = 48; // défilement automatique du lasso près des bords
const LASSO_SPEED = 22;

let pane = null;
let scroller = null;
let canvas = null;
let hintEl = null;
let emptyEl = null;
let headerEls = {};
let callbacks = {};
let resizeObserver = null;

let cats = []; // [{ id, label, items }]
let rows = []; // [{ type, cat, y, h, items }]
let snaps = []; // positions d'arrêt de la molette (une par rangée)
let navRows = []; // rangées de tuiles, pour les flèches haut et bas
let flat = []; // toutes les tuiles, dans l'ordre de lecture
let posOf = new Map(); // clé de tuile → { r, c } dans navRows
let modOrder = []; // identifiants (minuscules) des mods sélectionnables, dans l'ordre
let totalH = 0;
let cols = 2;
let gapX = MIN_GAP_X;
let offsetX = PAD_X; // marge gauche de la grille, centrée
let lastWidth = 0;
const attached = new Map(); // clé → nœud affiché
const detached = new Map(); // clé → nœud gardé pour réutilisation

let rafRender = 0;
let scrollActive = false;
let scrolling = false;
let scrollStart = 0;
let scrollDist = 0;
let lastTop = 0;
let stableTimer = 0;
let hintTimer = 0;
let hintHideTimer = 0;
let lastScrollEnd = -1e9;

let wheelRaf = 0;
let wheelTarget = null;
let wheelFrom = 0;
let wheelStart = 0;
let wheelAcc = 0;
let lastWheel = 0;

let focusKey = null; // tuile qui porte le focus clavier (tabindex mobile)
let focusInside = false;

export function initLibrary(el, cb) {
  pane = el;
  callbacks = cb;
  pane.dataset.drop = 'l1';
  registerList('l1', {
    order: () => modOrder,
    idOf: (low) => (modIndex().get(low) || {}).id || low,
  });
  onSelection(() => {
    decorateAll();
    updateCounters();
  });
}

// ---------------------------------------------------------------------------
// Construction de la liste
// ---------------------------------------------------------------------------

function fold(s) {
  return String(s || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

function collator() {
  try {
    return new Intl.Collator(currentLang(), { sensitivity: 'base', numeric: true });
  } catch {
    return new Intl.Collator('en', { sensitivity: 'base', numeric: true });
  }
}

function buildCategories() {
  const lib = store.library;
  if (!lib) return [];
  const q = fold(store.search.trim());
  const match = (text, extra) => !q || fold(text).includes(q) || (extra && fold(extra).includes(q));
  // La recherche porte aussi sur le nom de l'auteur. Les mods
  // trouvés par leur nom restent en place ; ceux trouvés seulement par leur
  // auteur vont plus bas, dans une catégorie « Par nom d'auteur ».
  const byAuthor = (author) => !!q && !!author && fold(author).includes(q);
  const coll = collator();
  const byName = (a, b) => coll.compare(a.name, b.name);
  // Maps d'abord : au premier lancement, tous les mods sont « Non
  // classés » ; les maps en tête permettent de créer tout de suite les parties.
  const mapsFirst = (a, b) => (b.data.is_map ? 1 : 0) - (a.data.is_map ? 1 : 0) || byName(a, b);

  let mods = [];
  const authorHits = [];
  for (const m of lib.mods) {
    const low = m.id.toLowerCase();
    const it = { type: 'mod', key: `m:${low}`, low, name: modTitle(m), data: m, unclassified: false };
    if (match(it.name, it.data.id)) mods.push(it);
    else if (byAuthor(m.author)) authorHits.push(it);
  }
  const dlc = (lib.dlc || [])
    .map((d) => ({ type: 'dlc', key: `d:${d.id.toLowerCase()}`, name: pickName(d.names) || d.id, data: d }))
    .filter((it) => match(it.name, it.data.id));

  // Ordre imposé par le catalogue (FS2011), sinon ordre alphabétique.
  const byRank = (a, b) => (a.data.rank ?? 1e9) - (b.data.rank ?? 1e9) || byName(a, b);
  const out = [];
  if (lib.classification && partiesSupported()) {
    // Non classés : ni dans les mods communs, ni dans aucune partie. Le
    // jeu ne les verra jamais tant qu'ils ne sont pas classés. Un mod quitte
    // cette catégorie dès qu'il est classé.
    const m = membership();
    const loose = [];
    const rest = [];
    for (const it of mods) {
      if (m.common.has(it.low) || m.anyParty.has(it.low)) rest.push(it);
      else {
        it.unclassified = true;
        loose.push(it);
      }
    }
    out.push({ id: 'unclassified', label: t('list1.cat_unclassified'), items: loose.sort(mapsFirst) });
    mods = rest;
  }
  out.push({ id: 'dlc', label: t('list1.cat_dlc'), items: dlc.sort(byRank) });
  out.push({ id: 'maps', label: t('list1.cat_maps'), items: mods.filter((m) => m.data.is_map).sort(byName) });
  out.push({ id: 'others', label: t('list1.cat_others'), items: mods.filter((m) => !m.data.is_map).sort(byName) });
  if (authorHits.length) out.push({ id: 'by_author', label: t('list1.cat_by_author'), items: authorHits.sort(byName) });
  return out.filter((c) => c.items.length);
}

function itemHeight(it) {
  return it.type === 'dlc' && it.data.shape === 'wide' ? WIDE_H + NAME_H : ART_H + NAME_H;
}

function itemX(col) {
  return offsetX + Math.round(col * (TILE_W + gapX));
}

function layout() {
  const width = scroller.clientWidth - 8 - 2 * PAD_X;
  lastWidth = width;
  cols = Math.max(2, Math.floor((width + MIN_GAP_X) / (TILE_W + MIN_GAP_X)));
  gapX = cols > 1 ? Math.min(MAX_GAP_X, Math.max(MIN_GAP_X, (width - cols * TILE_W) / (cols - 1))) : 0;
  // La grille est centrée horizontalement dans la liste.
  const used = cols * TILE_W + (cols - 1) * gapX;
  offsetX = PAD_X + Math.max(0, Math.round((width - used) / 2));
  rows = [];
  snaps = [];
  navRows = [];
  flat = [];
  posOf = new Map();
  modOrder = [];
  let y = 0;
  for (const cat of cats) {
    rows.push({ type: 'head', cat, y, h: HEAD_H });
    snaps.push(y);
    y += HEAD_H;
    for (let i = 0; i < cat.items.length; i += cols) {
      const items = cat.items.slice(i, i + cols);
      const rh = Math.max(...items.map(itemHeight));
      // La première rangée d'une catégorie défile avec son titre.
      if (i > 0) snaps.push(Math.max(0, y - Math.round(GAP_Y / 2)));
      const row = { type: 'row', cat, y, h: rh, items };
      rows.push(row);
      items.forEach((it, c) => {
        posOf.set(it.key, { r: navRows.length, c });
        flat.push(it);
        if (it.type === 'mod') modOrder.push(it.low);
      });
      navRows.push(row);
      y += rh + GAP_Y;
    }
    y += CAT_SPACE;
  }
  totalH = y + 30;
  canvas.style.height = `${totalH}px`;
}

function firstRowAt(y) {
  let lo = 0;
  let hi = rows.length - 1;
  let ans = rows.length;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (rows[mid].y + rows[mid].h >= y) {
      ans = mid;
      hi = mid - 1;
    } else {
      lo = mid + 1;
    }
  }
  return ans;
}

// ---------------------------------------------------------------------------
// Tuiles
// ---------------------------------------------------------------------------

function makeHead(cat) {
  // Chaque catégorie prend une couleur du thème (couleur pleine).
  const acc = { unclassified: 1, dlc: 2, maps: 3, others: 4, by_author: 1 }[cat.id] || 1;
  const el = h('div', { class: `cat-head acc-${acc}${cat.id === 'unclassified' ? ' is-unclassified' : ''}` },
    h('span', { text: cat.label }),
    h('span', { class: 'cat-count', text: formatNumber(cat.items.length) }),
    cat.id === 'dlc' ? h('span', { class: 'cat-note', text: t('list1.dlc_note') }) : null,
    cat.id === 'unclassified' ? h('span', { class: 'cat-note', text: t('list1.unclassified_note') }) : null);
  el._shown = true;
  return el;
}

function makeTile(it) {
  const isDlc = it.type === 'dlc';
  const d = it.data;
  const el = h('div', {
    class: `tile is-pending${isDlc ? ' is-dlc' : ''}${isDlc && d.present === false ? ' is-absent' : ''}${isDlc && d.shape === 'wide' ? ' is-wide' : ''}`,
    tabindex: '-1',
    role: 'option',
    'aria-label': it.name,
  });
  const ph = h('div', { class: 'tile-ph' }, icon('package'));
  const art = h('div', { class: 'tile-art' }, ph);
  el._img = null;
  if (d.icon) {
    const img = h('img', { class: 'tile-img', alt: '', draggable: 'false', decoding: 'async' });
    img.dataset.src = isDlc ? dlcIconUrl(activeVersion(), d.icon) : iconUrl(activeVersion(), d.icon, 'medium');
    img.addEventListener('load', () => img.classList.add('loaded'));
    img.addEventListener('error', () => {
      img.remove();
      el._img = null;
      el.classList.remove('has-img');
    });
    art.append(img);
    el._img = img;
    el.classList.add('has-img');
  }
  // Trait fin intérieur de la carte, par-dessus l'image.
  art.append(h('div', { class: 'tile-edge', 'aria-hidden': 'true' }));
  if (!isDlc) {
    // Contour en pointillés des mods non classés (dessiné par un masque SVG :
    // tirets et espaces de même longueur).
    art.append(h('div', { class: 'tile-ring', 'aria-hidden': 'true' }));
    // Badges en haut à gauche : mod non compressé ; faux mod (démonstration).
    const badges = [];
    if (isDemo()) badges.push(demoBadge());
    if (d.kind === 'dir') {
      badges.push(h('span', { class: 'badge', 'data-i18n-tip': 'mod.unpacked', 'aria-label': t('mod.unpacked') }, icon('folder')));
    }
    if (badges.length) art.append(h('div', { class: 'tile-badges' }, ...badges));
    // Badge de map : icône « map », en bas à gauche de l'image.
    if (d.is_map) {
      art.append(h('div', { class: 'tile-map' },
        h('span', { class: 'badge', 'data-i18n-tip': 'mod.map', 'aria-label': t('mod.map') }, icon('map'))));
    }
    // Bouton « i » en haut à droite de l'image : épingle la fiche du
    // mod (elle reste à l'écran, ses liens se cliquent). Au clavier, touche I.
    const info = h('button', {
      class: 'tile-info', type: 'button', tabindex: '-1', 'data-i18n-tip': 'list1.info_tip',
      'aria-label': t('list1.info_tip'),
    }, icon('info'));
    info.addEventListener('click', (e) => {
      e.stopPropagation();
      togglePin(el, el._item);
    });
    art.append(info);
    el._marks = h('div', { class: 'tile-marks' });
    el._marksSig = '';
    art.append(el._marks);
    if (d.is_map) {
      // « ＋ Partie » : au centre de l'image, visible au survol ; au
      // clavier, touche Entrée.
      const plus = h('button', {
        class: 'tile-plus', type: 'button', tabindex: '-1', 'data-i18n-tip': 'list1.plus_party_tip',
        'aria-label': t('list1.plus_party_tip'),
      }, icon('plus', 'ico-s'), h('span', { text: t('list1.plus_party') }));
      plus.addEventListener('click', (e) => {
        e.stopPropagation();
        hideCard();
        plusParty(el._item.data);
      });
      art.append(plus);
      el._plus = plus;
    }
  }
  el.append(art, h('div', { class: 'tile-name', text: it.name }));
  el.dataset.key = it.key;
  el._item = it;
  el._shown = false;
  el.addEventListener('pointerenter', () => {
    if (!document.documentElement.classList.contains('is-dragging')) scheduleCard(el, el._item);
  });
  el.addEventListener('pointerleave', () => hideCard(el));
  el.addEventListener('focus', () => {
    focusKey = el.dataset.key;
    if (el.matches(':focus-visible')) showCard(el, el._item);
  });
  el.addEventListener('blur', () => hideCard(el));
  return el;
}

// État variable d'une tuile : sélection, non classé, repères, ＋ Partie.
function decorate(el) {
  const it = el._item;
  if (!it || !el.classList.contains('tile')) return;
  el.tabIndex = el.dataset.key === tabKey ? 0 : -1;
  if (it.type !== 'mod') return;
  const sel = isSelected('l1', it.low);
  el.classList.toggle('is-selected', sel);
  el.setAttribute('aria-selected', sel ? 'true' : 'false');
  el.classList.toggle('is-unclassified', !!it.unclassified);
  const m = membership();
  const inParty = m.party.has(it.low);
  const inCommon = m.common.has(it.low);
  const sig = `${inParty ? 'p' : ''}${inCommon ? 'c' : ''}`;
  if (el._marks && sig !== el._marksSig) {
    el._marksSig = sig;
    clear(el._marks);
    if (inParty) el._marks.append(h('span', { class: 'mark mark-party', 'data-i18n-tip': 'list1.mark_party', 'aria-label': t('list1.mark_party') }));
    if (inCommon) el._marks.append(h('span', { class: 'mark mark-common', 'data-i18n-tip': 'list1.mark_common', 'aria-label': t('list1.mark_common') }));
  }
  if (el._plus) el._plus.hidden = !partiesSupported();
}

let tabKey = null;

function decorateAll() {
  for (const el of attached.values()) decorate(el);
}

// Signature d'un élément : si elle change, la tuile est refaite.
function sigOf(it) {
  const d = it.data;
  return `${it.name}|${d.icon || ''}|${d.is_map ? 1 : 0}|${d.kind || ''}|${d.shape || ''}`;
}

function place(el, x, y, hgt) {
  el._x = x;
  el._y = y;
  el._h = hgt;
  el.style.translate = `${x}px ${y}px`;
}

function setShown(el, shown) {
  el._shown = shown;
  el.classList.toggle('is-pending', !shown);
  if (!shown) el.classList.remove('deploy');
}

function loadImage(el) {
  const img = el._img;
  if (img && !img.hasAttribute('src')) img.src = img.dataset.src;
  return img;
}

function showNow(el) {
  setShown(el, true);
  loadImage(el);
}

function getNode(key, sig, factory) {
  let el = attached.get(key);
  if (el && el._sig === sig) return el;
  let inherit = false;
  if (el) {
    // Même élément, contenu changé (nom, icône…) : la nouvelle tuile prend la
    // place de l'ancienne sans nouvelle animation.
    inherit = el._shown;
    el.remove();
    attached.delete(key);
    el = null;
  }
  el = detached.get(key);
  if (el) {
    detached.delete(key);
    if (el._sig !== sig) el = null;
  }
  if (!el) {
    el = factory();
    el._sig = sig;
  }
  if (inherit && !el._shown) showNow(el);
  attached.set(key, el);
  canvas.append(el);
  return el;
}

function release(key, el) {
  attached.delete(key);
  if (el === document.activeElement) scroller.focus({ preventScroll: true });
  el.remove();
  // Une tuile sortie de la zone dessinée libère son image décodée (relue
  // depuis le cache du navigateur si elle revient).
  if (el._img) {
    setShown(el, false);
    if (el._img.hasAttribute('src')) {
      el._img.removeAttribute('src');
      el._img.classList.remove('loaded');
    }
  } else if (el.classList.contains('tile')) {
    setShown(el, false);
  }
  detached.set(key, el);
  if (detached.size > DETACHED_MAX) {
    const first = detached.keys().next().value;
    detached.delete(first);
  }
}

function render() {
  rafRender = 0;
  draw();
  reveal();
}

// Place les tuiles de la zone dessinée (vue ± une demi-hauteur au-dessus et
// une hauteur et demie au-dessous) ; libère les autres. Pendant un défilement,
// les tuiles qui arrivent s'affichent aussitôt, sans attente.
function draw() {
  if (!scroller || !rows.length) {
    for (const [k, el] of attached) release(k, el);
    return;
  }
  const top = scroller.scrollTop;
  const vh = scroller.clientHeight;
  const from = top - vh * 0.5;
  const to = top + vh * 1.5;
  const wanted = new Set();
  for (let i = firstRowAt(from); i < rows.length && rows[i].y <= to; i++) {
    const row = rows[i];
    if (row.type === 'head') {
      const key = `h:${row.cat.id}`;
      wanted.add(key);
      const el = getNode(key, `${row.cat.label}|${row.cat.items.length}`, () => makeHead(row.cat));
      place(el, offsetX, row.y, HEAD_H);
      continue;
    }
    row.items.forEach((it, col) => {
      wanted.add(it.key);
      const el = getNode(it.key, sigOf(it), () => makeTile(it));
      el._item = it;
      place(el, itemX(col), row.y, itemHeight(it));
    });
  }
  for (const [key, el] of attached) if (!wanted.has(key)) release(key, el);

  // Tabindex mobile : une seule tuile atteignable par Tab.
  tabKey = attached.has(focusKey) ? focusKey : null;
  if (!tabKey) {
    let best = null;
    for (const el of attached.values()) {
      if (!el.classList.contains('tile') || el._y + el._h < top) continue;
      if (!best || el._y < best._y || (el._y === best._y && el._x < best._x)) best = el;
    }
    tabKey = best ? best.dataset.key : null;
  }
  for (const el of attached.values()) {
    if (scrollActive && !el._shown) showNow(el);
    else if (el._shown) loadImage(el);
    decorate(el);
  }
  if (focusInside && focusKey && attached.has(focusKey)) {
    const el = attached.get(focusKey);
    if (document.activeElement !== el) el.focus({ preventScroll: true });
  }
}

function scheduleRender() {
  if (!rafRender) rafRender = requestAnimationFrame(render);
}

// Tuiles en attente (ouverture de la liste, recherche, nouveau contenu) : celles
// de la vue se déploient dans l'ordre de lecture, avec un micro-délai entre
// deux tuiles ; les autres s'affichent aussitôt.
function reveal() {
  const top = scroller.scrollTop;
  const vh = scroller.clientHeight;
  const list = [];
  for (const el of attached.values()) {
    if (el._shown) continue;
    const inView = el._y + el._h >= top - 20 && el._y <= top + vh + 20;
    if (inView && !scrollActive) list.push(el);
    else showNow(el);
  }
  if (!list.length) return;
  list.sort((a, b) => a._y - b._y || a._x - b._x);
  const waits = [];
  for (const el of list) {
    el._shown = true;
    const img = loadImage(el);
    if (img && !img.complete && img.decode) waits.push(img.decode().catch(() => {}));
  }
  const animate = !reducedMotion();
  const start = () => {
    let i = 0;
    for (const el of list) {
      // Tuile sortie de la zone entre-temps, ou déjà affichée par un appel voisin.
      if (!el._shown || !el.isConnected || !el.classList.contains('is-pending')) continue;
      el.classList.remove('is-pending', 'deploy');
      if (animate) {
        void el.offsetWidth;
        el.style.setProperty('--deploy-delay', `${Math.min(i * DEPLOY_STEP, DEPLOY_MAX)}ms`);
        el.classList.add('deploy');
        el.addEventListener('animationend', () => el.classList.remove('deploy'), { once: true });
      }
      i++;
    }
  };
  if (!waits.length || !animate) {
    start();
    return;
  }
  Promise.race([Promise.all(waits), new Promise((r) => setTimeout(r, DECODE_WAIT))]).then(start);
}

// ---------------------------------------------------------------------------
// Molette : un cran = une rangée
// ---------------------------------------------------------------------------

function onWheel(e) {
  if (e.ctrlKey || !rows.length) return;
  const unit = e.deltaMode === 1 ? 40 : e.deltaMode === 2 ? scroller.clientHeight : 1;
  const dy = e.deltaY * unit;
  if (!dy || Math.abs(e.deltaX) > Math.abs(dy)) return;
  e.preventDefault();
  const now = performance.now();
  if (now - lastWheel > 220) wheelAcc = 0;
  lastWheel = now;
  let step = 0;
  if (Math.abs(dy) >= 50) {
    step = Math.sign(dy); // un cran de molette
  } else {
    // Pavé tactile ou molette fine : les petits mouvements s'additionnent.
    wheelAcc += dy;
    if (Math.abs(wheelAcc) >= 100) {
      step = Math.sign(wheelAcc);
      wheelAcc = 0;
    }
  }
  if (!step) return;
  const max = Math.max(0, scroller.scrollHeight - scroller.clientHeight);
  const base = wheelTarget ?? scroller.scrollTop;
  let target;
  if (step > 0) {
    target = snaps.find((p) => p > base + 2);
    if (target === undefined) target = max;
  } else {
    target = 0;
    for (const p of snaps) {
      if (p < base - 2) target = p;
      else break;
    }
  }
  scrollToRow(Math.max(0, Math.min(max, target)));
}

function scrollToRow(target) {
  wheelFrom = scroller.scrollTop;
  wheelTarget = target;
  wheelStart = performance.now();
  if (reducedMotion()) {
    stopWheel();
    scroller.scrollTop = target;
    return;
  }
  if (!wheelRaf) wheelRaf = requestAnimationFrame(stepWheel);
}

function stepWheel() {
  wheelRaf = 0;
  if (wheelTarget === null) return;
  const k0 = Math.min(1, Math.max(0, (performance.now() - wheelStart) / WHEEL_MS));
  const k = 1 - (1 - k0) ** 3;
  scroller.scrollTop = wheelFrom + (wheelTarget - wheelFrom) * k;
  if (k0 < 1) wheelRaf = requestAnimationFrame(stepWheel);
  else wheelTarget = null;
}

function stopWheel() {
  if (wheelRaf) cancelAnimationFrame(wheelRaf);
  wheelRaf = 0;
  wheelTarget = null;
}

// ---------------------------------------------------------------------------
// Défilement et repère alphabétique
// ---------------------------------------------------------------------------

function onScroll() {
  const now = performance.now();
  const top = scroller.scrollTop;
  hideCard();
  if (!scrollActive) {
    scrollActive = true;
    scrollStart = now;
    scrollDist = 0;
    lastTop = top;
    clearTimeout(hintTimer);
    if (now - lastScrollEnd < HINT_HIDE) {
      // Reprise rapide du défilement : le repère est encore affiché, on continue.
      scrollStart = now - HINT_DELAY;
      enterScrolling();
    } else {
      hintTimer = setTimeout(() => {
        if (scrollActive) enterScrolling();
      }, HINT_DELAY);
    }
  }
  scrollDist += Math.abs(top - lastTop);
  lastTop = top;
  if (!scrolling && scrollDist > scroller.clientHeight * 1.2) enterScrolling();
  if (scrolling) updateHint();
  clearTimeout(stableTimer);
  stableTimer = setTimeout(onStable, STABLE_MS);
  scheduleRender();
}

function enterScrolling() {
  if (scrolling) return;
  scrolling = true;
  scroller.classList.add('is-scrolling');
  clearTimeout(hintHideTimer);
  if (performance.now() - scrollStart >= HINT_DELAY - 5) showHint();
  else {
    clearTimeout(hintTimer);
    hintTimer = setTimeout(() => scrolling && showHint(), HINT_DELAY - (performance.now() - scrollStart));
  }
}

function onStable() {
  if (wheelTarget !== null) {
    // Glissement de molette encore en cours : on attend sa fin.
    stableTimer = setTimeout(onStable, STABLE_MS);
    return;
  }
  scrollActive = false;
  lastScrollEnd = performance.now();
  clearTimeout(hintTimer);
  endScrolling();
}

function endScrolling() {
  if (!scrolling) return;
  scrolling = false;
  scroller.classList.remove('is-scrolling');
  clearTimeout(hintHideTimer);
  hintHideTimer = setTimeout(() => hintEl.classList.remove('on'), HINT_HIDE);
}

function showHint() {
  updateHint();
  hintEl.classList.add('on');
}

function updateHint() {
  if (!rows.length) return;
  const center = scroller.scrollTop + scroller.clientHeight / 2;
  let i = Math.min(firstRowAt(center), rows.length - 1);
  if (rows[i].type === 'head' && i + 1 < rows.length) i++;
  const row = rows[i];
  if (!row.items) return;
  const it = row.items[Math.min(row.items.length - 1, Math.floor(row.items.length / 2))];
  hintEl.firstChild.textContent = row.cat.label;
  setHintName(it.name);
}

// Nom du repère : les 3 premières lettres en accent, le reste en gris.
// Les caractères qui précèdent la première lettre (« [Map] ») restent gris.
let hintShown = '';
function setHintName(name) {
  if (name === hintShown) return;
  hintShown = name;
  const m = /^(\P{L}*)(\p{L}{0,3})([\s\S]*)$/u.exec(name) || [name, '', '', ''];
  hintEl.lastChild.replaceChildren(
    h('span', { class: 'hint-rest', text: m[1] }),
    h('span', { class: 'hint-lead', text: m[2] }),
    h('span', { class: 'hint-rest', text: m[3] }),
  );
}

// ---------------------------------------------------------------------------
// Sélection à la souris : clic, glisser, lasso
// ---------------------------------------------------------------------------

function canvasPoint(e) {
  const p = toLocal(e.clientX, e.clientY);
  const r = localRect(canvas);
  return { x: p.x - r.left, y: p.y - r.top };
}

function onPointerDown(e) {
  if (e.button !== 0) return;
  stopWheel();
  setActiveList('l1');
  // Ascenseur : rien d'autre à faire.
  if (e.target === scroller && e.offsetX >= scroller.clientWidth) return;
  let target = e.target;
  if (scrolling) {
    // Clic juste après un défilement : les tuiles redeviennent cliquables
    // tout de suite (pendant le défilement, elles ignorent la souris).
    endScrolling();
    target = document.elementFromPoint(e.clientX, e.clientY) || target;
  }
  if (target.closest('.tile-plus, .tile-info')) return;
  const tile = target.closest('.tile');
  if (tile) {
    if (tile.classList.contains('is-dlc') || !tile._item) return; // DLC : informatif
    focusKey = tile.dataset.key;
    const low = tile._item.low;
    const after = pressTile(e, 'l1', low);
    trackDrag(e, 'l1', () => (selectionList() === 'l1' ? selectedIds() : []), after);
    return;
  }
  startLasso(e);
}

// Lasso : rectangle tracé depuis une zone vide. Les positions viennent
// de la mise en page, pas des tuiles affichées : le lasso peut couvrir des
// rangées hors de la vue (défilement automatique près des bords).
function startLasso(e) {
  e.preventDefault();
  scroller.focus({ preventScroll: true });
  const additive = e.ctrlKey || e.metaKey;
  const base = additive && selectionList() === 'l1' ? [...modOrder.filter((low) => isSelected('l1', low))] : [];
  const start = canvasPoint(e);
  const pid = e.pointerId;
  let last = e;
  let box = null;
  let raf = 0;
  let sig = '';
  scroller.setPointerCapture(pid);
  const update = () => {
    const p = canvasPoint(last);
    const x1 = Math.min(start.x, p.x);
    const y1 = Math.min(start.y, p.y);
    const x2 = Math.max(start.x, p.x);
    const y2 = Math.max(start.y, p.y);
    if (!box) {
      box = h('div', { class: 'lasso' });
      canvas.append(box);
    }
    box.style.translate = `${x1}px ${y1}px`;
    box.style.width = `${x2 - x1}px`;
    box.style.height = `${y2 - y1}px`;
    const hit = [];
    for (let i = firstRowAt(y1); i < rows.length && rows[i].y <= y2; i++) {
      const row = rows[i];
      if (row.type !== 'row') continue;
      row.items.forEach((it, col) => {
        if (it.type !== 'mod') return;
        const x = itemX(col);
        const hgt = itemHeight(it);
        if (x < x2 && x + TILE_W > x1 && row.y < y2 && row.y + hgt > y1) hit.push(it.low);
      });
    }
    const keys = base.concat(hit.filter((k) => !base.includes(k)));
    const s = keys.join('|');
    if (s !== sig) {
      sig = s;
      if (keys.length) setSelection('l1', keys, { anchor: hit[0] || null });
      else clearSelection();
    }
  };
  const tick = () => {
    raf = 0;
    if (!box) return;
    const r = localRect(scroller);
    const p = toLocal(last.clientX, last.clientY);
    let dy = 0;
    if (p.y < r.top + LASSO_EDGE) dy = -LASSO_SPEED * Math.min(1, (r.top + LASSO_EDGE - p.y) / LASSO_EDGE);
    else if (p.y > r.bottom - LASSO_EDGE) dy = LASSO_SPEED * Math.min(1, (p.y - (r.bottom - LASSO_EDGE)) / LASSO_EDGE);
    if (dy) {
      scroller.scrollTop += dy;
      update();
      raf = requestAnimationFrame(tick);
    }
  };
  const move = (ev) => {
    if (ev.pointerId !== pid) return;
    last = ev;
    if (!box && Math.abs(ev.clientX - e.clientX) + Math.abs(ev.clientY - e.clientY) < 5) return;
    hideCard();
    update();
    if (!raf) raf = requestAnimationFrame(tick);
  };
  const up = (ev) => {
    if (ev.pointerId !== pid) return;
    scroller.removeEventListener('pointermove', move);
    scroller.removeEventListener('pointerup', up);
    scroller.removeEventListener('pointercancel', up);
    if (raf) cancelAnimationFrame(raf);
    if (box) box.remove();
    else if (!additive) clearSelection(); // clic dans une zone vide
  };
  scroller.addEventListener('pointermove', move);
  scroller.addEventListener('pointerup', up);
  scroller.addEventListener('pointercancel', up);
}

// ---------------------------------------------------------------------------
// Clavier : flèches, Espace, Entrée (＋ Partie), Ctrl+A, F2
// ---------------------------------------------------------------------------

function ensureVisible(it) {
  const pos = posOf.get(it.key);
  if (!pos) return;
  const row = navRows[pos.r];
  const prev = navRows[pos.r - 1];
  // Première rangée d'une catégorie : son titre reste visible avec elle.
  const rowTop = !prev || prev.cat !== row.cat ? row.y - HEAD_H : row.y - GAP_Y / 2;
  const rowBottom = row.y + row.h + GAP_Y / 2;
  const top = scroller.scrollTop;
  const vh = scroller.clientHeight;
  let target = null;
  if (rowTop < top) target = Math.max(0, rowTop);
  else if (rowBottom > top + vh) target = rowBottom - vh;
  if (target !== null) {
    stopWheel();
    scroller.scrollTop = target;
  }
}

function focusItem(it, { extend = false } = {}) {
  if (!it) return;
  focusKey = it.key;
  ensureVisible(it);
  draw();
  const el = attached.get(it.key);
  if (el) el.focus({ preventScroll: true });
  if (extend && it.type === 'mod') rangeTo('l1', it.low);
}

function onKeyDown(e) {
  if (e.target.closest('input, button.tile-plus, button.tile-info')) return;
  if (!flat.length) return;
  const cur = flat.find((it) => it.key === focusKey) || null;
  const pos = cur ? posOf.get(cur.key) : null;
  const go = (it) => {
    e.preventDefault();
    focusItem(it, { extend: e.shiftKey });
  };
  switch (e.key) {
    case 'ArrowRight':
      return go(cur ? flat[Math.min(flat.length - 1, flat.indexOf(cur) + 1)] : flat[0]);
    case 'ArrowLeft':
      return go(cur ? flat[Math.max(0, flat.indexOf(cur) - 1)] : flat[0]);
    case 'ArrowDown':
    case 'ArrowUp':
    case 'PageDown':
    case 'PageUp': {
      if (!pos) return go(flat[0]);
      const page = Math.max(1, Math.floor(scroller.clientHeight / (ART_H + NAME_H + GAP_Y)));
      const delta = { ArrowDown: 1, ArrowUp: -1, PageDown: page, PageUp: -page }[e.key];
      const r = Math.max(0, Math.min(navRows.length - 1, pos.r + delta));
      const row = navRows[r];
      return go(row.items[Math.min(pos.c, row.items.length - 1)]);
    }
    case 'Home':
      return go(flat[0]);
    case 'End':
      return go(flat[flat.length - 1]);
    case ' ':
      if (cur && cur.type === 'mod') {
        e.preventDefault();
        if (e.shiftKey) rangeTo('l1', cur.low);
        else toggle('l1', cur.low);
      }
      return undefined;
    case 'Enter':
      if (cur && cur.type === 'mod' && cur.data.is_map && partiesSupported()) {
        e.preventDefault();
        hideCard();
        plusParty(cur.data);
      }
      return undefined;
    case 'i':
    case 'I': {
      // Épingle (ou referme) la fiche de la tuile qui a le focus.
      const el = cur && cur.type === 'mod' ? attached.get(cur.key) : null;
      if (el && !e.ctrlKey && !e.altKey && !e.metaKey) {
        e.preventDefault();
        togglePin(el, el._item);
      }
      return undefined;
    }
    case 'F2': {
      // Renommer : un seul mod sélectionné, ou la tuile qui a le focus.
      e.preventDefault();
      const ids = selectionList() === 'l1' && selectionSize() === 1 ? selectedIds()
        : (cur && cur.type === 'mod' ? [cur.data.id] : []);
      if (ids.length === 1) {
        hideCard();
        openRename(ids[0]);
      } else {
        toast('actions.rename_help', {}, 'info');
      }
      return undefined;
    }
    default:
      return undefined;
  }
}

// ---------------------------------------------------------------------------
// En-tête de la liste 1
// ---------------------------------------------------------------------------

function buildHeader() {
  const search = h('input', {
    class: 'field-input', type: 'search', spellcheck: 'false', autocomplete: 'off',
    placeholder: t('list1.search'), 'aria-label': t('list1.search'),
  });
  search.value = store.search;
  const clearBtn = h('button', { class: 'icon-btn icon-btn-s search-clear', type: 'button', 'data-i18n-tip': 'list1.search_clear', 'aria-label': t('list1.search_clear') }, icon('x'));
  clearBtn.hidden = !store.search;
  const apply = debounce(() => {
    store.search = search.value;
    clearBtn.hidden = !search.value;
    rebuild({ resetScroll: true, animate: true });
  }, 90);
  search.addEventListener('input', apply);
  search.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && search.value) {
      e.preventDefault();
      e.stopPropagation();
      search.value = '';
      apply();
    }
  });
  clearBtn.addEventListener('click', () => {
    search.value = '';
    apply();
    search.focus();
  });

  const counters = h('div', { class: 'counters', 'aria-live': 'polite' });
  const progress = h('div', { class: 'lib-progress' });
  const anomBtn = h('button', { class: 'anomaly-indicator', type: 'button', hidden: true, onclick: () => callbacks.onAnomalies() });
  // Rechercher de nouveaux mods dans les téléchargements.
  const newMods = h('button', {
    class: 'icon-btn find-new-btn', type: 'button', 'data-tip-text': t('list1.find_new'), 'aria-label': t('list1.find_new'),
    onclick: () => openDownloads(),
  }, icon('folder-sync'));

  // Titre et compteurs alignés sur la même ligne de base.
  const head = h('div', { class: 'lib-head' },
    h('div', { class: 'lib-titlebar' }, h('h1', { class: 'lib-title mgrad', text: t('list1.title') }), counters),
    h('div', { class: 'lib-tools' }, progress, anomBtn, newMods,
      h('div', { class: 'search' }, icon('search'), search, clearBtn)));
  headerEls = { head, counters, progress, anomBtn, search };
  return head;
}

// Compteurs « Sélectionnés · Actifs · Tous ».
function updateCounters() {
  const { counters } = headerEls;
  if (!counters) return;
  const lib = store.library;
  const total = lib ? lib.mods.length : 0;
  let active = activeCount();
  if (active === null) {
    const v = versionInfo();
    const kind = v && v.applied ? v.applied.kind : null;
    active = kind === 'full' ? total : kind === 'empty' ? 0 : null;
  }
  clear(counters);
  const counter = (label, value) => h('span', { class: 'counter' }, h('b', { text: value }), label);
  counters.append(
    counter(t('list1.selected'), formatNumber(selectionSize())),
    counter(t('list1.active'), active === null ? '—' : formatNumber(active)),
    counter(t('list1.all'), formatNumber(total)));
}

function updateHeader() {
  const lib = store.library;
  const { progress, anomBtn } = headerEls;
  if (!progress) return;
  updateCounters();

  clear(progress);
  if (lib && lib.status === 'scanning') {
    progress.append(icon('loader-circle', 'spin'), t('list1.scanning', { done: lib.progress.done, total: lib.progress.total }));
  } else if (lib && lib.icons_pending > 0) {
    progress.append(icon('loader-circle', 'spin'), t('list1.icons_pending', { count: lib.icons_pending }));
  }

  const anomalies = lib ? lib.anomalies : [];
  anomBtn.hidden = !anomalies.length;
  if (anomalies.length) {
    clear(anomBtn);
    anomBtn.append(icon('triangle-alert', 'ico-s'), formatNumber(anomalies.length));
    anomBtn.classList.toggle('has-new', anomalies.some((a) => a.new));
    anomBtn.dataset.tipText = t('list1.anomalies', { count: anomalies.length });
    anomBtn.setAttribute('aria-label', anomBtn.dataset.tipText);
  }
}

export function focusSearch() {
  headerEls.search?.focus();
}

// ---------------------------------------------------------------------------
// États vides
// ---------------------------------------------------------------------------

function emptyState() {
  const v = versionInfo();
  const lib = store.library;
  // Le message est posé dans une carte opaque, lisible sur tout fond.
  const box = (ico, title, text, action) => h('div', { class: 'grid-empty' },
    h('div', { class: 'grid-empty-card' },
      icon(ico, ico === 'loader-circle' ? 'spin' : ''), h('h3', { text: title }), text ? h('p', { text }) : null, action || null));
  const settingsBtn = h('button', { class: 'btn', type: 'button', onclick: () => callbacks.onSettings() }, icon('settings'), t('list1.open_settings'));
  if (!v) return null;
  if (!v.ready) {
    return box('folder-open', t('list1.not_configured', { game: v.name }), t('list1.not_configured_help'), settingsBtn);
  }
  if (!lib || (lib.status === 'scanning' && !lib.mods.length && !lib.dlc.length)) {
    return box('loader-circle', t('list1.reading'), null);
  }
  if (lib.status === 'error' && lib.error) {
    return box('circle-alert', t(lib.error.key, lib.error.params), t('list1.not_configured_help'), settingsBtn);
  }
  if (store.search && !cats.length) {
    return box('search', t('list1.no_match', { query: store.search }), null);
  }
  if (!cats.length) {
    return box('package', t('list1.empty'), t('list1.empty_help'));
  }
  return null;
}

// ---------------------------------------------------------------------------
// Rendu complet
// ---------------------------------------------------------------------------

export function renderLibrary() {
  if (!pane) return;
  clear(pane);
  attached.clear();
  detached.clear();
  stopWheel();
  focusKey = null;
  scroller = h('div', {
    class: 'grid-scroll', role: 'listbox', tabindex: '-1', 'aria-multiselectable': 'true', 'aria-label': t('list1.title'),
  });
  canvas = h('div', { class: 'grid-canvas' });
  scroller.append(canvas);
  hintEl = h('div', { class: 'scroll-hint', 'aria-hidden': 'true' }, h('div', { class: 'hint-cat' }), h('div', { class: 'hint-name' }));
  emptyEl = h('div');
  pane.append(buildHeader(), h('div', { class: 'grid-wrap' }, scroller, hintEl, emptyEl));
  scroller.addEventListener('scroll', onScroll, { passive: true });
  scroller.addEventListener('wheel', onWheel, { passive: false });
  scroller.addEventListener('pointerdown', onPointerDown);
  scroller.addEventListener('keydown', onKeyDown);
  scroller.addEventListener('focusin', () => {
    focusInside = true;
    setActiveList('l1');
  });
  scroller.addEventListener('focusout', (e) => {
    if (!scroller.contains(e.relatedTarget)) focusInside = false;
  });
  // Un seul observateur : l'ancien est déconnecté avant d'en créer un autre.
  resizeObserver?.disconnect();
  resizeObserver = new ResizeObserver(() => {
    if (Math.abs(scroller.clientWidth - 8 - 2 * PAD_X - lastWidth) > 1 || !rows.length) layout();
    scheduleRender();
  });
  resizeObserver.observe(scroller);
  rebuild({ animate: true });
}

// Contenu modifié (bibliothèque, parties, recherche, langue) : nouvelle mise
// en page. animate : toutes les tuiles visibles se déploient à nouveau
// (ouverture de la liste, recherche) ; sinon seules les nouvelles tuiles se
// déploient.
export function rebuild({ resetScroll = false, animate = false } = {}) {
  if (!scroller) return;
  cats = buildCategories();
  updateHeader();
  const empty = emptyState();
  clear(emptyEl);
  if (empty) emptyEl.append(empty);
  // Version non configurée ou illisible — le message s'affichait
  // par-dessus les DLC du catalogue (illisible) ; la grille reste vide.
  const v = versionInfo();
  if (v && (!v.ready || (store.library?.status === 'error' && store.library.error))) cats = [];
  if (resetScroll) {
    stopWheel();
    scroller.scrollTop = 0;
  }
  layout();
  draw();
  if (scrollActive) return;
  if (animate) {
    for (const el of attached.values()) {
      if (el.classList.contains('cat-head')) {
        if (!reducedMotion()) {
          el.classList.remove('deploy');
          void el.offsetWidth;
          el.style.setProperty('--deploy-delay', '0ms');
          el.classList.add('deploy');
          el.addEventListener('animationend', () => el.classList.remove('deploy'), { once: true });
        }
      } else if (el._shown) {
        el._shown = false;
        el.classList.add('is-pending');
      }
    }
  }
  reveal();
}

// Icônes prêtes (conversion en arrière-plan) : mise à jour des tuiles affichées.
export function applyIcons(items) {
  if (!store.library) return;
  const byId = new Map(store.library.mods.map((m) => [m.id, m]));
  let changed = false;
  for (const it of items) {
    const m = byId.get(it.id);
    if (m && m.icon !== it.icon) {
      m.icon = it.icon;
      m.icon_state = it.icon ? 'ok' : 'failed';
      changed = true;
      const key = `m:${it.id.toLowerCase()}`;
      detached.delete(key);
      const el = attached.get(key);
      if (el) {
        const item = { ...el._item, data: m };
        const fresh = makeTile(item);
        fresh._sig = sigOf(item);
        place(fresh, el._x, el._y, el._h);
        setShown(fresh, el._shown);
        el.replaceWith(fresh);
        attached.set(key, fresh);
        decorate(fresh);
        // L'icône arrive en fondu dans une tuile déjà affichée.
        if (fresh._shown) loadImage(fresh);
      }
    }
  }
  if (changed) updateHeader();
}

export function refreshHeaderOnly() {
  updateHeader();
}

export async function requestRescan(quick) {
  try {
    await api.post('/api/library/rescan', { version: activeVersion(), quick });
  } catch {
    /* ignoré */
  }
}
