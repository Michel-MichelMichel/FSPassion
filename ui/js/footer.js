// Pied de page : lien GitHub à gauche ; « Lancer le jeu » et « Quitter » à droite.

import { api } from './api.js';
import { launchGame } from './apply.js';
import { clear, h, icon } from './dom.js';
import { t } from './i18n.js';
import { isRunning, store, versionInfo } from './state.js';
import { toastError } from './toast.js';
import { footerUpdatePill } from './updates.js';

let footer = null;
let onQuit = () => {};
let onUpdates = () => {};

export function initFooter(el, opts) {
  footer = el;
  onQuit = opts.onQuit;
  onUpdates = opts.onUpdates || onUpdates;
}

export function renderFooter() {
  if (!footer || !store.app) return;
  clear(footer);
  const info = store.app.app.info || {};
  const gh = info.github_url;
  const ghLogo = h('span', { class: 'gh-logo', 'aria-hidden': 'true' });
  ghLogo.style.setProperty('--ico', 'url("/assets/brand/github.svg")');
  const ghText = h('span', { class: 'gh-text', 'aria-hidden': 'true' });
  ghText.style.setProperty('--ico', 'url("/assets/brand/github-text.svg")');
  const ghBtn = h('button', { class: 'gh-btn', type: 'button', 'aria-label': 'GitHub' }, ghLogo, ghText);
  if (gh) {
    ghBtn.addEventListener('click', () => api.post('/api/link', { key: 'github' }).catch(toastError));
    ghBtn.dataset.tipText = t('footer.github_tip');
  } else {
    ghBtn.setAttribute('aria-disabled', 'true');
    ghBtn.dataset.tipText = t('footer.github_soon');
  }

  const v = versionInfo();
  const running = isRunning();
  const launch = h('button', { class: 'btn btn-primary btn-l launch-btn', type: 'button' },
    icon(running ? 'loader-circle' : 'play', running ? 'spin' : ''),
    h('span', { text: running ? t('footer.running') : t('footer.launch') }));
  const canLaunch = v && v.available && v.cfg.game_exe && v.checks.game_exe && v.checks.game_exe.level === 'ok';
  if (running || !canLaunch) launch.setAttribute('aria-disabled', 'true');
  launch.dataset.tipText = !canLaunch ? t('footer.launch_unconfigured', { game: v ? v.name : '' }) : t('footer.launch_tip');
  launch.addEventListener('click', () => {
    if (launch.getAttribute('aria-disabled') === 'true') return;
    launchGame();
  });

  footer.append(
    ghBtn,
    h('span', { class: 'footer-version', text: `v${store.app.app.version}` }),
    ...[footerUpdatePill(() => onUpdates())].filter(Boolean),
    h('div', { class: 'footer-spacer' }),
    launch,
    h('button', { class: 'btn btn-ghost btn-l', type: 'button', onclick: () => onQuit() }, icon('log-out'), h('span', { text: t('footer.quit') })),
  );
}
