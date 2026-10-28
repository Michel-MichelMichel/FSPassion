// Fenêtre « Anomalies détectées ». Ce ne sont pas des événements
// graves : le ton reste informatif.

import { replaceMissing } from './actions.js';
import { api } from './api.js';
import { confirmDialog, openDialog } from './dialog.js';
import { clear, gameLogo, h, icon } from './dom.js';
import { t } from './i18n.js';
import { openRename } from './modops.js';
import { activeVersion, isRunning, refreshLibrary, refreshState, setParties, store, versionInfo } from './state.js';
import { toast, toastError } from './toast.js';

let dlg = null;

const ORDER = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9'];

function detailText(a) {
  const d = a.detail || {};
  switch (a.type) {
    case 'A2': return d.nested ? t('anomalies.A2.nested', { path: d.nested }) : '';
    case 'A3': return d.reason === 'xml' ? t('anomalies.A3.xml') : t('anomalies.A3.zip');
    case 'A5': return t('anomalies.A5.suggestion', { name: d.suggestion });
    case 'A6': {
      const v = store.app.versions.find((x) => x.id === d.detected);
      return t('anomalies.A6.detected', { game: v ? v.name : d.detected });
    }
    case 'A7': {
      const where = (d.parties || []).slice();
      if (d.common) where.push(t('list3.title'));
      return where.length ? t('anomalies.A7.in', { list: where.join(', ') }) : '';
    }
    case 'A8': return t('anomalies.A8.copy', { list: (d.folders || []).join(', ') });
    case 'A9': return d.zip_and_dir ? t('anomalies.A9.zip_and_dir', { name: a.name }) : t('anomalies.A9.files', { list: (d.files || []).join(', ') });
    default: return '';
  }
}

async function act(action, value) {
  try {
    await api.post('/api/anomalies', { version: activeVersion(), action, value });
    await refreshState();
    await refreshLibrary();
  } catch (err) {
    toastError(err);
  }
}

// A7 / A8 : retirer des listes, restaurer la copie, ou supprimer.
async function missing(action, id) {
  if (action !== 'remove' && isRunning()) {
    toast('apply.running', { game: (versionInfo() || {}).name || '' }, 'warn');
    return;
  }
  if (action === 'delete') {
    const ok = await confirmDialog({
      title: t('anomalies.A8.delete_title'), text: t('anomalies.A8.delete_text', { name: id }),
      ok: t('delete.ok'), danger: true,
    });
    if (!ok) return;
  }
  try {
    const res = await api.post('/api/missing/resolve', { version: activeVersion(), action, ids: [id] });
    if (res.state) setParties(res.state);
    await refreshLibrary();
    toast(`missing.${action === 'remove' ? 'removed' : action === 'restore' ? 'restored' : 'deleted'}`, { count: 1 }, 'success');
  } catch (err) {
    toastError(err);
  }
}

// Nom de l'élément : un lien qui ouvre l'Explorateur dans le dossier de mods,
// l'élément sélectionné.
async function reveal(a) {
  try {
    await api.post('/api/reveal', { version: activeVersion(), storage: a.storage, name: a.name });
  } catch (err) {
    toastError(err);
  }
}

// Version du jeu concernée et dossier(s) de mods.
function gameLine() {
  const v = versionInfo();
  const lib = store.library;
  if (!v) return null;
  const storages = lib ? lib.storages || [] : [];
  return h('div', { class: 'anom-game' },
    gameLogo(v.logo),
    h('div', { class: 'anom-game-text' },
      h('div', { class: 'anom-game-name', text: t('anomalies.game', { game: v.name }) }),
      storages.length ? h('div', { class: 'anom-game-path', text: t('anomalies.folder', { path: storages.join('  ·  ') }) }) : null));
}

function build(body) {
  clear(body);
  const lib = store.library;
  const list = lib ? lib.anomalies : [];
  body.append(gameLine() || '');
  if (!list.length) {
    body.append(h('div', { class: 'anom-empty', text: t('anomalies.none') }));
  } else {
    body.append(h('p', { class: 'anom-intro', text: t('anomalies.intro') }));
  }
  const groups = new Map();
  for (const a of list) {
    if (!groups.has(a.type)) groups.set(a.type, []);
    groups.get(a.type).push(a);
  }
  for (const type of ORDER) {
    const items = groups.get(type);
    if (!items) continue;
    const ul = h('div', { class: 'anom-items' });
    for (const a of items) {
      const actions = h('div', { class: 'ai-actions' });
      if (a.type === 'A4') {
        const c = h('input', { type: 'checkbox' });
        c.addEventListener('change', () => c.checked && act('hide_folder', a.name));
        actions.append(h('label', { class: 'check' }, c, t('anomalies.hide_folder')));
      }
      if (a.type === 'A7') {
        // « Remplacer par… » : un mod renommé par son auteur reprend sa place.
        actions.append(h('button', { class: 'btn btn-s', type: 'button', onclick: () => replaceMissing(a.name) },
          icon('arrow-right-left', 'ico-s'), t('lists.replace')));
        actions.append(h('button', { class: 'btn btn-s', type: 'button', onclick: () => missing('remove', a.name) },
          icon('minus', 'ico-s'), t('missing.remove')));
      }
      if (a.type === 'A8') {
        // Mod supprimé à la main, encore présent par ses liens (étape 5).
        actions.append(h('button', { class: 'btn btn-s', type: 'button', onclick: () => missing('restore', a.name) },
          icon('rotate-ccw', 'ico-s'), t('missing.restore')));
        actions.append(h('button', { class: 'btn btn-s btn-danger', type: 'button', onclick: () => missing('delete', a.name) },
          icon('trash-2', 'ico-s'), t('actions.delete')));
      }
      if (a.type === 'A5' && a.detail && a.detail.kind) {
        // Renommer…, avec le nom corrigé proposé.
        const id = a.detail.kind === 'zip' && a.name.toLowerCase().endsWith('.zip') ? a.name.slice(0, -4) : a.name;
        actions.append(h('button', { class: 'btn btn-s', type: 'button', onclick: () => openRename(id) },
          icon('pencil', 'ico-s'), t('anomalies.rename')));
      }
      const detail = detailText(a);
      ul.append(h('div', { class: 'anom-item' },
        h('div', {},
          h('button', {
            class: 'ai-name ai-link', type: 'button', text: a.name,
            'data-tip-text': t(a.type === 'A7' ? 'anomalies.open_folder' : 'anomalies.show_in_folder'),
            onclick: () => reveal(a),
          }),
          detail ? h('div', { class: 'ai-detail', text: detail }) : null),
        a.new ? h('span', { class: 'ai-new', text: t('anomalies.new') }) : null,
        actions));
    }
    const hideType = h('input', { type: 'checkbox' });
    hideType.addEventListener('change', () => hideType.checked && act('hide_type', type));
    body.append(h('section', { class: 'anom-group' },
      h('div', { class: 'anom-group-head' },
        h('span', { class: 'anom-type', text: type }),
        h('div', {},
          h('div', { class: 'anom-title', text: t(`anomalies.${type}.title`, { count: items.length }) }),
          h('div', { class: 'anom-explain', text: t(`anomalies.${type}.explain`) }))),
      ul,
      h('div', { class: 'anom-group-foot' }, h('label', { class: 'check' }, hideType, t('anomalies.hide_type')))));
  }
  const others = lib ? lib.others : [];
  if (others.length) {
    body.append(h('details', { class: 'anom-others' },
      h('summary', { text: t('anomalies.others', { count: others.length }) }),
      h('ul', {}, others.map((o) => h('li', { text: o.name })))));
  }
}

export function openAnomalies() {
  if (dlg && !dlg.closed) return;
  const body = h('div', { class: 'anom-body' });
  build(body);
  const foot = h('div', { class: 'dlg-foot' },
    h('div', { class: 'spacer' }),
    h('button', { class: 'btn btn-primary', type: 'button', onclick: () => dlg.close() }, t('common.close')));
  dlg = openDialog(h('div', { style: { display: 'contents' } }, body, foot), {
    title: t('anomalies.title'),
    cls: 'dlg-anomalies',
    onClose: () => {
      dlg = null;
      // Les anomalies affichées sont désormais connues : la fenêtre ne s'ouvrira
      // plus d'elle-même pour elles.
      act('mark_seen');
    },
  });
  dlg.rebuild = () => build(body);
}

export function refreshAnomaliesDialog() {
  if (dlg && !dlg.closed && dlg.rebuild) dlg.rebuild();
}

export function anomaliesOpen() {
  return !!(dlg && !dlg.closed);
}
