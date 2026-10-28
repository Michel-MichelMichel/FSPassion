// Bienvenue (premier lancement) et notice.

import { api } from './api.js';
import { openDialog } from './dialog.js';
import { clear, h } from './dom.js';
import { blocks, t } from './i18n.js';
import { changeLanguage, languageSelect } from './settings.js';
import { store } from './state.js';

let noticeDlg = null;

export function openWelcome(onDone) {
  const body = h('div');
  const render = () => {
    clear(body);
    body.append(
      h('div', { class: 'welcome-hero' },
        // Logo en haut à gauche, sélecteur de langue en haut à droite
        // (le même que dans Paramètres > Affichage), texte en bas.
        h('div', { class: 'welcome-top' },
          // Le logo FS Passion, comme dans l'en-tête et « À propos ».
          h('div', { class: 'welcome-logo', role: 'img', 'aria-label': 'FS Passion' }, h('span', { class: 'app-logo app-logo-art', 'aria-hidden': 'true' })),
          languageSelect(async (code) => {
            await changeLanguage(code);
            render();
          })),
        h('p', { text: t('welcome.subtitle') })),
      h('div', { class: 'dlg-foot' },
        h('div', { class: 'spacer' }),
        h('button', {
          class: 'btn btn-primary btn-l', type: 'button', autofocus: true,
          onclick: async () => {
            try {
              await api.post('/api/settings', { welcome_done: true });
              store.app.settings.welcome_done = true;
            } catch {
              /* sans gravité */
            }
            dlg.close();
            onDone && onDone();
          },
        }, t('common.ok'))),
    );
  };
  render();
  const dlg = openDialog(body, { cls: 'dlg-welcome', dismissible: false, dragWindow: true });
}

export function openNotice() {
  if (noticeDlg && !noticeDlg.closed) return;
  const content = h('div', { class: 'notice-body' });
  for (const b of blocks('notice.blocks')) {
    if (b.h) content.append(h('h3', { text: b.h }));
    if (b.p) content.append(h('p', { text: b.p }));
    if (b.key) content.append(h('p', { class: 'is-key', text: b.key }));
    if (b.ul) content.append(h('ul', {}, b.ul.map((x) => h('li', { text: x }))));
  }
  const check = h('input', { type: 'checkbox', checked: store.app.settings.show_notice_at_start !== false });
  check.addEventListener('change', async () => {
    try {
      await api.post('/api/settings', { show_notice_at_start: check.checked });
      store.app.settings.show_notice_at_start = check.checked;
    } catch {
      /* sans gravité */
    }
  });
  const foot = h('div', { class: 'dlg-foot' },
    h('label', { class: 'check' }, check, t('notice.at_start')),
    h('div', { class: 'spacer' }),
    h('button', { class: 'btn btn-primary', type: 'button', autofocus: true, onclick: () => noticeDlg.close() }, t('notice.understood')));
  noticeDlg = openDialog(h('div', { style: { display: 'contents' } }, content, foot), {
    title: t('notice.title'),
    cls: 'dlg-notice',
    // Un clic sur le fond ne ferme plus la notice (bouton « J'ai compris »).
    backdropClose: false,
    dragWindow: true,
    onClose: () => { noticeDlg = null; },
  });
}
