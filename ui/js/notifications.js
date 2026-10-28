// Bouton « Notifications » (cloche) de l'en-tête (0.2.1) : relire les messages
// courts déjà disparus. Pastille = nombre de messages non lus. L'historique
// dure le temps de la session.

import { clear, h, icon } from './dom.js';
import { currentLang, formatNumber, t } from './i18n.js';
import {
  clearNotifications, levelIcon, markAllRead, notifications, onNotifications, unreadCount,
} from './toast.js';

let unsubscribe = null;

function timeText(d) {
  try {
    return new Intl.DateTimeFormat(currentLang(), { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(d);
  } catch {
    return d.toLocaleTimeString();
  }
}

export function buildBell() {
  const badge = h('span', { class: 'bell-badge', 'aria-hidden': 'true' });
  const btn = h('button', {
    class: 'icon-btn bell-btn no-drag', type: 'button', 'aria-haspopup': 'dialog', 'aria-expanded': 'false',
    'data-i18n-tip': 'notifications.title',
  }, icon('bell'), badge);
  const panel = h('div', { class: 'menu notif-menu', role: 'dialog', 'aria-label': t('notifications.title') });
  const wrap = h('div', { class: 'bell-pick no-drag' }, btn, panel);

  const refreshBadge = () => {
    const n = unreadCount();
    badge.textContent = n > 99 ? '99+' : n ? formatNumber(n) : '';
    btn.classList.toggle('has-unread', n > 0);
    btn.setAttribute('aria-label', n ? t('notifications.unread', { count: n }) : t('notifications.title'));
  };

  // Messages encore non lus à l'ouverture : signalés dans la liste.
  let fresh = new Set();
  const fill = () => {
    clear(panel);
    const list = notifications();
    for (const n of list) if (!n.read) fresh.add(n.id);
    const head = h('div', { class: 'notif-head' },
      h('span', { class: 'notif-title', text: t('notifications.title') }),
      list.length ? h('button', {
        class: 'btn btn-ghost btn-s', type: 'button', text: t('notifications.clear'),
        onclick: () => {
          clearNotifications();
          fill();
        },
      }) : null);
    panel.append(head);
    if (!list.length) {
      panel.append(h('div', { class: 'menu-empty', text: t('notifications.none') }));
      return;
    }
    const scroll = h('div', { class: 'notif-list' });
    for (const n of list) {
      scroll.append(h('div', { class: `notif-item notif-${n.level}${fresh.has(n.id) ? ' is-unread' : ''}` },
        icon(levelIcon(n.level), 'notif-ico'),
        h('div', { class: 'notif-text' },
          h('div', { text: n.text }),
          h('div', { class: 'notif-time', text: timeText(n.time) }))));
    }
    panel.append(scroll);
  };

  const outside = (e) => {
    if (!wrap.contains(e.target)) close();
  };
  const keys = (e) => {
    if (e.key === 'Escape') {
      e.stopPropagation();
      close();
      btn.focus();
    }
  };
  function open() {
    fresh = new Set();
    fill();
    panel.classList.add('on');
    btn.setAttribute('aria-expanded', 'true');
    document.addEventListener('pointerdown', outside, true);
    document.addEventListener('keydown', keys, true);
    // Les messages sont lus : la pastille s'efface (ils restent signalés dans
    // la liste jusqu'à la prochaine ouverture).
    markAllRead();
  }
  function close() {
    panel.classList.remove('on');
    btn.setAttribute('aria-expanded', 'false');
    document.removeEventListener('pointerdown', outside, true);
    document.removeEventListener('keydown', keys, true);
  }
  btn.addEventListener('click', () => (panel.classList.contains('on') ? close() : open()));

  if (unsubscribe) unsubscribe();
  unsubscribe = onNotifications(() => {
    refreshBadge();
    if (panel.classList.contains('on') && wrap.isConnected) {
      fill();
      markAllRead();
    }
  });
  refreshBadge();
  return wrap;
}
