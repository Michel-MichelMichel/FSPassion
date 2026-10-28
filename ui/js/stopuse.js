// Ne plus utiliser FS Passion (4.18) — version 0.7.0.
// 1. invitation à exporter la configuration d'abord (bouton sur place) ;
// 2. ce qui va se passer, version par version ;
// 3. cases à cocher : supprimer aussi les parties, caches, réglages, journaux,
//    langues personnelles (aucune cochée par défaut) ;
// 4. confirmation explicite, puis bilan et fermeture de FS Passion.
// Le désinstalleur Windows (0.8) ouvre directement cette fenêtre (--uninstall).

import { api, shell } from './api.js';
import { exportConfig } from './backup.js';
import { openDialog } from './dialog.js';
import { h, icon } from './dom.js';
import { t } from './i18n.js';
import { store } from './state.js';
import { toastError } from './toast.js';

const OPTION_KEYS = ['parties', 'caches', 'settings', 'logs', 'langs'];
let dlg = null;

function closedPage() {
  const app = document.getElementById('app');
  app.replaceChildren(h('div', { class: 'grid-empty' }, icon('log-out'),
    h('h3', { text: t('stop.closed') }), h('p', { text: t('app.closed_help') })));
}

async function quitApp(uninstaller = false) {
  try {
    if (store.app && store.app.app.stopped) await api.post('/api/stop/quit', { uninstaller });
    else await api.post('/api/app/quit');
  } catch {
    /* déjà fermé */
  }
  if (shell === 'browser') setTimeout(closedPage, 300);
}

function overrideText(v) {
  if (v.override === 'restore') return t('stop.plan.restore', { dir: v.directory || '—' });
  if (v.override === 'deactivate') return t('stop.plan.deactivate');
  if (v.override === 'missing') return t('stop.plan.missing');
  return t('stop.plan.none');
}

function keptText(kept) {
  return kept.map((k) => t('stop.plan.kept', { name: k.name, count: k.files })).join(' ');
}

export async function openStopUsing({ uninstall = false } = {}) {
  if (dlg && !dlg.closed) return;
  let prev;
  try {
    prev = await api.get('/api/stop/preview');
  } catch (err) {
    toastError(err);
    return;
  }
  const checks = new Map();
  const options = h('div', { class: 'stop-options' },
    h('div', { class: 'set-group-title', text: t('stop.options.title') }),
    ...OPTION_KEYS.map((k) => {
      const c = h('input', { type: 'checkbox' });
      checks.set(k, c);
      return h('label', { class: 'check' }, c, t(`stop.options.${k}`));
    }));
  const understand = h('input', { type: 'checkbox' });
  const ok = h('button', { class: 'btn btn-danger', type: 'button', disabled: true },
    icon('log-out'), h('span', { text: t('settings.stop.button') }));
  const cancel = h('button', { class: 'btn btn-ghost', type: 'button', text: t('common.cancel') });
  const running = prev.running.length > 0;
  understand.addEventListener('change', () => { ok.disabled = !understand.checked || running; });

  const rows = prev.versions.map((v) => h('li', { class: 'stop-ver' },
    h('div', { class: 'stop-ver-name', text: v.name }),
    h('div', { class: 'set-help', text: overrideText(v) }),
    v.folders ? h('div', { class: 'set-help', text: t('stop.plan.folders', { count: v.folders }) }) : null,
    v.kept && v.kept.length ? h('div', { class: 'set-help', text: keptText(v.kept) }) : null));

  const body = h('div', { class: 'dlg-body stop-dlg' },
    h('div', { class: 'stop-export' },
      h('p', { text: t('stop.export_first') }),
      h('button', { class: 'btn', type: 'button', onclick: () => exportConfig() }, icon('file-up'), t('settings.backup.export'))),
    h('p', { text: t('stop.intro') }),
    rows.length ? h('ul', { class: 'stop-vers' }, rows) : h('p', { class: 'set-help', text: t('stop.no_version') }),
    h('p', { class: 'set-help', text: t('stop.mods_safe') }),
    prev.admin_flag ? h('p', { class: 'set-help', text: t('stop.admin_flag') }) : null,
    options,
    running ? h('div', { class: 'alert-box', text: t('stop.running', { game: prev.running.join(', ') }) }) : null,
    h('label', { class: 'check stop-confirm' }, understand, t('stop.understand')),
    h('div', { class: 'dlg-actions' }, cancel, ok));

  dlg = openDialog(body, {
    title: t('settings.stop.title'),
    cls: 'dlg-stop',
    dismissible: !uninstall,
    onClose: () => { dlg = null; },
  });
  cancel.addEventListener('click', () => {
    dlg.close();
    // Désinstallation : annuler ferme FS Passion, le désinstalleur continue.
    if (uninstall) quitApp(false);
  });
  ok.addEventListener('click', async () => {
    ok.disabled = true;
    cancel.disabled = true;
    const chosen = OPTION_KEYS.filter((k) => checks.get(k).checked);
    try {
      const res = await api.post('/api/stop', { options: chosen, confirm: true });
      if (store.app) store.app.app.stopped = true;
      dlg.close();
      showDone(res);
    } catch (err) {
      ok.disabled = false;
      cancel.disabled = false;
      toastError(err);
    }
  });
}

function showDone(res) {
  const rows = res.versions.map((v) => h('li', {},
    h('strong', { text: v.name }), ' : ',
    v.error ? t(`stop.done.error.${v.error === 'stop.folders_failed' ? 'folders' : 'override'}`)
      : t('stop.done.version', { count: v.folders || 0 }),
    v.set_aside && v.set_aside.length ? h('div', { class: 'set-help', text: t('stop.done.set_aside', { count: v.set_aside.length }) }) : null,
    v.kept && v.kept.length ? h('div', { class: 'set-help', text: keptText(v.kept) }) : null));
  const uninstaller = res.uninstaller ? h('input', { type: 'checkbox', checked: true }) : null;
  const close = h('button', { class: 'btn btn-primary', type: 'button', autofocus: true },
    icon('log-out'), h('span', { text: t('stop.done.close') }));
  const body = h('div', { class: 'dlg-body stop-dlg' },
    h('p', { text: t(res.errors ? 'stop.done.partial' : 'stop.done.text') }),
    rows.length ? h('ul', { class: 'stop-vers' }, rows) : null,
    h('p', { class: 'set-help', text: t('stop.mods_safe') }),
    uninstaller ? h('label', { class: 'check' }, uninstaller, t('stop.done.uninstaller')) : null,
    h('div', { class: 'dlg-actions' }, close));
  // Plus de retour possible : FS Passion se ferme.
  const done = openDialog(body, { title: t('stop.done.title'), cls: 'dlg-stop', dismissible: false });
  close.addEventListener('click', () => {
    close.disabled = true;
    done.close();
    quitApp(!!(uninstaller && uninstaller.checked));
  });
}
