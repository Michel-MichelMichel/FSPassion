// En-tête : logo à gauche ; à droite, la barre « Partie en cours »
// (menu des parties, actions sur les parties, mods communs, Appliquer,
// paramètres) ; l'icône de la version active à mi-distance des deux.
// Les boutons de fenêtre sont à part, collés à l'angle (frame.js).
// Repère d'état discret sous le menu des parties.

import {
  createParty, deleteParty, duplicateParty, partyLabel, renameParty, selectParty, setCommonEnabled,
} from './actions.js';
import { api, iconUrl } from './api.js';
import { applyBlocker, applySelected, needsApply } from './apply.js';
import { demoPill } from './demo.js';
import { clear, gameLogo, h, icon } from './dom.js';
import { makeDragZone } from './frame.js';
import { buildBell } from './notifications.js';
import { setContentMinWidth } from './scale.js';
import { currentLang, t } from './i18n.js';
import {
  EMPTY, FULL, activeVersion, isRunning, modIndex, partiesSupported, refreshLibrary, refreshParties, refreshState,
  selectedParty, store, userParty, versionInfo,
} from './state.js';
import { applyTheme, chosenTheme, oppositeTheme, themeMode } from './theme.js';
import { toastError } from './toast.js';
import { tourButton } from './tour.js';
import { markSettingsButton } from './updates.js';

let topbar = null;
let openSettings = () => {};

export function initHeader(el, { onSettings }) {
  topbar = el;
  openSettings = onSettings;
  makeDragZone(topbar);
  // L'en-tête passe sur 2 lignes quand la fenêtre est trop étroite.
  window.addEventListener('resize', fitHeader);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitHeader).catch(() => {});
}

// En-tête sur 2 lignes quand la barre « Partie en cours » ne tient
// plus sur une seule ligne (fenêtre étroite, langue aux textes longs, mode
// démonstration…). Ligne du haut : « Partie en cours » puis le menu des
// parties ; ligne du dessous : Ajouter, Dupliquer, Renommer, Supprimer, Mods
// communs, Appliquer, thème, notifications, paramètres. Mesure faite dans le
// repère de l'interface (offsetLeft, offsetWidth), indépendante de la
// réduction d'échelle.
// Redimensionnement :
// - hystérésis : l'en-tête passe sur 2 lignes dès que la barre déborde, mais
//   ne revient sur 1 ligne qu'avec RELAX px de marge. Sans elle, une fenêtre
//   redimensionnée autour du seuil faisait alterner les deux dispositions ;
// - le logo de la version reste centré entre le logo FS Passion et la barre
//   des parties telle qu'elle serait sur 1 ligne (centerVersion). La barre
//   rétrécit en passant sur 2 lignes : le logo ne saute plus de gauche à
//   droite, il glisse régulièrement avec la largeur de la fenêtre.
const RELAX = 48;
let oneLineBarW = 0;

export function fitHeader() {
  if (!topbar) return;
  const bar = topbar.querySelector('.party-bar');
  if (!bar) return;
  const cs = getComputedStyle(topbar);
  const padRight = parseFloat(cs.paddingRight) || 0;
  const wasCompact = topbar.classList.contains('is-compact');
  const vz = topbar.querySelector('.version-zone');
  if (vz) vz.style.translate = '';
  // Largeur minimale de l'en-tête sur 2 lignes : en dessous, toute
  // l'interface est réduite (scale.js).
  topbar.classList.add('is-compact');
  setContentMinWidth(naturalWidth(cs));
  topbar.classList.remove('is-compact');
  oneLineBarW = bar.offsetWidth;
  // Sur 1 ligne, les espaces extensibles
  // prennent toute la place libre, la barre touche donc toujours le bord
  // droit. La marge disponible se lit dans les espaces (au-delà de leur
  // largeur minimale), pas au bord : l'en-tête restait bloqué sur 2 lignes.
  const overflow = bar.offsetLeft + bar.offsetWidth > topbar.clientWidth - padRight + 0.5;
  let slack = 0;
  for (const sp of topbar.querySelectorAll(':scope > .topbar-spacer')) {
    slack += sp.offsetWidth - (parseFloat(getComputedStyle(sp).minWidth) || 0);
  }
  const compact = overflow || (wasCompact && slack < RELAX);
  topbar.classList.toggle('is-compact', compact);
  centerVersion();
}

// Logo de la version : au milieu de l'espace entre le logo FS Passion (ou le
// repère de démonstration) et la barre des parties sur 1 ligne, sans jamais
// toucher la barre réelle. Un décalage (« translate ») ne change pas la mise
// en page : les mesures de fitHeader restent justes.
function centerVersion() {
  const vz = topbar.querySelector('.version-zone');
  const bar = topbar.querySelector('.party-bar');
  if (!vz || !bar) return;
  const gap = 24;
  const padRight = parseFloat(getComputedStyle(topbar).paddingRight) || 0;
  const prev = vz.previousElementSibling?.previousElementSibling; // logo ou repère de démonstration
  const prevRight = prev ? prev.offsetLeft + prev.offsetWidth : 0;
  const virtualBarLeft = topbar.clientWidth - padRight - (oneLineBarW || bar.offsetWidth);
  const minLeft = prevRight + gap;
  const maxLeft = bar.offsetLeft - gap - vz.offsetWidth;
  const want = (prevRight + virtualBarLeft - vz.offsetWidth) / 2;
  const left = maxLeft < minLeft ? vz.offsetLeft : Math.min(maxLeft, Math.max(minLeft, want));
  const dx = Math.round(left - vz.offsetLeft);
  vz.style.translate = dx ? `${dx}px 0` : '';
}

// Somme des largeurs des éléments de l'en-tête, les espaces étant à leur
// minimum (min-width des .topbar-spacer).
function naturalWidth(cs) {
  let w = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
  for (const el of topbar.children) {
    const s = getComputedStyle(el);
    if (s.position === 'absolute' || s.display === 'none') continue;
    const margins = (parseFloat(s.marginLeft) || 0) + (parseFloat(s.marginRight) || 0);
    w += margins + (el.classList.contains('topbar-spacer') ? parseFloat(s.minWidth) || 0 : el.offsetWidth);
  }
  return w;
}

export function renderHeader() {
  if (!topbar || !store.app) return;
  const v = versionInfo();
  clear(topbar);
  topbar.append(
    // Logo « deux tracteurs » (assets\FS_Passion_logo\logo.svg), toute la hauteur de l'en-tête.
    h('div', { class: 'brand', role: 'img', 'aria-label': 'FS Passion' }, h('span', { class: 'app-logo app-logo-art', 'aria-hidden': 'true' })),
    ...[demoPill()].filter(Boolean),
    h('div', { class: 'topbar-spacer' }),
    // Logo Farming Simulator, presque collé à l'icône de version,
    // aligné sur son bas. Décoratif : aucune interaction.
    h('div', { class: 'version-zone' },
      h('span', { class: 'fs-logo', 'aria-hidden': 'true' }),
      buildVersionPicker(v)),
    h('div', { class: 'topbar-spacer' }),
    h('div', { class: 'party-bar' },
      buildPartyBlock(v),
      buildPartyTools(v),
      buildCommonSwitch(v),
      buildApply(v),
      buildThemeToggle(),
      buildBell(),
      tourButton(),
      settingsButton()),
  );
  renderStatus();
  fitHeader();
}

// Roue des Paramètres ; pastille quand une mise à jour de FS Passion est
// disponible (updates.js).
function settingsButton() {
  const btn = h('button', {
    class: 'icon-btn settings-btn no-drag', type: 'button', 'data-i18n-tip': 'header.settings',
    'aria-label': t('header.settings'), onclick: () => openSettings(),
  }, icon('settings'), h('span', { class: 'update-dot', 'aria-hidden': 'true' }));
  markSettingsButton(btn);
  return btn;
}

// ---------------------------------------------------------------------------
// Version active : une icône, celle de la version en cours. Au survol (après
// ~150 ms), les versions s'affichent en rangée horizontale, icônes seules
// ; l'icône survolée grossit, un clic choisit la version.
// ---------------------------------------------------------------------------

function buildVersionPicker(v) {
  const wrap = h('div', { class: 'version-pick no-drag' });
  const btn = h('button', {
    class: 'version-btn', type: 'button', 'aria-haspopup': 'menu', 'aria-expanded': 'false',
    'aria-label': t('header.version', { name: v ? v.name : '' }),
  }, v ? gameLogo(v.logo) : null);
  const menu = h('div', { class: 'menu version-menu', role: 'menu', 'aria-orientation': 'horizontal' });
  let openTimer = 0;
  let closeTimer = 0;

  const fill = () => {
    clear(menu);
    for (const ver of store.app.versions) {
      const coming = !ver.available;
      // Une version absente (ni le jeu, ni son dossier « Mes
      // documents », ni un dossier de mods) est grisée, ne grossit pas au
      // survol et ne se choisit pas ici. Elle reste réglable dans Paramètres →
      // Jeu et chemins (installation à un endroit inhabituel).
      const absent = !coming && !ver.installed && !ver.ready;
      const current = ver.id === activeVersion();
      const disabled = coming || (absent && !current);
      const sub = coming ? t('versions.coming') : ver.installed ? (ver.ready ? t('versions.ready') : t('versions.installed'))
        : ver.ready ? t('versions.ready') : `${t('versions.not_installed')}\n${t('versions.absent_help')}`;
      const item = h('button', {
        class: `version-item${absent ? ' is-absent' : ''}${coming ? ' is-coming' : ''}`, type: 'button', role: 'menuitemradio',
        'aria-checked': String(current), 'aria-current': String(current),
        'aria-disabled': disabled ? 'true' : null, tabindex: '-1',
        'aria-label': ver.name, 'data-tip-text': `${ver.name}\n${sub}`,
      }, gameLogo(ver.logo));
      item.addEventListener('click', () => {
        if (disabled) return;
        close();
        selectVersion(ver.id);
      });
      menu.append(item);
    }
  };
  const open = () => {
    clearTimeout(closeTimer);
    if (wrap.classList.contains('open')) return;
    fill();
    wrap.classList.add('open');
    menu.classList.add('on');
    btn.setAttribute('aria-expanded', 'true');
  };
  const close = () => {
    clearTimeout(openTimer);
    wrap.classList.remove('open');
    menu.classList.remove('on');
    btn.setAttribute('aria-expanded', 'false');
  };
  wrap.addEventListener('pointerenter', (e) => {
    if (e.pointerType !== 'mouse') return;
    clearTimeout(closeTimer);
    openTimer = setTimeout(open, 150);
  });
  wrap.addEventListener('pointerleave', () => {
    clearTimeout(openTimer);
    closeTimer = setTimeout(close, 180);
  });
  btn.addEventListener('click', () => (wrap.classList.contains('open') ? close() : open()));
  btn.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      open();
      const first = menu.querySelector('.version-item[aria-current="true"]') || menu.querySelector('.version-item:not([aria-disabled])');
      if (first) first.focus();
    }
  });
  menu.addEventListener('keydown', (e) => {
    const items = [...menu.querySelectorAll('.version-item:not([aria-disabled])')];
    const i = items.indexOf(document.activeElement);
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      items[(i + 1) % items.length]?.focus();
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      items[(i - 1 + items.length) % items.length]?.focus();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      close();
      btn.focus();
    } else if (e.key === 'Tab') {
      close();
    }
  });
  wrap.append(btn, menu);
  return wrap;
}

// Navigation au clavier dans un menu vertical (menu des parties).
function menuKeys(e, menu, close, btn) {
  const items = [...menu.querySelectorAll('.menu-item:not([aria-disabled])')];
  const i = items.indexOf(document.activeElement);
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    items[(i + 1) % items.length]?.focus();
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    items[(i - 1 + items.length) % items.length]?.focus();
  } else if (e.key === 'Escape') {
    e.preventDefault();
    e.stopPropagation();
    close();
    btn.focus();
  } else if (e.key === 'Tab') {
    close();
  }
}

// ---------------------------------------------------------------------------
// Interface claire ou sombre : soleil en mode sombre (passer au clair),
// lune en mode clair. Bascule vers le thème jumeau (Catppuccin Mocha ↔ Latte,
// Nord ↔ Nord Snow) ; pour un thème sans jumeau, le premier thème de l'autre mode.
// ---------------------------------------------------------------------------

function buildThemeToggle() {
  const light = themeMode(chosenTheme()) === 'light';
  const target = oppositeTheme();
  const key = light ? 'header.theme_dark' : 'header.theme_light';
  const btn = h('button', {
    class: 'icon-btn theme-btn no-drag', type: 'button', 'aria-label': t(key),
    'data-tip-text': target ? `${t(key)}\n${target.name}` : t(key),
    'aria-disabled': target ? null : 'true',
  }, icon(light ? 'moon' : 'sun'));
  btn.addEventListener('click', async () => {
    const next = oppositeTheme();
    if (!next) return;
    try {
      const res = await api.post('/api/settings', { theme: next.id });
      Object.assign(store.app.settings, res);
      const root = document.documentElement;
      root.classList.add('mode-transition');
      applyTheme(next);
      setTimeout(() => root.classList.remove('mode-transition'), 320);
      renderHeader();
      document.dispatchEvent(new CustomEvent('fsp-theme'));
    } catch (err) {
      toastError(err);
    }
  });
  return btn;
}

export async function selectVersion(vid) {
  if (vid === activeVersion()) return;
  try {
    await api.post('/api/version/active', { version: vid });
    store.library = null;
    store.parties = null;
    await refreshState();
    await Promise.all([refreshLibrary(), refreshParties()]);
  } catch (err) {
    toastError(err);
  }
}

// ---------------------------------------------------------------------------
// Partie en cours
// ---------------------------------------------------------------------------

// Nom d'après l'override, quand les parties ne sont pas disponibles.
export function partyName(applied) {
  const kind = applied ? applied.kind : 'unknown';
  switch (kind) {
    case 'full': return t('party.full');
    case 'empty': return t('party.empty');
    case 'other': return t('party.other');
    case 'party': return t('party.other');
    case 'unsupported': return t('party.unsupported');
    default: return t('party.unknown');
  }
}

function collator() {
  try {
    return new Intl.Collator(currentLang(), { sensitivity: 'base', numeric: true });
  } catch {
    return new Intl.Collator('en', { sensitivity: 'base', numeric: true });
  }
}

// Icône de la map d'une partie (petite variante), ou icône générique.
function partyIcon(party) {
  const wrap = h('span', { class: 'party-ico' });
  const m = party && party.map ? modIndex().get(party.map.toLowerCase()) : null;
  if (m && m.icon) wrap.append(h('img', { src: iconUrl(activeVersion(), m.icon, true), alt: '', draggable: 'false' }));
  else wrap.append(icon(party && party.special ? 'layers' : 'map'));
  return wrap;
}

// La bibliothèque arrive après les parties : l'icône de la map est mise à
// jour sans refaire l'en-tête (un menu ouvert reste ouvert).
export function updatePartyIcon() {
  const old = topbar && topbar.querySelector('.party-select .party-ico');
  if (!old || !partiesSupported()) return;
  const sel = selectedParty();
  old.replaceWith(partyIcon(sel.special ? { special: true } : sel));
}

function buildPartyBlock(v) {
  const unsupported = v && !v.has_override;
  const ready = partiesSupported();
  const sel = selectedParty();
  const p = store.parties;
  const label = ready ? partyLabel(sel.id) : partyName(v ? v.applied : null);
  const wrap = h('div', { class: 'party-block' });
  const btn = h('button', {
    class: 'party-select', type: 'button', 'aria-haspopup': 'menu', 'aria-expanded': 'false',
    'aria-disabled': unsupported || !ready ? 'true' : null,
  },
  ready ? partyIcon(sel.special ? { special: true } : sel) : null,
  h('span', { class: 'party-name', text: label }),
  ready && p.applied === sel.id ? h('span', { class: 'menu-tag', text: t('party.applied_tag') }) : null,
  icon('chevron-down'));
  if (!ready && !unsupported && p && p.reason) btn.dataset.tipText = t(p.reason.key, p.reason.params || {});
  const menu = h('div', { class: 'menu party-menu', role: 'menu' });
  const pick = h('div', { class: 'version-pick party-pick no-drag' }, btn, menu);
  const close = () => {
    menu.classList.remove('on');
    btn.setAttribute('aria-expanded', 'false');
    document.removeEventListener('pointerdown', outside, true);
  };
  const outside = (e) => {
    if (!pick.contains(e.target)) close();
  };
  const item = (pid, text, sub, ico, special) => {
    const isSel = sel && sel.id === pid;
    const el = h('button', {
      class: `menu-item${special ? ' menu-special' : ''}`, type: 'button', role: 'menuitemradio', tabindex: '-1',
      'aria-checked': String(isSel), 'aria-current': String(isSel),
    },
    ico,
    h('span', { class: 'mi-text' }, h('span', { text }), ...[].concat(sub).filter(Boolean).map((x) => h('span', { class: 'mi-sub', text: x }))),
    p.applied === pid ? h('span', { class: 'menu-tag', text: t('party.applied_tag') }) : null,
    isSel ? icon('check', 'ico-s') : null);
    el.addEventListener('click', () => {
      close();
      if (!isSel) selectParty(pid);
    });
    return el;
  };
  const fill = () => {
    const count = store.library ? store.library.mods.length : null;
    clear(menu);
    // Les parties de l'utilisateur par ordre alphabétique, avec l'icône de leur
    // map ; puis la Partie Pleine et la Partie Vide, dans un style distinct.
    const list = p.parties.slice().sort((a, b) => collator().compare(a.name, b.name));
    if (!list.length) menu.append(h('div', { class: 'menu-empty', text: t('party.none_yet') }));
    const scroll = h('div', { class: 'menu-scroll' });
    for (const party of list) {
      scroll.append(item(party.id, party.name, t('party.mods_count', { count: party.mods.length }), partyIcon(party), false));
    }
    if (list.length) menu.append(scroll);
    menu.append(h('div', { class: 'menu-sep' }),
      item(FULL, t('party.full'), [count === null ? '' : t('party.full_count', { count }), t('party.full_tip')], partyIcon({ special: true }), true),
      item(EMPTY, t('party.empty'), t('party.empty_sub'), partyIcon({ special: true }), true));
  };
  btn.addEventListener('click', () => {
    if (unsupported || !ready) return;
    if (menu.classList.contains('on')) {
      close();
      return;
    }
    fill();
    menu.classList.add('on');
    btn.setAttribute('aria-expanded', 'true');
    document.addEventListener('pointerdown', outside, true);
    const cur = menu.querySelector('.menu-item[aria-current="true"]');
    if (cur) cur.scrollIntoView({ block: 'nearest' });
  });
  btn.addEventListener('keydown', (e) => {
    if ((e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') && !unsupported && ready) {
      e.preventDefault();
      if (!menu.classList.contains('on')) btn.click();
      (menu.querySelector('.menu-item[aria-current="true"]') || menu.querySelector('.menu-item'))?.focus();
    }
  });
  menu.addEventListener('keydown', (e) => menuKeys(e, menu, close, btn));
  wrap.append(h('span', { class: 'party-label', text: t('header.current_party') }), pick,
    h('div', { class: 'party-status', 'aria-live': 'polite' }));
  return wrap;
}

function buildPartyTools(v) {
  const ready = partiesSupported();
  const user = userParty();
  const mk = (ico, key, enabled, run, why) => {
    const b = h('button', { class: 'icon-btn', type: 'button', 'aria-label': t(key) }, icon(ico));
    if (enabled) {
      b.dataset.i18nTip = key;
      b.addEventListener('click', run);
    } else {
      b.setAttribute('aria-disabled', 'true');
      b.dataset.tipText = why ? `${t(key)}\n${why}` : t(key);
    }
    return b;
  };
  const special = ready && !user ? t('parties.special_locked') : null;
  const reason = !ready && store.parties && store.parties.reason ? t(store.parties.reason.key, store.parties.reason.params || {}) : null;
  const tools = h('div', { class: 'party-tools no-drag' },
    mk('plus', 'header.create', ready, createParty, reason),
    mk('copy-plus', 'header.duplicate', !!user, duplicateParty, special || reason),
    mk('pencil', 'header.rename', !!user, renameParty, special || reason),
    mk('trash-2', 'header.delete', !!user, deleteParty, special || reason));
  if (v && !v.has_override) tools.style.visibility = 'hidden';
  return tools;
}

// Switch « Mods communs » de la partie sélectionnée (désactivé pour les
// parties spéciales : la Partie Pleine a déjà tous les mods, la Vide aucun).
function buildCommonSwitch(v) {
  const ready = partiesSupported();
  const sel = selectedParty();
  const user = userParty();
  const checked = user ? user.common_enabled : !!(sel && sel.id === FULL);
  const input = h('input', { type: 'checkbox', checked, disabled: !user });
  const label = h('label', { class: `switch common-switch no-drag${user ? '' : ' is-disabled'}` }, input,
    h('span', { class: 'switch-track' }), h('span', { text: t('header.common_mods') }));
  label.dataset.tipText = user ? t('header.common_mods_tip')
    : `${t('header.common_mods_tip')}\n${ready ? t('parties.special_locked') : ''}`.trim();
  input.addEventListener('change', () => setCommonEnabled(input.checked));
  if (v && !v.has_override) label.style.visibility = 'hidden';
  return label;
}

function buildApply(v) {
  // Bouton principal (rempli de l'accent) seulement quand il faut appliquer.
  const needed = !applyBlocker() && needsApply();
  const btn = h('button', { class: `btn ${needed ? 'btn-primary is-needed' : ''} apply-btn no-drag`, type: 'button' },
    icon('check'), h('span', { text: t('header.apply') }));
  const why = applyBlocker();
  if (why) {
    btn.setAttribute('aria-disabled', 'true');
    btn.dataset.tipText = t(why, { game: v ? v.name : '' });
  } else {
    // Mis en évidence quand la partie sélectionnée n'est pas appliquée, ou a
    // changé depuis sa dernière application.
    btn.dataset.tipText = needsApply() ? t('header.apply_tip') : t('header.apply_done_tip');
  }
  btn.addEventListener('click', () => {
    if (btn.getAttribute('aria-disabled') === 'true') return;
    applySelected();
  });
  if (v && !v.has_override) btn.style.visibility = 'hidden';
  return btn;
}

// ---------------------------------------------------------------------------
// Repère d'état : une ligne courte sous le menu des parties, au lieu
// d'un bandeau sur toute la largeur de la fenêtre.
// ---------------------------------------------------------------------------

export function renderStatus() {
  const el = topbar && topbar.querySelector('.party-status');
  if (!el || !store.app) return;
  const v = versionInfo();
  clear(el);
  let text = '';
  let ico = 'info';
  let level = 'info';
  if (v && isRunning(v.id)) {
    text = t('status.running', { game: v.name });
    ico = 'play';
  } else if (v && v.available && v.has_override && v.cfg.user_dir && v.checks.user_dir && v.checks.user_dir.key === 'path.no_gamesettings') {
    text = t('path.no_gamesettings');
    ico = 'circle-alert';
    level = 'warn';
  } else if (partiesSupported() && !store.parties.applied && store.parties.applied_directory) {
    text = t('status.other_folder_path', { path: store.parties.applied_directory });
    level = 'warn';
  } else if (v && v.applied && v.applied.kind === 'other' && v.applied.directory) {
    text = t('status.other_folder_path', { path: v.applied.directory });
    level = 'warn';
  } else if (partiesSupported() && store.parties.applied && store.parties.applied !== store.parties.selected) {
    // La partie sélectionnée n'est pas celle que le jeu charge.
    text = t('status.applied', { name: partyLabel(store.parties.applied) });
  } else if (partiesSupported() && store.parties.applied_stale) {
    text = t('status.stale');
    ico = 'refresh-cw';
  }
  el.classList.toggle('on', !!text);
  el.classList.toggle('is-warn', level === 'warn');
  if (!text) {
    delete el.dataset.tipText;
    return;
  }
  el.append(icon(ico, 'ico-s'), h('span', { text }));
  el.dataset.tipText = text;
}
