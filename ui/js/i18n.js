// Textes de l'interface. Tout vient des fichiers de langue.
// Les textes sont toujours insérés comme du texte brut (textContent), jamais
// interprétés comme du HTML : un fichier de langue ne peut rien exécuter.

import { api } from './api.js';

let strings = {};
let code = 'en';
let pluralRules = new Intl.PluralRules('en');
const changeListeners = new Set();

export function currentLang() {
  return code;
}

export async function loadLanguage(lang) {
  const data = await api.get(`/api/i18n?lang=${encodeURIComponent(lang || '')}`);
  strings = data.strings || {};
  code = data.code || 'en';
  try {
    pluralRules = new Intl.PluralRules(code);
  } catch {
    pluralRules = new Intl.PluralRules('en');
  }
  document.documentElement.lang = code;
  for (const fn of changeListeners) fn(code);
}

export function onLanguageChange(fn) {
  changeListeners.add(fn);
}

function lookup(key) {
  let node = strings;
  for (const part of key.split('.')) {
    if (node && typeof node === 'object' && part in node) node = node[part];
    else return undefined;
  }
  return node;
}

function format(text, params) {
  return text.replace(/\{(\w+)\}/g, (m, name) => {
    if (params && params[name] !== undefined && params[name] !== null) {
      const v = params[name];
      return typeof v === 'number' ? formatNumber(v) : String(v);
    }
    return m;
  });
}

export function formatNumber(n) {
  try {
    return new Intl.NumberFormat(code).format(n);
  } catch {
    return String(n);
  }
}

// t('clé', {count: 3}) — pluriels { "one": "…", "other": "…" }.
export function t(key, params = {}) {
  let v = lookup(key);
  if (v === undefined) return key;
  if (v && typeof v === 'object' && !Array.isArray(v)) {
    const n = Number(params.count ?? 0);
    const cat = n === 0 && v.zero ? 'zero' : pluralRules.select(n);
    v = v[cat] ?? v.other ?? '';
  }
  if (Array.isArray(v)) return v.map((x) => format(String(x), params));
  return format(String(v), params);
}

// Bloc de texte riche sans HTML : liste de { h | p | ul } (notice).
export function blocks(key) {
  const v = lookup(key);
  return Array.isArray(v) ? v : [];
}

// Applique les traductions aux éléments marqués data-i18n, data-i18n-tip,
// data-i18n-placeholder et data-i18n-aria.
export function applyI18n(root = document) {
  root.querySelectorAll('[data-i18n]').forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  root.querySelectorAll('[data-i18n-tip]').forEach((el) => {
    el.dataset.tip = t(el.dataset.i18nTip);
    el.setAttribute('aria-label', el.dataset.tip);
  });
  root.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  root.querySelectorAll('[data-i18n-aria]').forEach((el) => {
    el.setAttribute('aria-label', t(el.dataset.i18nAria));
  });
}

// Titre d'un mod dans la langue de l'interface, sinon l'anglais, sinon la
// première langue disponible. L'allemand n'est affiché qu'aux utilisateurs
// dont l'interface est en allemand, ou quand c'est la seule langue.
// Codes de langue des modDesc.xml (propres au jeu) : « cz » pour le tchèque,
// « cs » pour le chinois simplifié, « jp », « kr », « br », « ea »…
const FS_LANG = {
  cs: 'cz', ja: 'jp', ko: 'kr', 'zh-Hans': 'cs', 'zh-Hant': 'ct',
  'pt-BR': 'br', 'pt-PT': 'pt', 'es-419': 'ea', nb: 'no',
};

export function pickTitle(titles) {
  if (!titles) return '';
  const wanted = (FS_LANG[code] || code.split('-')[0]).toLowerCase();
  const map = {};
  for (const [k, v] of Object.entries(titles)) map[k.toLowerCase()] = v;
  if (map[wanted]) return map[wanted];
  if (map.en) return map.en;
  if (map._) return map._;
  const others = Object.keys(map).filter((k) => k !== 'de');
  if (others.length) return map[others[0]];
  return map.de || '';
}

// Nom affiché d'un mod : le titre complet de son modDesc.xml (balise
// <title>, dans la langue de l'interface si elle existe), sinon le nom court
// du fichier.
export function modTitle(m) {
  if (!m) return '';
  return pickTitle(m.titles) || m.short || m.id;
}

// Titre dans la langue de l'interface seulement (sinon chaîne vide).
export function langTitle(titles) {
  if (!titles) return '';
  const wanted = (FS_LANG[code] || code.split('-')[0]).toLowerCase();
  for (const [k, v] of Object.entries(titles)) if (k.toLowerCase() === wanted && v) return v;
  return '';
}

// Nom d'un DLC : traductions du catalogue (codes de l'interface) ou titre du
// modDesc.xml (codes du jeu).
export function pickName(names) {
  if (!names) return '';
  if (names[code]) return names[code];
  const lang = code.split('-')[0];
  if (names[lang]) return names[lang];
  return pickTitle(names);
}
