// Téléchargements et intégration.
// Fenêtre « Nouveaux mods trouvés » : les mods du dossier de téléchargements,
// leur version du jeu (modifiable), leur état et leur destination. Intégrer =
// déplacer le fichier dans le dossier de mods de la version choisie.

import { api } from './api.js';
import { openDialog } from './dialog.js';
import { clear, gameLogo, h, icon } from './dom.js';
import { sizeText } from './hovercard.js';
import { pickTitle, t } from './i18n.js';
import { refreshLibrary, refreshParties, refreshState, setParties, setting, store } from './state.js';
import { toast, toastError } from './toast.js';

let open = false;
let autoDone = false;

function rowTitle(it) {
  return pickTitle(it.titles) || it.id;
}

// État pour la version choisie (calculé par le cœur pour chaque version configurée).
function stateFor(it, vid) {
  return (it.states && it.states[vid]) || { state: 'unconfigured', checked: false };
}

function stateLabel(st) {
  switch (st.state) {
    case 'new': return t('downloads.state.new');
    case 'update': return t('downloads.state.update', { from: st.from || '?', to: st.to || '?' });
    case 'older': return t('downloads.state.older', { from: st.from || '?', to: st.to || '?' });
    case 'present': return t('downloads.state.present');
    case 'conflict': return t('downloads.state.conflict');
    default: return t('downloads.state.unconfigured');
  }
}

function canIntegrate(st) {
  return ['new', 'update', 'older'].includes(st.state);
}

// Recherche, puis fenêtre. auto : au lancement de FS Passion, la fenêtre ne
// s'ouvre que s'il y a quelque chose à intégrer (nouveau ou mise à jour).
export async function openDownloads({ auto = false } = {}) {
  if (open) return;
  let res;
  try {
    res = await api.post('/api/downloads/scan');
  } catch (err) {
    if (!auto) toastError(err);
    return;
  }
  const items = res.items || [];
  const defaultVersion = (it) => {
    const ok = res.versions.map((v) => v.id);
    // Version détectée (y compris si elle n'est pas configurée).
    if (it.detected) return it.detected;
    return ok.includes(res.active) ? res.active : ok[0] || res.active;
  };
  const rows = items.map((it) => {
    const vid = defaultVersion(it);
    const st = stateFor(it, vid);
    return { it, vid, checked: !!st.checked, dest: 'none', storage: 0 };
  });
  if (auto && !rows.some((r) => r.checked)) return;
  if (!rows.length) {
    toast('downloads.none', { folder: res.folder }, 'info');
    return;
  }
  open = true;
  buildDialog(res, rows);
}

// Nom court d'un dossier de stockage : « 2 · D:\\…\\Mods2 ».
function storageLabel(path, i) {
  const parts = String(path).split(/[\\/]/).filter(Boolean);
  const tail = parts.length > 2 ? `${parts[0]}\\…\\${parts[parts.length - 1]}` : String(path);
  return `${i + 1} · ${tail}`;
}

function buildDialog(res, rows) {
  const versions = res.versions || [];
  // Colonne « Stockage » : seulement si une version en a plusieurs.
  const withStorage = versions.some((v) => (v.storages || []).length > 1);
  const table = h('div', { class: `dl-table${withStorage ? ' has-storage' : ''}`, role: 'table' });
  const count = h('span', { class: 'dl-count' });
  const ok = h('button', { class: 'btn btn-primary', type: 'button' }, icon('download'), h('span', { class: 'dl-ok-text' }));
  const ignoreBtn = h('button', { class: 'btn', type: 'button' }, icon('eye-off'), h('span', { text: t('downloads.ignore') }));

  const refreshButtons = () => {
    const n = rows.filter((r) => r.checked && canIntegrate(stateFor(r.it, r.vid))).length;
    ok.querySelector('.dl-ok-text').textContent = t('downloads.integrate', { count: n });
    ok.toggleAttribute('disabled', !n);
    const sel = rows.filter((r) => r.checked).length;
    ignoreBtn.toggleAttribute('disabled', !sel);
    count.textContent = t('downloads.count', { count: rows.length });
  };

  const draw = () => {
    clear(table);
    table.append(h('div', { class: 'dl-row dl-headrow', role: 'row' },
      h('span', {}), h('span', { text: t('downloads.col_mod') }), h('span', { text: t('downloads.col_version') }),
      h('span', { text: t('downloads.col_state') }),
      withStorage ? h('span', { text: t('downloads.col_storage') }) : null,
      h('span', { text: t('downloads.col_dest') })));
    for (const r of rows) table.append(row(r));
    refreshButtons();
  };

  const row = (r) => {
    const it = r.it;
    const st = stateFor(it, r.vid);
    const possible = canIntegrate(st);
    const box = h('input', { type: 'checkbox', checked: r.checked && possible, disabled: !possible, 'aria-label': rowTitle(it) });
    box.addEventListener('change', () => {
      r.checked = box.checked;
      draw();
    });
    // Version du jeu : détectée, modifiable.
    const sel = h('select', { class: 'field-select', 'aria-label': t('downloads.col_version') });
    const ids = versions.map((v) => v.id);
    if (!ids.includes(r.vid)) sel.append(h('option', { value: r.vid, text: r.vid }));
    for (const v of versions) sel.append(h('option', { value: v.id, text: v.short || v.name, selected: v.id === r.vid }));
    sel.value = r.vid;
    sel.addEventListener('change', () => {
      r.vid = sel.value;
      r.checked = !!stateFor(it, r.vid).checked;
      r.dest = 'none';
      r.storage = 0;
      draw();
    });
    // Destination : seulement pour un mod nouveau de la version active.
    let dest = h('span', { class: 'dl-faint', text: st.state === 'new' ? t('downloads.dest_unclassified') : '—' });
    if (st.state === 'new' && r.vid === res.active && res.classification) {
      dest = h('select', { class: 'field-select', 'aria-label': t('downloads.col_dest') },
        h('option', { value: 'none', text: t('downloads.dest_none') }),
        h('option', { value: 'common', text: t('list3.title') }),
        res.party ? h('option', { value: 'party', text: t('downloads.dest_party', { name: res.party.name }) }) : null);
      dest.value = r.dest;
      dest.addEventListener('change', () => { r.dest = dest.value; });
    }
    const v = versions.find((x) => x.id === r.vid);
    const running = v && v.running;
    // Stockage : au choix pour un mod nouveau (principal par défaut) ; une mise à
    // jour reste dans le stockage du mod qu'elle remplace.
    let where = null;
    if (withStorage) {
      const list = (v && v.storages) || [];
      if (st.state === 'new' && list.length > 1) {
        where = h('select', { class: 'field-select', 'aria-label': t('downloads.col_storage') },
          ...list.map((path, i) => h('option', { value: String(i), text: storageLabel(path, i), title: path })));
        where.value = String(r.storage || 0);
        where.addEventListener('change', () => { r.storage = Number(where.value) || 0; });
      } else {
        const i = Number(st.storage || 0);
        where = h('span', { class: 'dl-faint', text: list[i] ? storageLabel(list[i], i) : '—', title: list[i] || '' });
      }
    }
    const stateCls = st.state === 'older' || st.state === 'conflict' || st.state === 'unconfigured' ? 'is-warn' : (st.state === 'update' ? 'is-update' : '');
    const art = h('span', { class: 'rl-art' }, it.icon ? h('img', { src: it.icon, alt: '', draggable: 'false' }) : icon(it.is_map ? 'map' : 'package', 'ico-s'));
    return h('div', { class: `dl-row${possible ? '' : ' is-off'}`, role: 'row' },
      box,
      h('span', { class: 'dl-mod' }, art,
        h('span', { class: 'rl-text' },
          h('span', { text: rowTitle(it) }),
          h('span', { class: 'rl-sub', text: `${it.file} · ${sizeText(it.size)}` }),
          it.suffix_removed ? h('span', { class: 'rl-sub', text: t('downloads.suffix', { name: `${it.id}.zip` }) }) : null)),
      h('span', { class: 'dl-ver' }, v ? gameLogo(v.logo) : null, sel),
      h('span', { class: `dl-state ${stateCls}` },
        h('span', { text: stateLabel(st) }),
        st.state === 'older' && r.checked ? h('span', { class: 'rl-sub', text: t('downloads.older_confirm') }) : null,
        running ? h('span', { class: 'rl-sub', text: t('downloads.postpone', { game: v.name }) }) : null),
      where ? h('span', { class: 'dl-storage' }, where) : null,
      h('span', { class: 'dl-dest' }, dest));
  };

  const body = h('div', { class: 'dlg-body dl-body' },
    h('p', { class: 'dlg-text', text: t('downloads.intro', { folder: res.folder }) }),
    table);
  const later = h('button', { class: 'btn btn-ghost', type: 'button', text: t('downloads.later') });
  const foot = h('div', { class: 'dlg-foot' }, count, h('div', { class: 'spacer' }), ignoreBtn, later, ok);
  const dlg = openDialog(h('div', { style: { display: 'contents' } }, body, foot), {
    title: t('downloads.title'), cls: 'dlg-downloads', onClose: () => { open = false; },
  });
  later.addEventListener('click', () => dlg.close());
  ignoreBtn.addEventListener('click', async () => {
    const files = rows.filter((r) => r.checked).map((r) => r.it.file);
    if (!files.length) return;
    try {
      await api.post('/api/downloads/ignore', { files });
      toast('downloads.ignored', { count: files.length }, 'info');
      dlg.close();
    } catch (err) {
      toastError(err);
    }
  });
  ok.addEventListener('click', async () => {
    const chosen = rows.filter((r) => r.checked && canIntegrate(stateFor(r.it, r.vid)));
    if (!chosen.length) return;
    ok.disabled = true;
    try {
      const out = await api.post('/api/downloads/integrate', {
        items: chosen.map((r) => ({
          file: r.it.file, version: r.vid, destination: r.dest,
          party: r.dest === 'party' && res.party ? res.party.id : undefined,
          replace_older: stateFor(r.it, r.vid).state === 'older',
          storage: stateFor(r.it, r.vid).state === 'new' ? (r.storage || 0) : 0,
        })),
      });
      dlg.close();
      report(out, versions);
      if (out.state) setParties(out.state);
      await Promise.all([refreshLibrary(), refreshParties(), refreshState()]);
    } catch (err) {
      ok.disabled = false;
      toastError(err);
    }
  });
  draw();
}

// « 3 mods intégrés : 2 dans FS25, 1 dans FS22. »
function report(out, versions) {
  const name = (vid) => (versions.find((v) => v.id === vid) || {}).short || vid;
  const parts = Object.entries(out.done || {}).map(([vid, list]) => t('downloads.in_version', { count: list.length, game: name(vid) }));
  const vids = Object.keys(out.done || {});
  if (out.count && vids.length === 1) toast('downloads.done_in', { count: out.count, game: name(vids[0]) }, 'success');
  else if (out.count) toast('downloads.done', { count: out.count, list: parts.join(', ') }, 'success');
  for (const f of out.failed || []) toast(f.error || 'downloads.failed', { file: f.file, path: f.detail || '' }, 'error');
  if ((out.skipped || []).length) toast('downloads.skipped', { count: out.skipped.length }, 'info');
  if ((out.postponed || []).length) {
    toast('downloads.postponed', { count: out.postponed.length, game: name(out.postponed[0].version) }, 'info');
  }
}

// Au lancement de FS Passion (réglage « Rechercher les nouveaux mods au
// lancement ») : une seule fois par session.
export function maybeAutoDownloads() {
  if (autoDone || !store.app || setting('scan_downloads_at_start') === false) return;
  if (store.app.demo && store.app.demo.active) return;
  autoDone = true;
  openDownloads({ auto: true }).catch(() => {});
}


