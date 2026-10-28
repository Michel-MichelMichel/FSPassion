// Bandeau d'actions (4.6) : il glisse depuis le bas dès qu'un mod est
// sélectionné, avec le nombre de mods sélectionnés et les actions de classement.
// Un bouton sans effet sur la sélection est désactivé.

import { addMods, possibleActions, removeMods } from './actions.js';
import { clear, h, icon } from './dom.js';
import { formatNumber, t } from './i18n.js';
import { openDelete, openRename } from './modops.js';
import { clearSelection, onSelection, selectedIds, selectionList, selectionSize } from './selection.js';
import { isRunning, modIndex, subscribe, versionInfo } from './state.js';

let bar = null;
let app = null;

export function initActionBar(el, appEl) {
  bar = el;
  app = appEl;
  onSelection(render);
  subscribe('parties', render);
  subscribe('library', render);
  window.addEventListener('resize', fitBar);
}

// 0.7.2 : fenêtre étroite. Quand les 4 boutons de classement ne tiennent plus
// sur une ligne, ils passent en 2 colonnes (2 + 2) ; les listes gardent alors
// un peu plus de place en bas pour le bandeau, plus haut.
function fitBar() {
  if (!bar || !bar.classList.contains('on')) return;
  const g = bar.querySelector('.ab-sort');
  if (!g || !g.firstElementChild) return;
  g.classList.remove('is-grid');
  const wrapped = g.offsetHeight > g.firstElementChild.offsetHeight * 1.5;
  g.classList.toggle('is-grid', wrapped);
  app.classList.toggle('has-actionbar-tall', wrapped);
}

function button(ico, label, enabled, run, cls = '', tip = null) {
  const b = h('button', { class: `btn btn-s ab-btn ${cls}`.trim(), type: 'button' }, icon(ico, 'ico-s'), h('span', { text: label }));
  if (!enabled) b.setAttribute('aria-disabled', 'true');
  if (tip) {
    b.dataset.tipText = tip;
    b.setAttribute('aria-label', label);
  }
  b.addEventListener('click', () => {
    if (b.getAttribute('aria-disabled') === 'true') return;
    run();
  });
  return b;
}

export function render() {
  if (!bar) return;
  const n = selectionSize();
  const on = n > 0;
  bar.classList.toggle('on', on);
  app.classList.toggle('has-actionbar', on);
  bar.setAttribute('aria-hidden', on ? 'false' : 'true');
  bar.inert = !on;
  if (!on) {
    app.classList.remove('has-actionbar-tall');
    return;
  }
  const ids = selectedIds();
  const list = selectionList();
  const can = possibleActions(ids);
  clear(bar);
  // Renommer et Supprimer (0.4) : icône seule, le nom est dans l'infobulle
  // (0.2.1 : avec les textes agrandis, le bandeau garde sa place).
  const v = versionInfo();
  const running = isRunning();
  const runningTip = running ? t('apply.running', { game: v ? v.name : '' }) : '';
  const present = ids.filter((id) => modIndex().has(String(id).toLowerCase()));
  const canRename = list === 'l1' && n === 1 && present.length === 1 && !running;
  const rename = button('pencil', t('actions.rename'), canRename, () => openRename(present[0]), 'is-compact',
    running ? `${t('actions.rename')}\n${runningTip}` : (canRename ? `${t('actions.rename')} (F2)` : `${t('actions.rename')}\n${t('actions.rename_help')}`));
  const del = button('trash-2', t('actions.delete'), present.length > 0 && !running, () => openDelete(present), 'btn-danger is-compact',
    running ? `${t('actions.delete')}\n${runningTip}` : t('actions.delete'));
  bar.append(
    h('div', { class: 'ab-count', 'aria-live': 'polite' },
      h('b', { text: formatNumber(n) }), h('span', { text: t('actions.selected', { count: n }) })),
    h('div', { class: 'ab-group ab-sort' },
      button('plus', t('actions.add_party'), can.addParty, () => addMods('party', ids)),
      button('layers', t('actions.add_common'), can.addCommon, () => addMods('common', ids)),
      button('minus', t('actions.remove_party'), can.removeParty, () => removeMods('party', ids)),
      button('minus', t('actions.remove_common'), can.removeCommon, () => removeMods('common', ids))),
    h('div', { class: 'ab-group' }, rename),
    h('div', { class: 'ab-spacer' }),
    del,
    h('button', {
      class: 'icon-btn icon-btn-s ab-close', type: 'button', 'data-i18n-tip': 'actions.close',
      'aria-label': t('actions.close'), onclick: () => clearSelection(),
    }, icon('x')),
  );
  fitBar();
}
