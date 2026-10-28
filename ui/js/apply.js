// « Appliquer », « Lancer le jeu » avec application et contrôle de l'override
// au démarrage. Écrit dans les dossiers du jeu (dossiers de parties, ligne
// d'override). La réconciliation de toutes les parties précède chaque « Appliquer ».

import { partyLabel } from './actions.js';
import { api } from './api.js';
import { openDialog } from './dialog.js';
import { h, icon } from './dom.js';
import { t } from './i18n.js';
import {
  activeVersion, isRunning, partiesSupported, refreshLibrary, refreshState, selectedParty, setParties, store, versionInfo,
} from './state.js';
import { toast, toastError } from './toast.js';

let busy = false;

// La partie sélectionnée doit-elle être appliquée (pas encore appliquée, ou
// modifiée depuis sa dernière application) ?
export function needsApply() {
  return !!(partiesSupported() && store.parties.needs_apply);
}

// Raison pour laquelle « Appliquer » est inactif, ou null.
export function applyBlocker() {
  const v = versionInfo();
  if (!v || !v.has_override) return 'apply.unsupported';
  if (!partiesSupported()) return 'apply.not_ready';
  if (isRunning()) return 'apply.running';
  if (!v.cfg.user_dir || (v.checks.user_dir && v.checks.user_dir.key === 'path.no_gamesettings')) return 'apply.no_gamesettings';
  if (busy) return 'apply.busy';
  return null;
}

function gameName() {
  const v = versionInfo();
  return v ? v.name : '';
}

// Message de fin : nombre de mods, puis mods manquants et fichiers rapatriés.
export function reportApply(res) {
  const name = partyLabel(res.party);
  toast('apply.done', { name, count: res.count }, 'success');
  if (res.missing && res.missing.length) {
    toast('apply.missing', { count: res.missing.length, list: res.missing.slice(0, 6).join(', ') }, 'warn');
  }
  // 0.6 : mods d'un autre disque, sans droits pour les liens symboliques (4.20).
  if (res.blocked && res.blocked.length) {
    toast('apply.blocked', { count: res.blocked.length, list: res.blocked.slice(0, 6).join(', ') }, 'warn');
  }
  const tidy = res.tidy || {};
  if (tidy.updated && tidy.updated.length) toast('apply.updated', { count: tidy.updated.length }, 'info');
  if (tidy.added && tidy.added.length) toast('apply.added', { count: tidy.added.length, name }, 'info');
  if (tidy.unclassified && tidy.unclassified.length) toast('reconcile.unclassified', { count: tidy.unclassified.length }, 'info');
  if ((tidy.set_aside && tidy.set_aside.length) || (tidy.old_versions && tidy.old_versions.length)) {
    toast('apply.set_aside', { count: (tidy.set_aside || []).length + (tidy.old_versions || []).length }, 'warn');
  }
  if (res.party !== '_vide' && res.count === 0) toast('apply.empty_party', { name }, 'warn');
}

export async function applySelected(pid = null) {
  const why = applyBlocker();
  if (why) {
    toast(why, { game: gameName() }, 'warn');
    return null;
  }
  busy = true;
  document.dispatchEvent(new CustomEvent('fsp-apply', { detail: { busy: true } }));
  try {
    const res = await api.post('/api/parties/apply', { version: activeVersion(), id: pid || undefined });
    setParties(res.state);
    reportApply(res);
    refreshState().catch(() => {});
    if (res.tidy && Object.values(res.tidy).some((x) => x.length)) refreshLibrary().catch(() => {});
    return res;
  } catch (err) {
    toastError(err);
    return null;
  } finally {
    busy = false;
    document.dispatchEvent(new CustomEvent('fsp-apply', { detail: { busy: false } }));
  }
}

// « Lancer le jeu » : si la partie sélectionnée n'est pas appliquée (ou pas à
// jour), on propose de l'appliquer d'abord (Q10).
export async function launchGame() {
  const sel = selectedParty();
  let applyFirst = false;
  if (sel && needsApply() && !applyBlocker()) {
    const choice = await askApplyBeforeLaunch(partyLabel(sel.id));
    if (choice === 'cancel') return;
    applyFirst = choice === 'apply';
  }
  try {
    const res = await api.post('/api/game/launch', { version: activeVersion(), apply: applyFirst });
    if (res.applied) {
      reportApply(res.applied);
      refreshState().catch(() => {});
    }
    if (applyFirst) {
      const parties = await api.get(`/api/parties?version=${encodeURIComponent(activeVersion())}`);
      setParties(parties);
    }
    // 0.5 : le lancement réussi n'affiche plus de message ; seul un échec est signalé.
    if (!res.ok) toast(res.key, res.params || {}, 'error');
  } catch (err) {
    toastError(err);
  }
}

function askApplyBeforeLaunch(name) {
  return new Promise((resolve) => {
    let result = 'cancel';
    const done = (r) => {
      result = r;
      dlg.close();
    };
    const body = h('div', { class: 'dlg-body' },
      h('p', { class: 'dlg-text', text: t('launch.apply_text', { name, game: gameName() }) }),
      h('div', { class: 'dlg-actions' },
        h('button', { class: 'btn btn-ghost', type: 'button', text: t('common.cancel'), onclick: () => done('cancel') }),
        h('button', { class: 'btn', type: 'button', text: t('launch.without_apply'), onclick: () => done('launch') }),
        h('button', { class: 'btn btn-primary', type: 'button', autofocus: true, onclick: () => done('apply') },
          icon('check'), h('span', { text: t('launch.apply_and_launch') }))));
    const dlg = openDialog(body, { title: t('launch.apply_title', { name }), cls: 'dlg-launch', onClose: () => resolve(result) });
  });
}

// ---------------------------------------------------------------------------
// Contrôle de l'override (3.5) : le jeu charge un dossier que FS Passion ne
// connaît pas. Une seule fois par dossier et par session.
// ---------------------------------------------------------------------------

const asked = new Set();
let checkOpen = false;

export function maybeCheckOverride() {
  if (!partiesSupported() || checkOpen) return;
  const check = store.parties.override_check;
  if (!check) return;
  const key = `${store.parties.version}|${check.directory}`;
  if (asked.has(key)) return;
  asked.add(key);
  checkOpen = true;
  const vid = store.parties.version;
  const suggest = check.suggest;
  const run = async (action) => {
    dlg.close();
    try {
      const res = await api.post('/api/override/resolve', {
        version: vid, action, directory: check.directory, id: action === 'reapply' ? suggest : undefined,
      });
      if (action === 'reapply') {
        setParties(res.state);
        reportApply(res);
      } else {
        if (action === 'adopt') toast('override.adopted', { path: check.directory }, 'success');
        await refreshState();
        const parties = await api.get(`/api/parties?version=${encodeURIComponent(vid)}`);
        setParties(parties);
        if (action === 'adopt') refreshLibrary().catch(() => {});
      }
    } catch (err) {
      toastError(err);
    }
  };
  const running = isRunning(vid);
  const reapply = h('button', { class: 'btn btn-primary', type: 'button', onclick: () => run('reapply') },
    icon('check'), h('span', { text: t('override.reapply', { name: partyLabel(suggest) }) }));
  const adopt = h('button', { class: 'btn', type: 'button', onclick: () => run('adopt') },
    icon('folder-open'), h('span', { text: t('override.adopt') }));
  if (running) {
    reapply.setAttribute('aria-disabled', 'true');
    adopt.setAttribute('aria-disabled', 'true');
    reapply.onclick = null;
    adopt.onclick = null;
  }
  const body = h('div', { class: 'dlg-body override-dlg' },
    h('p', { class: 'dlg-text', text: t('override.text', { game: gameName() }) }),
    h('div', { class: 'override-path' }, icon('folder'), h('span', { text: check.directory })),
    h('p', { class: 'set-help', text: running ? t('apply.running', { game: gameName() }) : t('override.help') }),
    h('div', { class: 'dlg-actions is-center' },
      h('button', { class: 'btn btn-ghost', type: 'button', text: t('override.ignore'), onclick: () => run('ignore') }),
      adopt, reapply));
  const dlg = openDialog(body, { title: t('override.title'), cls: 'dlg-override', onClose: () => { checkOpen = false; } });
}
