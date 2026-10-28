"""0.7.1 : reconnaissance des exécutables de Farming Simulator 2013 (version 64 bits
livrée sous le nom FarmingSimulator2013_64bit.exe, et le lanceur FarmingSimulator2013.exe)."""

from pathlib import Path

from fspassion import detect, versions


def test_fs2013_accepts_64bit_and_launcher_exe():
    v = versions.get("FS2013")
    assert v is not None
    assert "farmingsimulator2013_64bit.exe" in v.exe_names
    assert "farmingsimulator2013.exe" in v.exe_names
    assert "farmingsimulator2013game.exe" in v.exe_names


def test_fs2013_64bit_exe_identifies_the_version():
    found = detect.version_of_exe(Path("D:/Farming Simulator 2013/FarmingSimulator2013_64bit.exe"))
    assert found is not None
    assert found.id == "FS2013"
