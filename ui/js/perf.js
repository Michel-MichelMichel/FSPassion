// Mesures de performance (0.7.0, chapitre 8 R11) : temps d'affichage au
// démarrage et fluidité réelle du défilement des listes, sur le PC de
// l'utilisateur. Rien n'est affiché : les chiffres rejoignent la section
// « Performance » de « Copier le diagnostic ». Rien ne sort du PC.

import { api } from './api.js';

const LONG_FRAME_MS = 33; // une image de plus de 33 ms = moins de 30 images/s
const IDLE_MS = 400; // fin d'un défilement : 400 ms sans mouvement

let session = null;

function listOf(target) {
  if (!target || !target.closest) return null;
  if (target.closest('#list1')) return 'l1';
  const pane = target.closest('.side-pane');
  return pane ? pane.dataset.drop || null : null;
}

function frame(now) {
  if (!session) return;
  if (session.last) {
    const dt = now - session.last;
    session.frames += 1;
    session.ms += dt;
    if (dt > LONG_FRAME_MS) session.long += 1;
    if (dt > session.worst) session.worst = dt;
  }
  session.last = now;
  if (now - session.moved > IDLE_MS) {
    const s = session;
    session = null;
    if (s.frames >= 10) {
      api.post('/api/perf', {
        scroll: { list: s.list, frames: s.frames, ms: Math.round(s.ms), long: s.long, worst_ms: Math.round(s.worst) },
      }).catch(() => {});
    }
    return;
  }
  requestAnimationFrame(frame);
}

function moved(e) {
  const list = listOf(e.target);
  if (!list) return;
  const now = performance.now();
  if (session && session.list === list) {
    session.moved = now;
    return;
  }
  session = { list, frames: 0, ms: 0, long: 0, worst: 0, last: 0, moved: now };
  requestAnimationFrame(frame);
}

export function initPerf() {
  api.post('/api/perf', {
    ready_ms: Math.round(performance.now()),
    width: window.innerWidth,
    height: window.innerHeight,
    dpr: Math.round((window.devicePixelRatio || 1) * 100) / 100,
  }).catch(() => {});
  document.addEventListener('wheel', moved, { capture: true, passive: true });
  document.addEventListener('scroll', moved, { capture: true, passive: true });
}
