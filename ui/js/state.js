// État partagé de l'interface : ce que le cœur a renvoyé, plus l'état local.

import { api } from './api.js';

const subscribers = new Map();

export const store = {
  app: null, // état global (/api/state)
  library: null, // bibliothèque de la version active (/api/library)
  parties: null, // parties et mods communs de la version active (/api/parties)
  search: '',
  ui: { settingsOpen: false },
};

export const FULL = '_pleine';
export const EMPTY = '_vide';

export function subscribe(topic, fn) {
  if (!subscribers.has(topic)) subscribers.set(topic, new Set());
  subscribers.get(topic).add(fn);
  return () => subscribers.get(topic).delete(fn);
}

export function notify(topic, payload) {
  for (const fn of subscribers.get(topic) || []) {
    try {
      fn(payload);
    } catch (err) {
      console.error(err);
    }
  }
}

export async function refreshState() {
  store.app = await api.get('/api/state');
  notify('state', store.app);
  return store.app;
}

// Appels regroupés : une demande pendant une autre en relance une seule après.
function grouped(fn) {
  let pending = null;
  let again = false;
  return async () => {
    if (pending) {
      again = true;
      return pending;
    }
    pending = (async () => {
      do {
        again = false;
        await fn();
      } while (again);
    })();
    try {
      await pending;
    } finally {
      pending = null;
    }
  };
}

// Recharge la bibliothèque de la version active.
export const refreshLibrary = grouped(async () => {
  const vid = activeVersion();
  const lib = await api.get(`/api/library?version=${encodeURIComponent(vid)}`);
  if (lib.version === activeVersion()) {
    store.library = lib;
    notify('library', lib);
  }
});

// Recharge les parties de la version active.
export const refreshParties = grouped(async () => {
  const vid = activeVersion();
  const parties = await api.get(`/api/parties?version=${encodeURIComponent(vid)}`);
  if (parties.version === activeVersion()) setParties(parties);
});

// État des parties renvoyé par une action (créer, classer…).
export function setParties(parties) {
  if (!parties || parties.version !== activeVersion()) return;
  store.parties = parties;
  notify('parties', parties);
}

export function activeVersion() {
  return store.app ? store.app.active_version : 'FS25';
}

export function versionInfo(vid = activeVersion()) {
  if (!store.app) return null;
  return store.app.versions.find((v) => v.id === vid) || null;
}

export function setting(key) {
  return store.app ? store.app.settings[key] : undefined;
}

export function isRunning(vid = activeVersion()) {
  return !!(store.app && store.app.running.includes(vid));
}

// ---------------------------------------------------------------------------
// Parties et classement
// ---------------------------------------------------------------------------

export function partiesSupported() {
  return !!(store.parties && store.parties.supported);
}

export function isSpecial(pid) {
  return pid === FULL || pid === EMPTY;
}

export function partyById(pid) {
  if (!partiesSupported()) return null;
  return store.parties.parties.find((p) => p.id === pid) || null;
}

// Partie sélectionnée : une partie de l'utilisateur, ou une partie spéciale.
export function selectedParty() {
  if (!partiesSupported()) return null;
  const sel = store.parties.selected;
  if (isSpecial(sel)) return { id: sel, special: true };
  return partyById(sel) || { id: FULL, special: true };
}

// Partie de l'utilisateur sélectionnée (null pour la Partie Vide ou Pleine).
export function userParty() {
  const p = selectedParty();
  return p && !p.special ? p : null;
}

let cache = { lib: null, parties: null, index: null, member: null };

// Mods de la bibliothèque par identifiant en minuscules.
export function modIndex() {
  if (cache.lib !== store.library || !cache.index) {
    cache = { lib: store.library, parties: null, index: new Map(), member: null };
    for (const m of (store.library && store.library.mods) || []) cache.index.set(m.id.toLowerCase(), m);
  }
  return cache.index;
}

// Appartenance de chaque mod (identifiants en minuscules) : partie
// sélectionnée, mods communs, au moins une partie, et noms des parties.
export function membership() {
  modIndex();
  if (cache.parties === store.parties && cache.member) return cache.member;
  const party = new Set();
  const common = new Set();
  const anyParty = new Set();
  const partiesOf = new Map();
  if (partiesSupported()) {
    for (const id of store.parties.common_mods) common.add(id.toLowerCase());
    const sel = userParty();
    for (const p of store.parties.parties) {
      for (const id of p.mods) {
        const low = id.toLowerCase();
        anyParty.add(low);
        if (!partiesOf.has(low)) partiesOf.set(low, []);
        partiesOf.get(low).push(p.name);
        if (sel && p.id === sel.id) party.add(low);
      }
    }
  }
  cache.parties = store.parties;
  cache.member = { party, common, anyParty, partiesOf };
  return cache.member;
}

// Nombre de mods actifs de la partie sélectionnée : mods de la partie + mods
// communs (si le switch est activé), sans doublon, présents sur le disque.
export function activeCount() {
  const sel = selectedParty();
  const index = modIndex();
  if (!sel) return null;
  if (sel.id === FULL) return index.size;
  if (sel.id === EMPTY) return 0;
  const ids = new Set(sel.mods.map((m) => m.toLowerCase()));
  if (sel.common_enabled) for (const m of store.parties.common_mods) ids.add(m.toLowerCase());
  let n = 0;
  for (const low of ids) if (index.has(low)) n++;
  return n;
}
