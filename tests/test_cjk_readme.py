"""0.9.4 : polices CJK (Sarasa Gothic réduite et renommée), README illustré."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "assets" / "fonts"
sys.path.insert(0, str(ROOT / "tools"))

TTFont = pytest.importorskip("fontTools.ttLib").TTFont

import build_cjk_fonts  # noqa: E402


def test_cjk_fonts_are_declared_for_their_language():
    css = (ROOT / "ui" / "css" / "base.css").read_text(encoding="utf-8")
    for filename, lang, family in build_cjk_fonts.VARIANTS.values():
        assert f'url("/assets/fonts/{filename}")' in css
        assert re.search(rf':root:lang\({re.escape(lang)}\)[^{{]*\{{\s*--font-cjk: "{family}"', css), lang
    assert "var(--font-cjk)" in css.split("--font-ui:")[1].split(";")[0]


@pytest.mark.parametrize("variant", list(build_cjk_fonts.VARIANTS))
def test_cjk_font_is_renamed_and_covers_its_language(variant):
    filename, lang, family = build_cjk_fonts.VARIANTS[variant]
    path = FONTS / filename
    assert path.is_file(), f"lancer tools/build_cjk_fonts.py ({filename} manquant)"
    font = TTFont(path)
    names = {n.nameID: str(n) for n in font["name"].names}
    assert names[1] == family
    # Licence OFL : le nom réservé « Source » ne doit plus apparaître
    for name_id in (1, 3, 4, 6, 16, 17):
        assert "Source" not in names.get(name_id, "")
        assert "Sarasa" not in names.get(name_id, "")
    cmap = font.getBestCmap()
    missing = sorted(build_cjk_fonts.text_charset(lang) - set(cmap))
    assert not missing, f"{lang} : relancer tools/build_cjk_fonts.py ({''.join(map(chr, missing[:20]))})"
    assert len(cmap) > 2000
    assert path.stat().st_size < 1_500_000


def test_sarasa_licence_and_credits():
    licence = (FONTS / "OFL-Sarasa.txt").read_text(encoding="utf-8")
    assert "SIL Open Font License, Version 1.1" in licence and "SIL Open Font License v1.1" in licence
    assert "Reserved Font Name 'Source'" in licence
    for readme in (ROOT / "README.md", ROOT / "readme" / "README.fr.md"):
        assert "OFL-Sarasa.txt" in readme.read_text(encoding="utf-8")


def test_readmes_show_the_logo_and_the_languages():
    count = len(list((ROOT / "lang").glob("*.json")))
    main = (ROOT / "README.md").read_text(encoding="utf-8")
    assert 'src="assets/FS_Passion_logo/Final_grand.png"' in main
    assert f"interface in {count} languages" in main
    assert "French and English" not in main
    assert (ROOT / "assets" / "FS_Passion_logo" / "Final_grand.png").is_file()
    for path in (ROOT / "readme").glob("README.*.md"):
        text = path.read_text(encoding="utf-8")
        assert 'src="../assets/FS_Passion_logo/Final_grand.png"' in text, path.name
        assert re.search(rf"(?<!\d){count}(?!\d)", text), path.name


def test_readme_translations_are_up_to_date():
    import readme_translations as rt

    for code, data in rt.T.items():
        path = ROOT / "readme" / f"README.{code}.md"
        assert path.read_text(encoding="utf-8") == rt.render(code, data), (
            f"{path.name} : relancer tools/readme_translations.py"
        )


def test_lang_metadata_names_every_language():
    names = [json.loads(p.read_text(encoding="utf-8"))["_meta"]["name"] for p in (ROOT / "lang").glob("*.json")]
    import readme_translations as rt

    assert sorted(rt.ui_languages()) == sorted(names)


def test_translations_follow_the_english_structure():
    """Chaque README traduit suit README.md : même nombre de sections, mêmes points,
    point « Langues » avec les langues à venir, lien d'aide, point SignPath et liens
    vers toutes les langues (le français est rédigé à la main et doit suivre aussi)."""
    import readme_translations as rt

    en = (ROOT / "README.md").read_text(encoding="utf-8")
    en_sections = [ln for ln in en.splitlines() if ln.startswith("## ")]
    en_bullets = [ln for ln in en.split("\n## ", 1)[0].splitlines() if ln.startswith("- ")]
    ui = {json.loads(p.read_text(encoding="utf-8"))["_meta"]["code"] for p in (ROOT / "lang").glob("*.json")}
    assert set(rt.SOON) == set(rt.NAMES) - ui
    for path in sorted((ROOT / "readme").glob("README.*.md")):
        text = path.read_text(encoding="utf-8")
        head, _, _ = text.partition("\n## ")
        sections = [ln for ln in text.splitlines() if ln.startswith("## ")]
        # Les traductions résument « For developers » et renvoient au README anglais ; le français le garde.
        expected = len(en_sections) if path.name == "README.fr.md" else len(en_sections) - 1
        assert len(sections) == expected, path.name
        bullets = [ln for ln in head.splitlines() if ln.startswith("- ")]
        assert len(bullets) == len(en_bullets), path.name
        languages = bullets[8]  # le point « Langues » suit les huit premiers points, comme dans README.md
        assert re.search(rf"(?<!\d){len(rt.SOON)}(?!\d)", languages), path.name
        assert all(rt.NAMES[c] in languages for c in rt.SOON), path.name
        assert "help-improve-the-translations" in text, path.name
        assert "SignPath" in text, path.name
        own = path.name[len("README."):-len(".md")]
        assert all(f"README.{c}.md" in text for c in rt.NAMES if c != own), path.name
        assert "{" not in text, path.name
