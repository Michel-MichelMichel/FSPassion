"""Langues (4.16) et absence de texte d'interface écrit en dur (I7)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fspassion import config, i18n

ROOT = Path(__file__).resolve().parents[1]


def flat_keys(node, prefix=""):
    keys = set()
    for k, v in node.items():
        if k == "_meta":
            continue
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict) and not ("other" in v and set(v) <= {"zero", "one", "two", "few", "many", "other"}):
            keys |= flat_keys(v, full)
        else:
            keys.add(full)
    return keys


def load(code):
    return json.loads((ROOT / "lang" / f"{code}.json").read_text(encoding="utf-8"))


def test_fr_and_en_have_same_keys():
    fr, en = flat_keys(load("fr")), flat_keys(load("en"))
    assert fr - en == set(), "clés absentes de en.json"
    assert en - fr == set(), "clés absentes de fr.json"


def test_meta():
    for code in ("fr", "en"):
        meta = load(code)["_meta"]
        assert meta["code"] == code and meta["name"]
        # Les drapeaux des langues ont été supprimés en 0.1.1 : le menu ne montre que les noms.
        assert "flags" not in meta


def _js_keys():
    """Clés de langue utilisées par l'interface (appels t('…') et attributs)."""
    keys = set()
    pattern = re.compile(r"""(?:\bt\(|data-i18n-tip['"]?:\s*|soon\([^,]+,\s*|blocks\()['"]([a-z0-9_]+(?:\.[A-Za-z0-9_]+)+)['"]""")
    for js in (ROOT / "ui" / "js").glob("*.js"):
        for m in pattern.finditer(js.read_text(encoding="utf-8")):
            keys.add(m.group(1))
    return keys


def _py_keys():
    keys = set()
    pattern = re.compile(r"""["']((?:path|library\.error|launch|error|detect)\.[a-z_.]+)["']""")
    for py in (ROOT / "src" / "fspassion").glob("*.py"):
        for m in pattern.finditer(py.read_text(encoding="utf-8")):
            keys.add(m.group(1))
    return keys


def test_all_used_keys_exist():
    strings = load("en")

    def exists(key):
        node = strings
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True

    used = _js_keys() | _py_keys()
    assert len(used) > 80
    missing = sorted(k for k in used if not exists(k))
    assert missing == []


def test_no_hardcoded_ui_text():
    """I7 : aucun texte d'interface écrit en dur dans le JavaScript.

    Seuls les noms propres (logo, marques) sont admis.
    """
    allowed = {"FS", "Passion", "GitHub", "Buy Me a Coffee", "Stripe", "FS Passion"}
    pattern = re.compile(r"""\btext:\s*['"]([^'"]+)['"]""")
    for js in (ROOT / "ui" / "js").glob("*.js"):
        for m in pattern.finditer(js.read_text(encoding="utf-8")):
            assert m.group(1) in allowed, f"{js.name}: {m.group(1)!r}"


def test_user_language_override_and_limits(monkeypatch):
    folder = i18n.ensure_user_lang_folder()
    assert (folder / "_modele_en.json").is_file()  # modèle copié, jamais chargé comme langue
    # Une langue personnelle nommée par l'utilisateur
    eu = {"_meta": {"code": "eu", "name": "Euskara"}, "list1": {"title": "Mod guztiak"}}
    (folder / "eu.json").write_text(json.dumps(eu), encoding="utf-8")
    # Correction d'une langue fournie (même code)
    frfix = {"_meta": {"code": "fr", "name": "Français (corrigé)"}, "list1": {"title": "Tous mes mods"}}
    (folder / "fr-perso.json").write_text(json.dumps(frfix), encoding="utf-8")
    # Fichier invalide (contient un nombre) et fichier trop gros
    (folder / "bad.json").write_text(json.dumps({"_meta": {"code": "xx", "name": "X"}, "a": 1}), encoding="utf-8")
    (folder / "big.json").write_text(json.dumps({"_meta": {"code": "yy", "name": "Y"}, "a": "x" * (i18n.MAX_USER_LANG_BYTES + 10)}), encoding="utf-8")

    langs = i18n.Languages()
    codes = {lang["code"]: lang for lang in langs.available()}
    assert codes["eu"]["name"] == "Euskara" and codes["eu"]["personal"]
    assert codes["fr"]["personal"]
    assert langs.strings("eu")["list1"]["title"] == "Mod guztiak"
    assert langs.strings("eu")["list1"]["search"] == load("en")["list1"]["search"]  # repli anglais
    assert langs.strings("fr")["list1"]["title"] == "Tous mes mods"
    assert langs.strings("fr")["list1"]["search"] == load("fr")["list1"]["search"]
    rejected = {r["file"] for r in langs.rejected}
    assert rejected == {"bad.json", "big.json"}
    assert "list1.search" in langs.missing_keys("eu")


def test_lang_file_meta_must_be_text(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"_meta": {"code": ["fr"], "name": "X"}}), encoding="utf-8")
    assert i18n._read_lang_file(p, None) == (None, "no_meta")  # une liste ferait planter le chargement


def test_best_match():
    langs = i18n.Languages()
    assert langs.best_match("fr-FR") == "fr"
    assert langs.best_match("fr-CA") == "fr"
    assert langs.best_match("en-US") == "en"
    assert langs.best_match("de-DE") == "de"  # 0.9.2 : traduit
    assert langs.best_match("pt-PT") == "pt-PT"  # 0.9.3 : traduit
    assert langs.best_match("pt-BR") == "pt-BR"
    assert langs.best_match("nn-NO") == "nb"  # nynorsk : bokmål
    assert langs.best_match("cs-CZ") == "cs"
    assert langs.best_match("es-MX") == "es"
    assert langs.best_match("ja-JP") == "en"  # pas encore traduit : anglais
    assert langs.best_match(None) == "en"


def test_lang_dir_location():
    assert config.user_lang_dir().name == "lang"
