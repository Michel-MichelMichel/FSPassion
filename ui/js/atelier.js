// Atelier de thèmes : outil de développement, dans le navigateur.
// Deux couleurs (fond Mica et accent), lueurs du Mica, grain, effet ;
// Mode clair ou sombre, couleur des textes, plusieurs couleurs
// d'accent (jusqu'à 4), thème jumeau pour le bouton soleil/lune ;
// dégradé bicolore ; style (bicolore, palette), surfaces et textes
// officiels, effet néon ;
// application instantanée à toute l'interface,
// contraste affiché ; enregistrement dans ui/themes.json ou copie de la
// définition.

import { api } from './api.js';
import { clear, copyText, flashCopied, h, icon } from './dom.js';
import { formatNumber, t } from './i18n.js';
import {
  allThemes, applyTheme, chosenTheme, contrast, hexToRgb, paintSwatch, setThemes, smallTextColor, themeMode, themeStyle,
  themeSurfaces, themeWindow,
} from './theme.js';
import { toastError } from './toast.js';

let panel = null;
let editing = null;

function normalizeHex(v) {
  const rgb = hexToRgb(v);
  if (!rgb) return null;
  return '#' + rgb.map((x) => x.toString(16).padStart(2, '0')).join('').toUpperCase();
}

export function toggleAtelier(host) {
  if (panel) {
    panel.remove();
    panel = null;
    applyTheme(chosenTheme());
    return;
  }
  editing = normalize({ ...chosenTheme() });
  panel = h('div', { class: 'atelier', role: 'dialog', 'aria-label': t('atelier.title') });
  host.append(panel);
  render();
  makeDraggable(panel, panel.querySelector('.atelier-head'));
}

function normalize(th) {
  return {
    mica: 60, mode: 'dark', neon: 0, ...th,
    accents: Array.isArray(th.accents) ? th.accents.slice(0, 4) : [],
    gradient: Array.isArray(th.gradient) ? th.gradient.slice(0, 2) : [],
    surfaces: Array.isArray(th.surfaces) ? th.surfaces.slice(0, 4) : [],
    texts: Array.isArray(th.texts) ? th.texts.slice(0, 4) : [],
  };
}

function colorRow(label, key) {
  const start = editing[key] || (themeMode(editing) === 'light' ? '#1B1B1F' : '#FFFFFF');
  const color = h('input', { type: 'color', value: start.toLowerCase() });
  const text = h('input', { class: 'field-input', type: 'text', value: editing[key] || '', spellcheck: 'false', maxlength: '7' });
  const set = (v) => {
    const hex = normalizeHex(v);
    if (!hex) return;
    editing[key] = hex;
    color.value = hex.toLowerCase();
    text.value = hex;
    live();
  };
  color.addEventListener('input', () => set(color.value));
  text.addEventListener('change', () => set(text.value));
  return h('div', { class: 'at-row' }, h('label', { text: label }), color, text);
}

// Couleur n° i d'une liste (accents, dégradé).
function listColorRow(key, i, label) {
  const value = editing[key][i] || editing.light;
  const color = h('input', { type: 'color', value: value.toLowerCase() });
  const text = h('input', { class: 'field-input', type: 'text', value, spellcheck: 'false', maxlength: '7' });
  const set = (v) => {
    const hex = normalizeHex(v);
    if (!hex) return;
    editing[key][i] = hex;
    color.value = hex.toLowerCase();
    text.value = hex;
    live();
  };
  color.addEventListener('input', () => set(color.value));
  text.addEventListener('change', () => set(text.value));
  return h('div', { class: 'at-row' }, h('label', { text: label }), color, text);
}

function accentRow(i) {
  return listColorRow('accents', i, t('atelier.accent_n', { n: i + 1 }));
}

function selectRow(label, value, options, onChange) {
  const sel = h('select', { class: 'field-input' }, ...options.map(([v, txt]) => h('option', { value: v, text: txt })));
  sel.value = value;
  sel.addEventListener('change', () => onChange(sel.value));
  return h('div', { class: 'at-row' }, h('label', { text: label }), sel);
}

function rangeRow(label, key, max = 100) {
  const out = h('span', { class: 'num', text: String(editing[key] ?? 0) });
  const r = h('input', { type: 'range', min: '0', max: String(max), value: String(editing[key] ?? 0) });
  r.addEventListener('input', () => {
    editing[key] = Number(r.value);
    out.textContent = r.value;
    live();
  });
  return h('div', { class: 'at-row' }, h('label', { text: label }), r, out);
}

let contrastEl = null;

function live() {
  // Thème palette : le fond de la fenêtre est la première surface.
  if (themeStyle(editing) === 'palette' && editing.surfaces.length) editing.dark = editing.surfaces[0];
  applyTheme(editing, { preview: true });
  if (contrastEl) {
    const ref = themeSurfaces(editing)[1] || themeWindow(editing);
    const c = contrast(editing.light, ref);
    const small = smallTextColor(editing.light, ref);
    contrastEl.classList.toggle('is-low', c < 4.5);
    const ratio = formatNumber(Math.round(c * 100) / 100);
    contrastEl.textContent = c < 4.5
      ? t('atelier.contrast_low', { ratio, color: small })
      : t('atelier.contrast_ok', { ratio });
  }
}

function render() {
  // Le panneau défile ; on garde la position quand il est reconstruit.
  const keepScroll = panel.querySelector('.atelier-body')?.scrollTop || 0;
  clear(panel);
  const effect = h('select', { class: 'field-input' },
    h('option', { value: 'none', text: t('atelier.effect_none') }),
    h('option', { value: 'metal', text: t('atelier.effect_metal') }));
  effect.value = editing.effect || 'none';
  effect.addEventListener('change', () => {
    editing.effect = effect.value;
    live();
  });
  const list = h('div', { class: 'at-list' });
  for (const th of allThemes()) {
    const b = h('button', { type: 'button', 'aria-pressed': String(th.id === editing.id), 'data-tip-text': th.name },
      (() => {
        const dot = h('span', { class: 'swatch-dot' });
        paintSwatch(dot, th);
        return dot;
      })());
    b.addEventListener('click', () => {
      editing = normalize({ ...th });
      render();
      live();
    });
    list.append(b);
  }
  const idInput = h('input', { class: 'field-input', type: 'text', value: editing.id, spellcheck: 'false' });
  idInput.addEventListener('change', () => { editing.id = idInput.value.trim().toLowerCase().replace(/[^a-z0-9-]/g, '-') || 'theme'; });
  const nameInput = h('input', { class: 'field-input', type: 'text', value: editing.name, spellcheck: 'false' });
  nameInput.addEventListener('change', () => { editing.name = nameInput.value.trim() || editing.id; });
  contrastEl = h('div', { class: 'at-contrast' });

  panel.append(
    h('div', { class: 'atelier-head' },
      icon('palette'), h('h2', { text: t('atelier.title') }),
      h('button', { class: 'icon-btn icon-btn-s', type: 'button', 'aria-label': t('common.close'), 'data-i18n-tip': 'common.close', onclick: () => toggleAtelier() }, icon('x'))),
    h('div', { class: 'atelier-body' },
      list,
      h('div', { class: 'at-row' }, h('label', { text: t('atelier.id') }), idInput),
      h('div', { class: 'at-row' }, h('label', { text: t('atelier.name') }), nameInput),
      selectRow(t('atelier.style'), themeStyle(editing), [['duo', t('atelier.style_duo')], ['palette', t('atelier.style_palette')],
        ['classic', t('atelier.style_classic')]], (v) => {
        editing.style = v === 'classic' ? undefined : v;
        if (v === 'palette' && editing.surfaces.length < 2) editing.surfaces = [editing.dark, editing.dark, editing.dark];
        render();
        live();
      }),
      selectRow(t('atelier.mode'), themeMode(editing), [['dark', t('atelier.mode_dark')], ['light', t('atelier.mode_light')]], (v) => {
        editing.mode = v;
        live();
      }),
      ...(themeStyle(editing) === 'palette'
        ? [0, 1, 2, 3].map((i) => listColorRow('surfaces', i, t(`atelier.surface_${i + 1}`)))
        : [colorRow(t('atelier.dark'), 'dark')]),
      ...(themeStyle(editing) === 'duo' ? [] : [colorRow(t('atelier.text'), 'text')]),
      ...(themeStyle(editing) === 'palette'
        ? [1, 2, 3].map((i) => listColorRow('texts', i, t('atelier.text_n', { n: i + 1 })))
        : []),
      colorRow(t('atelier.light'), 'light'),
      contrastEl,
      themeStyle(editing) === 'duo' ? null : (() => {
        const box = h('input', { type: 'checkbox', checked: editing.accents.length > 1 });
        box.addEventListener('change', () => {
          editing.accents = box.checked ? [editing.light, editing.light, editing.light, editing.light] : [];
          render();
          live();
        });
        return h('label', { class: 'at-row at-check' }, box, h('span', { text: t('atelier.multi') }));
      })(),
      ...(editing.accents.length > 1 && themeStyle(editing) !== 'duo' ? [0, 1, 2, 3].map(accentRow) : []),
      themeStyle(editing) === 'duo' ? null : (() => {
        const box = h('input', { type: 'checkbox', checked: editing.gradient.length === 2 });
        box.addEventListener('change', () => {
          editing.gradient = box.checked ? [editing.light, editing.light] : [];
          render();
          live();
        });
        return h('label', { class: 'at-row at-check' }, box, h('span', { text: t('atelier.gradient') }));
      })(),
      ...(editing.gradient.length === 2 && themeStyle(editing) !== 'duo' ? [
        listColorRow('gradient', 0, t('atelier.gradient_from')),
        listColorRow('gradient', 1, t('atelier.gradient_to')),
      ] : []),
      selectRow(t('atelier.pair'), editing.pair || '', [['', t('atelier.pair_none')],
        ...allThemes().filter((x) => x.id !== editing.id).map((x) => [x.id, x.name])], (v) => {
        editing.pair = v || undefined;
      }),
      rangeRow(t('atelier.neon'), 'neon'),
      h('div', { class: 'at-help', text: t('atelier.neon_help') }),
      themeStyle(editing) === 'classic' ? rangeRow(t('atelier.mica'), 'mica') : null,
      rangeRow(t('atelier.grain'), 'grain'),
      h('div', { class: 'at-row' }, h('label', { text: t('atelier.effect') }), effect),
      rangeRow(t('atelier.intensity'), 'effect_intensity')),
    // Boutons hors de la zone qui défile, toujours visibles.
    h('div', { class: 'at-actions' },
        h('button', { class: 'btn btn-s btn-primary', type: 'button', onclick: save }, icon('check', 'ico-s'), t('atelier.save')),
        h('button', { class: 'btn btn-s', type: 'button', onclick: copyDef }, icon('clipboard-copy', 'ico-s'), t('atelier.copy')),
        h('button', { class: 'btn btn-s btn-ghost', type: 'button', onclick: () => {
          editing = { ...editing, id: `${editing.id}-2`, name: `${editing.name} 2` };
          render();
          live();
        } }, icon('plus', 'ico-s'), t('atelier.new'))),
  );
  const body = panel.querySelector('.atelier-body');
  if (body) body.scrollTop = keepScroll;
  live();
}

function definition() {
  const out = {
    id: editing.id,
    name: editing.name,
    dark: editing.dark,
    light: editing.light,
    grain: editing.grain ?? 0,
    mica: editing.mica ?? 60,
    effect: editing.effect || 'none',
    effect_intensity: editing.effect_intensity ?? 0,
  };
  // Champs optionnels, seulement s'ils servent (un thème d'origine reste identique).
  const style = themeStyle(editing);
  if (style !== 'classic') out.style = style;
  if (themeMode(editing) === 'light') out.mode = 'light';
  // Surfaces et textes officiels (thème palette), néon.
  const surf = (editing.surfaces || []).filter((c) => hexToRgb(c));
  if (style === 'palette' && surf.length >= 2) {
    out.surfaces = surf;
    out.dark = surf[0];
  }
  const texts = (editing.texts || []).slice(1).filter((c) => hexToRgb(c));
  if (style === 'palette' && editing.text && texts.length) out.texts = [editing.text, ...texts];
  if (Number(editing.neon) > 0) out.neon = Number(editing.neon);
  if (editing.text) out.text = editing.text;
  const acc = (editing.accents || []).filter((c) => hexToRgb(c));
  if (acc.length > 1) out.accents = acc;
  const grad = (editing.gradient || []).filter((c) => hexToRgb(c));
  if (grad.length === 2) out.gradient = grad;
  if (editing.pair) out.pair = editing.pair;
  return out;
}

async function copyDef(e) {
  // Pas de notification, la coche du bouton suffit.
  if (await copyText(JSON.stringify(definition(), null, 2))) flashCopied(e?.currentTarget);
}

async function save() {
  const def = definition();
  const list = allThemes().filter((x) => x.id !== def.id);
  const idx = allThemes().findIndex((x) => x.id === def.id);
  const next = [...list];
  next.splice(idx >= 0 ? idx : next.length, 0, def);
  try {
    await api.post('/api/themes/save', { themes: next });
    setThemes(next);
    render();
  } catch (err) {
    toastError(err);
  }
}

function makeDraggable(el, handle) {
  let start = null;
  handle.addEventListener('pointerdown', (e) => {
    if (e.target.closest('button')) return;
    const r = el.getBoundingClientRect();
    start = { x: e.clientX, y: e.clientY, left: r.left, top: r.top };
    handle.setPointerCapture(e.pointerId);
  });
  handle.addEventListener('pointermove', (e) => {
    if (!start) return;
    const scale = Number(document.documentElement.style.getPropertyValue('--ui-scale') || 1) || 1;
    el.style.left = `${(start.left + e.clientX - start.x) / scale}px`;
    el.style.top = `${(start.top + e.clientY - start.y) / scale}px`;
    el.style.right = 'auto';
  });
  handle.addEventListener('pointerup', () => { start = null; });
}
