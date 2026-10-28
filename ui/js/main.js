// FS Passion — démarrage de l'interface.

import { initActionBar } from './actionbar.js';
import { addMods, removeMods } from './actions.js';
import { anomaliesOpen, openAnomalies, refreshAnomaliesDialog } from './anomalies.js';
import { maybeCheckOverride } from './apply.js';
import { maybeOfferDemo } from './demo.js';
import { maybeAutoDownloads } from './downloads.js';
import { api, atelierRequested, connectEvents, on, shell } from './api.js';
import { toggleAtelier } from './atelier.js';
import { initDialogs, isDialogOpen } from './dialog.js';
import { initDnd, isDragging } from './dnd.js';
import { h, icon } from './dom.js';
import { buildEdges, mountWindowControls } from './frame.js';
import { initGlow } from './glow.js';
import { initFooter, renderFooter } from './footer.js';
import { initHeader, renderHeader, renderStatus, updatePartyIcon } from './header.js';
import { initHovercard } from './hovercard.js';
import { applyI18n, loadLanguage, onLanguageChange, t } from './i18n.js';
import { applyIcons, focusSearch, initLibrary, rebuild, refreshHeaderOnly, renderLibrary, requestRescan } from './library.js';
import { initReconcile, maybeShowMissing, maybeShowOlder, refreshMissingDialog } from './reconcile.js';
import { initPerf } from './perf.js';
import { initScale } from './scale.js';
import { closeSettings, initSettings, openSettings } from './settings.js';
import { activeList, clearSelection, pruneSelection, selectAll, selectedIds, selectionList, selectionSize } from './selection.js';
import { hidePreview, initSideLists, renderSideLists, setDragOver } from './sidelists.js';
import {
  activeVersion, partiesSupported, refreshLibrary, refreshParties, refreshState, store, subscribe, userParty,
} from './state.js';
import { allThemes, applyTheme, initMetal, loadThemes, setOptions } from './theme.js';
import { initToasts, toast, toastError } from './toast.js';
import { initTooltips } from './tooltip.js';
import { openStopUsing } from './stopuse.js';
import { openNotice, openWelcome } from './welcome.js';
import { initTour, isTourOpen, maybeShowTourHint, startTour } from './tour.js';

const app = document.getElementById('app');
let started = false;
let anomaliesAuto = false;
let lastVersion = null;

function themeFromSettings() {
  const id = store.app.settings.theme;
  return allThemes().find((x) => x.id === id) || allThemes()[0];
}

function applyOptions() {
  const s = store.app.settings;
  setOptions({ lightEffects: s.light_effects !== false, reduceMotion: s.reduce_motion, loop: !!s.theme_loop });
}

function renderAll() {
  renderHeader();
  renderLibrary();
  renderSideLists();
  renderFooter();
  applyI18n(app);
}

// Fenêtre « FS Passion est fermé » (navigateur, après « Quitter »).
function showClosed() {
  app.replaceChildren(h('div', { class: 'grid-empty' }, icon('log-out'), h('h3', { text: t('app.closed') }), h('p', { text: t('app.closed_help') })));
}

async function quit() {
  try {
    await api.post('/api/app/quit');
  } catch {
    /* déjà fermé */
  }
  if (shell === 'browser') setTimeout(showClosed, 300);
}

function maybeOpenAnomalies() {
  const lib = store.library;
  if (!lib || lib.status !== 'ready' || anomaliesAuto || anomaliesOpen() || isDialogOpen() || isTourOpen()) return;
  if (lib.anomalies.some((a) => a.new)) {
    anomaliesAuto = true;
    openAnomalies();
  }
}

// Fenêtres du démarrage, l'une après l'autre (chacune seulement quand aucune
// autre n'est ouverte) : anomalies nouvelles, override inconnu, démonstration,
// mods absents des dossiers de mods (0.4), nouveaux téléchargements (0.4).
let bootDone = false; // bienvenue et notice déjà proposées

// 0.9.0 : en dernier, l'ampoule du tour guidé est mise en évidence une fois
// (premier lancement, après la bienvenue et la notice). Pendant le tour,
// aucune de ces fenêtres ne s'ouvre ; elles reprennent à sa fermeture.
function nextStartupStep() {
  if (!started || !bootDone || isTourOpen()) return;
  maybeOpenAnomalies();
  if (!isDialogOpen()) maybeCheckOverride();
  if (!isDialogOpen()) maybeOfferDemo();
  if (!isDialogOpen()) maybeShowMissing();
  if (!isDialogOpen()) maybeShowOlder();
  if (!isDialogOpen()) maybeAutoDownloads();
  if (!isDialogOpen()) maybeShowTourHint();
}

let libTimer = 0;
function scheduleLibraryRefresh() {
  clearTimeout(libTimer);
  libTimer = setTimeout(() => refreshLibrary().catch(() => {}), 120);
}

// Glisser-déposer (4.6) : ce que chaque liste accepte, et ce que fait le dépôt.
// `copy` : Ctrl maintenu (0.4, correction). Entre les listes 2 et 3, la copie
// ajoute le mod à l'autre liste sans le retirer de la sienne ; vers la liste 1,
// il n'y a rien à copier.
function dropAccepts(src, dst, copy = false) {
  if (!partiesSupported()) return false;
  if (dst === 'l2') return (src === 'l1' || src === 'l3') && !!userParty();
  if (dst === 'l3') return src === 'l1' || src === 'l2';
  if (dst === 'l1') return !copy && (src === 'l2' || src === 'l3');
  return false;
}

function dropMods(src, dst, ids, copy = false) {
  if (src === 'l1' && dst === 'l2') addMods('party', ids);
  else if (src === 'l1' && dst === 'l3') addMods('common', ids);
  else if (src === 'l2' && dst === 'l3') addMods('common', ids, { source: copy ? null : 'party' });
  else if (src === 'l3' && dst === 'l2') addMods('party', ids, { source: copy ? null : 'common' });
  else if (src === 'l2' && dst === 'l1') removeMods('party', ids);
  else if (src === 'l3' && dst === 'l1') removeMods('common', ids);
}

// Raccourcis de la sélection (4.6) : Échap, Ctrl+A, Suppr.
function selectionKeys(e) {
  if (isDialogOpen() || isDragging()) return;
  const inField = e.target.closest && e.target.closest('input, textarea, select');
  if (e.key === 'Escape' && selectionSize() && !inField) {
    e.preventDefault();
    clearSelection();
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a' && !inField) {
    e.preventDefault();
    selectAll(activeList());
  } else if (e.key === 'Delete' && !inField && (selectionList() === 'l2' || selectionList() === 'l3')) {
    e.preventDefault();
    removeMods(selectionList() === 'l2' ? 'party' : 'common', selectedIds());
  }
}

async function start() {
  initScale(app);
  initTooltips(document.getElementById('tooltip'));
  initToasts(document.getElementById('toasts'));
  initDialogs(document.getElementById('layer'));
  initTour(app);
  initHovercard(document.getElementById('hovercard'));
  initMetal(document.getElementById('metal-light'));
  initGlow(app);

  await loadThemes();
  try {
    await refreshState();
  } catch {
    app.classList.remove('is-loading');
    showClosed();
    return;
  }
  await loadLanguage(store.app.settings.language);
  applyTheme(themeFromSettings());
  applyOptions();

  initHeader(document.getElementById('topbar'), { onSettings: () => openSettings() });
  initLibrary(document.getElementById('list1'), {
    onAnomalies: () => openAnomalies(),
    onSettings: () => openSettings('paths'),
  });
  initSideLists(document.getElementById('side'), document.getElementById('preview'));
  initActionBar(document.getElementById('actionbar'), app);
  initDnd(app, { accepts: dropAccepts, drop: dropMods, over: setDragOver });
  initFooter(document.getElementById('footer'), { onQuit: quit });
  initSettings({
    onNotice: () => openNotice(),
    onAnomalies: () => openAnomalies(),
    onAtelier: () => toggleAtelier(app),
    // 0.9.0 : « Visite guidée » (Paramètres → Aide) ferme les paramètres d'abord.
    onTour: () => {
      closeSettings();
      setTimeout(() => startTour(), 300);
    },
  });
  buildEdges(app);
  mountWindowControls(app, document.getElementById('topbar'));
  lastVersion = activeVersion();
  renderAll();
  app.classList.remove('is-loading');
  started = true;
  // Mesures pour le diagnostic (0.7.0) : affichage prêt, fluidité du défilement.
  initPerf();

  subscribe('state', () => {
    renderHeader();
    renderSideLists();
    renderFooter();
    applyOptions();
    if (activeVersion() !== lastVersion) {
      lastVersion = activeVersion();
      anomaliesAuto = false;
      clearSelection();
      hidePreview();
      renderLibrary();
    } else {
      refreshHeaderOnly();
    }
    // Chemins modifiés, version changée… : les parties peuvent changer aussi.
    refreshParties().catch(() => {});
  });
  subscribe('library', () => {
    updatePartyIcon();
    rebuild();
    renderSideLists();
    renderStatus();
    pruneSelection();
    refreshAnomaliesDialog();
    refreshMissingDialog();
    maybeOpenAnomalies();
    nextStartupStep();
  });
  subscribe('parties', (parties) => {
    renderHeader();
    rebuild();
    renderSideLists();
    pruneSelection();
    if (parties && parties.notice) toast(parties.notice.key, parties.notice.params || {}, parties.notice.level || 'warn');
    // Override vers un dossier inconnu : « Adopter », « Réappliquer » ou
    // « Ne rien faire » (3.5), quand aucune autre fenêtre n'est ouverte.
    if (!isDialogOpen() && !isTourOpen()) maybeCheckOverride();
  });
  // Pendant « Appliquer », le bouton est inactif.
  document.addEventListener('fsp-apply', () => renderHeader());
  onLanguageChange(() => {
    if (started) renderAll();
  });
  // Une fenêtre se ferme (bienvenue, notice…) : les anomalies nouvelles
  // peuvent maintenant s'afficher.
  document.addEventListener('fsp-dialog-closed', () => setTimeout(nextStartupStep, 350));

  initReconcile();
  connectEvents();
  // 0.9.1 : réveil après la dormance (fenêtre cachée ou réduite pendant le
  // jeu) : les événements de la veille ont pu se perdre, tout est relu.
  document.addEventListener('fsp-wake', () => {
    connectEvents();
    refreshState().catch(() => {});
    refreshParties().catch(() => {});
    scheduleLibraryRefresh();
  });
  on('library', (ev) => {
    if (ev.version === activeVersion()) scheduleLibraryRefresh();
  });
  on('icons', (ev) => {
    if (ev.version !== activeVersion() || !store.library) return;
    store.library.icons_pending = ev.pending;
    applyIcons(ev.items);
  });
  on('game', async (ev) => {
    store.app.running = ev.running;
    renderStatus();
    renderFooter();
    await refreshState().catch(() => {});
  });
  on('detect', (ev) => {
    if (!ev.running) {
      refreshState().then(() => {
        if (!isDialogOpen()) maybeOfferDemo();
        return refreshLibrary();
      }).catch(() => {});
    }
  });
  on('state', () => refreshState().catch(() => {}));
  // Une autre fenêtre (navigateur ou application) a modifié les parties.
  on('parties', (ev) => {
    if (ev.version === activeVersion()) refreshParties().catch(() => {});
  });
  on('backup', (ev) => {
    const v = store.app.versions.find((x) => x.id === ev.version);
    toast('backup.created', { game: v ? v.name : ev.version }, 'info');
  });
  on('toast', (ev) => toast(ev.key, ev.params || {}, ev.level || 'info'));
  let downTimer = 0;
  on('connection', (ev) => {
    clearTimeout(downTimer);
    if (!ev.up) downTimer = setTimeout(showClosed, 4000);
  });

  // Reprise du focus : nouveau scan rapide (liste, tailles, dates), 4.4.
  let lastFocusScan = 0;
  window.addEventListener('focus', () => {
    const now = Date.now();
    if (now - lastFocusScan < 3000) return;
    lastFocusScan = now;
    requestRescan(true);
  });

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f' && !isDialogOpen()) {
      e.preventDefault();
      focusSearch();
      return;
    }
    selectionKeys(e);
  });
  // Pas de menu contextuel du navigateur dans l'application.
  if (shell === 'window') document.addEventListener('contextmenu', (e) => e.preventDefault());

  await Promise.all([refreshLibrary().catch(toastError), refreshParties().catch(toastError)]);

  // Désinstallation (4.18, 0.7.0) : lancé par le désinstalleur Windows avec
  // --uninstall, FS Passion ouvre directement « Ne plus utiliser FS Passion ».
  if (store.app.app.uninstall_mode) {
    openStopUsing({ uninstall: true });
    return;
  }
  // Premier lancement : bienvenue (langue), puis notice. Ensuite : notice à
  // chaque démarrage tant que la case reste cochée (4.15).
  if (!store.app.settings.welcome_done) {
    openWelcome(() => openNotice());
  } else if (store.app.settings.show_notice_at_start !== false) {
    openNotice();
  }
  if (atelierRequested && store.app.app.dev) toggleAtelier(app);
  bootDone = true;
  nextStartupStep();
}

start().catch((err) => {
  console.error(err);
  app.classList.remove('is-loading');
  toastError(err);
});
