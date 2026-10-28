"""Arguments de lancement (0.3, 0.4) : -restart / -skipStartVideos, -cheats, game.xml, plateformes."""

from fspassion import gamesettings, launcher


def test_skip_argument_depends_on_version():
    assert launcher.launch_args("FS19", {"skip_start_videos": True}) == ["-restart"]
    assert launcher.launch_args("FS2011", {"skip_start_videos": True}) == ["-restart"]
    assert launcher.launch_args("FS2013", {"skip_start_videos": True}) == ["-restart"]
    assert launcher.launch_args("FS15", {"skip_start_videos": True}) == ["-restart"]
    assert launcher.launch_args("FS25", {"skip_start_videos": True}) == ["-skipStartVideos"]
    assert launcher.launch_args("FS17", {"skip_start_videos": True}) == ["-restart"]
    assert launcher.launch_args("FS22", {"skip_start_videos": True}) == ["-skipStartVideos"]


def test_cheats_and_no_options():
    assert launcher.launch_args("FS25", {"cheats": True}) == ["-cheats"]
    assert launcher.launch_args("FS25", {"skip_start_videos": True, "cheats": True}) == [
        "-skipStartVideos", "-cheats"]
    assert launcher.launch_args("FS25", {}) == []
    assert launcher.launch_args("FS25", None) == []


def test_steam_uri_receives_arguments():
    uri = "steam://rungameid/1234"
    assert launcher.steam_uri_with_args(uri, ["-skipStartVideos", "-cheats"]) == \
        "steam://run/1234//-skipStartVideos%20-cheats/"
    assert launcher.steam_uri_with_args(uri, []) is None
    assert launcher.steam_uri_with_args("com.epicgames.launcher://apps/x", ["-cheats"]) is None


def test_game_xml_controls_switched_to_true(tmp_path):
    f = tmp_path / "game.xml"
    original = (
        '<?xml version="1.0" encoding="utf-8" standalone="no" ?>\r\n'
        "<game>\r\n"
        "    <development>\r\n"
        "        <controls>false</controls>\r\n"
        "    </development>\r\n"
        "</game>\r\n"
    )
    f.write_bytes(original.encode("utf-8"))
    assert gamesettings.enable_development_controls(f) == "changed"
    new = f.read_bytes().decode("utf-8")
    assert new == original.replace("<controls>false</controls>", "<controls>true</controls>")
    assert (tmp_path / "game.xml.bak").read_bytes() == original.encode("utf-8")
    assert gamesettings.enable_development_controls(f) == "unchanged"


def test_game_xml_bom_kept_and_missing_cases(tmp_path):
    f = tmp_path / "game.xml"
    f.write_bytes(b"\xef\xbb\xbf<game><development><controls>false</controls></development></game>")
    assert gamesettings.enable_development_controls(f) == "changed"
    assert f.read_bytes().startswith(b"\xef\xbb\xbf")
    assert b"<controls>true</controls>" in f.read_bytes()

    f.write_bytes(b"<game><other/></game>")
    assert gamesettings.enable_development_controls(f) == "absent"
    assert gamesettings.enable_development_controls(tmp_path / "missing.xml") == "absent"


def test_args_route_by_platform():
    steam = {"platform": "steam", "uri": "steam://rungameid/1234"}
    epic = {"platform": "epic", "uri": "com.epicgames.launcher://apps/x?action=launch&silent=true"}
    store = {"platform": "xbox", "uri": "shell:AppsFolder\\x!App"}
    assert launcher.args_mode("auto", steam) == "steam"
    assert launcher.args_mode("auto", epic) == "epic"
    assert launcher.args_mode("auto", store) == "unsupported"
    assert launcher.args_mode("auto", {"platform": "xbox", "uri": None}) == "command"
    assert launcher.args_mode("auto", {"platform": "steam_dependent", "uri": None}) == "command"
    assert launcher.args_mode("exe", steam) == "command"
    assert launcher.args_text(["-restart", "-cheats"]) == "-restart -cheats"


def test_steam_launch_never_sends_arguments(tmp_path, monkeypatch):
    """Steam demande de confirmer à chaque lancement des arguments venus d'un autre
    programme : le jeu est lancé par son adresse simple (0.4)."""
    exe = tmp_path / "FarmingSimulator2025.exe"
    exe.write_bytes(b"MZ")
    started = []
    monkeypatch.setattr(launcher, "_start", lambda target, cwd=None, args=None: started.append((target, args)) or True)
    cfg = {"game_exe": str(exe), "launch_method": "auto", "launch_args": {"skip_start_videos": True, "cheats": True}}
    res = launcher.launch("FS25", cfg, {"platform": "steam", "uri": "steam://rungameid/2300320"})
    assert res["ok"] and res["args_mode"] == "steam"
    assert started == [("steam://rungameid/2300320", None)]
    started.clear()
    res = launcher.launch("FS25", cfg, {"platform": "exe", "uri": None})
    assert started == [(str(exe), ["-skipStartVideos", "-cheats"])]
    assert res["args_mode"] == "command"


def test_development_controls_state(tmp_path):
    f = tmp_path / "game.xml"
    assert gamesettings.development_controls(f) is None
    f.write_text("<game><development><controls>false</controls></development></game>")
    assert gamesettings.development_controls(f) is False
    gamesettings.enable_development_controls(f)
    assert gamesettings.development_controls(f) is True
