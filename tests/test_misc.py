"""Réglages, anomalies, DLC, journaux."""

from __future__ import annotations

import json

from fspassion import anomalies, config, dlc, fsutil, logs, versions


def test_settings_defaults_and_corruption(tmp_path):
    s = config.Settings(tmp_path / "settings.json")
    assert s.get("theme") == "gruvbox-light" and s.get("language") is None
    s.update_version("FS25", {"mods_dir": "D:/Mods"})
    s2 = config.Settings(tmp_path / "settings.json")
    assert s2.version("FS25")["mods_dir"] == "D:/Mods"
    assert s2.version("FS25")["launch_method"] == "auto"
    # Fichier corrompu : mis de côté, valeurs par défaut, jamais de plantage
    (tmp_path / "settings.json").write_text("{ pas du json", encoding="utf-8")
    s3 = config.Settings(tmp_path / "settings.json")
    assert s3.get("theme") == "gruvbox-light"
    assert list(tmp_path.glob("settings.json.illisible-*"))


def test_settings_not_overwritten_when_set_aside_fails(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text("{ pas du json", encoding="utf-8")

    def refuse(self, target):
        raise OSError("verrouillé")

    monkeypatch.setattr(type(path), "replace", refuse)
    s = config.Settings(path)
    s.update_version("FS25", {"mods_dir": "D:/Mods"})  # tentative d'enregistrement
    assert path.read_text(encoding="utf-8") == "{ pas du json"  # le fichier illisible reste en place


def test_atomic_write(tmp_path):
    p = tmp_path / "a" / "b.json"
    fsutil.atomic_write_json(p, {"x": "é"})
    assert json.loads(p.read_text(encoding="utf-8")) == {"x": "é"}
    assert [f.name for f in p.parent.iterdir()] == ["b.json"]  # aucun fichier temporaire laissé


def test_mod_names():
    assert anomalies.is_valid_mod_name("FS25_Hof_Bergmann2")
    assert not anomalies.is_valid_mod_name("FS25_Hof Bergmann")
    assert not anomalies.is_valid_mod_name("FS25_Rénové")
    assert not anomalies.is_valid_mod_name("FS25_X\n")  # un saut de ligne final n'est pas toléré
    assert anomalies.suggest_name("FS25_Tracteur Rénové (1)") == "FS25_Tracteur_Renove"
    assert anomalies.suggest_name("FS25_Großer-Hof") == "FS25_Grosser_Hof"


def test_anomaly_visibility():
    items = [anomalies.make("A1", "a.rar", 0), anomalies.make("A4", "Dossier", 0), anomalies.make("A4", "Autre", 0)]
    vis = anomalies.visible(items, ["A1"], ["dossier"])
    assert [a["name"] for a in vis] == ["Autre"]
    assert anomalies.key_of(items[0]) == "A1|0|a.rar"


def test_dlc_prettify_and_catalog(tmp_path):
    assert dlc.prettify("skyAgriculturePack") == "Sky Agriculture Pack"
    assert dlc.prettify("FS19_claasDominator108SL") == "Claas Dominator108 SL"
    folder = tmp_path / "pdlc"
    folder.mkdir()
    (folder / "vredoPack.dlc").write_bytes(b"x")
    (folder / "beansAndAlpacasExpansion.dlc").write_bytes(b"x")  # DLC annoncé : mots-clés
    (folder / "brandNewPack.dlc").write_bytes(b"x")
    (folder / "readme.txt").write_text("x")
    other = tmp_path / "pdlc2"
    other.mkdir()
    (other / "VREDOPACK.dlc").write_bytes(b"x")  # même DLC aux deux endroits
    items = dlc.scan_dlc(versions.require("FS25"), [folder, other])
    ids = [d["id"] for d in items if d["present"]]
    assert ids == ["beansAndAlpacasExpansion", "brandNewPack", "vredoPack"]
    by = {d["id"]: d for d in items}
    assert by["vredoPack"]["known"]
    assert by["beansAndAlpacasExpansion"]["known"]  # trouvé par mots-clés
    assert not by["brandNewPack"]["known"] and by["brandNewPack"]["names"]["_"] == "Brand New Pack"


def test_log_anonymization(monkeypatch):
    monkeypatch.setenv("USERPROFILE", "C:\\Users\\Utilisateur")
    assert logs.anonymize("Fichier C:\\Users\\Utilisateur\\Documents\\x") == "Fichier %USERPROFILE%\\Documents\\x"
    assert logs.anonymize("c:/users/utilisateur/AppData") == "%USERPROFILE%/AppData"


def test_human_size():
    assert fsutil.human_size(512) == {"value": 512, "unit": "B"}
    assert fsutil.human_size(3 * 1024 * 1024)["unit"] == "MB"


def test_dlc_wiki_names_and_profarm(tmp_path):
    """0.2.1 : noms du wiki (sans « Farming Simulator 11 - »), priorité au catalogue
    même pour un .zip, et règle « profarm » de FS2011."""
    import fakemods

    folder = tmp_path / "pdlc2.1"
    fakemods.make_dlc(folder, ["dlcPack3.dlc", "ProFarm_Pack1.dlc", "proFARMsomething.zip"])
    items = {d["id"]: d for d in dlc.scan_dlc(versions.require("FS2011"), [folder])}
    assert items["dlcPack3"]["names"]["_"] == "Trailers and Glasshouse Pack (DLC 3)"
    assert items["ProFarm_Pack1"]["names"]["_"] == "ProFarm1"
    assert items["proFARMsomething"]["names"]["_"] == "ProFarm1"  # le catalogue l'emporte sur le modDesc
    folder15 = tmp_path / "pdlc15"
    fakemods.make_dlc(folder15, ["FS15_newHollandLoaderPack.zip"])
    items = dlc.scan_dlc(versions.require("FS15"), [folder15])
    assert items[0]["names"]["_"] == "New Holland Loader Pack (Free)"


def test_tray_settings_and_fallback():
    """0.2.1 : réglages de la zone de notification ; hors Windows (ou sans
    pystray), l'icône n'est pas créée et la croix quitte comme avant."""
    from fspassion.core import Core
    from fspassion.events import EventBus
    from fspassion.tray import Tray

    core = Core(dev=True, bus=EventBus())
    assert core.settings.get("close_to_tray") is True
    assert core.settings.get("focus_after_game") is True
    res = core.set_settings({"close_to_tray": False, "focus_after_game": False})
    assert res["close_to_tray"] is False and res["focus_after_game"] is False
    assert core.state()["app"]["tray"] is False
    texts = core.tray_texts()
    assert texts["show"] and texts["quit"] and texts["hint"]
    tray = Tray(core.tray_texts, lambda: None, lambda: None)
    if not tray.start():
        assert tray.active is False
    tray.stop()


def test_web_links_from_app_info():
    """0.6.5 : seules les adresses d'app_info.json s'ouvrent, en https et sur leur domaine."""
    from fspassion import config

    info = config.load_app_info()
    assert config.web_link(info, "github") == info["github_url"]
    assert config.web_link(info, "buymeacoffee") == info["donations"]["buymeacoffee"]
    assert config.web_link(info, "stripe") == info["donations"]["stripe"]
    assert "paypal" not in info["donations"]
    assert config.web_link(info, "paypal") is None
    for key in ("github", "buymeacoffee", "stripe"):
        assert config.web_link(info, key).startswith("https://")


def test_web_link_rejects_other_addresses():
    from fspassion import config

    def info(url):
        return {"github_url": url, "donations": {"stripe": url}}

    for bad in ("http://github.com/x", "https://github.com.evil.example/x", "https://evil.example/github.com",
                "file:///C:/Windows", "https://user@github.com/x", "https://github.com:444/x", None, 3):
        assert config.web_link(info(bad), "github") is None, bad
    assert config.web_link(info("https://github.com/x"), "stripe") is None  # mauvais domaine pour Stripe
    assert config.web_link(info("https://donate.stripe.com/abc"), "stripe") == "https://donate.stripe.com/abc"
    assert config.web_link(info("https://github.com/x"), "inconnu") is None
