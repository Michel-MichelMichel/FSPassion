"""Version 0.9.10 : au lancement du jeu, FS Passion se range dans la zone de
notification (réglage « Fermer dans la zone de notification »), sinon il se
réduit dans la barre des tâches."""

from __future__ import annotations

from pathlib import Path

from fspassion import core as core_mod
from fspassion.core import Core
from fspassion.events import EventBus

ROOT = Path(__file__).resolve().parents[1]


class FakeNative:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def minimize(self) -> None:
        self.calls.append("minimize")

    def sleep_later(self, delay: float = 2.0) -> None:
        self.calls.append("sleep")


def _core(monkeypatch) -> tuple[Core, FakeNative]:
    fake = FakeNative()
    monkeypatch.setattr(core_mod, "native", fake)
    return Core(dev=True, bus=EventBus()), fake


def test_game_launch_hides_to_tray(monkeypatch):
    core, fake = _core(monkeypatch)
    hidden: list[bool] = []
    core.hide_to_tray = lambda: hidden.append(True) or True
    core._hide_for_game()
    assert hidden == [True]
    assert fake.calls == []  # pas de réduction dans la barre des tâches


def test_game_launch_minimizes_without_tray(monkeypatch):
    core, fake = _core(monkeypatch)
    core.hide_to_tray = lambda: False  # réglage désactivé ou icône absente
    core._hide_for_game()
    assert fake.calls == ["minimize", "sleep"]
    core.hide_to_tray = None
    fake.calls.clear()
    core._hide_for_game()
    assert fake.calls == ["minimize", "sleep"]


def test_app_gives_the_tray_hook_to_core():
    app = (ROOT / "src" / "fspassion" / "app.py").read_text(encoding="utf-8")
    assert "core.hide_to_tray = to_tray" in app
    assert "core.hide_to_tray = None" in app
