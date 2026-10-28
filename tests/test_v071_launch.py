"""0.7.1 : une case cochée pendant la détection ne doit pas être annulée."""

import threading

from tests.test_v04 import env  # noqa: F401  (fixture)

from fspassion import detect


def test_toggle_during_detection_is_not_lost(env, monkeypatch):  # noqa: F811
    core = env["core"]
    real_prefill = detect.prefill
    workers = []

    def racing_prefill(cfg, det, vid):
        # L'utilisateur coche « passer la vidéo » pendant que la détection calcule
        # la configuration de FS25 : le réglage doit attendre la fin, puis tenir.
        if vid == "FS25" and not workers:
            t = threading.Thread(target=core.set_launch_args, args=("FS25", True, False))
            workers.append(t)
            t.start()
        return real_prefill(cfg, det, vid)

    monkeypatch.setattr(detect, "prefill", racing_prefill)
    monkeypatch.setattr(detect, "detect_all", lambda: {})
    core.detect(None, silent=True)
    for t in workers:
        t.join(timeout=10)
    assert core.settings.version("FS25")["launch_args"]["skip_start_videos"] is True
