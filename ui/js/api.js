// Communication avec le cœur de FS Passion (serveur local).
// Le jeton de session n'apparaît dans aucune adresse : le serveur le place dans un
// cookie HttpOnly à l'ouverture, et le navigateur le renvoie à chaque requête
// (API, icônes, flux d'événements). L'origine est contrôlée par le serveur.

const params = new URLSearchParams(location.search);
// « window » : interface dans la fenêtre de l'application ; « browser » : navigateur.
export const shell = params.get('shell') === 'window' ? 'window' : 'browser';
export const atelierRequested = params.get('atelier') === '1';

export class ApiError extends Error {
  constructor(key, params = {}, status = 0) {
    super(key);
    this.key = key;
    this.params = params;
    this.status = status;
  }
}

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'X-FSP-Shell': shell },
    cache: 'no-store',
  };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(path, opts);
  } catch {
    throw new ApiError('error.offline');
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    throw new ApiError((data && data.error) || 'error.unexpected', (data && data.params) || {}, res.status);
  }
  return data;
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body = {}) => request('POST', path, body),
};

// size : 'medium' (300 px, tuiles de la liste 1), true (96 px, listes 2 et 3), false (taille d'origine).
// Versions qui ont une variante moyenne (300 px) de leurs icônes : voir
// MEDIUM_VERSIONS dans src/fspassion/icons.py (0.7.9). Pour les autres, les
// icônes d'origine font 256 px au plus : la grande variante sert aux tuiles.
const MEDIUM_VERSIONS = new Set(['FS25', 'FS28']);

export function iconUrl(version, base, size = false) {
  const medium = size === 'medium' && MEDIUM_VERSIONS.has(version);
  const suffix = medium ? '-medium' : size && size !== 'medium' ? '-small' : '';
  const name = `${base}${suffix}.webp`;
  return `/icons/${encodeURIComponent(version)}/${encodeURIComponent(name)}`;
}

export function dlcIconUrl(version, name) {
  return `/dlc-icons/${encodeURIComponent(version)}/${encodeURIComponent(name)}`;
}

// Flux d'événements (Server-Sent Events), avec reconnexion automatique.
const listeners = new Map();

export function on(type, fn) {
  if (!listeners.has(type)) listeners.set(type, new Set());
  listeners.get(type).add(fn);
  return () => listeners.get(type).delete(fn);
}

function emit(type, payload) {
  for (const fn of listeners.get(type) || []) {
    try {
      fn(payload);
    } catch (err) {
      console.error(err);
    }
  }
}

let source = null;
export function connectEvents() {
  if (source) source.close();
  source = new EventSource('/api/events');
  source.onmessage = (ev) => {
    let data;
    try {
      data = JSON.parse(ev.data);
    } catch {
      return;
    }
    emit(data.type, data);
    emit('*', data);
  };
  source.onopen = () => emit('connection', { up: true });
  source.onerror = () => emit('connection', { up: false });
}
