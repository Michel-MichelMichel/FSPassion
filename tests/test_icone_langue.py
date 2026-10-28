"""0.9.5 : icône Langue devant la liste, bienvenue agrandie, README (langues à venir, corrections)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_language_icon_is_before_the_list_button():
    js = _read("ui", "js", "settings.js")
    sel = js.split("export function languageSelect(onPick)", 1)[1].split("\n}\n", 1)[0]
    btn = sel.split("const btn =", 1)[1].split(";\n", 1)[0]
    assert "icon('languages'" not in btn
    assert "h('div', { class: 'lang-select' }, icon('languages', 'lang-select-ico'), box)" in sel


def test_welcome_uses_the_same_language_select():
    js = _read("ui", "js", "welcome.js")
    css = _read("ui", "css", "dialogs.css")
    assert "languageSelect(" in js and "languageList(" not in js
    assert js.index("welcome-logo") < js.index("languageSelect(") < js.index("welcome.subtitle") < js.index("common.ok")
    assert ".dlg-welcome { width: 820px; overflow: visible; }" in css
    assert ".welcome-top { display: flex;" in css


def test_readme_announces_languages_and_explains_corrections():
    md = _read("README.md")
    assert "Coming soon: 12 more languages" in md
    for name in ("Magyar", "Русский", "日本語", "한국어", "简体中文", "繁體中文", "Español (Latinoamérica)"):
        assert name in md
    assert "## Help improve the translations" in md
    assert "%APPDATA%\\FSPassion\\lang\\" in md and "data\\lang\\" in md


def test_personal_language_limit_allows_non_latin_copies():
    from fspassion import i18n

    assert i18n.MAX_USER_LANG_BYTES >= 300 * 1024
