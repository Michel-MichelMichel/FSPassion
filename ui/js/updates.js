// Mises à jour de FS Passion : état reçu du cœur (Releases GitHub),
// repères discrets et encart des Paramètres → Application.
//
// Repères (aucun message qui surgit) :
// - une pastille sur la roue des Paramètres ;
// - « Nouvelle version x.y.z » à côté du numéro de version, dans le pied de
//   page (un clic ouvre l'encart) ;
// - une entrée dans l'historique de la cloche, une fois par version et par
//   session.

import { api, on } from './api.js';
import { h, icon } from './dom.js';
import { currentLang, t } from './i18n.js';
import { notify, store } from './state.js';
import { noteOnly, toastError } from './toast.js';

const noted = new Set();
let installing = false;

export function updateState() {
  return (store.app && store.app.update) || null;
}

export function updateAvailable() {
  const u = updateState();
  return !!(u && u.enabled && u.available && u.latest);
}

function noteIfNew() {
  const u = updateState();
  if (!updateAvailable() || noted.has(u.latest.version)) return;
  noted.add(u.latest.version);
  noteOnly(t('settings.updates.note', { version: u.latest.version }), 'info');
}

// Pastille de la roue des Paramètres : posée sans redessiner l'en-tête.
export function markSettingsButton(btn = document.querySelector('.settings-btn')) {
  if (!btn) return;
  const on = updateAvailable();
  btn.classList.toggle('has-update', on);
  const base = t('header.settings');
  const tip = on ? `${base} · ${t('settings.updates.note', { version: updateState().latest.version })}` : base;
  btn.setAttribute('aria-label', tip);
  btn.dataset.tipText = tip;
}

export function initUpdates({ onChange }) {
  on('update', (ev) => {
    if (!store.app || !ev.state) return;
    store.app.update = ev.state;
    noteIfNew();
    markSettingsButton();
    notify('update', ev.state);
    onChange?.();
  });
}

// Appelé après chaque /api/state.
export function syncUpdates() {
  noteIfNew();
  markSettingsButton();
}

// Pied de page : « Nouvelle version 1.0.0 », à côté du numéro de version.
export function footerUpdatePill(onOpen) {
  if (!updateAvailable()) return null;
  const v = updateState().latest.version;
  return h('button', {
    class: 'update-pill', type: 'button',
    'data-tip-text': t('settings.updates.pill_tip'),
    onclick: () => onOpen(),
  }, icon('cloud-download'), h('span', { text: t('settings.updates.pill', { version: v }) }));
}

// -- Encart des Paramètres --------------------------------------------------

function formatWhen(iso, withTime) {
  if (!iso) return '';
  const d = new Date(withTime ? iso : `${iso}T12:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  try {
    return new Intl.DateTimeFormat(currentLang(), withTime
      ? { dateStyle: 'long', timeStyle: 'short' } : { dateStyle: 'long' }).format(d);
  } catch {
    return iso;
  }
}

function errorText(key) {
  if (!key) return '';
  const txt = t(`settings.updates.error_${key}`);
  return txt.startsWith('settings.') ? t('settings.updates.error_unreachable') : txt;
}

function statusText(u) {
  if (!u.enabled) return t('settings.updates.off');
  if (u.checking) return t('settings.updates.checking');
  const last = u.last_check ? ` ${t('settings.updates.last_check', { date: formatWhen(u.last_check, true) })}` : '';
  if (u.error) return `${errorText(u.error)}${last}`;
  if (u.available) return last.trim();
  if (u.up_to_date) return `${t('settings.updates.up_to_date', { version: u.current })}${last}`;
  return t('settings.updates.never', { version: u.current });
}

async function install(btn) {
  if (installing || btn.getAttribute('aria-disabled') === 'true') return;
  installing = true;
  btn.setAttribute('aria-disabled', 'true');
  try {
    const res = await api.post('/api/update/install', {});
    if (res.state) store.app.update = res.state;
    if (res.action === 'quit') {
      document.documentElement.classList.add('is-updating');
      notify('update', store.app.update);
      store.ui.updateClosing = true;
    } else if (res.action === 'revealed') {
      noteOnly(t('settings.updates.portable_ready', { file: res.file }), 'success');
    }
  } catch (e) {
    toastError(e);
  } finally {
    installing = false;
    notify('update', store.app.update);
  }
}

export function buildUpdates(saveSettings) {
  const u = updateState() || { enabled: false, source_ok: false, current: store.app.app.version, kind: 'source', download: {} };
  const rows = [];
  rows.push(h('label', { class: 'switch' },
    (() => {
      const input = h('input', { type: 'checkbox', checked: !!u.enabled });
      input.addEventListener('change', async () => {
        if (await saveSettings({ update_check: input.checked })) {
          store.app.update = { ...u, enabled: input.checked };
          notify('update', store.app.update);
        }
      });
      return input;
    })(),
    h('span', { class: 'switch-track' }), h('span', { text: t('settings.updates.allow') })));
  rows.push(h('div', { class: 'set-help', text: t('settings.updates.help') }));

  const dl = u.download || {};
  if (updateAvailable()) {
    const card = h('div', { class: 'update-card' },
      h('div', { class: 'update-card-head' },
        icon('cloud-download', 'update-card-ico'),
        h('div', {},
          h('div', { class: 'update-card-title', text: t('settings.updates.available', { version: u.latest.version }) }),
          h('div', { class: 'set-help', text: [
            u.latest.published ? t('settings.updates.published', { date: formatWhen(u.latest.published, false) }) : '',
            t('settings.updates.current', { version: u.current }),
          ].filter(Boolean).join(' · ') }))));
    const btns = h('div', { class: 'set-row update-actions' });
    if (u.kind === 'installed' || u.kind === 'portable') {
      const busy = dl.state === 'downloading' || store.ui.updateClosing;
      const label = store.ui.updateClosing ? t('settings.updates.closing')
        : dl.state === 'downloading' ? t('settings.updates.downloading', { percent: Math.round((dl.progress || 0) * 100) })
          : t(u.kind === 'installed' ? 'settings.updates.install' : 'settings.updates.download_portable');
      const main = h('button', { class: 'btn btn-primary', type: 'button' },
        icon(busy ? 'loader-circle' : 'download', busy ? 'spin' : ''), h('span', { text: label }));
      if (busy || !u.can_install) main.setAttribute('aria-disabled', 'true');
      main.addEventListener('click', () => install(main));
      btns.append(main);
    }
    if (u.latest.has_page) {
      btns.append(h('button', {
        class: `btn ${u.kind === 'source' ? 'btn-primary' : 'btn-ghost'}`, type: 'button',
        onclick: () => api.post('/api/update/page', {}).catch(toastError),
      }, icon('external-link'), h('span', { text: t('settings.updates.see_release') })));
    }
    card.append(btns);
    if (dl.state === 'downloading') {
      const bar = h('div', { class: 'update-progress', role: 'progressbar', 'aria-valuemin': '0', 'aria-valuemax': '100', 'aria-valuenow': String(Math.round((dl.progress || 0) * 100)) },
        h('span', { class: 'update-progress-fill' }));
      bar.firstChild.style.width = `${Math.round((dl.progress || 0) * 100)}%`;
      card.append(bar);
    }
    const help = store.ui.updateClosing ? t('settings.updates.closing_help')
      : !u.can_install && u.kind !== 'source' ? t('settings.updates.error_missing_file')
        : dl.state === 'error' ? errorText(dl.error)
          : t(`settings.updates.how_${u.kind}`);
    card.append(h('div', { class: `set-help${dl.state === 'error' ? ' is-error' : ''}`, text: help }));
    rows.push(card);
  }

  const status = h('div', { class: 'set-help update-status', 'aria-live': 'polite', text: statusText(u) });
  const check = h('button', { class: 'btn btn-ghost', type: 'button' },
    icon(u.checking ? 'loader-circle' : 'refresh-cw', u.checking ? 'spin' : ''), t('settings.updates.check'));
  if (!u.enabled || !u.source_ok || u.checking) check.setAttribute('aria-disabled', 'true');
  check.addEventListener('click', async () => {
    if (check.getAttribute('aria-disabled') === 'true') return;
    check.setAttribute('aria-disabled', 'true');
    try {
      store.app.update = await api.post('/api/update/check', {});
      noteIfNew();
      markSettingsButton();
    } catch (e) {
      toastError(e);
    } finally {
      notify('update', store.app.update);
    }
  });
  rows.push(h('div', { class: 'set-row catalog-row' }, status, check));
  return rows;
}
