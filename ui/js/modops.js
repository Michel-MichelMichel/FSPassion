// Renommer un mod et Supprimer définitivement.
// Ce sont les deux seules actions de FS Passion qui touchent aux fichiers des
// mods eux-mêmes, et seulement après confirmation.

import { iconUrl, api } from './api.js';
import { confirmDialog, openDialog } from './dialog.js';
import { h, icon } from './dom.js';
import { sizeText } from './hovercard.js';
import { modTitle, t } from './i18n.js';
import { clearSelection } from './selection.js';
import {
  activeVersion, isRunning, modIndex, refreshLibrary, refreshParties, refreshState, setParties, versionInfo,
} from './state.js';
import { toast, toastError } from './toast.js';

const NAME_RE = /^[A-Za-z0-9_]+$/;

function gameName() {
  const v = versionInfo();
  return v ? v.name : '';
}

function art(mod) {
  const el = h('div', { class: 'pp-art' });
  if (mod && mod.icon) el.append(h('img', { src: iconUrl(activeVersion(), mod.icon, true), alt: '', draggable: 'false' }));
  else el.append(icon(mod && mod.is_map ? 'map' : 'package'));
  return el;
}

function whereText(parties, common) {
  const names = (parties || []).slice().sort((a, b) => a.localeCompare(b));
  if (common) names.push(t('list3.title'));
  return names.length ? names.join(', ') : t('rename.no_list');
}

// ---------------------------------------------------------------------------
// Renommer : un seul avertissement, puis renommage répercuté partout
// ---------------------------------------------------------------------------

export async function openRename(modId) {
  if (isRunning()) {
    toast('rename.running', { game: gameName() }, 'warn');
    return;
  }
  let info;
  try {
    info = await api.post('/api/mods/rename-preview', { version: activeVersion(), id: modId });
  } catch (err) {
    toastError(err);
    return;
  }
  const mod = modIndex().get(info.id.toLowerCase());
  const taken = new Set(info.taken);
  const invalidNow = !NAME_RE.test(info.id);
  const input = h('input', {
    class: 'field-input rename-input', type: 'text', spellcheck: 'false', autocomplete: 'off', autofocus: true,
    maxlength: String(info.max + 20), 'aria-label': t('rename.label'),
  });
  // Nom actuel conservé, sauf s'il est refusé par le jeu : la suggestion.
  input.value = invalidNow ? info.suggestion : info.rest;
  const err = h('div', { class: 'name-error', 'aria-live': 'polite' });
  const final = h('div', { class: 'rename-final' });
  const ext = info.kind === 'zip' ? '.zip' : '';

  const check = () => {
    const full = info.prefix + input.value.trim();
    let key = '';
    if (!input.value.trim()) key = 'rename.empty';
    else if (full.length > info.max) key = 'rename.too_long';
    else if (!NAME_RE.test(full)) key = 'rename.invalid';
    else if (full === info.id) key = 'rename.same';
    else if (full.toLowerCase() !== info.id.toLowerCase() && taken.has(full.toLowerCase())) key = 'rename.taken';
    err.textContent = key && key !== 'rename.same' ? t(key, { name: full, max: info.max }) : '';
    final.textContent = t('rename.final', { file: `${full}${ext}` });
    ok.toggleAttribute('disabled', !!key);
    return !key;
  };

  const warn = h('div', { class: 'alert-box rename-warn' },
    h('p', {}, icon('triangle-alert', 'ico-s'), h('span', { text: t('rename.warning_modhub') })),
    h('p', { text: t(info.is_map ? 'rename.warning_save_map' : 'rename.warning_save') }),
    info.dependents.length
      ? h('p', { text: t('rename.warning_deps', { count: info.dependents.length, list: info.dependents.slice(0, 6).join(', ') }) })
      : null);
  const ok = h('button', { class: 'btn btn-primary', type: 'submit' }, icon('pencil'), h('span', { text: t('rename.ok') }));
  const cancel = h('button', { class: 'btn btn-ghost', type: 'button', text: t('common.cancel') });
  const form = h('form', { class: 'dlg-body rename-dlg' },
    h('div', { class: 'pp-head' }, art(mod),
      h('div', { class: 'pp-title' },
        h('div', { class: 'pp-map', text: mod ? modTitle(mod) : info.id }),
        h('div', { class: 'pp-id', text: info.file }))),
    h('label', { class: 'name-field' },
      h('span', { class: 'path-label', text: t('rename.label') }),
      h('div', { class: 'rename-line' },
        info.prefix ? h('span', { class: 'rename-prefix', text: info.prefix, 'data-tip-text': t('rename.prefix_tip') }) : null,
        input,
        ext ? h('span', { class: 'rename-ext', text: ext }) : null),
      err),
    final,
    h('p', { class: 'set-help', text: t('rename.rule') }),
    h('p', { class: 'rename-where', text: t('rename.where', { list: whereText(info.parties, info.common) }) }),
    warn,
    h('div', { class: 'dlg-actions' }, cancel, ok));
  const dlg = openDialog(form, { title: t('rename.title'), cls: 'dlg-rename' });
  cancel.addEventListener('click', () => dlg.close());
  input.addEventListener('input', check);
  check();
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!check() || ok.disabled) return;
    ok.disabled = true;
    const newId = info.prefix + input.value.trim();
    try {
      const res = await api.post('/api/mods/rename', { version: activeVersion(), id: info.id, new: newId });
      dlg.close();
      clearSelection();
      if (res.state) setParties(res.state);
      await refreshLibrary();
      // Pas de message « renommé » (la liste le montre déjà).
      // Deuxième temps : les listes ne suivent que sur accord.
      await askUpdateLists(res);
    } catch (error) {
      ok.disabled = false;
      if (error && error.key && error.key.startsWith('rename.') && error.key !== 'rename.running') {
        err.textContent = t(error.key, { ...(error.params || {}), max: info.max });
      } else {
        dlg.close();
        toastError(error);
      }
    }
  });
  // Curseur en fin de nom : on complète le plus souvent (« …_perso »).
  requestAnimationFrame(() => {
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  });
}

// Après le renommage du fichier : les listes qui contenaient l'ancien nom
// suivent-elles le nouveau ? Oui (toutes les listes), ou rien (elles gardent
// l'ancien nom, et FS Passion les signalera comme mods absents).
async function askUpdateLists(res) {
  const where = res.where || { parties: [], common: false };
  if (!where.parties.length && !where.common) return;
  const yes = await confirmDialog({
    title: t('rename.lists_title'),
    text: t('rename.lists_ask', { old: res.old, name: res.new, list: whereText(where.parties, where.common) }),
    ok: t('rename.lists_yes'),
    cancel: t('rename.lists_no'),
  });
  if (!yes) return;
  try {
    const done = await api.post('/api/mods/rename-lists', { version: activeVersion(), old: res.old, new: res.new });
    if (done.state) setParties(done.state);
    await refreshLibrary();
  } catch (err) {
    toastError(err);
  }
}

// ---------------------------------------------------------------------------
// Supprimer définitivement : liste des mods et des parties, double
// validation, Corbeille de Windows quand c'est possible
// ---------------------------------------------------------------------------

export async function openDelete(ids) {
  const present = ids.filter((id) => modIndex().has(String(id).toLowerCase()));
  if (!present.length) return;
  if (isRunning()) {
    toast('delete.running', { game: gameName() }, 'warn');
    return;
  }
  let info;
  try {
    info = await api.post('/api/mods/delete-preview', { version: activeVersion(), ids: present });
  } catch (err) {
    toastError(err);
    return;
  }
  if (!info.mods.length) return;
  const list = h('div', { class: 'del-list' });
  for (const m of info.mods) {
    const mod = modIndex().get(m.id.toLowerCase());
    list.append(h('div', { class: 'del-item' },
      h('span', { class: 'rl-art' }, mod && mod.icon
        ? h('img', { src: iconUrl(activeVersion(), mod.icon, true), alt: '', draggable: 'false' })
        : icon(m.kind === 'dir' ? 'folder' : 'package', 'ico-s')),
      h('span', { class: 'rl-text' },
        h('span', { text: mod ? modTitle(mod) : m.id }),
        h('span', { class: 'rl-sub', text: `${m.file}${m.size ? ` · ${sizeText(m.size)}` : ''}` })),
      h('span', { class: 'del-where', text: whereText(m.parties, m.common) })));
  }
  const understand = h('input', { type: 'checkbox' });
  const ok = h('button', { class: 'btn btn-danger', type: 'button', 'aria-disabled': 'true' },
    icon('trash-2'), h('span', { text: t('delete.ok') }));
  understand.addEventListener('change', () => {
    if (understand.checked) ok.removeAttribute('aria-disabled');
    else ok.setAttribute('aria-disabled', 'true');
  });
  const body = h('div', { class: 'dlg-body delete-dlg' },
    h('p', { class: 'dlg-text', text: t('delete.intro', { count: info.mods.length }) }),
    list,
    h('div', { class: 'alert-box is-critical' },
      h('p', {}, icon('triangle-alert', 'ico-s'), h('span', { text: t('delete.irreversible') })),
      h('p', { text: t(info.recycle ? 'delete.recycle' : 'delete.no_recycle') })),
    h('label', { class: 'check delete-check' }, understand, t('delete.understand', { count: info.mods.length })),
    h('div', { class: 'dlg-actions' },
      h('button', { class: 'btn btn-ghost', type: 'button', text: t('common.cancel'), onclick: () => dlg.close() }),
      ok));
  const dlg = openDialog(body, { title: t('delete.title', { count: info.mods.length }), cls: 'dlg-delete' });
  ok.addEventListener('click', async () => {
    if (ok.getAttribute('aria-disabled') === 'true') return;
    ok.setAttribute('aria-disabled', 'true');
    try {
      const res = await api.post('/api/mods/delete', {
        version: activeVersion(), ids: info.mods.map((m) => m.id), confirm: true,
      });
      dlg.close();
      clearSelection();
      if (res.state) setParties(res.state);
      await refreshLibrary();
      const n = res.recycled.length + res.deleted.length;
      if (res.recycled.length) toast('delete.done_recycled', { count: res.recycled.length }, 'success');
      if (res.deleted.length) toast('delete.done_deleted', { count: res.deleted.length }, 'success');
      if (res.failed.length) toast('delete.failed', { count: res.failed.length, list: res.failed.join(', ') }, 'error');
      if (!n && !res.failed.length) toast('delete.nothing', {}, 'info');
    } catch (err) {
      dlg.close();
      toastError(err);
      refreshParties().catch(() => {});
      refreshState().catch(() => {});
    }
  });
}
