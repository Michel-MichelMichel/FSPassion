"""Configuration des tests : le code est dans src/, les réglages dans un dossier temporaire."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

DATA = ROOT / "tests" / "data"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Chaque test a ses propres réglages : rien n'est écrit chez l'utilisateur."""
    home = tmp_path / "fsp-home"
    monkeypatch.setenv("FSPASSION_HOME", str(home))
    return home


@pytest.fixture
def data_dir() -> Path:
    return DATA
