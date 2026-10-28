// Paramètres : fenêtre unique de taille fixe, au-dessus de la fenêtre
// principale. Une colonne de navigation à gauche, une seule page affichée à la
// fois : Jeu et chemins, Affichage, Application, Aide et à propos. Pas
// d'accordéon ni d'animation de dépliage : on change de page d'un coup.

import { demoAvailable, isDemo, startDemo, stopDemo } from './demo.js';
import { snapWheel } from './snapscroll.js';
import { api } from './api.js';
import { exportConfig, importConfig } from './backup.js';
import { openDownloads } from './downloads.js';
import { openDialog } from './dialog.js';
import { clear, copyText, flashCopied, gameLogo, h, icon, reducedMotion } from './dom.js';
import { renderHeader, selectVersion } from './header.js';
import { currentLang, formatNumber, loadLanguage, t } from './i18n.js';
import { uiScale } from './scale.js';
import { activeVersion, refreshLibrary, refreshState, store, subscribe, versionInfo } from './state.js';
import {
  allThemes, applyTheme, contrast, endPreview, paintSwatch, previewTheme, reduceMotionActive, setOptions,
  themeMode, themeStyle, themeSurfaces, themeWindow,
} from './theme.js';
import { openStopUsing } from './stopuse.js';
import { toast, toastError } from './toast.js';
import { buildUpdates } from './updates.js';

let dlg = null;
// Sous-sections des Paramètres pour le défilement à la molette.
// Thèmes, un cran = une rangée de pastilles (avec 20 thèmes, le bloc
// entier faisait un saut énorme). Les pastilles d'une même rangée ont le même
// haut : un seul arrêt par rangée.
const SNAP_TARGETS = [
  '.set-group', '.set-group > :not(.set-group-head)', '.ver-box > :not(.ver-box-title)',
  '.path-field > .path-card', '.launch-wrap > *', '.rights-box', '.fold-body .path-field',
  '.swatch-groups > .set-group-title', '.swatch',
].join(', ');
let openId = 'game';
let navEls = new Map();
let pane = null;
let unsub = null;
let actions = {};
let layoutEl = null;
let frameSvg = null;
let framePath = null;
let frameGlow = null;
let frameObs = null;

export function initSettings(a) {
  actions = a;
}

const SECTIONS = [
  { id: 'game', ico: 'hard-drive', build: buildGame },
  { id: 'look', ico: 'palette', build: buildLook },
  { id: 'app', ico: 'settings', build: buildApp },
  { id: 'help', ico: 'info', build: buildHelp },
];

// Anciens noms de sections (.x) : un appel avec l'un d'eux ouvre la page
// qui contient désormais ce réglage.
const ALIASES = {
  paths: 'game', anomalies: 'game',
  general: 'app', downloads: 'app', window: 'app', backup: 'app', stop: 'app',
  language: 'look', theme: 'look',
  donate: 'help', about: 'help', notice: 'help', logs: 'help',
  updates: 'app',
};

export function openSettings(section) {
  if (section) openId = ALIASES[section] || section;
  if (dlg && !dlg.closed) {
    showPage(openId);
    if (section === 'updates') revealUpdates();
    return;
  }
  navEls = new Map();
  const nav = h('nav', { class: 'settings-nav', 'aria-label': t('settings.title') });
  for (const sec of SECTIONS) {
    const btn = h('button', { class: 'nav-item', type: 'button' },
      icon(sec.ico), h('span', { text: t(`settings.${sec.id}.title`) }));
    btn.addEventListener('click', () => showPage(sec.id));
    navEls.set(sec.id, { btn, sec });
    nav.append(btn);
  }
  pane = h('div', { class: 'settings-pane' });
  // Molette : un cran = une sous-section (un chemin, un réglage, un
  // bloc), et non plus une section entière. Les points trop proches (< 90 px)
  // sont fusionnés, pour qu'un cran fasse toujours avancer.
  snapWheel(pane, () => {
    const k = uiScale() || 1;
    const top0 = pane.getBoundingClientRect().top;
    const pts = [...pane.querySelectorAll(SNAP_TARGETS)]
      .filter((el) => el.offsetParent !== null)
      .map((el) => Math.round((el.getBoundingClientRect().top - top0) / k + pane.scrollTop - 14))
      .filter((y) => y > 0)
      .sort((a, b) => a - b);
    const out = [0];
    for (const y of pts) if (y - out[out.length - 1] >= 90) out.push(y);
    return out;
  });
  frameSvg = svgEl('svg', { class: 'set-frame', 'aria-hidden': 'true', focusable: 'false' });
  framePath = svgEl('path', {});
  // Lueur qui court le long du contour (thèmes bicolores, themes.css).
  frameGlow = [
    svgEl('path', { class: 'set-frame-glow set-frame-halo', pathLength: '1000' }),
    svgEl('path', { class: 'set-frame-glow', pathLength: '1000' }),
  ];
  frameSvg.append(framePath, ...frameGlow);
  const body = h('div', { class: 'settings-layout' }, frameSvg, nav, pane);
  layoutEl = body;
  dlg = openDialog(body, {
    title: t('settings.title'),
    cls: 'dlg-settings',
    onClose: () => {
      endPreview();
      if (unsub) unsub();
      unsub = null;
      document.removeEventListener('fsp-theme', refreshOpen);
      dlg = null;
      pane = null;
      navEls = new Map();
      frameObs?.disconnect();
      frameObs = null;
      layoutEl = null;
      frameSvg = null;
      framePath = null;
      frameGlow = null;
    },
  });
  const unsubState = subscribe('state', () => refreshOpen());
  const unsubUpdate = subscribe('update', () => refreshOpen());
  unsub = () => {
    unsubState();
    unsubUpdate();
  };
  document.addEventListener('fsp-theme', refreshOpen);
  frameObs = new ResizeObserver(() => drawFrame());
  frameObs.observe(layoutEl);
  showPage(openId);
  if (section === 'updates') revealUpdates();
}

// Encart « Mises à jour de FS Passion » amené en haut de la page.
function revealUpdates() {
  requestAnimationFrame(() => {
    const el = pane && pane.querySelector('.set-updates');
    if (el) pane.scrollTop = Math.max(0, el.offsetTop - 14);
  });
}

function showPage(id) {
  openId = id;
  for (const [sid, n] of navEls) {
    const on = sid === id;
    n.btn.classList.toggle('is-active', on);
    if (on) n.btn.setAttribute('aria-current', 'page');
    else n.btn.removeAttribute('aria-current');
  }
  renderPage(true);
  if (pane) pane.scrollTop = 0;
  drawFrame();
}

function renderPage(opening) {
  const n = navEls.get(openId);
  if (!n || !pane) return;
  clear(pane);
  pane.append(
    h('h2', { class: 'settings-page-title mgrad', text: t(`settings.${n.sec.id}.title`) }),
    ...[].concat(n.sec.build({ opening })).filter(Boolean));
}

function refreshOpen() {
  if (!dlg || !pane) return;
  // Ne pas reconstruire pendant une saisie : on perdrait le texte en cours.
  if (pane.contains(document.activeElement) && document.activeElement.tagName === 'INPUT') return;
  const keep = pane.scrollTop;
  renderPage(false);
  pane.scrollTop = keep;
}

// ---------------------------------------------------------------------------
// Outils
// ---------------------------------------------------------------------------

// Contour d'un seul tenant : le menu sélectionné et la page forment une même
// forme aux coins arrondis, et le raccord entre les deux est arrondi aussi.
// Le tracé est recalculé à partir de la position réelle des éléments.
const FRAME_R = 10;

function svgEl(tag, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function drawFrame() {
  if (!layoutEl || !framePath || !pane) return;
  const n = navEls.get(openId);
  if (!n) return;
  const nav = n.btn.parentElement;
  const R = FRAME_R;
  // Menu sélectionné : bords gauche, haut et bas ; son bord droit est la page.
  const tX = nav.offsetLeft + n.btn.offsetLeft + 0.5;
  const tT = nav.offsetTop + n.btn.offsetTop + 0.5;
  const tB = tT + n.btn.offsetHeight - 1;
  // Page : contour complet, décalé d'un demi-trait pour rester net.
  const pL = pane.offsetLeft + 0.5;
  const pT = pane.offsetTop + 0.5;
  const pR = pane.offsetLeft + pane.offsetWidth - 0.5;
  const pB = pane.offsetTop + pane.offsetHeight - 0.5;
  const d = [
    `M ${tX + R} ${tT}`,
    `L ${pL - R} ${tT}`,
    `A ${R} ${R} 0 0 0 ${pL} ${tT - R}`, // raccord haut : menu → page
    `L ${pL} ${pT + R}`,
    `A ${R} ${R} 0 0 1 ${pL + R} ${pT}`,
    `L ${pR - R} ${pT}`,
    `A ${R} ${R} 0 0 1 ${pR} ${pT + R}`,
    `L ${pR} ${pB - R}`,
    `A ${R} ${R} 0 0 1 ${pR - R} ${pB}`,
    `L ${pL + R} ${pB}`,
    `A ${R} ${R} 0 0 1 ${pL} ${pB - R}`,
    `L ${pL} ${tB + R}`,
    `A ${R} ${R} 0 0 0 ${pL - R} ${tB}`, // raccord bas : page → menu
    `L ${tX + R} ${tB}`,
    `A ${R} ${R} 0 0 1 ${tX} ${tB - R}`,
    `L ${tX} ${tT + R}`,
    `A ${R} ${R} 0 0 1 ${tX + R} ${tT}`,
    'Z',
  ].join(' ');
  frameSvg.setAttribute('viewBox', `0 0 ${layoutEl.clientWidth} ${layoutEl.clientHeight}`);
  framePath.setAttribute('d', d);
  // Le tracé glisse d'un menu à l'autre (même structure, seules les
  // coordonnées changent) ; sans animation si Windows la réduit.
  framePath.style.transition = reducedMotion() ? 'none' : '';
  framePath.style.d = `path("${d}")`;
  for (const g of frameGlow || []) {
    g.setAttribute('d', d);
    g.style.transition = framePath.style.transition;
    g.style.d = `path("${d}")`;
  }
}

async function saveSettings(patch) {
  try {
    const res = await api.post('/api/settings', patch);
    Object.assign(store.app.settings, res);
    return res;
  } catch (err) {
    toastError(err);
    return null;
  }
}

function switchCtl(labelKey, checked, onChange, disabled = false) {
  const input = h('input', { type: 'checkbox', checked: !!checked, disabled });
  input.addEventListener('change', () => onChange(input.checked));
  return h('label', { class: `switch${disabled ? ' is-disabled' : ''}` }, input, h('span', { class: 'switch-track' }), h('span', { text: t(labelKey) }));
}

function statusLine(check) {
  const el = h('div', { class: 'path-status' });
  if (!check || check.level === 'empty') return el;
  const level = check.level;
  el.classList.add(`is-${level}`);
  el.append(icon(level === 'ok' ? 'circle-check' : level === 'warn' ? 'triangle-alert' : 'circle-alert'), t(check.key, check.params || {}));
  return el;
}

function copyBtn(text) {
  const b = h('button', { class: 'icon-btn icon-btn-s', type: 'button', 'data-i18n-tip': 'common.copy', 'aria-label': t('common.copy') }, icon('clipboard-copy'));
  if (!text) b.setAttribute('aria-disabled', 'true');
  b.addEventListener('click', async () => {
    if (!text) return;
    if (await copyText(text)) flashCopied(b);
  });
  return b;
}

async function browse(kind, field, vid, initial) {
  try {
    const res = await api.post('/api/browse', { kind, field, version: vid, initial });
    return res.path || null;
  } catch (err) {
    toastError(err);
    return null;
  }
}

// Bloc d'une page : un titre, puis son contenu. `headCtl`, un réglage
// posé à droite sur la ligne du titre.
function group(ico, titleKey, content, cls = '', headCtl = null) {
  if (headCtl) headCtl.classList.add('set-head-ctl');
  return h('div', { class: `set-group ${cls}`.trim() },
    h('h3', { class: 'set-group-head' }, icon(ico), h('span', { text: t(titleKey) }), headCtl),
    ...[].concat(content).filter(Boolean));
}

// Contenu replié par défaut derrière un texte : le bouton
// affiche « Afficher… », puis « Masquer… » quand le contenu est ouvert.
function foldable(showKey, hideKey, content) {
  const body = h('div', { class: 'fold-body' }, content);
  body.hidden = true;
  const label = h('span', { text: t(showKey) });
  const btn = h('button', { class: 'fold-toggle', type: 'button', 'aria-expanded': 'false' }, label, icon('chevron-down', 'ico-s'));
  btn.addEventListener('click', () => {
    const open = body.hidden;
    body.hidden = !open;
    btn.setAttribute('aria-expanded', String(open));
    label.textContent = t(open ? hideKey : showKey);
  });
  return h('div', { class: 'fold' }, btn, body);
}

// ---------------------------------------------------------------------------
// Page « Jeu et chemins » : réglages propres à la version sélectionnée
// ---------------------------------------------------------------------------

function buildGame() {
  const v = versionInfo();
  const row = h('div', { class: 'versions-row', role: 'group', 'aria-label': t('settings.paths.versions') });
  for (const ver of store.app.versions) {
    const chip = h('button', {
      class: `ver-chip${!ver.installed && ver.available ? ' is-dim' : ''}`, type: 'button',
      'aria-pressed': String(ver.id === activeVersion()),
      'aria-disabled': ver.available ? null : 'true',
    }, gameLogo(ver.logo), h('span', { text: ver.available ? ver.short : t('versions.coming') }));
    chip.setAttribute('aria-label', ver.name);
    chip.addEventListener('click', () => ver.available && selectVersion(ver.id));
    row.append(chip);
  }
  // Rangée des versions et carte de la version choisie : une seule section.
  const section = h('div', { class: 'set-group' }, row);
  const out = [section];
  if (v) {
    section.append(h('div', { class: 'ver-box' },
      h('div', { class: 'ver-box-title' }, gameLogo(v.logo), h('span', { text: v.name })),
      pathField(v, 'game_exe', 'file'),
      pathField(v, 'user_dir', 'folder'),
      modsDirs(v),
      derived(v),
      // Deux boutons, pour que l'on sache toujours ce qui sera modifié.
      detectButtons(v),
      launchMethod(v),
    ));
  }
  out.push(group('triangle-alert', 'settings.anomalies.title', buildAnomalies()));
  out.push(group('flask-conical', 'settings.demo.title', buildDemo()));
  return out;
}

// Essayer FS Passion sans le jeu, ou quitter le mode démonstration.
function buildDemo() {
  if (isDemo()) {
    return [
      h('div', { class: 'set-help', text: t('settings.demo.active_help') }),
      h('div', { class: 'set-row' },
        h('button', { class: 'btn btn-danger', type: 'button', onclick: () => stopDemo() }, icon('log-out'), t('demo.stop_ok'))),
    ];
  }
  const start = h('button', { class: 'btn', type: 'button' }, icon('flask-conical'), t('settings.demo.start'));
  if (demoAvailable()) start.addEventListener('click', () => startDemo());
  else {
    start.setAttribute('aria-disabled', 'true');
    start.dataset.tipText = t('demo.unavailable');
  }
  return [
    h('div', { class: 'set-help', text: t('settings.demo.help') }),
    h('div', { class: 'set-row' }, start),
  ];
}

// Carte d'un chemin : au survol, un cadre lumineux l'entoure,
// le titre et le champ glissent légèrement vers le haut, et l'état « Trouvé »
// apparaît (il est masqué le reste du temps ; les erreurs restent visibles).
// Le cadre s'éclaire davantage près de la souris.
function pathCard(...children) {
  const card = h('div', { class: 'path-field path-card' }, ...children);
  card.addEventListener('pointermove', (e) => {
    const r = card.getBoundingClientRect();
    const k = uiScale();
    card.style.setProperty('--mx', `${Math.round((e.clientX - r.left) / k)}px`);
    card.style.setProperty('--my', `${Math.round((e.clientY - r.top) / k)}px`);
  }, { passive: true });
  return card;
}

function pathField(v, field, kind, opts = {}) {
  const value = v.cfg[field] || '';
  const input = h('input', { class: 'field-input', type: 'text', spellcheck: 'false', value, readonly: opts.readonly || null });
  const save = async () => {
    if (input.value.trim() === value) return;
    await setPath(v.id, field, input.value);
  };
  input.addEventListener('change', save);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      input.blur();
    }
  });
  const browseBtn = h('button', { class: 'btn', type: 'button' }, icon('folder-open'), t('settings.paths.browse'));
  browseBtn.addEventListener('click', async () => {
    const p = await browse(kind, field, v.id, input.value);
    if (p) {
      input.value = p;
      await setPath(v.id, field, p);
    }
  });
  if (opts.readonly) browseBtn.hidden = true;
  return pathCard(
    h('label', { class: 'path-label' }, opts.num ? h('span', { class: 'path-num', text: opts.num }) : null, ' ', t(`settings.paths.${field}`)),
    h('div', { class: 'path-line' }, input, browseBtn),
    statusLine(v.checks[field]),
    opts.help ? h('div', { class: 'set-help', text: opts.help }) : null);
}

// Dossiers de mods : chemin n° 1 (principal), puis jusqu'à deux
// dossiers de stockage supplémentaires, en général sur d'autres disques.
function modsDirs(v) {
  const wrap = h('div', { class: 'path-field' });
  wrap.append(h('div', { class: 'set-group-title', text: t('settings.paths.mods_dirs') }));
  const main = pathField(v, 'mods_dir', 'folder', {
    num: '1',
    readonly: v.mods_dir_fixed,
    help: v.mods_dir_fixed ? t('settings.paths.fixed_fs2011') : null,
  });
  wrap.append(main);
  if (v.mods_dir_fixed || !v.storage) return wrap;
  const extra = (v.cfg.extra_mods_dirs || []).slice();
  extra.forEach((value, i) => wrap.append(extraField(v, extra, i)));
  if (extra.length < v.storage.max_extra) {
    const add = h('button', { class: 'btn btn-ghost btn-s', type: 'button' }, icon('plus'), t('settings.paths.add_storage'));
    add.addEventListener('click', async () => {
      const p = await browse('folder', 'extra_mods_dir', v.id, '');
      if (p) await setStorages(v, [...extra, p]);
    });
    wrap.append(h('div', { class: 'set-row storage-add' }, add,
      h('span', { class: 'set-help', text: t('settings.paths.add_storage_help') })));
  }
  if (v.storage.needs_symlinks) wrap.append(rightsBox(v));
  return wrap;
}

function extraField(v, extra, i) {
  const value = extra[i] || '';
  const input = h('input', { class: 'field-input', type: 'text', spellcheck: 'false', value });
  const save = async (next) => {
    const dirs = extra.slice();
    dirs[i] = next;
    await setStorages(v, dirs.filter((x) => x && x.trim()));
  };
  input.addEventListener('change', () => {
    if (input.value.trim() !== value) save(input.value);
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      input.blur();
    }
  });
  const browseBtn = h('button', { class: 'btn', type: 'button' }, icon('folder-open'), t('settings.paths.browse'));
  browseBtn.addEventListener('click', async () => {
    const p = await browse('folder', 'extra_mods_dir', v.id, input.value);
    if (p) await save(p);
  });
  const removeBtn = h('button', {
    class: 'icon-btn storage-remove', type: 'button', 'data-i18n-tip': 'settings.paths.remove_storage',
    'aria-label': t('settings.paths.remove_storage'),
  }, icon('x'));
  removeBtn.addEventListener('click', () => setStorages(v, extra.filter((_, j) => j !== i)));
  return pathCard(
    h('label', { class: 'path-label' }, h('span', { class: 'path-num', text: String(i + 2) }), ' ', t('settings.paths.extra_dir')),
    h('div', { class: 'path-line' }, input, browseBtn, removeBtn),
    statusLine(v.storage.extra[i]),
    h('div', { class: 'set-help', text: t('settings.paths.extra_help') }));
}

async function setStorages(v, dirs) {
  try {
    const res = await api.post('/api/version/storages', { version: v.id, dirs });
    await refreshState();
    if (v.id === activeVersion()) await refreshLibrary();
    // Un dossier sur un autre disque, sans droits pour les liens symboliques :
    // FS Passion explique et propose les solutions.
    const r = res.rights || {};
    if (res.storage && res.storage.needs_symlinks && r.symlinks === false && r.windows) openRights(r);
  } catch (err) {
    toastError(err);
  }
}

// État des droits pour les liens symboliques, sous les dossiers de mods.
function rightsBox() {
  const r = store.app.rights || {};
  const box = h('div', { class: 'rights-box' });
  if (r.symlinks === false) {
    box.classList.add('is-warn');
    box.append(h('div', { class: 'rights-line' }, icon('shield'), h('span', { text: t('rights.missing') })),
      h('div', { class: 'set-row' },
        h('button', { class: 'btn btn-primary', type: 'button', onclick: () => openRights(r) }, icon('shield'), t('rights.get')),
        h('button', { class: 'btn btn-ghost', type: 'button', onclick: () => rightsAction('check') }, icon('refresh-cw'), t('rights.check'))));
  } else {
    box.append(h('div', { class: 'rights-line' }, icon('circle-check'),
      h('span', { text: !r.symlinks ? t('rights.unknown') : t(r.dev_mode ? 'rights.ok_dev' : r.admin ? 'rights.ok' : 'rights.ok_plain') })));
    if (r.symlinks !== true) {
      box.append(h('div', { class: 'set-row' },
        h('button', { class: 'btn btn-ghost', type: 'button', onclick: () => rightsAction('check') }, icon('refresh-cw'), t('rights.check'))));
    }
  }
  if (r.run_as_admin) {
    box.append(h('div', { class: 'set-row' },
      h('span', { class: 'set-help', text: t('rights.admin_on') }),
      h('button', { class: 'btn btn-ghost btn-s', type: 'button', onclick: () => rightsAction('no_admin') }, t('rights.admin_off'))));
  }
  return box;
}

async function rightsAction(action) {
  try {
    const res = await api.post('/api/rights', { action });
    if (res.restart) {
      toast('rights.restarting', {}, 'info');
      return res;
    }
    await refreshState();
    if (action === 'check' && res.needed) {
      toast(res.symlinks ? 'rights.now_ok' : 'rights.still_missing', {}, res.symlinks ? 'success' : 'warn');
      if (res.symlinks) await refreshLibrary();
    }
    return res;
  } catch (err) {
    toastError(err);
    return null;
  }
}

// Fenêtre « Droits pour les autres disques » : administrateur (case
// cochée par FS Passion, avec ses conséquences) ou Mode développeur. Un compte
// Windows standard n'a que le Mode développeur (sinon FS Passion tournerait
// sous un autre compte, avec d'autres dossiers).
function openRights(r) {
  const standard = !!r.standard_user;
  // En développement (lancer_dev.bat), pas de réglage permanent : une relance
  // en administrateur, pour cette fois.
  const once = !store.app.frozen;
  const consequences = h('ul', { class: 'rights-list' },
    h('li', { text: t('rights.uac') }),
    h('li', { text: t('rights.game_normal') }),
    h('li', { text: t('rights.no_drop') }));
  const later = h('button', { class: 'btn btn-ghost', type: 'button', text: t('rights.later') });
  const devBtn = h('button', { class: `btn ${standard ? 'btn-primary' : ''}`, type: 'button' }, icon('settings'), t('rights.dev_mode'));
  const adminBtn = standard ? null
    : h('button', { class: 'btn btn-primary', type: 'button', autofocus: true }, icon('shield'), t(once ? 'rights.admin_once' : 'rights.admin'));
  const body = h('div', { class: 'dlg-body' },
    h('p', { class: 'dlg-text', text: t('rights.intro') }),
    standard ? h('p', { class: 'dlg-text', text: t('rights.standard') }) : null,
    standard ? null : h('div', { class: 'rights-option' },
      h('h3', { text: t(once ? 'rights.admin_once_title' : 'rights.admin_title') }),
      h('p', { class: 'set-help', text: t(once ? 'rights.admin_once_text' : 'rights.admin_text') }),
      consequences),
    h('div', { class: 'rights-option' },
      h('h3', { text: t('rights.dev_title') }),
      h('p', { class: 'set-help', text: t('rights.dev_text') })),
    h('p', { class: 'set-help rights-note', text: t('rights.without') }),
    h('div', { class: 'dlg-actions' }, later, devBtn, adminBtn));
  const d = openDialog(body, { title: t('rights.title'), cls: 'dlg-rights' });
  later.addEventListener('click', () => d.close());
  devBtn.addEventListener('click', async () => {
    await rightsAction('dev_settings');
    d.close();
  });
  if (adminBtn) {
    adminBtn.addEventListener('click', async () => {
      adminBtn.setAttribute('aria-disabled', 'true');
      const res = await rightsAction('admin');
      if (!res) adminBtn.removeAttribute('aria-disabled');
      else d.close();
    });
  }
}

function derived(v) {
  const list = h('div', { class: 'derived' });
  list.append(h('div', { class: 'set-group-title', text: t('settings.paths.derived') }));
  for (const d of v.derived) {
    const cls = !d.applicable ? 'is-na' : (!d.exists ? 'is-missing' : '');
    const text = !d.applicable ? t('settings.paths.not_applicable') : (d.path || '—');
    list.append(h('div', { class: `derived-row ${cls}` },
      h('span', { class: 'd-label', text: t(`settings.paths.d_${d.key}`) }),
      h('span', { class: 'd-path', text, title: d.path || '' }),
      copyBtn(d.applicable && d.path ? d.path : '')));
  }
  return list;
}

function launchMethod(v) {
  const seg = h('div', { class: 'segmented', role: 'group', 'aria-label': t('settings.paths.launch_method') });
  for (const m of ['auto', 'platform', 'exe']) {
    const b = h('button', { type: 'button', 'aria-pressed': String(v.cfg.launch_method === m), text: t(`settings.paths.launch_${m}`) });
    b.addEventListener('click', async () => {
      try {
        await api.post('/api/version/launch-method', { version: v.id, method: m });
        await refreshState();
      } catch (err) {
        toastError(err);
      }
    });
    seg.append(b);
  }
  // Bloc « Mode de lancement du jeu » sur un fond zébré, puis les arguments.
  const mode = h('div', { class: 'path-field launch-mode' },
    h('div', { class: 'set-group-title', text: t('settings.paths.launch_method') }),
    h('div', { class: 'set-row' }, seg),
    h('div', { class: 'set-help', text: t('settings.paths.launch_help') }),
    switchCtl('settings.paths.minimize_on_launch', store.app.settings.minimize_on_launch, (on) => saveSettings({ minimize_on_launch: on })));
  return h('div', { class: 'launch-wrap' }, mode, launchArgs(v));
}

// Arguments de lancement, cochés par version du jeu.
// Ils ne sont ajoutés par FS Passion que quand il lance l'exécutable.
// Steam (qui demanderait de confirmer à chaque lancement) et Epic Games les
// prennent dans leurs propres options de lancement : texte à copier, et chemin
// du menu. Microsoft Store / Xbox : aucun moyen de les transmettre.
function launchArgs(v) {
  const args = v.cfg.launch_args || {};
  const li = v.launch || { args_mode: 'command', args: [], args_text: '' };
  const mode = li.args_mode || 'command';
  const option = (labelKey, infoKey, key, extra = null) => h('div', { class: 'arg-option' },
    switchCtl(labelKey, !!args[key], (on) => saveLaunchArgs(v, { [key]: on })),
    h('span', { class: 'set-help', text: t(infoKey) }),
    extra);
  // Replié par défaut, la section est longue.
  return foldable('settings.paths.args_show', 'settings.paths.args_hide', h('div', { class: 'path-field launch-args' },
    h('div', { class: 'set-group-title', text: t('settings.paths.args_title') }),
    h('div', { class: 'set-help', text: t(`settings.paths.args_help_${mode}`, { game: v.name }) }),
    option('settings.paths.args_skip', 'settings.paths.args_skip_info', 'skip_start_videos'),
    option('settings.paths.args_cheats', 'settings.paths.args_cheats_info', 'cheats', consoleLine(v, li)),
    platformArgs(v, li, mode)));
}

// État de la console dans game.xml, et bouton pour l'activer.
function consoleLine(v, li) {
  const line = h('div', { class: 'console-line' });
  if (li.controls === true) {
    line.classList.add('is-ok');
    line.append(icon('circle-check', 'ico-s'), h('span', { text: t('settings.paths.console_on') }));
  } else if (li.controls === false) {
    const btn = h('button', { class: 'btn btn-s', type: 'button' }, icon('check', 'ico-s'), h('span', { text: t('settings.paths.console_enable') }));
    btn.addEventListener('click', () => enableConsole(v, btn));
    line.append(icon('info', 'ico-s'), h('span', { text: t('settings.paths.console_off') }), btn);
  } else {
    line.append(icon('info', 'ico-s'), h('span', { text: t('settings.paths.args_game_xml_absent') }));
  }
  if (li.game_xml) line.dataset.tipText = li.game_xml;
  return line;
}

async function enableConsole(v, btn) {
  btn.setAttribute('aria-disabled', 'true');
  try {
    const state = await api.post('/api/version/console', { version: v.id });
    await refreshState();
    if (state?.game_xml === 'changed') toast('settings.paths.console_done', { game: v.name }, 'success');
    if (state?.game_xml === 'absent') toast('settings.paths.args_game_xml_absent', {}, 'info');
    if (state?.game_xml === 'error') toast('settings.paths.args_game_xml_error', {}, 'error');
  } catch (err) {
    toastError(err);
  } finally {
    btn.removeAttribute('aria-disabled');
  }
}

// Steam et Epic Games : le texte à coller dans la plateforme, et où le coller.
function platformArgs(v, li, mode) {
  if (mode === 'command') return null;
  if (mode === 'unsupported') {
    return h('div', { class: 'alert-box args-box' }, h('p', { text: t('settings.paths.args_store', { game: v.name }) }));
  }
  const text = li.args_text || '';
  const field = h('input', { class: 'field-input args-text', type: 'text', readonly: true, spellcheck: 'false', value: text,
    placeholder: t('settings.paths.args_none'), 'aria-label': t('settings.paths.args_copy_label') });
  field.addEventListener('focus', () => field.select());
  return h('div', { class: 'args-box' },
    h('div', { class: 'path-label', text: t(`settings.paths.args_${mode}_where`) }),
    h('ol', { class: 'args-steps' }, t(`settings.paths.args_${mode}_steps`, { game: v.name }).split('\n').map((x) => h('li', { text: x }))),
    h('div', { class: 'path-line' }, field, copyBtn(text)),
    h('div', { class: 'set-help', text: t('settings.paths.args_copy_help') }));
}

async function saveLaunchArgs(v, change) {
  // Valeurs actuelles, pas celles de l'affichage, pour ne pas annuler
  // une case cochée entre-temps (détection, autre case).
  const now = store.app?.versions?.find((x) => x.id === v.id)?.cfg?.launch_args;
  const cur = now || v.cfg.launch_args || {};
  const body = { version: v.id, skip_start_videos: !!cur.skip_start_videos, cheats: !!cur.cheats, ...change };
  try {
    const state = await api.post('/api/version/launch-args', body);
    await refreshState();
    if (state?.game_xml === 'absent') toast('settings.paths.args_game_xml_absent', {}, 'info');
    if (state?.game_xml === 'error') toast('settings.paths.args_game_xml_error', {}, 'error');
  } catch (err) {
    toastError(err);
  }
}

async function setPath(vid, field, value) {
  try {
    await api.post('/api/version/path', { version: vid, field, value });
    await refreshState();
    if (vid === activeVersion()) await refreshLibrary();
  } catch (err) {
    toastError(err);
  }
}

// Détection : « cette version » ne touche qu'à la version choisie ; « toutes les
// versions » touche à toutes.
function detectButtons(v) {
  const one = detectButton(v, 'settings.paths.detect_one', v.id);
  const all = detectButton(v, 'settings.paths.detect_all', null);
  return h('div', { class: 'detect-box' },
    h('div', { class: 'set-row' }, one, h('span', { class: 'set-help', text: t('settings.paths.detect_one_help') })),
    h('div', { class: 'set-row' }, all, h('span', { class: 'set-help', text: t('settings.paths.detect_all_help') })),
    h('div', { class: 'set-help', text: t('settings.paths.detect_help') }));
}

function detectButton(v, labelKey, vid) {
  if (isDemo()) {
    return h('button', { class: 'btn', type: 'button', 'aria-disabled': 'true', 'data-tip-text': t('demo.no_detect') }, icon('refresh-cw'), t(labelKey));
  }
  return h('button', { class: 'btn', type: 'button', onclick: (e) => detect(e.currentTarget, vid) }, icon('refresh-cw'), t(labelKey));
}

async function detect(btn, vid = null) {
  btn.setAttribute('aria-disabled', 'true');
  btn.querySelector('.ico')?.classList.add('spin');
  try {
    const res = await api.post('/api/detect', { version: vid });
    await refreshState();
    await refreshLibrary();
    if (res.found && res.found.length) {
      const names = res.found.map((id) => store.app.versions.find((x) => x.id === id)?.short || id).join(', ');
      toast('settings.paths.detect_found', { list: names }, 'success');
    } else {
      toast('settings.paths.detect_none', {}, 'info');
    }
  } catch (err) {
    toastError(err);
  } finally {
    btn.removeAttribute('aria-disabled');
    btn.querySelector('.ico')?.classList.remove('spin');
  }
}

// ---------------------------------------------------------------------------
// Page « Affichage » : langue et thème
// ---------------------------------------------------------------------------

function buildLook() {
  return [
    group('languages', 'settings.language.title', buildLanguage(), '', languageSelect(changeLanguage)),
    group('palette', 'settings.theme.title', buildTheme()),
  ];
}

// Langue (une bulle légère par langue, le nom seul, sans drapeau)

export function languageList(onPick) {
  const list = h('div', { class: 'lang-list', role: 'group', 'aria-label': t('settings.language.title') });
  for (const lang of store.app.languages) {
    const b = h('button', { class: 'lang-item', type: 'button', 'aria-pressed': String(lang.code === currentLang()), lang: lang.code },
      h('span', { class: 'lang-name', text: lang.name }),
      lang.personal ? h('span', { class: 'lang-personal', text: t('settings.language.personal') }) : null);
    b.addEventListener('click', () => onPick(lang.code));
    list.append(b);
  }
  return list;
}

export async function changeLanguage(code) {
  const res = await saveSettings({ language: code });
  if (!res) return;
  await loadLanguage(code);
  // La fenêtre des paramètres est refaite dans la nouvelle langue.
  if (dlg && !dlg.closed) {
    const keep = openId;
    dlg.close();
    openSettings(keep);
  }
}

// Un seul bouton-liste (icône Langue, nom de la langue en cours). Un clic
// déplie la liste verticale des langues. Ajouter une langue ne change rien ici.
// Sur la ligne du titre « Langue » ; la liste s'ouvre par-dessus le
// reste, sans rien décaler, et se ferme par Échap, un clic ailleurs ou un choix.
// L'icône Langue est placée devant le bouton-liste, plus à l'intérieur.
// Exporté : la fenêtre de bienvenue utilise le même sélecteur.
export function languageSelect(onPick) {
  const current = store.app.languages.find((l) => l.code === currentLang()) || { name: currentLang() };
  const btn = h('button', { class: 'btn lang-select-btn', type: 'button', 'aria-haspopup': 'true', 'aria-expanded': 'false', 'aria-label': t('settings.language.title') },
    h('span', { class: 'lang-select-name', text: current.name }), icon('chevron-down', 'ico-s'));
  const list = languageList((code) => {
    close();
    onPick(code);
  });
  list.classList.add('lang-list-vertical');
  list.dataset.ownScroll = '';
  list.hidden = true;
  const box = h('div', { class: 'lang-select-box' }, btn, list);
  const wrap = h('div', { class: 'lang-select' }, icon('languages', 'lang-select-ico'), box);
  const outside = (e) => {
    if (!wrap.contains(e.target)) close();
  };
  const onKey = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      close();
      btn.focus();
    }
  };
  function close() {
    list.hidden = true;
    btn.setAttribute('aria-expanded', 'false');
    document.removeEventListener('pointerdown', outside, true);
    window.removeEventListener('keydown', onKey, true);
  }
  btn.addEventListener('click', () => {
    if (!list.hidden) {
      close();
      return;
    }
    list.hidden = false;
    btn.setAttribute('aria-expanded', 'true');
    document.addEventListener('pointerdown', outside, true);
    // Sur window, avant la fenêtre des Paramètres : Échap ferme la liste seule.
    window.addEventListener('keydown', onKey, true);
    const cur = list.querySelector('[aria-pressed="true"]');
    if (cur) cur.scrollIntoView({ block: 'nearest' });
  });
  return wrap;
}

function buildLanguage() {
  const out = [
    h('div', { class: 'set-row' },
      h('button', { class: 'btn', type: 'button', onclick: () => api.post('/api/open', { what: 'lang' }).catch(toastError) }, icon('folder-open'), t('settings.language.open_folder')),
      h('span', { class: 'set-help', text: t('settings.language.personal_help') })),
  ];
  if (store.app.lang_rejected && store.app.lang_rejected.length) {
    out.push(h('div', { class: 'alert-box', text: t('settings.language.rejected', { list: store.app.lang_rejected.map((r) => r.file).join(', ') }) }));
  }
  return out;
}

function themeLabel(th) {
  const key = `themes.${th.id}`;
  const v = t(key);
  return v === key ? th.name : v;
}

function buildTheme() {
  const s = store.app.settings;
  // Thèmes sombres, puis thèmes clairs. Les thèmes bicolores
  // d'abord, puis les thèmes inspirés des thèmes populaires, sombres puis
  // clairs, dans le même ordre (chaque thème sombre au-dessus de son jumeau).
  const swatch = (th) => {
    const b = h('button', { class: 'swatch', type: 'button', 'aria-pressed': String(th.id === s.theme) },
      h('span', { class: 'swatch-dot' }),
      h('span', { text: themeLabel(th) }));
    paintSwatch(b.querySelector('.swatch-dot'), th);
    const ref = themeSurfaces(th)[1] || themeWindow(th);
    b.dataset.tipText = t('settings.theme.contrast', { ratio: formatNumber(Math.round(contrast(th.light, ref) * 10) / 10) });
    b.addEventListener('pointerenter', () => previewTheme(th));
    b.addEventListener('pointerleave', () => endPreview());
    b.addEventListener('focus', () => previewTheme(th));
    b.addEventListener('blur', () => endPreview());
    b.addEventListener('click', async () => {
      const res = await saveSettings({ theme: th.id });
      if (res) {
        applyTheme(th);
        renderHeader();
        refreshOpen();
      }
    });
    return b;
  };
  const rows = [];
  const groups = [
    ['group_duo', (th) => themeStyle(th) === 'duo'],
    ['mode_dark', (th) => themeStyle(th) !== 'duo' && themeMode(th) === 'dark'],
    ['mode_light', (th) => themeStyle(th) !== 'duo' && themeMode(th) === 'light'],
  ];
  for (const [key, keep] of groups) {
    const list = allThemes().filter(keep);
    if (!list.length) continue;
    rows.push(h('div', { class: 'set-group-title', text: t(`settings.theme.${key}`) }),
      h('div', { class: 'swatches', role: 'group', 'aria-label': t(`settings.theme.${key}`) }, ...list.map(swatch)));
  }
  const sw = h('div', { class: 'swatch-groups' }, ...rows);
  const effSystem = s.reduce_motion === null || s.reduce_motion === undefined;
  return [
    sw,
    h('div', { class: 'set-help', text: t('settings.theme.help') }),
    switchCtl('settings.theme.loop', s.theme_loop, async (on) => {
      if (await saveSettings({ theme_loop: on })) setOptions({ loop: on });
    }),
    switchCtl('settings.theme.light_effects', s.light_effects, async (on) => {
      if (await saveSettings({ light_effects: on })) setOptions({ lightEffects: on });
    }),
    h('div', {},
      switchCtl('settings.theme.reduce_motion', reduceMotionActive(), async (on) => {
        if (await saveSettings({ reduce_motion: on })) setOptions({ reduceMotion: on });
        refreshOpen();
      }),
      h('div', { class: 'set-help', style: { marginTop: '6px' }, text: effSystem ? t('settings.theme.follows_windows') : '' }),
      !effSystem ? h('button', { class: 'btn btn-ghost btn-s', type: 'button', onclick: async () => {
        if (await saveSettings({ reduce_motion: null })) setOptions({ reduceMotion: null });
        refreshOpen();
      } }, icon('rotate-ccw'), t('settings.theme.follow_windows')) : null),
    store.app.app.dev ? h('div', { class: 'set-row' },
      h('button', { class: 'btn', type: 'button', onclick: () => actions.onAtelier?.() }, icon('palette'), t('settings.theme.atelier'))) : null,
  ];
}

// ---------------------------------------------------------------------------
// Page « Application » : réglages généraux, sans lien avec une version
// ---------------------------------------------------------------------------

function buildApp() {
  return [
    group('cloud-download', 'settings.updates.title', buildUpdates(saveSettings), 'set-updates'),
    group('download', 'settings.downloads.title', buildDownloads()),
    group('app-window', 'settings.window.title', buildWindow()),
    windowModeGroup(),
    group('link', 'settings.internet.title', buildInternet()),
    group('save-check', 'settings.backup.title', buildBackup()),
    group('log-out', 'settings.stop.title', foldable('settings.stop.show', 'settings.stop.hide', buildStop()), 'is-alert'),
  ];
}

function buildDownloads() {
  const s = store.app.settings;
  const input = h('input', { class: 'field-input', type: 'text', spellcheck: 'false', value: s.downloads_dir || '' });
  input.addEventListener('change', () => saveSettings({ downloads_dir: input.value.trim() }));
  const browseBtn = h('button', { class: 'btn', type: 'button' }, icon('folder-open'), t('settings.paths.browse'));
  browseBtn.addEventListener('click', async () => {
    const p = await browse('folder', 'downloads_dir', null, input.value);
    if (p) {
      input.value = p;
      await saveSettings({ downloads_dir: p });
    }
  });
  return [
    pathCard(
      h('label', { class: 'path-label', text: t('settings.downloads.folder') }),
      h('div', { class: 'path-line' }, input, browseBtn),
      h('div', { class: 'set-help', text: t('settings.downloads.help') })),
    switchCtl('settings.downloads.scan_at_start', s.scan_downloads_at_start, (on) => saveSettings({ scan_downloads_at_start: on })),
    h('div', { class: 'set-row' },
      h('button', { class: 'btn', type: 'button', onclick: () => openDownloads() }, icon('folder-sync'), t('settings.downloads.scan_now'))),
  ];
}

// Fenêtre et zone de notification.
function buildWindow() {
  const s = store.app.settings;
  const trayOk = !!(store.app.app && store.app.app.tray);
  return [
    switchCtl('settings.window.close_to_tray', s.close_to_tray, (on) => saveSettings({ close_to_tray: on }), !trayOk),
    h('div', { class: 'set-help', text: t(trayOk ? 'settings.window.close_to_tray_help' : 'settings.window.tray_off') }),
    switchCtl('settings.window.focus_after_game', s.focus_after_game, (on) => saveSettings({ focus_after_game: on })),
    h('div', { class: 'set-help', text: t('settings.window.focus_after_game_help') }),
  ];
}

// Connexion Internet et catalogue des DLC distant.
let catalogChecking = false;

function catalogText(cat) {
  if (!cat || !cat.enabled) return t('settings.internet.catalog_off');
  const date = cat.updated ? formatDate(cat.updated) : '—';
  const key = cat.remote ? 'settings.internet.catalog_remote' : 'settings.internet.catalog_embedded';
  return t(key, { date });
}

function formatDate(day) {
  const d = new Date(`${day}T12:00:00`);
  if (Number.isNaN(d.getTime())) return day;
  try {
    return new Intl.DateTimeFormat(currentLang(), { dateStyle: 'long' }).format(d);
  } catch {
    return day;
  }
}

function buildInternet() {
  const s = store.app.settings;
  const cat = store.app.dlc_catalog || {};
  const status = h('div', { class: 'set-help catalog-status', 'aria-live': 'polite' });
  const err = cat.enabled && cat.error ? t(`settings.internet.error_${cat.error}`) : '';
  status.textContent = catalogText(cat) + (err && !err.startsWith('settings.') ? ` ${err}` : '');
  const check = h('button', { class: 'btn btn-ghost', type: 'button' }, icon('refresh-cw'), t('settings.internet.check'));
  if (!s.internet_access || !cat.source_ok || catalogChecking) check.setAttribute('aria-disabled', 'true');
  check.addEventListener('click', async () => {
    if (check.getAttribute('aria-disabled') === 'true') return;
    catalogChecking = true;
    check.setAttribute('aria-disabled', 'true');
    status.textContent = t('settings.internet.checking');
    try {
      const res = await api.post('/api/dlc/refresh', {});
      store.app.dlc_catalog = res.state;
    } catch (e) {
      toastError(e);
    } finally {
      catalogChecking = false;
      refreshOpen();
    }
  });
  return [
    switchCtl('settings.internet.allow', s.internet_access, async (on) => {
      if (await saveSettings({ internet_access: on })) {
        store.app.dlc_catalog = { ...(store.app.dlc_catalog || {}), enabled: on };
        refreshOpen();
      }
    }),
    h('div', { class: 'set-help', text: t('settings.internet.help') }),
    h('div', { class: 'set-row catalog-row' }, status, check),
  ];
}

// Sauvegarde de la configuration.
function buildBackup() {
  const demo = isDemo();
  const exp = h('button', { class: 'btn', type: 'button' }, icon('file-up'), t('settings.backup.export'));
  const imp = h('button', { class: 'btn', type: 'button' }, icon('file-down'), t('settings.backup.import'));
  if (demo) {
    for (const b of [exp, imp]) {
      b.setAttribute('aria-disabled', 'true');
      b.dataset.tipText = t('backup.demo_active');
    }
  } else {
    exp.addEventListener('click', () => exportConfig());
    imp.addEventListener('click', () => importConfig());
  }
  return [
    h('div', { class: 'set-help', text: t('settings.backup.help') }),
    h('div', { class: 'set-row' }, exp, imp),
  ];
}

// Ne plus utiliser FS Passion.
function buildStop() {
  return [
    h('div', { class: 'alert-box', text: t('settings.stop.text') }),
    // Un petit espace entre l'avertissement et le bouton.
    h('div', { class: 'set-row stop-row' },
      h('button', { class: 'btn btn-danger', type: 'button', onclick: () => openStopUsing() }, icon('log-out'), t('settings.stop.button'))),
  ];
}

// ---------------------------------------------------------------------------
// Page « Aide et à propos » : notice, journaux, informations, dons
// ---------------------------------------------------------------------------

function buildHelp({ opening = false } = {}) {
  return [
    group('book-open', 'settings.notice.title', buildNotice()),
    group('file-text', 'settings.logs.title', buildLogs()),
    group('info', 'settings.about.title', buildAbout()),
    group('hand-heart', 'settings.donate.title', buildDonate({ opening })),
  ];
}

function buildNotice() {
  return [
    h('div', { class: 'set-row' },
      h('button', { class: 'btn', type: 'button', onclick: () => actions.onNotice?.() }, icon('book-open'), t('settings.notice.open')),
      // Tour guidé de l'interface (aussi avec l'ampoule de l'en-tête).
      h('button', { class: 'btn', type: 'button', onclick: () => actions.onTour?.() }, icon('lightbulb'), t('settings.notice.tour'))),
    h('label', { class: 'check' },
      (() => {
        const c = h('input', { type: 'checkbox', checked: !!store.app.settings.show_notice_at_start });
        c.addEventListener('change', () => saveSettings({ show_notice_at_start: c.checked }));
        return c;
      })(),
      t('settings.notice.at_start')),
  ];
}

function buildAnomalies() {
  const cfg = store.app.anomalies_cfg || {};
  const hiddenCount = (cfg.hidden_types || []).length + Object.values(cfg.hidden_folders || {}).reduce((n, l) => n + l.length, 0);
  return [
    h('div', { class: 'set-row' },
      h('button', { class: 'btn', type: 'button', onclick: () => actions.onAnomalies?.() }, icon('triangle-alert'), t('settings.anomalies.show')),
      h('button', {
        class: 'btn btn-ghost', type: 'button', 'aria-disabled': hiddenCount ? null : 'true',
        onclick: async () => {
          if (!hiddenCount) return;
          try {
            await api.post('/api/anomalies', { version: activeVersion(), action: 'reset_hidden' });
            await refreshState();
            await refreshLibrary();
          } catch (err) {
            toastError(err);
          }
        },
      }, icon('eye'), t('settings.anomalies.reset', { count: hiddenCount }))),
  ];
}

function buildLogs() {
  return [
    h('div', { class: 'set-row' },
      h('button', { class: 'btn', type: 'button', onclick: () => api.post('/api/open', { what: 'logs' }).catch(toastError) }, icon('folder-open'), t('settings.logs.open_logs')),
      h('button', { class: 'btn', type: 'button', onclick: copyDiagnostic }, icon('clipboard-copy'), t('settings.logs.copy_diag'))),
  ];
}

export async function copyDiagnostic() {
  try {
    const res = await api.get('/api/diagnostic');
    if (await copyText(res.text)) toast('settings.logs.diag_copied', {}, 'success');
  } catch (err) {
    toastError(err);
  }
}

function buildAbout() {
  const app = store.app.app;
  const info = app.info || {};
  const gh = info.github_url;
  const out = [
    h('div', { class: 'about' },
      h('div', { class: 'about-logo', role: 'img', 'aria-label': 'FS Passion' }, h('span', { class: 'app-logo app-logo-art', 'aria-hidden': 'true' })),
      h('dl', {},
        h('dt', { text: t('settings.about.version') }), h('dd', { text: app.version }),
        h('dt', { text: t('settings.about.author') }), h('dd', { text: info.author || '' }),
        h('dt', { text: t('settings.about.license') }), h('dd', { text: info.license || '' }),
        h('dt', { text: 'GitHub' }), h('dd', {}, gh
          ? h('button', {
            class: 'web-link', type: 'button', text: gh.replace(/^https:\/\//, ''),
            'data-tip-text': t('footer.github_tip'),
            onclick: () => api.post('/api/link', { key: 'github' }).catch(toastError),
          })
          : t('settings.about.github_soon')))),
    h('div', { class: 'set-help', text: t('settings.about.official') }),
    h('div', { class: 'set-help', text: t('settings.about.unofficial') }),
    h('div', { class: 'set-help', text: t('settings.about.privacy') }),
  ];
  return out;
}

// Technique de la fenêtre (développement, dans la fenêtre de l'application).
// Déplacée de « Aide et à propos » vers « Application » ; les 3 boutons
// sont sur la ligne du titre, à leur taille.
function windowModeGroup() {
  const app = store.app.app;
  if (!(app.dev && app.window)) return null;
  const seg = h('div', { class: 'segmented', role: 'group', 'aria-label': t('settings.about.window_mode') });
  for (const m of ['native', 'script', 'thin']) {
    const b = h('button', { type: 'button', 'aria-pressed': String(store.app.settings.window_mode === m), text: t(`settings.about.window_${m}`) });
    b.addEventListener('click', async () => {
      if (await saveSettings({ window_mode: m })) {
        toast('settings.about.window_restart', {}, 'info');
        refreshOpen();
      }
    });
    seg.append(b);
  }
  return group('app-window', 'settings.about.window_mode',
    h('div', { class: 'set-help', text: t('settings.about.window_help', { current: t(`settings.about.window_${app.window_mode}`) }) }),
    '', seg);
}

// Dons : logos monochromes aux couleurs du thème, dessinés par masque.
function buildDonate({ opening = false } = {}) {
  const info = store.app.app.info || {};
  const don = info.donations || {};
  // [clé, fichier, nom, largeur, hauteur] : tailles équilibrées à l'œil.
  // PayPal retiré : il affichait l'identité du titulaire.
  // Stripe garde une couleur fixe (#635bff). Buy Me a Coffee est affiché
  // avec son pictogramme et son texte, en images : couleurs d'origine conservées.
  const logos = [
    { key: 'buymeacoffee', name: 'Buy Me a Coffee', images: ['Buymeacoffee-icon.svg', 'Buymeacoffee-text.svg'], height: 36 },
    { key: 'stripe', name: 'Stripe', file: 'Stripe.svg', color: '#635bff', width: 100, height: 42 },
  ];
  return [
    h('div', { class: 'set-help', text: t('settings.donate.text') }),
    h('div', { class: `brand-logos${opening ? ' play' : ''}` }, logos.map((logo, i) => {
      const url = don[logo.key];
      const b = h('button', { class: `brand-logo${logo.images ? ' brand-logo-img' : ''}`, type: 'button', 'aria-label': logo.name });
      if (logo.images) {
        for (const file of logo.images) b.append(h('img', { class: 'brand-img', src: `/assets/brand/${file}`, alt: '' }));
      } else {
        const mark = h('span', { class: 'brand-mark', 'aria-hidden': 'true' });
        mark.style.setProperty('--ico', `url("/assets/brand/${logo.file}")`);
        mark.style.background = logo.color;
        b.append(mark);
        b.style.width = `${logo.width}px`;
      }
      b.style.setProperty('--i', String(i));
      b.style.height = `${logo.height}px`;
      if (url) {
        b.dataset.tipText = logo.name;
        b.addEventListener('click', () => api.post('/api/link', { key: logo.key }).catch(toastError));
      } else {
        b.setAttribute('aria-disabled', 'true');
        b.dataset.tipText = `${logo.name}\n${t('settings.donate.no_link')}`;
      }
      return b;
    })),
  ];
}

// Fermée par « Visite guidée », avant le tour.
export function closeSettings() {
  if (dlg && !dlg.closed) dlg.close();
}

export function settingsOpen() {
  return !!(dlg && !dlg.closed);
}
