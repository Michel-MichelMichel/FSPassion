// Détail d'un mod : survol prolongé d'une tuile, ou focus au clavier.
// Pour une map : la liste des dépendances et leur état.
// Mods facultatifs et liens de téléchargement (<SearchMods> des
// anciennes versions) ; bouton « i » des tuiles : la fiche est épinglée, elle
// reste à l'écran et ses liens se cliquent. Elle se ferme par sa croix, Échap,
// un clic ailleurs, un nouveau clic sur « i », ou le défilement de la liste.

import { api } from './api.js';
import { clear, h, icon } from './dom.js';
import { formatNumber, modTitle, pickName, t } from './i18n.js';
import { localRect } from './scale.js';
import { activeVersion, membership, store } from './state.js';
import { toast, toastError } from './toast.js';

const MAX_DEPS = 14; // fiche au survol ; épinglée, elle montre tout

let card = null;
let timer = 0;
let current = null;
let pinned = null; // tuile dont la fiche est épinglée

// Pendant un redimensionnement de la fenêtre, les tuiles se
// réorganisent sous la souris immobile : chacune recevait un survol et ouvrait
// sa fiche, qui apparaissait et disparaissait au hasard. Classe « is-resizing »
// sur la page jusqu'à 350 ms après le dernier changement de taille : plus de
// survol des tuiles (lists.css), les fiches non épinglées se ferment.
let resizeTimer = 0;
function onResize() {
  const root = document.documentElement;
  if (!root.classList.contains('is-resizing')) {
    root.classList.add('is-resizing');
    if (!pinned) hideCard();
  }
  clearTimeout(timer);
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => root.classList.remove('is-resizing'), 350);
}

export function isResizing() {
  return document.documentElement.classList.contains('is-resizing');
}

export function initHovercard(el) {
  card = el;
  window.addEventListener('resize', onResize);
  document.addEventListener('scroll', (e) => {
    // Défilement dans la fiche épinglée elle-même : elle reste.
    if (card && e.target instanceof Node && card.contains(e.target)) return;
    hideCard();
  }, true);
  // Ouvrir un lien fait passer le navigateur devant : la fiche épinglée reste.
  window.addEventListener('blur', () => {
    if (!pinned) hideCard();
  });
  document.addEventListener('keydown', (e) => {
    if (pinned && e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      unpinCard();
    }
  }, true);
  document.addEventListener('pointerdown', (e) => {
    if (!pinned || !(e.target instanceof Element)) return;
    if (card.contains(e.target) || e.target.closest('.tile-info')) return;
    unpinCard();
  }, true);
}


// Épingle la fiche d'une tuile (bouton « i », touche I), ou la referme.
export function togglePin(anchor, item) {
  if (pinned === anchor) {
    unpinCard();
    return;
  }
  clearTimeout(timer);
  pinned = anchor;
  anchor.classList.add('is-pinned');
  showCard(anchor, item, { force: true });
}

export function unpinCard() {
  if (!pinned) return;
  pinned.classList.remove('is-pinned');
  pinned = null;
  hideCard();
}

// Lien de téléchargement d'un mod requis ou facultatif, ouvert dans le
// navigateur par le cœur (seule une adresse du modDesc.xml de `modId` est acceptée).
export async function openModLink(modId, url) {
  try {
    const res = await api.post('/api/mod-link', { version: activeVersion(), mod: modId, url });
    if (!res || !res.ok) toast('mod.link_failed', {}, 'warn');
  } catch (err) {
    toastError(err);
  }
}

export function linkHost(url) {
  try {
    return new URL(url).hostname.replace(/^www\./i, '');
  } catch {
    return url;
  }
}

// Noms à afficher pour un mod (détail du mod) : parties qui le contiennent.
export function partiesText(id) {
  const low = String(id).toLowerCase();
  const m = membership();
  const names = (m.partiesOf.get(low) || []).slice().sort((a, b) => a.localeCompare(b));
  if (m.common.has(low)) names.push(t('list3.title'));
  return names.length ? names.join(', ') : t('mod.parties_none');
}

// Bouton-lien : le nom du site ; l'adresse complète dans l'infobulle.
export function linkButton(modId, url, cls = 'hc-link') {
  const b = h('button', {
    class: cls, type: 'button', 'aria-label': `${t('mod.link_open')} ${url}`,
    'data-tip-text': `${t('mod.link_open')}\n${url}`,
  }, icon('external-link'), h('span', { text: linkHost(url) }));
  b.addEventListener('click', (e) => {
    e.stopPropagation();
    openModLink(modId, url);
  });
  return b;
}

// Adresse donnée par le modDesc.xml d'un mod pour un mod requis ou facultatif.
function linkOf(mod, name) {
  const low = name.toLowerCase();
  for (const kind of ['search_mods', 'optional_mods']) {
    const item = (mod[kind] || []).find((x) => x && x.name && x.name.toLowerCase() === low);
    if (item && item.url) return item.url;
  }
  return null;
}

export function sizeText(n) {
  if (n === null || n === undefined) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return t(`units.${units[i]}`, { value: formatNumber(Math.round(v * 10) / 10) });
}

// État d'une dépendance : présente, absente, ou DLC possédé / non possédé.
export function dependencyState(dep) {
  const lib = store.library;
  const low = dep.toLowerCase();
  if (low.startsWith('pdlc_')) {
    const name = low.slice(5);
    const owned = !!(lib && lib.dlc.some((d) => d.id.toLowerCase() === name));
    return { dlc: true, ok: owned };
  }
  const ok = !!(lib && lib.mods.some((m) => m.id.toLowerCase() === low));
  return { dlc: false, ok };
}

// Nom affiché d'une dépendance : titre du mod ou nom du DLC quand ils
// sont présents, sinon l'identifiant tel qu'il est écrit dans le modDesc.xml.
function depName(dep, st) {
  const lib = store.library;
  const low = dep.toLowerCase();
  if (st.dlc) {
    const d = lib && lib.dlc.find((x) => x.id.toLowerCase() === low.slice(5));
    return d ? pickName(d.names) || d.id : dep.slice(5);
  }
  const m = st.ok && lib ? lib.mods.find((x) => x.id.toLowerCase() === low) : null;
  return m ? modTitle(m) : dep;
}

function versionName(vid) {
  const v = store.app && store.app.versions.find((x) => x.id === vid);
  return v ? v.name : vid;
}

function buildMod(mod, pin = false) {
  const title = modTitle(mod);
  const tags = [];
  if (mod.is_map) tags.push(h('span', { class: 'hc-tag' }, icon('map'), t('mod.map')));
  if (mod.kind === 'dir') tags.push(h('span', { class: 'hc-tag' }, icon('folder'), t('mod.unpacked')));
  if (mod.multiplayer === true) tags.push(h('span', { class: 'hc-tag', text: t('mod.multiplayer') }));

  const rows = [
    [t('mod.version'), mod.version || '—'],
    [t('mod.author'), mod.author || '—'],
    [t('mod.game_version'), mod.game_version ? versionName(mod.game_version) : t('mod.gv_unknown')],
    [t('mod.size'), sizeText(mod.size)],
    [t('mod.parties'), partiesText(mod.id)],
  ];
  if (store.library && store.library.storages.length > 1) {
    rows.push([t('mod.storage'), store.library.storages[mod.storage] || '—']);
  }
  const grid = h('dl', { class: 'hc-grid' }, rows.map(([k, v]) => [h('dt', { text: k }), h('dd', { text: v })]));

  const out = [
    h('div', { class: 'hc-title', text: title }),
    h('div', { class: 'hc-id', text: mod.file }),
    tags.length ? h('div', { class: 'hc-tags' }, tags) : null,
    grid,
  ];
  const deps = mod.dependencies || [];
  const optional = (mod.optional_mods || []).filter((o) => o && o.name);
  const max = pin ? Infinity : MAX_DEPS;
  let links = 0;
  const depRow = (d, st, label) => {
    const url = linkOf(mod, d);
    if (url) links++;
    // Nom, puis le lien sur une seconde ligne : le nom reste lisible.
    return h('div', { class: `hc-dep ${st.ok ? '' : 'is-absent'}` },
      icon(st.ok ? 'circle-check' : (st.dlc ? 'package' : 'circle-x')),
      h('span', { class: 'dep-main' },
        h('span', { class: 'dep-name', text: depName(d, st) }),
        url ? linkButton(mod.id, url) : null),
      h('span', { class: 'dep-state', text: label }));
  };
  if (deps.length) {
    out.push(h('div', { class: 'hc-section', text: t('mod.dependencies', { count: deps.length }) }));
    out.push(h('div', { class: 'hc-deps' }, deps.slice(0, max).map((d) => {
      const st = dependencyState(d);
      const label = st.dlc ? (st.ok ? t('dep.dlc_owned') : t('dep.dlc_missing')) : (st.ok ? t('dep.present') : t('dep.absent'));
      return depRow(d, st, label);
    })));
    if (deps.length > max) out.push(h('div', { class: 'hc-more', text: t('mod.more', { count: deps.length - max }) }));
  } else if (mod.is_map) {
    out.push(h('div', { class: 'hc-section', text: t('mod.no_dependencies') }));
  }
  // Mods facultatifs (<SearchMods><optionalMod>), jamais exigés par le jeu.
  if (optional.length) {
    out.push(h('div', { class: 'hc-section', text: t('mod.optional', { count: optional.length }) }));
    out.push(h('div', { class: 'hc-deps is-optional' }, optional.slice(0, max).map((o) => {
      const st = dependencyState(o.name);
      return depRow(o.name, st, st.ok ? t('dep.present') : t('dep.absent'));
    })));
    if (optional.length > max) out.push(h('div', { class: 'hc-more', text: t('mod.more', { count: optional.length - max }) }));
  }
  // Anciennes versions : un mod requis absent ne bloque pas le chargement.
  if ((mod.search_mods || []).length || optional.length) {
    out.push(h('div', { class: 'hc-note' }, icon('info'), h('span', { text: t('mod.searchmods_note') })));
  }
  if (links) {
    out.push(h('div', { class: 'hc-note' }, icon('external-link'),
      h('span', { text: t(pin ? 'mod.links_old' : 'mod.links_hint') })));
  }
  if (mod.kind === 'dir') {
    out.push(h('div', { class: 'hc-warn' }, icon('info'), h('span', { text: t('mod.unpacked_tip') })));
  }
  if (mod.gv_warning === 'conflict') {
    out.push(h('div', { class: 'hc-warn' }, icon('triangle-alert'), h('span', { text: t('mod.gv_conflict') })));
  }
  return out;
}

function buildDlc(d) {
  return [
    h('div', { class: 'hc-title', text: pickName(d.names) }),
    h('div', { class: 'hc-id', text: d.file }),
    h('div', { class: 'hc-tags' }, h('span', { class: 'hc-tag' }, icon('package'), d.type === 'zip' ? t('dlc.free') : t('dlc.paid'))),
    h('div', { class: 'hc-section', text: t('dlc.info') }),
  ];
}

export function scheduleCard(anchor, item, delay = 550) {
  if (pinned) return; // une fiche épinglée reste seule à l'écran
  if (isResizing()) return;
  clearTimeout(timer);
  timer = setTimeout(() => showCard(anchor, item), delay);
}

export function showCard(anchor, item, { force = false } = {}) {
  if (!card || !anchor.isConnected || document.documentElement.classList.contains('is-dragging')) return;
  if (pinned && !force) return;
  if (isResizing() && !force) return;
  const pin = !!pinned && pinned === anchor;
  const wasOn = card.classList.contains('on') && current;
  current = anchor;
  clear(card);
  card.classList.toggle('is-pinned', pin);
  card.setAttribute('aria-hidden', 'false');
  if (pin) {
    card.append(h('button', {
      class: 'icon-btn icon-btn-s hc-close', type: 'button', 'data-i18n-tip': 'mod.unpin',
      'aria-label': t('mod.unpin'), onclick: () => unpinCard(),
    }, icon('x')));
  }
  card.append(...(item.type === 'dlc' ? buildDlc(item.data) : buildMod(item.data, pin)).filter(Boolean));
  if (!wasOn) {
    // Repart de la petite taille : le déploiement rejoue à chaque ouverture.
    card.style.transition = 'none';
    card.classList.remove('on');
  }
  const r = localRect(anchor);
  const app = card.parentElement;
  const W = app.clientWidth;
  const H = app.clientHeight;
  // La fiche ne monte jamais sur l'en-tête : son haut s'arrête sous lui, et
  // une fiche plus haute que la place restante défile (épinglée) ou est coupée.
  const bar = document.getElementById('topbar');
  const appTop = localRect(app).top;
  const minY = bar ? Math.round(localRect(bar).bottom - appTop) + 12 : 16;
  card.style.maxHeight = `${Math.max(160, H - minY - 16)}px`;
  const cw = card.offsetWidth;
  const ch = card.offsetHeight;
  let x = r.right + 14;
  let side = 'left';
  if (x + cw > W - 16) {
    x = r.left - cw - 14;
    side = 'right';
  }
  if (x < 16) {
    x = Math.min(W - cw - 16, r.left + 20);
    side = 'left';
  }
  let y = r.top;
  if (y + ch > H - 16) y = H - ch - 16;
  if (y < minY) y = minY;
  card.style.translate = `${Math.round(x)}px ${Math.round(y)}px`;
  card.style.setProperty('--hc-origin', side === 'left' ? '0 0' : '100% 0');
  if (!wasOn) {
    void card.offsetWidth;
    card.style.transition = '';
  }
  card.classList.add('on');
}

// Sans argument (défilement, glisser, lasso…) : la fiche se ferme, même
// épinglée. Avec la tuile (souris qui sort, perte du focus) : seulement si la
// fiche est la sienne et n'est pas épinglée.
export function hideCard(anchor) {
  clearTimeout(timer);
  const fromTile = anchor instanceof Element;
  if (fromTile && (anchor !== current || pinned)) return;
  if (pinned) {
    pinned.classList.remove('is-pinned');
    pinned = null;
  }
  current = null;
  if (card) {
    card.classList.remove('on', 'is-pinned');
    card.setAttribute('aria-hidden', 'true');
  }
}
