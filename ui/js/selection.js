// Sélection des mods : dans les trois listes, une liste à la fois.
// Clic, Ctrl+clic, Maj+clic (plage), lasso, Ctrl+A, Échap, clavier.
//
// Les éléments sont désignés par l'identifiant du mod en minuscules (clé) ;
// chaque liste fournit l'ordre de ses éléments sélectionnables et
// l'identifiant exact de chacun.

const listeners = new Set();
const lists = new Map(); // 'l1' | 'l2' | 'l3' → { order(): string[], idOf(key): string }

const sel = {
  list: null,
  keys: new Map(), // clé → identifiant exact
  anchor: null,
};
let active = 'l1';

export function registerList(list, provider) {
  lists.set(list, provider);
}

export function onSelection(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit() {
  for (const fn of listeners) {
    try {
      fn(sel);
    } catch (err) {
      console.error(err);
    }
  }
}

export function setActiveList(list) {
  active = list;
}

export function activeList() {
  return active;
}

export function selectionList() {
  return sel.keys.size ? sel.list : null;
}

export function selectionSize() {
  return sel.keys.size;
}

export function selectedIds() {
  return [...sel.keys.values()];
}

export function isSelected(list, key) {
  return sel.list === list && sel.keys.has(key);
}

function idOf(list, key) {
  const p = lists.get(list);
  return (p && p.idOf(key)) || key;
}

// Remplace la sélection (ou l'étend, additive) par `keys`, dans `list`.
export function setSelection(list, keys, { additive = false, anchor } = {}) {
  if (sel.list !== list || !additive) sel.keys = new Map();
  sel.list = list;
  for (const k of keys) sel.keys.set(k, idOf(list, k));
  if (anchor !== undefined) sel.anchor = anchor;
  active = list;
  emit();
}

export function toggle(list, key) {
  if (sel.list !== list) {
    sel.keys = new Map();
    sel.list = list;
  }
  if (sel.keys.has(key)) sel.keys.delete(key);
  else sel.keys.set(key, idOf(list, key));
  sel.anchor = key;
  active = list;
  emit();
}

// Maj+clic : plage depuis l'ancre, dans l'ordre d'affichage de la liste.
export function rangeTo(list, key, { additive = false } = {}) {
  const p = lists.get(list);
  if (!p) return;
  const order = p.order();
  const anchor = sel.list === list && sel.anchor && order.includes(sel.anchor) ? sel.anchor : key;
  const a = order.indexOf(anchor);
  const b = order.indexOf(key);
  if (a < 0 || b < 0) {
    setSelection(list, [key], { anchor: key });
    return;
  }
  const [from, to] = a <= b ? [a, b] : [b, a];
  setSelection(list, order.slice(from, to + 1), { additive, anchor });
}

export function selectAll(list) {
  const p = lists.get(list);
  if (!p) return;
  setSelection(list, p.order(), { anchor: null });
}

export function clearSelection() {
  if (!sel.keys.size && sel.list === null) return;
  sel.keys = new Map();
  sel.list = null;
  sel.anchor = null;
  emit();
}

// Après un changement de contenu : les éléments disparus de la liste quittent
// la sélection (par exemple des mods déplacés vers une autre liste).
export function pruneSelection() {
  if (!sel.list) return;
  const p = lists.get(sel.list);
  if (!p) return;
  const present = new Set(p.order());
  let changed = false;
  for (const k of [...sel.keys.keys()]) {
    if (!present.has(k)) {
      sel.keys.delete(k);
      changed = true;
    }
  }
  if (!sel.keys.size) {
    sel.list = null;
    sel.anchor = null;
  }
  if (changed) emit();
}

// Appui sur une tuile sélectionnable : la sélection change au bon moment pour
// permettre aussi bien un clic qu'un glisser de plusieurs mods.
// Renvoie une fonction à appeler au relâchement si aucun glisser n'a eu lieu.
export function pressTile(e, list, key) {
  active = list;
  const ctrl = e.ctrlKey || e.metaKey;
  const already = isSelected(list, key);
  if (e.shiftKey) {
    rangeTo(list, key, { additive: ctrl });
    return () => {};
  }
  if (ctrl) {
    if (!already) toggle(list, key);
    // Ctrl+clic sur un mod déjà sélectionné : il est retiré au relâchement
    // (un glisser l'emporte avec les autres).
    return () => already && toggle(list, key);
  }
  if (!already) {
    setSelection(list, [key], { anchor: key });
    return () => {};
  }
  // Clic simple sur un mod déjà sélectionné : lui seul reste sélectionné au
  // relâchement (un glisser emporte toute la sélection).
  return () => setSelection(list, [key], { anchor: key });
}
