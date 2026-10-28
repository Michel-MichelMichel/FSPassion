// Petits outils DOM. Les textes passent toujours par textContent.

export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (v === true) el.setAttribute(k, '');
    else el.setAttribute(k, String(v));
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

// Icône Lucide colorée par le thème (masque CSS sur currentColor).
// Copie réussie : pas de notification, l'icône du bouton devient une coche
// un court instant.
export function flashCopied(btn) {
  if (!btn) return;
  const ico = btn.querySelector('.ico');
  if (!ico) return;
  const before = ico.style.getPropertyValue('--ico');
  ico.style.setProperty('--ico', 'url("/assets/icons/check.svg")');
  btn.classList.add('is-copied');
  clearTimeout(btn._copiedTimer);
  btn._copiedTimer = setTimeout(() => {
    ico.style.setProperty('--ico', before);
    btn.classList.remove('is-copied');
  }, 1400);
}

export function icon(name, cls = '') {
  const el = document.createElement('span');
  el.className = `ico ${cls}`.trim();
  el.style.setProperty('--ico', `url("/assets/icons/${name}.svg")`);
  el.setAttribute('aria-hidden', 'true');
  return el;
}

// Logo d'une version du jeu (SVG en currentColor, rendu par masque).
export function gameLogo(file, cls = '') {
  const el = document.createElement('span');
  el.className = `game-logo ${cls}`.trim();
  el.style.setProperty('--logo', `url("/assets/game-logos/${encodeURIComponent(file)}")`);
  el.setAttribute('aria-hidden', 'true');
  return el;
}

export function debounce(fn, ms) {
  let id = 0;
  return (...args) => {
    clearTimeout(id);
    id = setTimeout(() => fn(...args), ms);
  };
}

export function reducedMotion() {
  return document.documentElement.classList.contains('reduce-motion');
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = h('textarea', { style: { position: 'fixed', opacity: '0' } });
    ta.value = text;
    document.body.append(ta);
    ta.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch {
      ok = false;
    }
    ta.remove();
    return ok;
  }
}
