// Actions sur les parties et classement des mods. Ces actions ne modifient que
// parties.json : aucun fichier du jeu ni aucun mod n'est touché (voir apply.js).

import { api, iconUrl } from './api.js';
import { confirmDialog, openDialog } from './dialog.js';
import { clear, h, icon } from './dom.js';
import { langTitle, modTitle, pickTitle, t } from './i18n.js';
import {
  activeVersion, membership, modIndex, partyById, refreshLibrary, setParties, store, userParty,
} from './state.js';
import { toast, toastError } from './toast.js';
import { linkButton } from './hovercard.js';

const MAX_NAME = 60;

function post(path, body) {
  return api.post(path, { version: activeVersion(), ...body });
}

// Après une action : nouvel état des parties ; la bibliothèque est relue si des
// mods manquants apparaissent ou disparaissent.
function applyState(state) {
  const before = missingCount();
  setParties(state);
  if (missingCount() !== before) refreshLibrary().catch(() => {});
}

function missingCount() {
  if (!store.parties || !store.parties.supported) return 0;
  const index = modIndex();
  const ids = new Set();
  for (const m of store.parties.common_mods) ids.add(m.toLowerCase());
  for (const p of store.parties.parties) for (const m of p.mods) ids.add(m.toLowerCase());
  let n = 0;
  for (const low of ids) if (!index.has(low)) n++;
  return n;
}

export function displayName(id) {
  const m = modIndex().get(String(id).toLowerCase());
  return m ? modTitle(m) : String(id);
}

// Nom de la partie spéciale ou de l'utilisateur.
export function partyLabel(pid) {
  if (pid === '_pleine') return t('party.full');
  if (pid === '_vide') return t('party.empty');
  const p = partyById(pid);
  return p ? p.name : '';
}

// Nom libre et unique : « Etruria », puis « Etruria 2 », « Etruria 3 »…
export function uniqueName(base) {
  const taken = new Set((store.parties ? store.parties.parties : []).map((p) => p.name.toLocaleLowerCase()));
  const clean = base.trim().slice(0, MAX_NAME) || base;
  if (!taken.has(clean.toLocaleLowerCase())) return clean;
  for (let i = 2; i < 1000; i++) {
    const suffix = ` ${i}`;
    const candidate = clean.slice(0, MAX_NAME - suffix.length) + suffix;
    if (!taken.has(candidate.toLocaleLowerCase())) return candidate;
  }
  return clean;
}

// ---------------------------------------------------------------------------
// Fenêtre « nom de la partie » (créer, dupliquer, renommer)
// ---------------------------------------------------------------------------

function nameError(value, exclude) {
  const clean = value.replace(/\s+/g, ' ').trim();
  if (!clean) return t('parties.name_empty');
  if (clean.length > MAX_NAME) return t('parties.name_too_long', { max: MAX_NAME });
  const low = clean.toLocaleLowerCase();
  if ((store.parties ? store.parties.parties : []).some((p) => p.id !== exclude && p.name.toLocaleLowerCase() === low)) {
    return t('parties.name_taken', { name: clean });
  }
  return '';
}

// Champ du nom, avec contrôle en direct. Renvoie { field, input, valid() }.
function nameField(value, exclude) {
  const input = h('input', {
    class: 'field-input', type: 'text', maxlength: String(MAX_NAME + 20), spellcheck: 'false', autocomplete: 'off',
    'aria-label': t('parties.name_label'), autofocus: true,
  });
  input.value = value;
  const err = h('div', { class: 'name-error', 'aria-live': 'polite' });
  const counter = h('span', { class: 'name-count' });
  const check = () => {
    const msg = input.value.trim() ? nameError(input.value, exclude) : '';
    err.textContent = msg;
    counter.textContent = `${input.value.replace(/\s+/g, ' ').trim().length}/${MAX_NAME}`;
    return !nameError(input.value, exclude);
  };
  input.addEventListener('input', check);
  check();
  const field = h('label', { class: 'name-field' },
    h('span', { class: 'path-label' }, t('parties.name_label'), counter), input, err);
  return {
    field, input,
    valid: () => {
      const ok = check();
      if (!ok) err.textContent = nameError(input.value, exclude);
      return ok;
    },
    error: (msg) => { err.textContent = msg; },
  };
}

// Fenêtre simple : un nom, puis `submit(nom)` (qui peut échouer).
function askName({ title, help, value = '', okLabel, exclude = null, submit }) {
  const nf = nameField(value, exclude);
  const ok = h('button', { class: 'btn btn-primary', type: 'submit' }, okLabel);
  const cancel = h('button', { class: 'btn btn-ghost', type: 'button', text: t('common.cancel') });
  const form = h('form', { class: 'dlg-body name-dlg' },
    help ? h('p', { class: 'dlg-text', text: help }) : null,
    nf.field,
    h('div', { class: 'dlg-actions' }, cancel, ok));
  const dlg = openDialog(form, { title, cls: 'dlg-s' });
  cancel.addEventListener('click', () => dlg.close());
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!nf.valid() || ok.disabled) return;
    ok.disabled = true;
    try {
      await submit(nf.input.value.replace(/\s+/g, ' ').trim());
      dlg.close();
    } catch (err) {
      ok.disabled = false;
      if (err && err.key && err.key.startsWith('parties.name_')) nf.error(t(err.key, err.params || {}));
      else {
        dlg.close();
        toastError(err);
      }
    }
  });
  requestAnimationFrame(() => {
    nf.input.focus();
    nf.input.select();
  });
}

// ---------------------------------------------------------------------------
// Parties
// ---------------------------------------------------------------------------

export async function selectParty(pid) {
  try {
    applyState(await post('/api/parties/select', { id: pid }));
  } catch (err) {
    toastError(err);
  }
}

export function createParty() {
  askName({
    title: t('parties.create_title'),
    help: t('parties.create_help'),
    okLabel: t('parties.create_ok'),
    submit: async (name) => {
      const res = await post('/api/parties/create', { name });
      applyState(res.state);
    },
  });
}

export function duplicateParty() {
  const p = userParty();
  if (!p) return;
  askName({
    title: t('parties.duplicate_title'),
    help: t('parties.duplicate_help', { name: p.name }),
    value: uniqueName(t('parties.copy_name', { name: p.name })),
    okLabel: t('parties.duplicate_ok'),
    submit: async (name) => {
      const res = await post('/api/parties/duplicate', { id: p.id, name });
      applyState(res.state);
    },
  });
}

export function renameParty() {
  const p = userParty();
  if (!p) return;
  askName({
    title: t('parties.rename_title'),
    value: p.name,
    exclude: p.id,
    okLabel: t('parties.rename_ok'),
    submit: async (name) => {
      const res = await post('/api/parties/rename', { id: p.id, name });
      applyState(res.state);
    },
  });
}

export async function deleteParty() {
  const p = userParty();
  if (!p) return;
  const ok = await confirmDialog({
    title: t('parties.delete_title'),
    text: t('parties.delete_text', { name: p.name, count: p.mods.length }),
    ok: t('parties.delete_ok'),
    danger: true,
  });
  if (!ok) return;
  try {
    const res = await post('/api/parties/delete', { id: p.id });
    applyState(res.state);
    // Seule la suppression de la partie appliquée est signalée (le jeu
    // charge alors une autre partie) ; le menu montre déjà le reste.
    if (res.was_applied) toast('parties.deleted_applied', { name: p.name, other: partyLabel(res.fallback) }, 'info');
  } catch (err) {
    toastError(err);
  }
}

export async function setCommonEnabled(enabled) {
  const p = userParty();
  if (!p) return;
  try {
    applyState(await post('/api/parties/common', { id: p.id, enabled }));
  } catch (err) {
    toastError(err);
  }
}

// ---------------------------------------------------------------------------
// Classement : ajouter, retirer, déplacer
// ---------------------------------------------------------------------------

function listOf(target) {
  if (target === 'common') return store.parties.common_mods;
  const p = userParty();
  return p ? p.mods : [];
}


// Dépendances absentes de la liste visée : « Ajouter aussi ses 2 dépendances ? ».
// La fenêtre dit quel mod choisi les réclame (« La map Etruria a besoin
// de ces mods »), regroupées par mod choisi.
function rootLabel(id) {
  const m = modIndex().get(String(id).toLowerCase());
  const name = m ? modTitle(m) : String(id);
  return t(m && m.is_map ? 'deps.needed_by_map' : 'deps.needed_by_mod', { name });
}

function groupByRoot(list, requiredBy) {
  const groups = new Map();
  for (const d of list) {
    const root = (requiredBy && requiredBy[d.toLowerCase()]) || '';
    if (!groups.has(root)) groups.set(root, []);
    groups.get(root).push(d);
  }
  return groups;
}

async function askDependencies(target, ids) {
  let deps;
  try {
    deps = await post('/api/deps', { ids });
  } catch (err) {
    // Sans la liste des dépendances, les mods sont ajoutés sans vérification : on le signale.
    toastError(err);
    return { extra: [], cancelled: false };
  }
  const requiredBy = deps.required_by || {};
  const inTarget = new Set(listOf(target).map((m) => m.toLowerCase()));
  const chosen = new Set(ids.map((m) => m.toLowerCase()));
  const extra = deps.present.filter((d) => !inTarget.has(d.toLowerCase()) && !chosen.has(d.toLowerCase()));
  // Mods facultatifs présents, pas encore dans la liste (<SearchMods>).
  const optional = (deps.optional || []).filter((o) => o.present && o.id && !inTarget.has(o.id.toLowerCase())
    && !chosen.has(o.id.toLowerCase()));
  if (deps.missing.length) {
    // Message gardé dans les notifications (cloche) : il dit quel mod les réclame.
    const parts = [...groupByRoot(deps.missing, requiredBy)].map(([root, list]) => {
      const m = modIndex().get(root.toLowerCase());
      return t('deps.missing_for', { list: list.join(', '), name: m ? modTitle(m) : root });
    });
    toast('deps.missing_warn', { count: deps.missing.length, list: parts.join(' ; ') }, 'warn');
  }
  if (!extra.length && !optional.length) return { extra: [], cancelled: false };
  return new Promise((resolve) => {
    let result = { extra: [], cancelled: true };
    const optChecks = optional.map((o) => [h('input', { type: 'checkbox' }), o]);
    const picked = () => optChecks.filter(([i]) => i.checked).map(([, o]) => o.id);
    const optBox = optional.length ? h('div', { class: 'deps-optional' },
      h('div', { class: 'deps-root' }, icon('layers', 'ico-s'), h('span', { text: t('deps.optional_intro', { count: optional.length }) })),
      h('div', { class: 'deps-list deps-checks' }, optChecks.map(([input, o]) => h('label', { class: 'check pp-dep pp-opt' },
        input,
        h('span', { class: 'dep-name', text: displayName(o.id) }),
        o.required_by ? h('span', { class: 'dep-id', text: t('deps.optional_for', { name: displayName(o.required_by) }) }) : null)))) : null;
    const groups = groupByRoot(extra, requiredBy);
    const MAX = 12;
    let shown = 0;
    const box = h('div', { class: 'deps-ask' });
    for (const [root, list] of groups) {
      if (shown >= MAX) break;
      box.append(h('div', { class: 'deps-root' }, icon('map', 'ico-s'), h('span', { text: root ? rootLabel(root) : t('deps.needed') })));
      const ul = h('ul', { class: 'deps-list' });
      for (const d of list) {
        if (shown >= MAX) break;
        shown++;
        const m = modIndex().get(d.toLowerCase());
        ul.append(h('li', {}, icon('circle-check', 'ico-s'),
          h('span', { class: 'dep-name', text: displayName(d) }),
          m && modTitle(m) !== m.id ? h('span', { class: 'dep-id', text: m.id }) : null));
      }
      box.append(ul);
    }
    const where = target === 'common' ? t('deps.where_common') : t('deps.where_party', { name: (userParty() || {}).name || '' });
    const cancel = h('button', { class: 'btn btn-ghost', type: 'button', text: t('common.cancel'), onclick: () => dlg.close() });
    // Les mods facultatifs cochés sont ajoutés quel que soit le bouton choisi.
    const buttons = extra.length ? [cancel,
      h('button', { class: 'btn', type: 'button', text: t('deps.ask_no'), onclick: () => { result = { extra: picked(), cancelled: false }; dlg.close(); } }),
      h('button', { class: 'btn btn-primary', type: 'button', autofocus: true, text: t('deps.ask_yes', { count: extra.length }),
        onclick: () => { result = { extra: extra.concat(picked()), cancelled: false }; dlg.close(); } })]
      : [cancel,
        h('button', { class: 'btn btn-primary', type: 'button', autofocus: true, text: t('deps.optional_continue'),
          onclick: () => { result = { extra: picked(), cancelled: false }; dlg.close(); } })];
    const body = h('div', { class: 'dlg-body' },
      extra.length ? h('p', { class: 'dlg-text', text: t('deps.ask_intro', { count: extra.length, where }) }) : null,
      extra.length ? box : null,
      extra.length > MAX ? h('p', { class: 'faint', text: t('mod.more', { count: extra.length - MAX }) }) : null,
      optBox,
      optBox ? h('p', { class: 'set-help', text: t('deps.optional_note', { where }) }) : null,
      h('div', { class: 'dlg-actions is-center' }, buttons));
    const title = extra.length ? t('deps.ask_title', { count: extra.length }) : t('deps.optional_title', { count: optional.length });
    const dlg = openDialog(body, { title, cls: 'dlg-deps', onClose: () => resolve(result) });
  });
}

// Ajoute des mods à la partie sélectionnée ou aux mods communs ; avec
// `source`, les déplace depuis l'autre liste.
export async function addMods(target, ids, { source = null } = {}) {
  if (!ids.length || !store.parties || !store.parties.supported) return;
  if (target === 'party' && !userParty()) return;
  const index = modIndex();
  const present = ids.filter((id) => index.has(id.toLowerCase()));
  const { extra, cancelled } = present.length ? await askDependencies(target, present) : { extra: [], cancelled: false };
  if (cancelled) return;
  const party = userParty();
  // Ajouter, déplacer ou retirer des mods n'affiche plus de message :
  // les listes le montrent aussitôt.
  try {
    if (source) {
      let res = await post('/api/parties/mods', { action: 'move', target, source, party: party && party.id, ids });
      if (extra.length) {
        res = await post('/api/parties/mods', { action: 'add', target, party: party && party.id, ids: extra });
      }
      applyState(res.state);
      return;
    }
    const res = await post('/api/parties/mods', { action: 'add', target, party: party && party.id, ids: present.concat(extra) });
    applyState(res.state);
  } catch (err) {
    toastError(err);
  }
}

// Retire des mods d'une liste (jamais une suppression de fichier).
export async function removeMods(target, ids) {
  if (!ids.length || !store.parties || !store.parties.supported) return;
  const party = userParty();
  if (target === 'party' && !party) return;
  try {
    const res = await post('/api/parties/mods', { action: 'remove', target, party: party && party.id, ids });
    applyState(res.state);
    // Pas de message, la liste le montre.
  } catch (err) {
    toastError(err);
  }
}

// Ce que peut faire une sélection (bandeau d'actions).
export function possibleActions(ids) {
  const m = membership();
  const index = modIndex();
  const party = userParty();
  const lows = ids.map((id) => id.toLowerCase());
  const present = lows.filter((l) => index.has(l));
  return {
    addParty: !!party && present.some((l) => !m.party.has(l)),
    addCommon: present.some((l) => !m.common.has(l)),
    removeParty: !!party && lows.some((l) => m.party.has(l)),
    removeCommon: lows.some((l) => m.common.has(l)),
  };
}

// ---------------------------------------------------------------------------
// « ＋ Partie » : une map et ses dépendances deviennent une partie
// ---------------------------------------------------------------------------

function depRow(name, ok, state, kind = 'mod', link = null) {
  return h('div', { class: `pp-dep ${ok ? '' : 'is-absent'}` },
    icon(ok ? 'circle-check' : (kind === 'dlc' ? 'package' : 'circle-x'), 'ico-s'),
    h('span', { class: 'dep-name', text: name }),
    link,
    h('span', { class: 'dep-state', text: state }));
}

// Lien de téléchargement d'un mod absent (<SearchMods>), s'il y en a un.
function depLink(deps, name) {
  const l = deps.links && deps.links[String(name).toLowerCase()];
  return l && l.url ? linkButton(l.mod, l.url) : null;
}

// Mods facultatifs (<SearchMods><optionalMod>) : une case par mod
// présent (décochée), les absents pour information avec leur lien.
function optionalBox(deps) {
  const list = deps.optional || [];
  const checks = [];
  if (!list.length) return { box: null, chosen: () => [] };
  const rows = list.map((o) => {
    if (!o.present) return depRow(o.name, false, t('dep.absent'), 'optional', depLink(deps, o.name));
    const input = h('input', { type: 'checkbox' });
    checks.push([input, o.id]);
    return h('label', { class: 'check pp-dep pp-opt' }, input,
      h('span', { class: 'dep-name', text: displayName(o.id) }),
      h('span', { class: 'dep-state', text: t('dep.present') }));
  });
  const box = h('div', { class: 'pp-optional' },
    h('div', { class: 'pp-section', text: t('plus.optional_title', { count: list.length }) }),
    h('div', { class: 'pp-list' }, rows),
    h('p', { class: 'pp-note', text: t(checks.length ? 'plus.optional_note' : 'plus.optional_none_present') }));
  return { box, chosen: () => checks.filter(([i]) => i.checked).map(([, id]) => id) };
}

export async function plusParty(mod) {
  if (!store.parties || !store.parties.supported) return;
  let deps = { present: [], missing: [], dlc: [], optional: [], links: {} };
  try {
    deps = await post('/api/deps', { ids: [mod.id] });
  } catch (err) {
    toastError(err);
    return;
  }
  // Titre de la map dans la langue de l'utilisateur : celui de la balise
  // <maps>, sinon celui du mod, sinon l'anglais ou la première langue.
  const title = langTitle(mod.map_titles) || langTitle(mod.titles) || pickTitle(mod.map_titles)
    || pickTitle(mod.titles) || mod.short || mod.id;
  const nf = nameField(uniqueName(title), null);
  const art = h('div', { class: 'pp-art' });
  if (mod.icon) art.append(h('img', { src: iconUrl(activeVersion(), mod.icon, true), alt: '', draggable: 'false' }));
  else art.append(icon('map'));

  const total = deps.present.length + deps.missing.length;
  const depsBox = h('div', { class: 'pp-deps' });
  const opt = optionalBox(deps);
  if (!total && !deps.dlc.length) {
    depsBox.append(h('p', { class: 'faint', text: t('plus.no_deps') }));
  } else {
    if (total) {
      depsBox.append(h('div', { class: 'pp-section', text: t('plus.deps_title', { count: total }) }));
      depsBox.append(h('div', { class: 'pp-list' },
        deps.present.map((d) => depRow(displayName(d), true, t('dep.present'))),
        deps.missing.map((d) => depRow(d, false, t('dep.absent'), 'mod', depLink(deps, d)))));
    }
    if (deps.dlc.length) {
      depsBox.append(h('div', { class: 'pp-section', text: t('plus.dlc_title') }));
      depsBox.append(h('div', { class: 'pp-list' },
        deps.dlc.map((d) => depRow(d.id, d.owned, d.owned ? t('dep.dlc_owned') : t('dep.dlc_missing'), 'dlc'))));
      depsBox.append(h('p', { class: 'pp-note', text: t('plus.dlc_note') }));
    }
    if (deps.missing.length) depsBox.append(h('p', { class: 'pp-note is-warn' }, icon('triangle-alert', 'ico-s'), h('span', { text: t('plus.missing_note') })));
  }
  if (opt.box) depsBox.append(opt.box);
  if (deps.links && Object.keys(deps.links).length) depsBox.append(h('p', { class: 'pp-note', text: t('mod.links_old') }));
  const summary = h('p', { class: 'pp-summary', text: t('plus.summary', { count: deps.present.length }) });
  const ok = h('button', { class: 'btn btn-primary', type: 'submit' }, icon('plus'), t('plus.create'));
  const cancel = h('button', { class: 'btn btn-ghost', type: 'button', text: t('common.cancel') });
  const form = h('form', { class: 'dlg-body plus-dlg' },
    h('div', { class: 'pp-head' }, art,
      h('div', { class: 'pp-title' },
        h('div', { class: 'pp-map', text: title }),
        h('div', { class: 'pp-id', text: mod.file || mod.id }))),
    nf.field,
    depsBox,
    summary,
    h('div', { class: 'dlg-actions' }, cancel, ok));
  const dlg = openDialog(form, { title: t('plus.title'), cls: 'dlg-plus' });
  cancel.addEventListener('click', () => dlg.close());
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!nf.valid() || ok.disabled) return;
    ok.disabled = true;
    try {
      const res = await post('/api/parties/create', {
        name: nf.input.value.replace(/\s+/g, ' ').trim(), map: mod.id, optional: opt.chosen(),
      });
      dlg.close();
      applyState(res.state);
      if (res.missing.length) {
        toast('plus.created_missing', { count: res.missing.length, list: res.missing.join(', ') }, 'warn');
      }
    } catch (err) {
      ok.disabled = false;
      if (err && err.key && err.key.startsWith('parties.name_')) nf.error(t(err.key, err.params || {}));
      else {
        dlg.close();
        toastError(err);
      }
    }
  });
  requestAnimationFrame(() => {
    nf.input.focus();
    nf.input.select();
  });
}

// ---------------------------------------------------------------------------
// « Remplacer par… » : un mod manquant, renommé par son auteur
// ---------------------------------------------------------------------------

function fold(s) {
  return String(s || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

export function replaceMissing(oldId) {
  const mods = (store.library ? store.library.mods : []).slice()
    .sort((a, b) => modTitle(a).localeCompare(modTitle(b), undefined, { sensitivity: 'base', numeric: true }));
  const search = h('input', { class: 'field-input', type: 'search', spellcheck: 'false', autocomplete: 'off',
    placeholder: t('list1.search'), 'aria-label': t('list1.search'), autofocus: true });
  const list = h('div', { class: 'replace-list', role: 'listbox' });
  const fill = () => {
    clear(list);
    const q = fold(search.value.trim());
    const found = mods.filter((m) => !q || fold(modTitle(m)).includes(q) || fold(m.id).includes(q));
    for (const m of found.slice(0, 200)) {
      const art = h('span', { class: 'rl-art' });
      if (m.icon) art.append(h('img', { src: iconUrl(activeVersion(), m.icon, true), alt: '', loading: 'lazy', draggable: 'false' }));
      else art.append(icon('package', 'ico-s'));
      list.append(h('button', { class: 'replace-item', type: 'button', role: 'option', onclick: () => choose(m) },
        art,
        h('span', { class: 'rl-text' }, h('span', { text: modTitle(m) }), h('span', { class: 'rl-sub', text: m.file })),
      ));
    }
    if (!found.length) list.append(h('p', { class: 'faint', text: t('list1.no_match', { query: search.value }) }));
  };
  search.addEventListener('input', fill);
  const body = h('div', { class: 'dlg-body replace-dlg' },
    h('p', { class: 'dlg-text', text: t('replace.help', { name: oldId }) }),
    h('div', { class: 'search' }, icon('search'), search),
    list);
  const dlg = openDialog(body, { title: t('replace.title'), cls: 'dlg-replace' });
  fill();
  async function choose(m) {
    try {
      const res = await post('/api/parties/replace', { old: oldId, new: m.id });
      dlg.close();
      applyState(res.state);
      refreshLibrary().catch(() => {});
      toast('replace.done', { old: oldId, name: res.new, count: res.lists }, 'success');
    } catch (err) {
      toastError(err);
    }
  }
}
