// Thèmes, grain et reflet métallique.
// Un thème = au moins deux couleurs : le fond (Mica, champ « dark ») et
// l'accent (champ « light »). Les surfaces sont des voiles neutres posés sur le
// fond, l'accent colore contours, logos et icônes. Changer de thème est
// instantané.
//
// Champs d'un thème :
// - « mode » : « dark » (défaut) ou « light » : interface sombre ou claire ;
// - « text » : couleur des textes (défaut : blanc en sombre, presque noir en clair) ;
// - « accents » : jusqu'à 4 couleurs (orange, vert, bleu, violet pour Catppuccin
//   et Nord). Chaque zone de l'interface prend la sienne (--c1 à --c4) ;
// - « gradient » : 2 couleurs, pour quelques textes importants et
//   l'animation des boutons « Appliquer » et « Lancer le jeu ». Icônes, images
//   et interrupteurs restent en couleurs pleines ;
// - « pair » : le thème jumeau de l'autre mode (bouton soleil/lune).
// Les accents trop peu contrastés sur le fond sont assombris (mode clair) ou
// éclaircis (mode sombre) automatiquement : la teinte reste, la lisibilité aussi.
//
// Champs complémentaires :
// - « style » : « duo » (thème bicolore : la couleur sombre partout, la couleur
//   dominante dans tous les textes et les icônes, des contours fins à la place
//   des nuances de fond, une lueur qui court le long des contours) ou
//   « palette » (thème inspiré d'un thème populaire : Catppuccin, Nord…) ;
// - « surfaces » (palette) : 2 à 4 couleurs officielles du thème, du plus
//   extérieur au plus intérieur : fenêtre, listes et fenêtres internes,
//   sections, sous-sections. Elles remplacent les voiles calculés ;
// - « texts » : 1 à 4 couleurs de texte officielles (principal, secondaire…) ;
// - « neon » : 0 à 100, effet néon (lueur des titres, icônes et contours, comme
//   Synthwave '84) ; 0 = sans effet.

const root = document.documentElement;
let themes = [];
let current = null; // thème appliqué (choisi ou en aperçu)
let chosenId = 'gruvbox-light'; // Thème par défaut
let loopTimer = 0;
let options = { lightEffects: true, reduceMotion: null, loop: false };

export async function loadThemes() {
  try {
    const res = await fetch('/themes.json', { cache: 'no-store' });
    const data = await res.json();
    themes = Array.isArray(data.themes) ? data.themes : [];
  } catch {
    themes = [];
  }
  if (!themes.length) {
    themes = [{ id: 'lime', name: 'Lime', style: 'duo', dark: '#1C1C1A', light: '#9ED86F', grain: 9, mica: 23, effect: 'none', effect_intensity: 0 }];
  }
  return themes;
}

export function allThemes() {
  return themes;
}

export function setThemes(list) {
  themes = list;
}

export function chosenTheme() {
  return themes.find((t) => t.id === chosenId) || themes[0];
}

// ---------------------------------------------------------------------------
// Couleurs et contraste (WCAG)
// ---------------------------------------------------------------------------

export function hexToRgb(hex) {
  let s = String(hex || '').trim().replace('#', '');
  if (s.length === 3) s = s.split('').map((c) => c + c).join('');
  if (!/^[0-9a-fA-F]{6}$/.test(s)) return null;
  return [0, 2, 4].map((i) => parseInt(s.slice(i, i + 2), 16));
}

function rgbToHex([r, g, b]) {
  return '#' + [r, g, b].map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0')).join('').toUpperCase();
}

function luminance(rgb) {
  const c = rgb.map((v) => {
    const x = v / 255;
    return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}

export function contrast(a, b) {
  const ra = hexToRgb(a);
  const rb = hexToRgb(b);
  if (!ra || !rb) return 1;
  const la = luminance(ra);
  const lb = luminance(rb);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

// Variante d'une couleur qui atteint le contraste `target` sur le fond :
// éclaircie sur un fond sombre, assombrie sur un fond clair. Les petits textes
// visent 4,5:1 (cas du Cuivre), les icônes et grands textes 3:1.
export function readableColor(color, bg, target = 4.5) {
  const base = hexToRgb(color);
  const back = hexToRgb(bg);
  if (!base || !back) return color;
  if (contrast(color, bg) >= target) return color;
  // On va vers le noir si la couleur est plus sombre que le fond, vers
  // le blanc sinon (un fond clair grisé comme Catppuccin Latte, luminance 0,35,
  // était traité comme un fond sombre).
  const toward = luminance(base) < luminance(back) ? 0 : 255;
  for (let k = 0.04; k <= 1; k += 0.02) {
    const mixed = rgbToHex(base.map((v) => v + (toward - v) * k));
    if (contrast(mixed, bg) >= target) return mixed;
  }
  return toward ? '#FFFFFF' : '#000000';
}

export function smallTextColor(light, dark) {
  return readableColor(light, dark, 4.5);
}

// Dégradé bicolore d'un thème : [départ, arrivée], ou [] s'il n'en a pas.
export function themeGradient(theme) {
  const g = Array.isArray(theme.gradient) ? theme.gradient.filter((c) => hexToRgb(c)) : [];
  return g.length === 2 ? g : [];
}

export function themeMode(theme) {
  return theme && theme.mode === 'light' ? 'light' : 'dark';
}

// Style d'un thème : « duo » (bicolore), « palette », ou « classic »
// (ancien thème sans style : voiles calculés, comme avant).
export function themeStyle(theme) {
  return theme && (theme.style === 'duo' || theme.style === 'palette') ? theme.style : 'classic';
}

// Surfaces officielles d'un thème : 0 à 4 couleurs valides.
export function themeSurfaces(theme) {
  const list = Array.isArray(theme && theme.surfaces) ? theme.surfaces.filter((c) => hexToRgb(c)) : [];
  return list.slice(0, 4);
}

// Couleurs de texte officielles : 0 à 4 couleurs valides.
export function themeTexts(theme) {
  const list = Array.isArray(theme && theme.texts) ? theme.texts.filter((c) => hexToRgb(c)) : [];
  return list.slice(0, 4);
}

// Couleur du fond de la fenêtre : la première surface, sinon « dark ».
export function themeWindow(theme) {
  const surf = themeSurfaces(theme);
  return surf.length ? surf[0] : theme.dark;
}

// Pastille d'un thème (Paramètres, atelier) : fond en haut à gauche, couleur
// dominante (ou roue des couleurs d'accent) en bas à droite. Pour un thème
// palette, le fond montré est celui des listes.
export function paintSwatch(dot, th) {
  const surf = themeSurfaces(th);
  dot.style.setProperty('--sw-dark', surf[1] || themeWindow(th));
  dot.style.setProperty('--sw-light', th.light);
  const acc = themeStyle(th) === 'duo' ? [th.light] : themeAccents(th);
  dot.classList.toggle('is-multi', acc.length > 1);
  if (acc.length > 1) dot.style.setProperty('--sw-accents', [...acc, acc[0]].join(', '));
  dot.classList.toggle('is-duo', themeStyle(th) === 'duo');
  dot.classList.toggle('is-neon', Number(th.neon) > 0);
}

// Couleurs d'accent d'un thème : ses « accents », sinon l'accent seul.
export function themeAccents(theme) {
  const list = Array.isArray(theme.accents) ? theme.accents.filter((c) => hexToRgb(c)) : [];
  return list.length >= 2 ? list.slice(0, 4) : [theme.light];
}

// ---------------------------------------------------------------------------
// Grain : une petite image de bruit, calculée une fois et répétée.
// ---------------------------------------------------------------------------

const grainCache = new Map();

function grainImage(intensity) {
  const level = Math.max(0, Math.min(100, Math.round(intensity || 0)));
  if (level === 0) return 'none';
  if (grainCache.has(level)) return grainCache.get(level);
  const size = 160;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  const img = ctx.createImageData(size, size);
  const k = (level / 100) * 0.2;
  let seed = 1234567;
  const rand = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
  for (let i = 0; i < size * size; i++) {
    const n = rand() * 2 - 1;
    const v = n > 0 ? 255 : 0;
    img.data[i * 4] = v;
    img.data[i * 4 + 1] = v;
    img.data[i * 4 + 2] = v;
    img.data[i * 4 + 3] = Math.round(Math.abs(n) ** 1.6 * k * 255);
  }
  ctx.putImageData(img, 0, 0);
  const url = `url("${canvas.toDataURL('image/png')}")`;
  grainCache.set(level, url);
  return url;
}

// ---------------------------------------------------------------------------
// Application d'un thème
// ---------------------------------------------------------------------------

const TEXT_TARGETS = [7, 4.5, 3, 2];
const TEXT_ALPHA = [1, 0.786, 0.545, 0.362];

export function applyTheme(theme, { preview = false } = {}) {
  if (!theme) return;
  current = theme;
  if (!preview) chosenId = theme.id;
  const style = themeStyle(theme);
  const surf = themeSurfaces(theme);
  const dark = themeWindow(theme);
  const mode = themeMode(theme);
  // Fond de référence pour la lisibilité : la surface des listes, où se trouve
  // l'essentiel des textes (le fond de la fenêtre pour un thème sans surfaces).
  const ref = surf[1] || dark;
  const light = readableColor(readableColor(theme.light, ref, 3), dark, 3);
  root.style.setProperty('--bg', dark);
  root.style.setProperty('--fg', light);
  root.style.setProperty('--fg-text', smallTextColor(light, ref));
  root.dataset.mode = mode;
  root.dataset.style = style;
  // Surfaces officielles : fenêtre, listes, sections, sous-sections.
  if (surf.length >= 2 && style !== 'duo') {
    const [s0, s1, s2 = s1, s3 = s2] = surf;
    root.style.setProperty('--surf-window', s0);
    root.style.setProperty('--surf-list', s1);
    root.style.setProperty('--surf-section', s2);
    root.style.setProperty('--surf-sub', s3);
    root.dataset.surfaces = '1';
  } else {
    for (const k of ['--surf-window', '--surf-list', '--surf-section', '--surf-sub']) root.style.removeProperty(k);
    delete root.dataset.surfaces;
  }
  // Textes : bicolore = la couleur dominante partout ; sinon la couleur des
  // textes du thème et ses couleurs secondaires officielles.
  const fallback = mode === 'light' ? '#1B1B1F' : '#FFFFFF';
  const text = style === 'duo' ? light : (hexToRgb(theme.text) ? theme.text : fallback);
  const base = readableColor(readableColor(text, ref, 7), dark, 4.5);
  root.style.setProperty('--text-base', base);
  const texts = style === 'duo' ? [] : themeTexts(theme);
  for (let i = 0; i < 4; i++) {
    const name = `--text-${i + 1}`;
    if (i === 0 && texts.length) root.style.setProperty(name, base);
    else if (texts[i]) root.style.setProperty(name, readableColor(texts[i], ref, TEXT_TARGETS[i]));
    else if (texts.length) root.style.setProperty(name, `color-mix(in srgb, ${base} ${TEXT_ALPHA[i] * 100}%, transparent)`);
    else root.style.removeProperty(name);
  }
  // Plusieurs couleurs d'accent : --c1 à --c4 (icônes, 3:1) et leurs variantes
  // pour les petits textes (4,5:1), puis le dégradé. Un thème bicolore n'a
  // qu'une couleur.
  const accents = (style === 'duo' ? [theme.light] : themeAccents(theme)).map((c) => readableColor(readableColor(c, ref, 3), dark, 3));
  const four = [0, 1, 2, 3].map((i) => accents[i % accents.length]);
  four.forEach((c, i) => {
    root.style.setProperty(`--c${i + 1}`, c);
    root.style.setProperty(`--c${i + 1}-text`, smallTextColor(c, ref));
  });
  if (accents.length > 1) root.dataset.multi = '1';
  else delete root.dataset.multi;
  // Dégradé bicolore, lisible sur le fond (3:1 : grands textes).
  const grad = style === 'duo' ? [] : themeGradient(theme).map((c) => readableColor(readableColor(c, ref, 3), dark, 3));
  if (grad.length === 2) root.dataset.grad = '1';
  else delete root.dataset.grad;
  const [ga, gb] = grad.length === 2 ? grad : [light, light];
  root.style.setProperty('--grad-a', ga);
  root.style.setProperty('--grad-b', gb);
  root.style.setProperty('--accent-grad', `linear-gradient(100deg, ${ga}, ${gb})`);
  root.style.setProperty('--grain', grainImage(theme.grain));
  // Intensité des lueurs du fond Mica ; 60 si le thème ne la donne pas.
  root.style.setProperty('--mica', String(Math.max(0, Math.min(100, theme.mica ?? 60)) / 100));
  root.style.setProperty('--metal-strength', String((theme.effect_intensity ?? 60) / 100));
  // Effet néon : intensité de 0 à 1.
  const neon = Math.max(0, Math.min(100, Number(theme.neon) || 0));
  root.style.setProperty('--neon', String(neon / 100));
  if (neon > 0) root.dataset.neon = '1';
  else delete root.dataset.neon;
  root.dataset.theme = theme.id;
  root.dataset.effect = theme.effect || 'none';
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark);
  root.style.colorScheme = mode;
  updateMetal();
  updateFx();
}

export function previewTheme(theme) {
  applyTheme(theme, { preview: true });
}

export function endPreview() {
  applyTheme(chosenTheme());
}

// Bouton soleil/lune : le thème jumeau de l'autre mode (« pair »),
// sinon le premier thème de l'autre mode, sinon rien (null).
export function oppositeTheme(theme = chosenTheme()) {
  if (!theme) return null;
  const want = themeMode(theme) === 'light' ? 'dark' : 'light';
  const pair = themes.find((t) => t.id === theme.pair && themeMode(t) === want);
  if (pair) return pair;
  const back = themes.find((t) => t.pair === theme.id && themeMode(t) === want);
  return back || themes.find((t) => themeMode(t) === want) || null;
}

// ---------------------------------------------------------------------------
// Options : effets de lumière, animations réduites, thème Loop
// ---------------------------------------------------------------------------

const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

export function reduceMotionActive() {
  return options.reduceMotion === null || options.reduceMotion === undefined
    ? motionQuery.matches
    : !!options.reduceMotion;
}

export function setOptions(next) {
  options = { ...options, ...next };
  root.classList.toggle('reduce-motion', reduceMotionActive());
  updateMetal();
  updateFx();
  updateLoop();
}

// Effets de lumière des thèmes : lueurs qui courent le long des
// contours (thèmes bicolores) et effet néon. Coupés avec « Effets de
// lumière » ; les lueurs animées s'arrêtent aussi avec « Réduire les
// animations » et quand la fenêtre n'est pas au premier plan.
function updateFx() {
  root.classList.toggle('fx-off', !options.lightEffects);
  root.classList.toggle('fx-still', !options.lightEffects || reduceMotionActive());
}

motionQuery.addEventListener?.('change', () => setOptions({}));

function updateLoop() {
  clearInterval(loopTimer);
  if (!options.loop || reduceMotionActive() || themes.length < 2) return;
  loopTimer = setInterval(() => {
    // Thème Loop : seulement les thèmes du même mode (clair ou sombre).
    const mode = themeMode(chosenTheme());
    const same = themes.filter((t) => themeMode(t) === mode);
    if (same.length < 2) return;
    const idx = same.findIndex((t) => t.id === chosenId);
    const next = same[(idx + 1) % same.length];
    root.classList.add('theme-transition');
    applyTheme(next);
    setTimeout(() => root.classList.remove('theme-transition'), 2100);
  }, 60000);
}

// Reflet métallique : une lumière douce qui suit la souris et éclaire les
// éléments cuivrés (mélange « color-dodge » : le fond sombre reste presque
// intact, le cuivre s'illumine). La lumière est déplacée par une
// transformation : rien n'est redessiné, seul l'assemblage final change.
let metalEl = null;
let metalOn = false;
let raf = 0;
let mx = -9999;
let my = -9999;

export function initMetal(el) {
  metalEl = el;
  window.addEventListener('pointermove', (e) => {
    mx = e.clientX;
    my = e.clientY;
    if (metalOn && !raf) raf = requestAnimationFrame(moveMetal);
  }, { passive: true });
  window.addEventListener('blur', () => {
    if (metalEl) metalEl.classList.remove('on');
    root.classList.add('is-idle');
  });
  window.addEventListener('focus', () => {
    updateMetal();
    root.classList.remove('is-idle');
  });
  document.documentElement.addEventListener('pointerleave', () => metalEl && metalEl.classList.remove('lit'));
  document.documentElement.addEventListener('pointerenter', () => metalEl && metalOn && metalEl.classList.add('lit'));
  updateMetal();
}

function moveMetal() {
  raf = 0;
  if (!metalEl) return;
  const scale = Number(root.style.getPropertyValue('--ui-scale') || 1) || 1;
  const x = mx / scale;
  const y = my / scale;
  metalEl.style.transform = `translate3d(${x}px, ${y}px, 0)`;
  metalEl.classList.add('lit');
}

function updateMetal() {
  const want = !!(current && current.effect === 'metal' && themeMode(current) === 'dark' && options.lightEffects && !reduceMotionActive());
  metalOn = want && document.hasFocus();
  if (metalEl) metalEl.classList.toggle('on', metalOn);
}
