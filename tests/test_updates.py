"""Mises à jour de FS Passion : recherche sur GitHub, vérification,
installation (sans jamais aller sur Internet pendant les tests)."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from fspassion import __version__, config, updates
from fspassion.core import SETTABLE, AppError, Core
from fspassion.events import EventBus

ROOT = Path(__file__).resolve().parents[1]
INFO = {"github_url": "https://github.com/Michel-MichelMichel/FSPassion"}


def _bump(version: str) -> str:
    a, b, c = (int(x) for x in version.split("."))
    return f"{a}.{b}.{c + 1}"


NEW = _bump(__version__)


def _release(version: str = NEW, **extra):
    base = "https://github.com/Michel-MichelMichel/FSPassion/releases/download"
    raw = {
        "tag_name": f"v{version}",
        "draft": False,
        "prerelease": False,
        "html_url": f"https://github.com/Michel-MichelMichel/FSPassion/releases/tag/v{version}",
        "published_at": "2026-11-02T10:00:00Z",
        "body": "Nouveautés",
        "assets": [
            {"name": f"FSPassion-{version}-setup.exe", "browser_download_url": f"{base}/v{version}/FSPassion-{version}-setup.exe", "size": 4},
            {"name": f"FSPassion-{version}-portable.zip", "browser_download_url": f"{base}/v{version}/FSPassion-{version}-portable.zip", "size": 4},
            {"name": "SHA256SUMS.txt", "browser_download_url": f"{base}/v{version}/SHA256SUMS.txt", "size": 100},
            {"name": "piege.exe", "browser_download_url": "https://exemple.invalid/piege.exe", "size": 1},
        ],
    }
    raw.update(extra)
    return raw


# --------------------------------------------------------------------------
# Numéros, adresses, publication
# --------------------------------------------------------------------------

def test_version_numbers():
    assert updates.parse_version("v1.2.3") == (1, 2, 3)
    assert updates.parse_version("0.10.0") == (0, 10, 0)
    for bad in ("1.0", "v1.0.0-beta", "latest", None, "1.2.3.4"):
        assert updates.parse_version(bad) is None
    assert updates.is_newer("0.10.0", "0.9.9")
    assert updates.is_newer("v1.0.0", "0.9.6")
    assert not updates.is_newer("0.9.6", "0.9.6")
    assert not updates.is_newer("0.9.5", "0.9.6")
    assert not updates.is_newer("1.0.0-rc1", "0.9.6")


def test_addresses_only_github():
    assert updates.api_url(INFO) == "https://api.github.com/repos/Michel-MichelMichel/FSPassion/releases/latest"
    assert updates.releases_url(INFO) == "https://github.com/Michel-MichelMichel/FSPassion/releases/latest"
    for url in ("http://github.com/a/b", "https://gitlab.com/a/b", "https://github.com/a",
                "https://github.com/a/b/c", "https://user:pw@github.com/a/b", "https://github.com/a/..", None):
        assert updates.api_url({"github_url": url}) is None
    # Le dépôt réel de l'application.
    assert updates.api_url(config.load_app_info()) is not None


def test_parse_release_keeps_only_expected_files():
    rel = updates.parse_release(_release())
    assert rel["version"] == NEW
    assert rel["installer"]["url"].endswith(f"FSPassion-{NEW}-setup.exe")
    assert rel["portable"]["url"].endswith(f"FSPassion-{NEW}-portable.zip")
    assert rel["sums"] is not None
    assert rel["published"] == "2026-11-02"
    assert rel["page"].startswith("https://github.com/")


@pytest.mark.parametrize("extra", [{"draft": True}, {"prerelease": True}, {"tag_name": "nightly"}])
def test_parse_release_refuses_drafts_and_prereleases(extra):
    with pytest.raises(updates.UpdateError) as exc:
        updates.parse_release(_release(**extra))
    assert exc.value.key == "invalid"


def test_parse_release_ignores_foreign_hosts():
    raw = _release()
    raw["assets"][0]["browser_download_url"] = "https://exemple.invalid/setup.exe"
    raw["html_url"] = "https://exemple.invalid/"
    rel = updates.parse_release(raw)
    assert rel["installer"] is None
    assert rel["page"] is None


def test_parse_sums():
    sha = "a" * 64
    text = f"{sha}  FSPassion-{NEW}-setup.exe\n{'b' * 64} *FSPassion-{NEW}-portable.zip\nligne abimee\n"
    sums = updates.parse_sums(text)
    assert sums[f"FSPassion-{NEW}-setup.exe"] == sha
    assert sums[f"FSPassion-{NEW}-portable.zip"] == "b" * 64
    assert len(sums) == 2


def test_redirects_guarded():
    ok = ("github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com")
    assert ok == updates.DOWNLOAD_HOSTS
    assert updates._host_ok("https://objects.githubusercontent.com/x", ok)
    assert not updates._host_ok("http://github.com/x", ok)
    assert not updates._host_ok("https://evil.example/x", ok)
    assert not updates._host_ok("https://github.com:8443/x", ok)
    handler = updates._GuardedRedirect(ok)
    import urllib.error
    import urllib.request

    req = urllib.request.Request("https://github.com/a")
    with pytest.raises(urllib.error.HTTPError):
        handler.redirect_request(req, None, 302, "Found", {}, "https://evil.example/x")


# --------------------------------------------------------------------------
# Téléchargement vérifié
# --------------------------------------------------------------------------

class _Resp(io.BytesIO):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_net(monkeypatch, files: dict[str, bytes]):
    calls = []

    def fake_open(url, hosts, accept):
        calls.append(url)
        if not updates._host_ok(url, hosts):
            raise updates.UpdateError("unreachable")
        for name, data in files.items():
            if url.endswith(name):
                return _Resp(data)
        raise updates.UpdateError("not_found")

    monkeypatch.setattr(updates, "_open", fake_open)
    return calls


def test_download_checks_sha(tmp_path, monkeypatch):
    data = b"MZ fake installer"
    _fake_net(monkeypatch, {"setup.exe": data})
    dest = tmp_path / "setup.exe"
    good = hashlib.sha256(data).hexdigest()
    updates.download("https://github.com/x/setup.exe", dest, 1000, good)
    assert dest.read_bytes() == data
    dest.unlink()
    with pytest.raises(updates.UpdateError) as exc:
        updates.download("https://github.com/x/setup.exe", dest, 1000, "0" * 64)
    assert exc.value.key == "checksum"
    assert not dest.exists() and not (tmp_path / "setup.exe.part").exists()
    with pytest.raises(updates.UpdateError):
        updates.download("https://github.com/x/setup.exe", dest, 4, good)  # trop gros
    assert not dest.exists()


def _updater(tmp_path, enabled=True, events=None):
    return updates.Updater(
        INFO, enabled=lambda: enabled,
        publish=lambda kind, **kw: events.append((kind, kw)) if events is not None else None,
        downloads_dir=lambda: tmp_path / "Downloads",
    )


def test_updater_check_and_install_file(tmp_path, monkeypatch):
    data = b"MZ" + b"\0" * 100
    sha = hashlib.sha256(data).hexdigest()
    sums = f"{sha}  FSPassion-{NEW}-setup.exe\n".encode()
    monkeypatch.setattr(updates, "latest_release", lambda info: updates.parse_release(_release()))
    _fake_net(monkeypatch, {"setup.exe": data, "SHA256SUMS.txt": sums})
    monkeypatch.setattr(updates, "install_kind", lambda: "installed")
    events = []
    up = _updater(tmp_path, events=events)
    st = up.check()
    assert st["available"] and st["latest"]["version"] == NEW and st["can_install"]
    assert st["last_check"] and st["error"] is None
    assert any(k == "update" for k, _ in events)
    path = up.download()
    assert path.name == f"FSPassion-{NEW}-setup.exe"
    assert path.parent == updates.updates_dir()
    assert up.state()["download"]["state"] == "ready"


def test_updater_refuses_without_checksum(tmp_path, monkeypatch):
    raw = _release()
    raw["assets"] = [a for a in raw["assets"] if a["name"] != "SHA256SUMS.txt"]
    monkeypatch.setattr(updates, "latest_release", lambda info: updates.parse_release(raw))
    monkeypatch.setattr(updates, "install_kind", lambda: "installed")
    up = _updater(tmp_path)
    assert not up.check()["can_install"]
    with pytest.raises(updates.UpdateError) as exc:
        up.download()
    assert exc.value.key == "no_checksum"


def test_updater_refuses_non_program(tmp_path, monkeypatch):
    data = b"PK not an exe"
    sha = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(updates, "latest_release", lambda info: updates.parse_release(_release()))
    _fake_net(monkeypatch, {"setup.exe": data, "SHA256SUMS.txt": f"{sha}  FSPassion-{NEW}-setup.exe".encode()})
    monkeypatch.setattr(updates, "install_kind", lambda: "installed")
    up = _updater(tmp_path)
    up.check()
    with pytest.raises(updates.UpdateError):
        up.download()
    assert not (updates.updates_dir() / f"FSPassion-{NEW}-setup.exe").exists()


def test_portable_goes_to_downloads(tmp_path, monkeypatch):
    data = b"PK portable"
    sha = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(updates, "latest_release", lambda info: updates.parse_release(_release()))
    _fake_net(monkeypatch, {"portable.zip": data, "SHA256SUMS.txt": f"{sha}  FSPassion-{NEW}-portable.zip".encode()})
    monkeypatch.setattr(updates, "install_kind", lambda: "portable")
    (tmp_path / "Downloads").mkdir()
    up = _updater(tmp_path)
    up.check()
    assert up.download() == tmp_path / "Downloads" / f"FSPassion-{NEW}-portable.zip"


def test_same_or_older_version_is_up_to_date(tmp_path, monkeypatch):
    monkeypatch.setattr(updates, "latest_release", lambda info: updates.parse_release(_release(__version__)))
    up = _updater(tmp_path)
    st = up.check()
    assert not st["available"] and st["up_to_date"]


def test_errors_are_reported_not_raised(tmp_path, monkeypatch):
    def boom(info):
        raise updates.UpdateError("not_found")

    monkeypatch.setattr(updates, "latest_release", boom)
    up = _updater(tmp_path)
    st = up.check()
    assert st["error"] == "not_found" and not st["available"]


def test_disabled_never_checks(tmp_path, monkeypatch):
    def forbidden(info):
        raise AssertionError("aucune recherche sans accord")

    monkeypatch.setattr(updates, "latest_release", forbidden)
    up = _updater(tmp_path, enabled=False)
    assert not up.check()["enabled"]
    with pytest.raises(updates.UpdateError):
        up.download()


def test_source_mode_never_downloads(tmp_path, monkeypatch):
    monkeypatch.setattr(updates, "latest_release", lambda info: updates.parse_release(_release()))
    up = _updater(tmp_path)
    st = up.check()
    assert st["kind"] == "source" and not st["can_install"]
    with pytest.raises(updates.UpdateError) as exc:
        up.download()
    assert exc.value.key == "unsupported"


def test_old_installers_cleaned(tmp_path):
    folder = updates.updates_dir()
    folder.mkdir(parents=True)
    (folder / "FSPassion-0.0.1-setup.exe").write_bytes(b"MZ")
    updates.clean_old_downloads()
    assert not any(folder.iterdir())


# --------------------------------------------------------------------------
# Cœur, réglages, interface, installeur, textes
# --------------------------------------------------------------------------

def test_setting_on_by_default_and_independent():
    assert config.default_settings()["update_check"] is True
    assert SETTABLE["update_check"] is bool
    core = Core(dev=True, bus=EventBus())
    core.set_settings({"update_check": False})
    assert core.settings.get("internet_access") is True  # catalogue des DLC non touché
    st = core.state()["update"]
    assert st["enabled"] is False
    with pytest.raises(AppError):
        core.update_check()


def test_install_refused_while_game_runs(monkeypatch):
    core = Core(dev=True, bus=EventBus())
    core.monitor.running = {"FS25"}
    with pytest.raises(AppError) as exc:
        core.update_install()
    assert exc.value.key == "settings.updates.error_game_running"


def test_export_keeps_update_choice():
    from fspassion import backup

    assert "update_check" in backup.NEUTRAL


def test_installer_relaunches_after_silent_update():
    iss = (ROOT / "packaging" / "installer.iss").read_text(encoding="utf-8-sig")
    assert "function RelaunchAfterUpdate" in iss
    assert "{param:RELAUNCH|0}" in iss
    assert "Check: RelaunchAfterUpdate" in iss
    src = (ROOT / "src" / "fspassion" / "updates.py").read_text(encoding="utf-8")
    for flag in ("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/RELAUNCH=1", "Wait-Process"):
        assert flag in src


def test_release_file_names_match_build():
    build = (ROOT / "tools" / "build.py").read_text(encoding="utf-8")
    assert 'f"FSPassion-{v}-portable.zip"' in build
    assert 'f"FSPassion-{v}-setup.exe"' in build
    assert '"SHA256SUMS.txt"' in build
    assert updates.installer_name("1.2.3") == "FSPassion-1.2.3-setup.exe"
    assert updates.portable_name("1.2.3") == "FSPassion-1.2.3-portable.zip"


def test_interface_wiring():
    js = (ROOT / "ui" / "js" / "settings.js").read_text(encoding="utf-8")
    assert "group('circle-arrow-up', 'settings.updates.title', buildUpdates(saveSettings), 'set-updates')" in js
    # L'encart est le premier de la page Application.
    app = js[js.index("function buildApp()"):]
    assert app.index("settings.updates.title") < app.index("settings.downloads.title")
    assert (ROOT / "assets" / "icons" / "circle-arrow-up.svg").is_file()
    upd = (ROOT / "ui" / "js" / "updates.js").read_text(encoding="utf-8")
    # Repère discret : jamais de message qui surgit, seulement la cloche.
    assert "noteOnly(" in upd and "toast(" not in upd.replace("toastError(", "")
    assert "markSettingsButton" in (ROOT / "ui" / "js" / "header.js").read_text(encoding="utf-8")
    assert "footerUpdatePill" in (ROOT / "ui" / "js" / "footer.js").read_text(encoding="utf-8")


ERROR_KEYS = ("not_found", "unreachable", "rate_limited", "invalid", "no_source", "checksum", "no_checksum",
              "missing_file", "disabled", "busy", "none", "unsupported", "launch", "game_running")


def test_texts_in_every_language():
    for f in sorted((ROOT / "lang").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        u = d["settings"]["updates"]
        for key in ("title", "allow", "help", "install", "check", "note", "pill", "pill_tip",
                    "how_installed", "how_portable", "how_source"):
            assert u.get(key), (f.name, key)
        for key in ERROR_KEYS:
            assert u.get(f"error_{key}"), (f.name, key)
        assert "{version}" in u["available"] and "{percent}" in u["downloading"]
        assert any("FS Passion" in str(b) and d["settings"]["app"]["title"] in str(b)
                   for b in d["notice"]["blocks"]), f.name
