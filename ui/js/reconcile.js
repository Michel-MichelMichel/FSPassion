// Réconciliation et mods absents.
// - Messages discrets après une réconciliation faite par le cœur (démarrage,
//   fermeture du jeu) : « 4 mises à jour récupérées »…
// - Au démarrage, fenêtre « Ces mods sont absents de votre dossier de mods
//   alors qu'ils sont présents dans des parties » (une fois par session et par
//   version), avec, pour chacun : Restaurer (s'il en reste une copie dans une
//   partie), Remplacer par…, Retirer des listes.

import { partyLabel, replaceMissing } from './actions.js';
import { api, on } from './api.js';
import { isDialogOpen, openDialog } from './dialog.js';
import { clear, h, icon } from './dom.js';
import { t } from './i18n.js';
import {
  activeVersion, isRunning, partiesSupported, refreshLibrary, refreshParties, setParties, store, versionInfo,
} from './state.js';
import { toast, toastError } from './toast.js';

const asked = new Set();
let dlg = null;

// Message discret, seulement s'il s'est passé quelque chose (étape 7).
export function reportReconcile(rep) {
  if (!rep) return;
  const updated = rep.updated || [];
  if (updated.length) toast('reconcile.updated', { count: updated.length, list: updated.slice(0, 5).join(', ') }, 'info');
  for (const [pid, list] of Object.entries(rep.added || {})) {
    if (list.length) toast('reconcile.added', { count: list.length, name: partyLabel(pid) || pid }, 'info');
  }
  if ((rep.unclassified || []).length) toast('reconcile.unclassified', { count: rep.unclassified.length }, 'info');
  if ((rep.reshaped || []).length) toast('reconcile.reshaped', { count: rep.reshaped.length, list: rep.reshaped.join(', ') }, 'info');
  // Une version plus ancienne déposée par le jeu a sa propre fenêtre.
  const aside = (rep.set_aside || []).length + (rep.old_versions || []).length - (rep.older || []).length;
  if (aside > 0) toast('apply.set_aside', { count: aside }, 'warn');
  if ((rep.errors || []).length) toast('reconcile.errors', { count: rep.errors.length, list: rep.errors.join(', ') }, 'warn');
}

export function initReconcile() {
  on('reconcile', (ev) => {
    if (ev.version !== activeVersion()) return;
    reportReconcile(ev.report);
    refreshParties().then(() => maybeShowOlder()).catch(() => {});
    refreshLibrary().catch(() => {});
  });
}

function missingList() {
  const lib = store.library;
  if (!lib || lib.status !== 'ready' || !partiesSupported()) return [];
  return (lib.anomalies || []).filter((a) => a.type === 'A7' || a.type === 'A8');
}

function whereOf(a) {
  const d = a.detail || {};
  const names = (d.parties || []).slice();
  if (d.common) names.push(t('list3.title'));
  return names.join(', ');
}

async function resolve(action, ids) {
  try {
    const res = await api.post('/api/missing/resolve', { version: activeVersion(), action, ids });
    if (res.state) setParties(res.state);
    await refreshLibrary();
    if (action === 'remove') toast('missing.removed', { count: ids.length }, 'success');
    if (action === 'restore') toast('missing.restored', { count: (res.done || []).length }, 'success');
    return res;
  } catch (err) {
    toastError(err);
    return null;
  }
}

function build(body) {
  clear(body);
  const items = missingList();
  if (!items.length) {
    if (dlg) dlg.close();
    return;
  }
  const running = isRunning();
  body.append(h('p', { class: 'dlg-text', text: t('missing.intro', { count: items.length }) }));
  const list = h('div', { class: 'miss-list' });
  for (const a of items) {
    const copy = a.type === 'A8';
    const actions = h('div', { class: 'miss-actions' });
    if (copy) {
      const restore = h('button', { class: 'btn btn-s', type: 'button' }, icon('rotate-ccw', 'ico-s'), h('span', { text: t('missing.restore') }));
      restore.dataset.tipText = t('missing.restore_tip');
      if (running) restore.setAttribute('aria-disabled', 'true');
      restore.addEventListener('click', async () => {
        if (restore.getAttribute('aria-disabled') === 'true') return;
        await resolve('restore', [a.name]);
        build(body);
      });
      actions.append(restore);
    } else {
      actions.append(h('button', { class: 'btn btn-s', type: 'button', onclick: () => replaceMissing(a.name) },
        icon('arrow-right-left', 'ico-s'), h('span', { text: t('lists.replace') })));
    }
    actions.append(h('button', {
      class: 'btn btn-s', type: 'button',
      onclick: async () => {
        await resolve('remove', [a.name]);
        build(body);
      },
    }, icon('minus', 'ico-s'), h('span', { text: t('missing.remove') })));
    const where = whereOf(a);
    const copyIn = copy ? (a.detail.folders || []).join(', ') : '';
    list.append(h('div', { class: 'miss-item' },
      icon(copy ? 'layers' : 'circle-x', copy ? 'ico-s is-copy' : 'ico-s'),
      h('div', { class: 'miss-text' },
        h('div', { class: 'miss-name', text: a.name }),
        where ? h('div', { class: 'miss-sub', text: t('missing.in', { list: where }) }) : null,
        h('div', { class: 'miss-sub', text: copy ? t('missing.copy', { list: copyIn }) : t('missing.no_copy') })),
      actions));
  }
  body.append(list);
  body.append(h('p', { class: 'set-help', text: t('missing.notice') }));
}

export function maybeShowMissing() {
  if (dlg || isDialogOpen()) return;
  const items = missingList();
  const v = versionInfo();
  if (!items.length || !v) return;
  const key = `${v.id}`;
  if (asked.has(key)) return;
  asked.add(key);
  const body = h('div', { class: 'dlg-body miss-body' });
  const removeAll = h('button', { class: 'btn', type: 'button' }, icon('minus'), h('span', { text: t('missing.remove_all') }));
  removeAll.addEventListener('click', async () => {
    const ids = missingList().map((a) => a.name);
    if (ids.length) await resolve('remove', ids);
    build(body);
  });
  const later = h('button', { class: 'btn btn-primary', type: 'button', text: t('missing.later') });
  const foot = h('div', { class: 'dlg-foot' }, removeAll, h('div', { class: 'spacer' }), later);
  dlg = openDialog(h('div', { style: { display: 'contents' } }, body, foot), {
    title: t('missing.title'), cls: 'dlg-missing', onClose: () => { dlg = null; },
  });
  later.addEventListener('click', () => dlg && dlg.close());
  build(body);
}

export function refreshMissingDialog() {
  if (dlg && dlg.el) {
    const body = dlg.el.querySelector('.miss-body');
    if (body) build(body);
  }
}

// ---------------------------------------------------------------------------
// Version plus ancienne déposée par le jeu. Le ModHub propose
// souvent sa version d'origine d'un mod modifié par l'utilisateur : le numéro de
// version du jeu est alors plus ancien. FS Passion l'a mise de côté
// (Recovered) et demande quoi faire. « Plus tard » : la question revient au
// prochain démarrage.
// ---------------------------------------------------------------------------

const olderAsked = new Set();
let olderDlg = null;

function olderList() {
  return (store.parties && store.parties.older) || [];
}

async function resolveOlder(item, action) {
  try {
    const res = await api.post('/api/older/resolve', { version: activeVersion(), path: item.path, action });
    if (res.state) setParties(res.state);
    if (action === 'use') await refreshLibrary();
    return true;
  } catch (err) {
    toastError(err);
    return false;
  }
}

function buildOlder(body) {
  clear(body);
  const items = olderList();
  if (!items.length) {
    if (olderDlg) olderDlg.close();
    return;
  }
  const running = isRunning();
  body.append(h('p', { class: 'dlg-text', text: t('older.intro', { count: items.length }) }));
  const list = h('div', { class: 'miss-list' });
  for (const it of items) {
    const keep = h('button', { class: 'btn btn-s', type: 'button' }, icon('shield', 'ico-s'),
      h('span', { text: t('older.keep', { version: it.old || '?' }) }));
    const use = h('button', { class: 'btn btn-s', type: 'button' }, icon('download', 'ico-s'),
      h('span', { text: t('older.use', { version: it.new || '?' }) }));
    use.dataset.tipText = t('older.use_tip');
    if (running) use.setAttribute('aria-disabled', 'true');
    keep.addEventListener('click', async () => {
      if (await resolveOlder(it, 'keep')) buildOlder(body);
    });
    use.addEventListener('click', async () => {
      if (use.getAttribute('aria-disabled') === 'true') return;
      if (await resolveOlder(it, 'use')) buildOlder(body);
    });
    list.append(h('div', { class: 'miss-item' },
      icon('triangle-alert', 'ico-s'),
      h('div', { class: 'miss-text' },
        h('div', { class: 'miss-name', text: it.name }),
        h('div', { class: 'miss-sub', text: t('older.versions', { mine: it.old || '?', game: it.new || '?' }) })),
      h('div', { class: 'miss-actions' }, keep, use)));
  }
  body.append(list);
  body.append(h('p', { class: 'set-help', text: t('older.help') }));
}

export function maybeShowOlder() {
  if (olderDlg || isDialogOpen()) return;
  const items = olderList().filter((x) => !olderAsked.has(x.path));
  if (!items.length) return;
  for (const x of items) olderAsked.add(x.path);
  const body = h('div', { class: 'dlg-body older-body' });
  const later = h('button', { class: 'btn btn-primary', type: 'button', text: t('older.later') });
  const foot = h('div', { class: 'dlg-foot' }, h('div', { class: 'spacer' }), later);
  olderDlg = openDialog(h('div', { style: { display: 'contents' } }, body, foot), {
    title: t('older.title'), cls: 'dlg-missing', onClose: () => { olderDlg = null; },
  });
  later.addEventListener('click', () => olderDlg && olderDlg.close());
  buildOlder(body);
}
