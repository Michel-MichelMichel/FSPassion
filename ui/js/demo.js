// Mode démonstration (14.2) : essayer FS Passion sans le jeu, avec de faux mods.

import { api } from './api.js';
import { openDialog } from './dialog.js';
import { h, icon } from './dom.js';
import { t } from './i18n.js';
import { refreshLibrary, refreshParties, refreshState, store } from './state.js';
import { toast, toastError } from './toast.js';

export function isDemo() {
  return !!(store.app && store.app.demo && store.app.demo.active);
}

export function demoAvailable() {
  return !!(store.app && store.app.demo && store.app.demo.available);
}

async function reload() {
  store.library = null;
  store.parties = null;
  await refreshState();
  await Promise.all([refreshLibrary(), refreshParties()]);
}

export async function startDemo() {
  const wait = openDialog(h('div', { class: 'dlg-body demo-wait' },
    icon('loader-circle', 'ico-l spin'), h('p', { class: 'dlg-text', text: t('demo.installing') })),
  { title: t('demo.title'), cls: 'dlg-s', dismissible: false });
  try {
    await api.post('/api/demo', { action: 'start' });
    wait.close();
    await reload();
    toast('demo.started', {}, 'success');
  } catch (err) {
    wait.close();
    toastError(err);
  }
}

export function stopDemo() {
  const body = h('div', { class: 'dlg-body' },
    h('p', { class: 'dlg-text', text: t('demo.stop_text') }),
    h('div', { class: 'dlg-actions' },
      h('button', { class: 'btn btn-ghost', type: 'button', text: t('common.cancel'), onclick: () => dlg.close() }),
      h('button', { class: 'btn btn-danger', type: 'button', autofocus: true, onclick: async () => {
        dlg.close();
        try {
          await api.post('/api/demo', { action: 'stop' });
          await reload();
          toast('demo.stopped', {}, 'success');
        } catch (err) {
          toastError(err);
        }
      } }, icon('log-out'), h('span', { text: t('demo.stop_ok') }))));
  const dlg = openDialog(body, { title: t('demo.stop_title'), cls: 'dlg-s' });
}

// Repère dans l'en-tête, à côté du logo : « Démonstration », et « Quitter ».
export function demoPill() {
  if (!isDemo()) return null;
  return h('div', { class: 'demo-pill no-drag', 'data-tip-text': t('demo.banner') },
    icon('flask-conical', 'ico-s'),
    h('span', { class: 'demo-label', text: t('demo.pill') }),
    h('button', { class: 'demo-quit', type: 'button', onclick: () => stopDemo() }, t('demo.quit')));
}

// Badge « essai » posé sur les tuiles en mode démonstration.
export function demoBadge(cls = 'badge badge-demo') {
  return h('span', { class: cls, 'data-i18n-tip': 'demo.badge', 'aria-label': t('demo.badge') }, icon('flask-conical'));
}

// Premier lancement sans aucun jeu trouvé : « Essayer FS Passion sans le jeu ? »
let offering = false;

export function maybeOfferDemo() {
  const app = store.app;
  if (!app || offering || isDemo() || app.detecting || !app.settings.welcome_done) return;
  if (!app.demo || app.demo.offered || !app.demo.available) return;
  const found = app.versions.some((v) => v.available && (v.installed || v.ready));
  if (found) return;
  offering = true;
  api.post('/api/demo', { action: 'offered' }).catch(() => {});
  app.demo.offered = true;
  const body = h('div', { class: 'dlg-body' },
    h('div', { class: 'demo-hero' }, icon('flask-conical', 'ico-l')),
    h('p', { class: 'dlg-text', text: t('demo.offer_text') }),
    h('p', { class: 'set-help', text: t(app.demo.local ? 'demo.offer_local' : 'demo.offer_download') }),
    h('div', { class: 'dlg-actions' },
      h('button', { class: 'btn btn-ghost', type: 'button', text: t('demo.offer_no'), onclick: () => dlg.close() }),
      h('button', { class: 'btn btn-primary', type: 'button', autofocus: true, onclick: () => {
        dlg.close();
        startDemo();
      } }, icon('flask-conical'), h('span', { text: t('demo.offer_yes') }))));
  const dlg = openDialog(body, { title: t('demo.offer_title'), cls: 'dlg-s', onClose: () => { offering = false; } });
}
