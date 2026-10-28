// Exporter et importer la configuration (4.17) — version 0.7.0.
// Exporter : dialogue « Enregistrer sous » de Windows, puis un fichier JSON.
// Importer : dialogue « Ouvrir », aperçu du fichier, option « Conserver vos
// chemins actuels » (cochée), puis confirmation. L'import n'applique rien.

import { api } from './api.js';
import { openDialog } from './dialog.js';
import { gameLogo, h, icon } from './dom.js';
import { currentLang, t } from './i18n.js';
import { versionInfo } from './state.js';
import { toast, toastError } from './toast.js';

let busy = false;

function fileName(path) {
  return String(path || '').split(/[\\/]/).pop();
}

function dateText(iso) {
  const d = new Date(iso);
  if (!iso || Number.isNaN(d.getTime())) return '';
  try {
    return new Intl.DateTimeFormat(currentLang(), { dateStyle: 'long', timeStyle: 'short' }).format(d);
  } catch {
    return d.toLocaleString();
  }
}

export async function exportConfig() {
  if (busy) return null;
  busy = true;
  try {
    const res = await api.post('/api/backup/export', {});
    if (res.cancelled) return null;
    // Le fichier n'est visible nulle part ailleurs : son nom est rappelé.
    toast('backup.exported', { file: fileName(res.path) }, 'success');
    return res;
  } catch (err) {
    toastError(err);
    return null;
  } finally {
    busy = false;
  }
}

export async function importConfig() {
  if (busy) return;
  busy = true;
  let prev;
  try {
    prev = await api.post('/api/backup/import-open', {});
  } catch (err) {
    toastError(err);
    return;
  } finally {
    busy = false;
  }
  if (!prev || prev.cancelled) return;
  showPreview(prev);
}

function versionRow(v) {
  const info = versionInfo(v.id);
  return h('li', { class: 'imp-ver' },
    info && info.logo ? gameLogo(info.logo, 'imp-logo') : null,
    h('div', { class: 'imp-ver-text' },
      h('div', { class: 'imp-ver-name', text: v.name }),
      // 0.7.0 : deux lignes seulement (nom, puis détail sur une ligne, tronqué).
      h('div', { class: 'imp-ver-count' },
        `${t('backup.import.parties', { count: v.parties })} · ${t('backup.import.common', { count: v.common })}`,
        v.names && v.names.length ? h('span', { class: 'imp-ver-names', text: ` · ${v.names.join(', ')}` }) : null)));
}

function showPreview(prev) {
  const keep = h('input', { type: 'checkbox', checked: true });
  const keepHelp = h('div', { class: 'set-help' });
  const syncHelp = () => {
    keepHelp.textContent = t(keep.checked ? 'backup.import.keep_help' : 'backup.import.replace_help');
  };
  keep.addEventListener('change', syncHelp);
  syncHelp();
  const ok = h('button', { class: 'btn btn-primary', type: 'button' }, icon('file-up'), h('span', { text: t('backup.import.ok') }));
  const cancel = h('button', { class: 'btn btn-ghost', type: 'button', text: t('common.cancel') });
  const when = dateText(prev.created);
  const body = h('div', { class: 'dlg-body imp-dlg' },
    h('p', { class: 'imp-file' }, icon('file-text', 'ico-s'), h('span', { text: prev.file })),
    h('p', { class: 'set-help', text: t('backup.import.from', { date: when || '?', version: prev.app_version || '?' }) }),
    prev.versions.length
      ? h('ul', { class: 'imp-vers' }, prev.versions.map(versionRow))
      : h('p', { class: 'set-help', text: t('backup.import.no_parties') }),
    h('div', { class: 'imp-keep' },
      h('label', { class: 'check' }, keep, t('backup.import.keep')),
      keepHelp,
      prev.paths_differ ? h('div', { class: 'set-help', text: t('backup.import.paths_differ') }) : null),
    h('div', { class: 'alert-box', text: t('backup.import.warning') }),
    h('div', { class: 'dlg-actions' }, cancel, ok));
  const dlg = openDialog(body, { title: t('backup.import.title'), cls: 'dlg-import' });
  cancel.addEventListener('click', () => dlg.close());
  ok.addEventListener('click', async () => {
    ok.disabled = true;
    try {
      const res = await api.post('/api/backup/import', { token: prev.token, keep_paths: keep.checked });
      dlg.close();
      showResult(res);
    } catch (err) {
      ok.disabled = false;
      toastError(err);
    }
  });
}

function showResult(res) {
  const rows = res.versions.map((v) => h('li', {},
    h('strong', { text: v.name }), ' : ',
    v.skipped
      ? t('backup.result.skipped')
      : t('backup.result.parties', { count: v.parties }),
    v.fallback ? h('div', { class: 'set-help', text: t('backup.result.fallback') }) : null));
  const ok = h('button', { class: 'btn btn-primary', type: 'button', autofocus: true, text: t('common.ok') });
  const body = h('div', { class: 'dlg-body imp-dlg' },
    h('p', { text: t('backup.result.done') }),
    rows.length ? h('ul', { class: 'imp-result' }, rows) : null,
    h('p', { class: 'set-help', text: t('backup.result.apply') }),
    h('p', { class: 'set-help', text: t('backup.result.backup', { file: fileName(res.backup) }) }),
    h('div', { class: 'dlg-actions' }, ok));
  // L'interface est rechargée à la fermeture : langue, thème, listes et
  // parties repartent tous du nouvel état.
  const dlg = openDialog(body, { title: t('backup.result.title'), cls: 'dlg-s', onClose: () => window.location.reload() });
  ok.addEventListener('click', () => dlg.close());
}
