"""0.8.0 : fabrication (exécutable, installeur, désinstalleur, version
portable, GitHub Actions), et corrections de l'en-tête."""

from __future__ import annotations

import os
import re
from pathlib import Path

from fspassion import app, launcher
from test_sauvegarde_dlc import env, make_party, override_dir  # noqa: F401 (fixture)

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


# -- en-tête -------------------------------------------------------------------

def test_header_returns_to_one_line():
    """Sur 1 ligne, la barre touche toujours le bord droit (les espaces
    extensibles prennent la place) : la marge se lit dans les espaces."""
    js = _read("ui", "js", "header.js")
    assert "slack += sp.offsetWidth" in js
    assert "const compact = overflow || (wasCompact && slack < RELAX);" in js


def test_header_logo_follows_the_header_height():
    css = _read("ui", "css", "layout.css")
    assert ".topbar > .brand { align-self: stretch; }" in css
    assert ".topbar .app-logo.app-logo-art { height: 100%; }" in css
    assert 'url("/assets/FS_Passion_logo/logo.svg")' in css
    assert "logo_deux_tracteurs_gravure2" not in css


# -- fabrication -------------------------------------------------------------------

def test_pyinstaller_spec_is_onedir_and_embeds_the_resources():
    spec = _read("packaging", "fspassion.spec")
    assert "exclude_binaries=True" in spec and "COLLECT(" in spec   # mode dossier (7.5)
    assert "console=False" in spec and "upx=False" in spec
    for res in ('tree("ui", "ui")', 'tree("lang", "lang")', '"src/fspassion/data"', "logo.svg", "LICENSE"):
        assert res in spec
    # Ressources choisies une par une : jamais tout « assets » (vidéo, .psd…).
    assert 'tree("assets", ' not in spec and "psd\"" not in spec


def test_build_script_steps():
    build = _read("tools", "build.py")
    for piece in ("portable.txt", "SHA256SUMS.txt", "ISCC", "MicrosoftEdgeWebview2Setup.exe", "make_demo_pack.py",
                  "-setup.exe", "-portable.zip"):
        assert piece in build
    assert "pyinstaller==" in _read("requirements-build.txt")
    assert "tools\\build.py" in _read("fabriquer.bat")


def test_installer_asks_its_own_questions_and_keeps_the_mutex():
    iss = _read("packaging", "installer.iss")
    # 0.9.8 : le désinstalleur n'ouvre plus FS Passion ; il pose ses questions
    # dans sa propre fenêtre puis lance FS Passion sans fenêtre.
    assert "[UninstallRun]" not in iss and "Parameters: \"--uninstall\"" not in iss
    assert "'--uninstall-check'" in iss and "'--uninstall-quiet'" in iss and "' --remove '" in iss
    assert "CreateCustomForm(" in iss and "SW_HIDE, ewWaitUntilTerminated" in iss
    assert "UninstallSilent()" in iss and "{param:FSPDONE|0}" in iss
    for key in ("parties", "caches", "settings", "logs", "langs"):
        assert "AddOption(B" in iss and f"'{key}'" in iss
    assert "PrivilegesRequired=lowest" in iss
    assert "NeedsWebView2" in iss and "F3017226-FE2A-4295-8BDF-00C3A9A7E4C5" in iss
    assert app.MUTEX_NAME in iss                      # FS Passion ouvert : à fermer d'abord
    # Le désinstalleur cherché par « Ne plus utiliser » (stopuse.uninstaller).
    assert "unins000.exe" in _read("src", "fspassion", "stopuse.py")


def test_github_workflow():
    # Le modèle est dans packaging\github\ (les outils de Claude ne peuvent pas
    # écrire dans .github\) ; une fois copié dans .github\workflows\, les deux
    # doivent rester identiques.
    wf = _read("packaging", "github", "build.yml")
    live = ROOT / ".github" / "workflows" / "build.yml"
    if live.is_file():
        assert live.read_text(encoding="utf-8").replace("\r\n", "\n") == wf.replace("\r\n", "\n")
    assert "runs-on: windows-2022" in wf and "python tools/build.py" in wf
    assert "tags: [\"v*.*.*\"]" in wf and "gh release create" in wf and "--draft" in wf
    assert "actions/upload-artifact@v6" in wf
    assert re.search(r"permissions:\s*\n\s*contents: read", wf)


def test_uninstall_quiet_option():
    a = app.parse_args(["--uninstall-quiet", "--remove", "parties,logs"])
    assert a.uninstall_quiet and a.remove == "parties,logs"
    assert app.parse_args(["--uninstall-check"]).uninstall_check


def test_uninstall_headless_does_stop_using_without_window(env, monkeypatch):  # noqa: F811
    core = env["core"]
    pid = make_party(env)
    core.party_apply("FS25", pid)
    monkeypatch.setattr(launcher, "running_versions", lambda names=None: set())
    assert core.uninstall_running() == []
    assert core.uninstall_headless(["parties", "inconnu"]) == 0
    assert override_dir(env["gs"]) == os.path.normpath(env["mods"])
    assert not env["parties"].exists()                  # dossiers de parties retirés
    assert not (env["fsp"] / "parties.json").exists()   # choisi dans le désinstalleur
    assert core.stopped


def test_uninstall_headless_waits_for_the_game(env, monkeypatch):  # noqa: F811
    core = env["core"]
    pid = make_party(env)
    core.party_apply("FS25", pid)
    before = override_dir(env["gs"])
    monkeypatch.setattr(launcher, "running_versions", lambda names=None: {"FS25"})
    assert core.uninstall_running() == ["FS25"]
    assert core.uninstall_headless([]) == 3
    assert override_dir(env["gs"]) == before and env["parties"].exists()
    assert not core.stopped


def test_uninstall_minimal_restores_the_override_only(env, monkeypatch):  # noqa: F811
    core = env["core"]
    pid = make_party(env)
    core.party_apply("FS25", pid)
    assert override_dir(env["gs"]) != os.path.normpath(env["mods"])
    monkeypatch.setattr(launcher, "running_versions", lambda names=None: set())
    done = core.uninstall_minimal()
    assert done == ["FS25"]
    assert override_dir(env["gs"]) == os.path.normpath(env["mods"])
    assert env["parties"].exists()                     # rien n'est supprimé
    assert (env["fsp"] / "parties.json").is_file()


def test_uninstall_minimal_skips_a_running_game(env, monkeypatch):  # noqa: F811
    core = env["core"]
    pid = make_party(env)
    core.party_apply("FS25", pid)
    before = override_dir(env["gs"])
    monkeypatch.setattr(launcher, "running_versions", lambda names=None: {"FS25"})
    assert core.uninstall_minimal() == []
    assert override_dir(env["gs"]) == before


def test_closing_in_uninstall_mode_quits_instead_of_hiding():
    src = _read("src", "fspassion", "app.py")
    assert "core.uninstall_mode or not tray.active" in src
    assert "if core.uninstall_mode and not core.stopped:" in src
